-- Top 10 products by revenue, ranked within their category (window function)
WITH product_revenue AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        ROUND(SUM(s.revenue), 2) AS total_revenue,
        ROUND(SUM(s.profit), 2)  AS total_profit,
        RANK() OVER (PARTITION BY p.category ORDER BY SUM(s.revenue) DESC) AS category_rank
    FROM sales s
    JOIN products p ON s.product_id = p.product_id
    GROUP BY p.product_id, p.product_name, p.category
)
SELECT *
FROM product_revenue
WHERE category_rank <= 3
ORDER BY category, category_rank;
