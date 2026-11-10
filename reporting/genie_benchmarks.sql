-- Expected SQL for three Genie benchmark questions. Compare using the same snapshot.

-- What is total completed-sales revenue?
SELECT SUM(revenue) AS revenue FROM retail_demo.gold.daily_revenue;

-- Which three products generated the most revenue?
SELECT product_id, product_name, revenue FROM retail_demo.gold.product_metrics
ORDER BY revenue DESC, product_id LIMIT 3;

-- Which region had the most revenue?
SELECT region, SUM(revenue) AS revenue FROM retail_demo.gold.regional_revenue
GROUP BY region ORDER BY revenue DESC, region LIMIT 1;
