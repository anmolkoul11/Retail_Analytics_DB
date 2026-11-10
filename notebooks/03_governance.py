# Databricks notebook source
# MAGIC %md
# MAGIC # Publish the dynamic customer view and explicit reader grants
# MAGIC `reader_principal`: account group or user's email. Empty means current user only.
# MAGIC `pii_group`: verified account group; empty means mask all readers, including owner.

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
print("Granted access to four aggregates and the masked view only.")
print("Raw customer_metrics remains restricted; do not grant SELECT on the entire gold schema.")
display(spark.sql(f"SHOW GRANTS ON CATALOG {catalog}"))
