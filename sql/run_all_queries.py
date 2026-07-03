import sqlite3
import pandas as pd
import os

DB_PATH = "/home/claude/projects/03-retail-sales-inventory/data/retail_analytics.db"
SQL_DIR = "/home/claude/projects/03-retail-sales-inventory/sql"
OUT_DIR = "/home/claude/projects/03-retail-sales-inventory/outputs"
os.makedirs(OUT_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)

queries = {
    "monthly_revenue_trend.csv": "01_monthly_revenue_trend.sql",
    "revenue_by_category.csv": "02_revenue_by_category.sql",
    "top_products_by_category.csv": "03_top_products_by_category.sql",
    "low_stock_report.csv": "04_low_stock_report.sql",
}

for out_name, sql_file in queries.items():
    with open(f"{SQL_DIR}/{sql_file}") as f:
        query = f.read()
    df = pd.read_sql_query(query, conn)
    out_path = f"{OUT_DIR}/{out_name}"
    df.to_csv(out_path, index=False)
    print(f"{out_name}: {len(df)} rows -> {out_path}")

conn.close()
