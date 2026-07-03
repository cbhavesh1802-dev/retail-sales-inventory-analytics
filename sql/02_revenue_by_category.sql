-- Revenue and profit margin by product category
SELECT
    category,
    COUNT(*)                                      AS order_count,
    SUM(quantity)                                  AS units_sold,
    ROUND(SUM(revenue), 2)                         AS total_revenue,
    ROUND(SUM(profit), 2)                          AS total_profit,
    ROUND(100.0 * SUM(profit) / SUM(revenue), 2)   AS profit_margin_pct
FROM sales
GROUP BY category
ORDER BY total_revenue DESC;
