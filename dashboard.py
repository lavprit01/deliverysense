# dashboard.py

import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

# CONFIG (match load_data.py)

DB_USER = "postgres"
DB_PASSWORD = quote_plus(os.getenv("DB_PASSWORD"))
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "deliverysense"

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    connect_args={"sslmode": "require"}
)

st.set_page_config(
    page_title="DeliverySense",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# CUSTOM STYLING

st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .kpi-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        text-align: left;
    }
    .kpi-label {
        font-size: 0.85rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.3rem;
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        color: #f9fafb;
    }
    .kpi-sub {
        font-size: 0.8rem;
        color: #6b7280;
        margin-top: 0.2rem;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: #f9fafb;
        margin-top: 2rem;
        margin-bottom: 0.3rem;
        border-left: 4px solid #6366f1;
        padding-left: 0.7rem;
    }
    .section-sub {
        font-size: 0.9rem;
        color: #9ca3af;
        margin-bottom: 1rem;
        padding-left: 0.9rem;
    }
    .insight-box {
        background-color: #1e293b;
        border-left: 3px solid #f59e0b;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        font-size: 0.9rem;
        color: #e5e7eb;
        margin-top: 0.6rem;
    }
</style>
""", unsafe_allow_html=True)



@st.cache_data(ttl=3600)
def load_status_breakdown():
    query = """
        SELECT order_status, COUNT(*) AS num_orders,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
        FROM orders
        GROUP BY order_status
        ORDER BY num_orders DESC;
    """
    return pd.read_sql(query, engine)

@st.cache_data(ttl=3600)
def load_delay_by_state():
    query = """
        SELECT
            c.customer_state,
            COUNT(*) AS num_orders,
            ROUND(AVG(EXTRACT(DAY FROM (o.order_delivered_customer_date - o.order_estimated_delivery_date))), 2) AS avg_delay_days,
            ROUND(100.0 * SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_late
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_status = 'delivered'
        GROUP BY c.customer_state
        ORDER BY avg_delay_days DESC;
    """
    return pd.read_sql(query, engine)

@st.cache_data(ttl=3600)
def load_delay_by_category():
    query = """
        SELECT
            p.product_category_name,
            COUNT(*) AS num_orders,
            ROUND(AVG(EXTRACT(DAY FROM (o.order_delivered_customer_date - o.order_estimated_delivery_date))), 2) AS avg_delay_days,
            ROUND(100.0 * SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_late
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        WHERE o.order_status = 'delivered'
        GROUP BY p.product_category_name
        HAVING COUNT(*) > 50
        ORDER BY avg_delay_days DESC
        LIMIT 15;
    """
    return pd.read_sql(query, engine)

@st.cache_data(ttl=3600)
def load_review_vs_delay():
    query = """
        SELECT
            CASE
                WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 'Late'
                ELSE 'On Time or Early'
            END AS delivery_status,
            COUNT(*) AS num_orders,
            ROUND(AVG(r.review_score), 2) AS avg_review_score
        FROM orders o
        JOIN order_reviews r ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered'
          AND o.order_delivered_customer_date IS NOT NULL
        GROUP BY delivery_status;
    """
    return pd.read_sql(query, engine)

@st.cache_data(ttl=3600)
def load_geo_root_cause():
    query = """
        SELECT
            CASE
                WHEN s.seller_state = c.customer_state THEN 'Same State'
                ELSE 'Different State'
            END AS seller_customer_match,
            COUNT(*) AS num_orders,
            ROUND(AVG(EXTRACT(DAY FROM (o.order_delivered_customer_date - o.order_estimated_delivery_date))), 2) AS avg_delay_days,
            ROUND(100.0 * SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_late
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN sellers s ON oi.seller_id = s.seller_id
        WHERE o.order_status = 'delivered'
        GROUP BY seller_customer_match;
    """
    return pd.read_sql(query, engine)

@st.cache_data(ttl=3600)
def load_overall_kpis():
    query = """
        SELECT
            COUNT(*) AS total_delivered,
            ROUND(100.0 * SUM(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_late,
            ROUND(AVG(EXTRACT(DAY FROM (order_delivered_customer_date - order_estimated_delivery_date))), 2) AS avg_delay_days
        FROM orders
        WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL;
    """
    return pd.read_sql(query, engine)


# SIDEBAR

with st.sidebar:
    st.markdown("## 📦 DeliverySense")
    st.caption("Delivery Funnel and Root Cause Analytics")
    st.markdown("---")
    st.markdown("**Dataset:** Olist Brazilian E-Commerce")
    st.markdown("**Author:** Lavprit Anand")
    st.markdown("---")
    section = st.radio(
        "Jump to section",
        ["Overview", "Regional Analysis", "Category Analysis", "Customer Impact", "Root Cause"],
    )
    st.markdown("---")
    


# HEADER

st.title("📦 DeliverySense")
st.markdown(
    "Where in the delivery journey do customers face the most friction, and why. "
    "An end to end funnel and root cause analysis built on the Olist dataset."
)

kpi_df = load_overall_kpis()
total_orders = int(kpi_df["total_delivered"].iloc[0])
pct_late = kpi_df["pct_late"].iloc[0]
avg_delay = kpi_df["avg_delay_days"].iloc[0]

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Delivered Orders</div>
            <div class="kpi-value">{total_orders:,}</div>
            <div class="kpi-sub">Total analyzed</div>
        </div>
    """, unsafe_allow_html=True)
with k2:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Late Deliveries</div>
            <div class="kpi-value">{pct_late}%</div>
            <div class="kpi-sub">Of all delivered orders</div>
        </div>
    """, unsafe_allow_html=True)
with k3:
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Avg Delay</div>
            <div class="kpi-value">{avg_delay}d</div>
            <div class="kpi-sub">Vs estimated delivery date</div>
        </div>
    """, unsafe_allow_html=True)
with k4:
    review_df = load_review_vs_delay()
    late_row = review_df[review_df["delivery_status"] == "Late"]
    ontime_row = review_df[review_df["delivery_status"] == "On Time or Early"]
    gap = None
    if not late_row.empty and not ontime_row.empty:
        gap = round(ontime_row["avg_review_score"].iloc[0] - late_row["avg_review_score"].iloc[0], 2)
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Review Score Gap</div>
            <div class="kpi-value">{gap if gap is not None else "N/A"}</div>
            <div class="kpi-sub">On time vs late deliveries</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")


# COLOR THEME FOR CHARTS

PRIMARY_COLOR = "#6366f1"
ACCENT_COLOR = "#f59e0b"
GOOD_COLOR = "#10b981"
BAD_COLOR = "#ef4444"

plotly_template = "plotly_dark"


# SECTION 1: OVERVIEW (funnel)

if section == "Overview":
    st.markdown('<div class="section-header">Order Status Funnel</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Where orders sit across the lifecycle, from creation to delivery</div>', unsafe_allow_html=True)

    df1 = load_status_breakdown()
    fig1 = px.funnel(
        df1.sort_values("num_orders", ascending=False),
        x="num_orders",
        y="order_status",
        template=plotly_template,
        color_discrete_sequence=[PRIMARY_COLOR],
    )
    fig1.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig1, use_container_width=True)

    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.dataframe(df1, use_container_width=True, hide_index=True)
    with col_b:
        top_status = df1.iloc[0]
        st.markdown(f"""
            <div class="insight-box">
            <b>Insight:</b> {top_status['order_status'].title()} accounts for {top_status['pct_of_total']}%
            of all orders. Any status outside "delivered" represents a funnel drop off worth investigating
            further, especially "canceled" and "unavailable".
            </div>
        """, unsafe_allow_html=True)


# SECTION 2: REGIONAL ANALYSIS

elif section == "Regional Analysis":
    st.markdown('<div class="section-header">Delivery Delay by Customer State</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Which regions of Brazil experience the worst delivery delays</div>', unsafe_allow_html=True)

    df3 = load_delay_by_state()
    df3["status"] = df3["avg_delay_days"].apply(lambda x: "Late on average" if x > 0 else "Early on average")

    fig3 = px.bar(
        df3,
        x="customer_state",
        y="avg_delay_days",
        color="status",
        color_discrete_map={"Late on average": BAD_COLOR, "Early on average": GOOD_COLOR},
        template=plotly_template,
        labels={"avg_delay_days": "Avg Delay (days)", "customer_state": "State"},
    )
    fig3.update_layout(height=450, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig3, use_container_width=True)

    tab1, tab2 = st.tabs(["Data Table", "% Late by State"])
    with tab1:
        st.dataframe(df3, use_container_width=True, hide_index=True)
    with tab2:
        fig3b = px.bar(
            df3.sort_values("pct_late", ascending=False),
            x="customer_state",
            y="pct_late",
            template=plotly_template,
            color_discrete_sequence=[ACCENT_COLOR],
            labels={"pct_late": "% of Orders Late", "customer_state": "State"},
        )
        fig3b.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig3b, use_container_width=True)

    worst_state = df3.iloc[0]
    st.markdown(f"""
        <div class="insight-box">
        <b>Insight:</b> {worst_state['customer_state']} has the highest average delay at
        {worst_state['avg_delay_days']} days, with {worst_state['pct_late']}% of orders arriving late.
        This points to a regional logistics gap rather than a platform-wide issue.
        </div>
    """, unsafe_allow_html=True)


# SECTION 3: CATEGORY ANALYSIS

elif section == "Category Analysis":
    st.markdown('<div class="section-header">Delivery Delay by Product Category</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Top 15 categories ranked by average delay, minimum 50 orders</div>', unsafe_allow_html=True)

    df4 = load_delay_by_category()
    fig4 = px.bar(
        df4.sort_values("avg_delay_days"),
        x="avg_delay_days",
        y="product_category_name",
        orientation="h",
        template=plotly_template,
        color="avg_delay_days",
        color_continuous_scale=["#10b981", "#f59e0b", "#ef4444"],
        labels={"avg_delay_days": "Avg Delay (days)", "product_category_name": "Category"},
    )
    fig4.update_layout(height=560, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
    st.plotly_chart(fig4, use_container_width=True)

    st.dataframe(df4, use_container_width=True, hide_index=True)

    worst_cat = df4.iloc[0]
    st.markdown(f"""
        <div class="insight-box">
        <b>Insight:</b> "{worst_cat['product_category_name']}" is the slowest category to deliver,
        averaging {worst_cat['avg_delay_days']} days of delay across {worst_cat['num_orders']} orders.
        Categories like this are strong candidates for dedicated fulfillment review.
        </div>
    """, unsafe_allow_html=True)


# SECTION 4: CUSTOMER IMPACT

elif section == "Customer Impact":
    st.markdown('<div class="section-header">Review Score: Late vs On Time Deliveries</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Quantifying how delivery delay affects customer satisfaction</div>', unsafe_allow_html=True)

    df5 = load_review_vs_delay()
    col1, col2 = st.columns([1, 1])
    with col1:
        fig5 = px.bar(
            df5,
            x="delivery_status",
            y="avg_review_score",
            color="delivery_status",
            color_discrete_map={"Late": BAD_COLOR, "On Time or Early": GOOD_COLOR},
            template=plotly_template,
            text="avg_review_score",
            labels={"avg_review_score": "Avg Review Score", "delivery_status": "Delivery Status"},
        )
        fig5.update_traces(textposition="outside")
        fig5.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10), yaxis_range=[0, 5])
        st.plotly_chart(fig5, use_container_width=True)
    with col2:
        fig5b = px.pie(
            df5,
            names="delivery_status",
            values="num_orders",
            template=plotly_template,
            color="delivery_status",
            color_discrete_map={"Late": BAD_COLOR, "On Time or Early": GOOD_COLOR},
            hole=0.5,
        )
        fig5b.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig5b, use_container_width=True)

    st.dataframe(df5, use_container_width=True, hide_index=True)

    if gap is not None:
        st.markdown(f"""
            <div class="insight-box">
            <b>Insight:</b> On time deliveries score {gap} points higher on average than late ones.
            This directly links delivery performance to customer satisfaction and, by extension,
            seller reputation and repeat purchase rate.
            </div>
        """, unsafe_allow_html=True)


# SECTION 5: ROOT CAUSE

elif section == "Root Cause":
    st.markdown('<div class="section-header">Seller-Customer State Match</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Testing whether shipping distance explains the delay pattern</div>', unsafe_allow_html=True)

    df6 = load_geo_root_cause()
    col1, col2 = st.columns([1, 1])
    with col1:
        fig6 = px.bar(
            df6,
            x="seller_customer_match",
            y="avg_delay_days",
            color="seller_customer_match",
            color_discrete_map={"Same State": GOOD_COLOR, "Different State": BAD_COLOR},
            template=plotly_template,
            text="avg_delay_days",
            labels={"avg_delay_days": "Avg Delay (days)", "seller_customer_match": "Seller/Customer Match"},
        )
        fig6.update_traces(textposition="outside")
        fig6.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig6, use_container_width=True)
    with col2:
        fig6b = px.bar(
            df6,
            x="seller_customer_match",
            y="pct_late",
            color="seller_customer_match",
            color_discrete_map={"Same State": GOOD_COLOR, "Different State": BAD_COLOR},
            template=plotly_template,
            text="pct_late",
            labels={"pct_late": "% Orders Late", "seller_customer_match": "Seller/Customer Match"},
        )
        fig6b.update_traces(textposition="outside")
        fig6b.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig6b, use_container_width=True)

    st.dataframe(df6, use_container_width=True, hide_index=True)

    diff_row = df6[df6["seller_customer_match"] == "Different State"]
    same_row = df6[df6["seller_customer_match"] == "Same State"]
    if not diff_row.empty and not same_row.empty:
        delay_multiplier = round(diff_row["avg_delay_days"].iloc[0] / max(same_row["avg_delay_days"].iloc[0], 0.01), 1)
        st.markdown(f"""
            <div class="insight-box">
            <b>Insight:</b> Orders shipped across states show meaningfully higher delay than
            same state orders, roughly {delay_multiplier}x. This supports shipping distance as a
            genuine driver of the delay pattern rather than a data artifact.
            </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.caption("DeliverySense - an end-to-end data analytics project covering database design, SQL analysis, and interactive dashboarding. Tech stack: PostgreSQL · pandas · SQLAlchemy · Streamlit · Plotly.")