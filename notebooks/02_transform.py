# Databricks notebook source
# MAGIC %md
# MAGIC # Notebook fallback — same SQL as the Lakeflow pipeline
# MAGIC Use a separate catalog from pipeline-owned materialized views (default `retail_demo_notebooks`).

# COMMAND ----------
from pathlib import Path
import sys
dbutils.widgets.text("catalog", "retail_demo_notebooks")
dbutils.widgets.text("project_root", "")
root = Path(dbutils.widgets.get("project_root"))
if not dbutils.widgets.get("project_root") or not (root / "retail/model.py").is_file():
    raise ValueError("Set project_root to the absolute workspace project folder")
sys.path.insert(0, str(root))
from retail.model import identifier, model_queries
catalog = identifier(dbutils.widgets.get("catalog"))
for target, query in model_queries(catalog).items():
    spark.sql(f"CREATE OR REPLACE TABLE {catalog}.{target} USING DELTA AS {query}")
print("Silver and gold snapshot tables refreshed")
