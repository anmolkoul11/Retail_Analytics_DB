# Databricks notebook source
# MAGIC %md
# MAGIC # Retail demo — Unity Catalog setup
# MAGIC Run once, then run ingestion. Use a new catalog dedicated to this demo.

# COMMAND ----------
import re

dbutils.widgets.text("catalog", "retail_demo")
catalog = dbutils.widgets.get("catalog")
if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", catalog):
    raise ValueError("Catalog must be a simple SQL identifier")

spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
for schema in ("raw_share", "bronze", "silver", "gold"):
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.raw_share.landing")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.raw_share.credentials")
print(f"Landing: /Volumes/{catalog}/raw_share/landing")
print("Setup grants no reader access. Audit existing inherited privileges before using an existing catalog.")
