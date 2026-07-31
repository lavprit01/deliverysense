-- Order status breakdown (funnel overview)

SELECT
    order_status,
    COUNT(*) AS num_orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM orders
GROUP BY order_status
ORDER BY num_orders DESC;

-- Per-order delivery delay

SELECT
    order_id,
    customer_id,
    order_purchase_timestamp,
    order_estimated_delivery_date,
    order_delivered_customer_date,
    EXTRACT(DAY FROM (order_delivered_customer_date - order_estimated_delivery_date)) AS delay_days,
    CASE
        WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 'Late'
        WHEN order_delivered_customer_date IS NULL THEN 'Not Delivered'
        ELSE 'On Time or Early'
    END AS delivery_status
FROM orders
WHERE order_status = 'delivered';

-- Delay aggregated by customer state

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

-- Delay aggregated by product category

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
HAVING COUNT(*) > 50   -- ignore tiny categories with noisy averages
ORDER BY avg_delay_days DESC
LIMIT 15;

-- Review Score - late vs on-time

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

-- Root Cause - seller state vs customer state (geography mistake)

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