import sqlite3
import pandas as pd
import os

DATA_DIR = "/home/claude/projects/03-retail-sales-inventory/data"
DB_PATH = f"{DATA_DIR}/retail_analytics.db"

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

products = pd.read_csv(f"{DATA_DIR}/products.csv")
sales = pd.read_csv(f"{DATA_DIR}/sales.csv")
inventory = pd.read_csv(f"{DATA_DIR}/inventory.csv")

conn = sqlite3.connect(DB_PATH)
products.to_sql("products", conn, index=False)
sales.to_sql("sales", conn, index=False)
inventory.to_sql("inventory", conn, index=False)

conn.execute("CREATE INDEX idx_sale_date ON sales(sale_date);")
conn.execute("CREATE INDEX idx_product ON sales(product_id);")
conn.commit()
conn.close()

print(f"Loaded products({len(products)}), sales({len(sales)}), inventory({len(inventory)}) into {DB_PATH}")
