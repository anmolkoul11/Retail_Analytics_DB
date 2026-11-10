# Databricks notebook source
# MAGIC %md
# MAGIC # Create the catalog and Volumes
# MAGIC Run this before ingestion. A separate demo catalog makes its objects and grants easier to manage.

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
print(f"Landing files: /Volumes/{catalog}/raw_share/landing")
print("Reader grants are set up later. If this catalog already existed, check its inherited permissions.")
