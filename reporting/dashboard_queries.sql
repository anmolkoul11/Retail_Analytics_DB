-- Add each query as its own dashboard dataset.
-- Use retail_demo_notebooks instead of retail_demo for the notebook-only path.

-- Daily revenue trend: order_date on the x-axis, revenue in USD on the y-axis.
SELECT order_date, revenue, order_count, average_order_value
FROM retail_demo.gold.daily_revenue ORDER BY order_date;

-- Compare total revenue by category.
SELECT category, SUM(revenue) AS revenue
FROM retail_demo.gold.category_revenue GROUP BY category ORDER BY revenue DESC;

-- Compare total revenue by customer region.
SELECT region, SUM(revenue) AS revenue
FROM retail_demo.gold.regional_revenue GROUP BY region ORDER BY revenue DESC;

-- Show the ten highest-revenue products in a table or bar chart.
SELECT product_id, product_name, category, revenue, units
FROM retail_demo.gold.product_metrics ORDER BY revenue DESC, product_id LIMIT 10;

-- Summary cards. Calculate AOV from the totals, not the average of daily AOV.
SELECT SUM(revenue) AS total_revenue, SUM(order_count) AS total_orders,
       ROUND(SUM(revenue) / NULLIF(SUM(order_count), 0), 2) AS average_order_value
FROM retail_demo.gold.daily_revenue;
