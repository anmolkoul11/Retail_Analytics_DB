# Databricks notebook source
# MAGIC %md
# MAGIC # Acceptance checks — run after governance

# COMMAND ----------
import re
dbutils.widgets.text("catalog", "retail_demo")
c = dbutils.widgets.get("catalog")
if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", c):
    raise ValueError("Invalid catalog")
checks = {
    "unique_order_lines": f"SELECT COUNT(*) FROM (SELECT order_id, line_id FROM {c}.silver.orders GROUP BY order_id, line_id HAVING COUNT(*) > 1)",
    "no_bad_silver": f"SELECT COUNT(*) FROM {c}.silver.orders WHERE quantity <= 0 OR net_amount < 0 OR currency <> 'USD' OR order_id IS NULL OR line_id IS NULL",
    "revenue_reconciles": f"SELECT CASE WHEN COALESCE((SELECT SUM(net_amount) FROM {c}.silver.orders WHERE status = 'completed'), 0) = COALESCE((SELECT SUM(revenue) FROM {c}.gold.daily_revenue), 0) THEN 0 ELSE 1 END",
    "latest_keys_accounted_for": f"SELECT ABS((SELECT COUNT(*) FROM {c}.silver.orders_ranked WHERE version_rank = 1) - (SELECT COUNT(*) FROM {c}.silver.orders) - (SELECT COUNT(*) FROM {c}.silver.orders_quarantine))",
}
for label, query in checks.items():
    errors = spark.sql(query).first()[0]
    assert errors == 0, f"{label}: {errors} violations"
    print(f"PASS {label}")
assert spark.table(f"{c}.silver.orders").limit(1).count() == 1, "No accepted rows"
display(spark.sql(f"""SELECT 'bronze' AS layer, COUNT(*) AS rows FROM {c}.bronze.orders_raw
  UNION ALL SELECT 'silver', COUNT(*) FROM {c}.silver.orders
  UNION ALL SELECT 'quarantine', COUNT(*) FROM {c}.silver.orders_quarantine"""))
