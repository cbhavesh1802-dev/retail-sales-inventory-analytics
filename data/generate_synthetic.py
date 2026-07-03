"""
Generates synthetic retail/e-commerce sales + inventory data:
products, daily sales transactions, and stock levels.
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta

np.random.seed(21)

CATEGORIES = {
    "Electronics":   (50, 800),
    "Home & Kitchen": (10, 150),
    "Apparel":        (8, 90),
    "Beauty":         (5, 60),
    "Sports":         (10, 200),
}

N_PRODUCTS = 150
START = date(2025, 1, 1)
DAYS = 545  # ~18 months through end of June 2026

# --- Products ---
products = []
for pid in range(1, N_PRODUCTS + 1):
    cat = np.random.choice(list(CATEGORIES.keys()))
    lo, hi = CATEGORIES[cat]
    price = round(np.random.uniform(lo, hi), 2)
    products.append({
        "product_id": pid,
        "product_name": f"{cat.split()[0]}-Item-{pid}",
        "category": cat,
        "unit_price": price,
        "unit_cost": round(price * np.random.uniform(0.4, 0.65), 2),
    })
products_df = pd.DataFrame(products)

# --- Daily sales ---
sales_rows = []
sale_id = 1
for d in range(DAYS):
    the_date = START + timedelta(days=d)
    # Weekend boost, slight upward trend over time, holiday-season spike in Nov-Dec
    dow_factor = 1.3 if the_date.weekday() >= 5 else 1.0
    trend_factor = 1 + (d / DAYS) * 0.4
    season_factor = 1.6 if the_date.month in (11, 12) else 1.0
    n_orders_today = int(np.random.poisson(35) * dow_factor * trend_factor * season_factor)

    for _ in range(n_orders_today):
        pid = np.random.randint(1, N_PRODUCTS + 1)
        qty = np.random.choice([1, 1, 1, 2, 2, 3], p=[0.4, 0.2, 0.15, 0.15, 0.05, 0.05])
        sales_rows.append({
            "sale_id": sale_id,
            "sale_date": the_date,
            "product_id": pid,
            "quantity": qty,
        })
        sale_id += 1

sales_df = pd.DataFrame(sales_rows)
sales_df = sales_df.merge(products_df[["product_id", "unit_price", "unit_cost", "category"]], on="product_id")
sales_df["revenue"] = (sales_df["quantity"] * sales_df["unit_price"]).round(2)
sales_df["cost"] = (sales_df["quantity"] * sales_df["unit_cost"]).round(2)
sales_df["profit"] = (sales_df["revenue"] - sales_df["cost"]).round(2)
sales_df = sales_df.drop(columns=["unit_price", "unit_cost"])

# --- Inventory snapshot (current stock + reorder point) ---
inventory_rows = []
for _, p in products_df.iterrows():
    sold_total = sales_df.loc[sales_df["product_id"] == p["product_id"], "quantity"].sum()
    avg_daily_sales = sold_total / DAYS
    starting_stock = np.random.randint(200, 2000)
    current_stock = max(0, int(starting_stock - sold_total + np.random.randint(-50, 200)))
    reorder_point = int(avg_daily_sales * 14)  # 2 weeks of cover
    inventory_rows.append({
        "product_id": p["product_id"],
        "current_stock": current_stock,
        "reorder_point": reorder_point,
        "avg_daily_sales": round(avg_daily_sales, 2),
        "days_of_cover": round(current_stock / avg_daily_sales, 1) if avg_daily_sales > 0 else None,
        "stock_status": "LOW" if current_stock < reorder_point else "OK",
    })
inventory_df = pd.DataFrame(inventory_rows)

products_df.to_csv("/home/claude/projects/03-retail-sales-inventory/data/products.csv", index=False)
sales_df.to_csv("/home/claude/projects/03-retail-sales-inventory/data/sales.csv", index=False)
inventory_df.to_csv("/home/claude/projects/03-retail-sales-inventory/data/inventory.csv", index=False)

print(f"Products: {len(products_df)} | Sales rows: {len(sales_df)} | Inventory rows: {len(inventory_df)}")
print(f"Low stock items: {(inventory_df['stock_status'] == 'LOW').sum()}")
