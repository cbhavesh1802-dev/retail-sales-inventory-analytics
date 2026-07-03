-- Monthly revenue, cost, profit trend
SELECT
    strftime('%Y-%m', sale_date) AS month,
    COUNT(*)                     AS order_count,
    SUM(quantity)                AS units_sold,
    ROUND(SUM(revenue), 2)       AS total_revenue,
    ROUND(SUM(cost), 2)          AS total_cost,
    ROUND(SUM(profit), 2)        AS total_profit,
    ROUND(100.0 * SUM(profit) / SUM(revenue), 2) AS profit_margin_pct
FROM sales
GROUP BY month
ORDER BY month;
