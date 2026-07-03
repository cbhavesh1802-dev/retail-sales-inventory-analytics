# Retail Sales & Inventory Analytics

Sales performance and inventory risk analysis for a multi-category retail business -- built with SQL, Python, and Power BI.

## Overview

This project analyzes 271K+ sales transactions across 800 products and 3.5 years to answer the questions a retail analyst is asked daily: what is driving revenue, which products lead each category, and what is at risk of stocking out?

## Key Findings

- Electronics is the top revenue category at ~EUR 2.69M, followed by Home & Kitchen and Sports (outputs/revenue_by_category.csv)
- Profit margins are consistent across categories (~46-48%), suggesting pricing strategy is applied uniformly rather than category-specific
- Monthly revenue trend shows clear seasonality, with a spike in Nov-Dec consistent with holiday shopping patterns (outputs/monthly_revenue_trend.csv)
- 71 products are flagged LOW stock -- below their 2-week reorder point based on trailing average daily sales (outputs/low_stock_report.csv)
- Top 3 products per category ranked by revenue, useful for merchandising and restock prioritization (outputs/top_products_by_category.csv)

## Project Structure

data/ - products.csv, sales.csv, inventory.csv, generate_synthetic.py
sql/ - 01_monthly_revenue_trend.sql, 02_revenue_by_category.sql, 03_top_products_by_category.sql (RANK window function), 04_low_stock_report.sql, load_db.py, run_all_queries.py
outputs/ - query results, ready for Power BI / Excel import

## How to Run

python sql/load_db.py
python sql/run_all_queries.py

## Methodology Notes

Reorder point is calculated as 2 weeks of coverage based on each products trailing average daily sales rate. Top products by category uses RANK() OVER (PARTITION BY category ORDER BY revenue DESC) to rank products within their own category rather than globally, so smaller categories still surface their top performers. Data is synthetic, generated with realistic weekday/weekend demand variation, a growth trend over time, and a holiday-season (Nov-Dec) sales spike.

## Tech Stack

SQL (SQLite, window functions) - Python (Pandas, NumPy) - Power BI - Excel
