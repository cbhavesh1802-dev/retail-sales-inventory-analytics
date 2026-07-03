-- Low-stock alert report: products at risk of stockout
SELECT
    p.product_name,
    p.category,
    i.current_stock,
    i.reorder_point,
    i.avg_daily_sales,
    i.days_of_cover,
    i.stock_status
FROM inventory i
JOIN products p ON i.product_id = p.product_id
ORDER BY i.days_of_cover ASC NULLS LAST;
