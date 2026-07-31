# load_data.py

import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

# --- 1. CONFIGURE YOUR CONNECTION ---
DB_USER = "postgres"
DB_PASSWORD = quote_plus(os.getenv("DB_PASSWORD"))
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "deliverysense"

engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# --- 2. MAP EACH CSV TO A TABLE NAME ---
DATA_FOLDER = "data/"

files_to_tables = {
    "olist_customers_dataset.csv": "customers",
    "olist_orders_dataset.csv": "orders",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "olist_geolocation_dataset.csv": "geolocation",
    "product_category_name_translation.csv": "category_translation",
}

# --- 3. LOAD EACH CSV INTO POSTGRES ---
for filename, table_name in files_to_tables.items():
    filepath = DATA_FOLDER + filename
    print(f"Loading {filename} -> table '{table_name}' ...")

    df = pd.read_csv(filepath)

    for col in df.columns:
        if "date" in col.lower() or "timestamp" in col.lower():
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"  -> Loaded {len(df)} rows into '{table_name}'")

print("\nAll done! All 9 tables loaded into the 'deliverysense' database.")