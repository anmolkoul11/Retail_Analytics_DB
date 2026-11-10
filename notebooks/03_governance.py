# Databricks notebook source
# MAGIC %md
# MAGIC # Set up reporting access
# MAGIC Set reader_principal to an account group or user email. Leave it blank to use the current user.
# MAGIC Set pii_group to the account group allowed to see email. Leaving it blank masks email for everyone.

# COMMAND ----------
from pathlib import Path
import sys
for name, default in {"catalog": "retail_demo", "project_root": "",
                      "reader_principal": "", "pii_group": ""}.items():
    dbutils.widgets.text(name, default)
root = Path(dbutils.widgets.get("project_root"))
if not dbutils.widgets.get("project_root") or not (root / "retail/model.py").is_file():
    raise ValueError("Set project_root to the absolute workspace project folder")
sys.path.insert(0, str(root))
from retail.model import PUBLIC_GOLD, identifier, masked_view_sql
catalog = identifier(dbutils.widgets.get("catalog"))
reader = dbutils.widgets.get("reader_principal") or spark.sql("SELECT current_user()").first()[0]
pii_group = dbutils.widgets.get("pii_group")
if reader in ("users", "admins") or pii_group in ("users", "admins"):
    raise ValueError("Use an account group or individual user, not workspace-local users/admins")
principal = "`" + reader.replace("`", "``") + "`"
spark.sql(f"CREATE OR REPLACE VIEW {catalog}.gold.customer_metrics_masked AS {masked_view_sql(catalog, pii_group)}")
spark.sql(f"GRANT USE CATALOG ON CATALOG {catalog} TO {principal}")
spark.sql(f"GRANT USE SCHEMA ON SCHEMA {catalog}.gold TO {principal}")
for name in PUBLIC_GOLD:
    spark.sql(f"GRANT SELECT ON VIEW {catalog}.gold.{name} TO {principal}" if name.endswith("_masked")
              else f"GRANT SELECT ON TABLE {catalog}.gold.{name} TO {principal}")
print("Reader access is set for the four aggregates and the masked customer view.")
print("Keep customer_metrics restricted; a schema-wide SELECT grant would expose the backing table.")
display(spark.sql(f"SHOW GRANTS ON CATALOG {catalog}"))
