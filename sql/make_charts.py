"""
Builds chart images from the query outputs in outputs/*.csv.
Saves PNGs to outputs/charts/.
"""

import pandas as pd
import matplotlib.pyplot as plt
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(PROJECT_ROOT, "outputs")
CHART_DIR = os.path.join(OUT_DIR, "charts")
os.makedirs(CHART_DIR, exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid")

# 1. Monthly revenue trend
df = pd.read_csv(os.path.join(OUT_DIR, "monthly_revenue_trend.csv"))
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(df["month"], df["total_revenue"], linewidth=2, color="#2980b9", label="Revenue")
ax.plot(df["month"], df["total_profit"], linewidth=2, color="#27ae60", label="Profit")
ax.set_xlabel("Month")
ax.set_ylabel("EUR")
ax.set_title("Monthly Revenue & Profit Trend")
step = max(1, len(df) // 12)
ax.set_xticks(range(0, len(df), step))
ax.set_xticklabels(df["month"][::step], rotation=45, ha="right")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, "monthly_revenue_trend.png"), dpi=150)
plt.close()

# 2. Revenue by category
df = pd.read_csv(os.path.join(OUT_DIR, "revenue_by_category.csv"))
fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(df["category"], df["total_revenue"], color="#2980b9")
ax.set_xlabel("Category")
ax.set_ylabel("Total Revenue (EUR)")
ax.set_title("Revenue by Product Category")
plt.xticks(rotation=20)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, "revenue_by_category.png"), dpi=150)
plt.close()

# 3. Profit margin by category
fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(df["category"], df["profit_margin_pct"], color="#27ae60")
ax.set_xlabel("Category")
ax.set_ylabel("Profit Margin (%)")
ax.set_title("Profit Margin by Product Category")
ax.set_ylim(0, max(df["profit_margin_pct"]) * 1.2)
plt.xticks(rotation=20)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, "profit_margin_by_category.png"), dpi=150)
plt.close()

# 4. Low stock summary
df = pd.read_csv(os.path.join(OUT_DIR, "low_stock_report.csv"))
counts = df["stock_status"].value_counts()
fig, ax = plt.subplots(figsize=(6, 6))
ax.pie(counts.values, labels=counts.index, autopct="%1.1f%%", colors=["#27ae60", "#c0392b"])
ax.set_title("Inventory Stock Status")
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, "stock_status_summary.png"), dpi=150)
plt.close()

print(f"4 charts saved to {CHART_DIR}")
