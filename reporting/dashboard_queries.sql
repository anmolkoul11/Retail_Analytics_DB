-- One AI/BI dashboard dataset per statement. Default pipeline catalog.
-- For notebook fallback, replace retail_demo with retail_demo_notebooks.

-- revenue_trend: line chart, x order_date, y revenue (USD).
SELECT order_date, revenue, order_count, average_order_value
FROM retail_demo.gold.daily_revenue ORDER BY order_date;

-- top_categories: horizontal bars, category vs revenue.
SELECT category, SUM(revenue) AS revenue
FROM retail_demo.gold.category_revenue GROUP BY category ORDER BY revenue DESC;

-- regional_breakdown: bars, region vs revenue.
SELECT region, SUM(revenue) AS revenue
FROM retail_demo.gold.regional_revenue GROUP BY region ORDER BY revenue DESC;

-- top_products: table or bars.
SELECT product_id, product_name, category, revenue, units
FROM retail_demo.gold.product_metrics ORDER BY revenue DESC, product_id LIMIT 10;

-- KPI totals: compute weighted AOV; do not average daily AOV.
SELECT SUM(revenue) AS total_revenue, SUM(order_count) AS total_orders,
       ROUND(SUM(revenue) / NULLIF(SUM(order_count), 0), 2) AS average_order_value
FROM retail_demo.gold.daily_revenue;
