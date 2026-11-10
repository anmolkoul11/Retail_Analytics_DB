# Databricks notebook source
# MAGIC %md
# MAGIC # Ingest one bounded source snapshot
# MAGIC Modes: `marketplace`, `sample`, `csv`, `table`, `open_sharing`. Raw source columns are retained.
# MAGIC Configure a column-name mapping for external sources; see docs/source-contract.md.

# COMMAND ----------
from pathlib import Path
import json
import sys
from datetime import datetime, timezone

for name, default in {
    "catalog": "retail_demo", "project_root": "", "source_mode": "sample",
    "source_table": "", "source_path": "", "column_mapping": "{}",
    "profile_path": "", "share_table": "", "max_rows": "50000", "provider_catalog": "retail_provider",
}.items():
    dbutils.widgets.text(name, default)
p = {name: dbutils.widgets.get(name) for name in (
    "catalog", "project_root", "source_mode", "source_table", "source_path",
    "column_mapping", "profile_path", "share_table", "max_rows", "provider_catalog")}
root = Path(p["project_root"])
if not p["project_root"] or not (root / "retail" / "model.py").is_file():
    raise ValueError("Set project_root to the absolute /Workspace/... folder containing retail/model.py")
sys.path.insert(0, str(root))
from retail.model import COLUMNS, OPTIONAL, identifier, table
from pyspark.sql import functions as F

catalog = identifier(p["catalog"])
limit = int(p["max_rows"])
if not 1 <= limit <= 50000:
    raise ValueError("max_rows must be between 1 and 50000 for this demo")
mapping = json.loads(p["column_mapping"])
if not isinstance(mapping, dict) or set(mapping) - set(COLUMNS):
    raise ValueError("column_mapping must map canonical field names to source column names")
mode = p["source_mode"]

# COMMAND ----------
if mode == "marketplace":
    from retail.provider import provider_adapter_sql
    provider = identifier(p["provider_catalog"])
    source_ref = f"{catalog}.raw_share.provider_order_lines"
    spark.sql(f"CREATE OR REPLACE VIEW {source_ref} AS {provider_adapter_sql(provider)}")
    raw = spark.read.table(source_ref)
elif mode == "sample":
    # Copy repository sample to the landing Volume so the demo demonstrates Volume ingestion.
    import shutil
    landing = Path(f"/Volumes/{catalog}/raw_share/landing/sample_orders.csv")
    shutil.copyfile(root / "data" / "sample_orders.csv", landing)
    source_ref = str(landing)
    raw = spark.read.option("header", True).option("inferSchema", False).csv(source_ref)
elif mode == "csv":
    source_ref = p["source_path"]
    if not source_ref.startswith(f"/Volumes/{catalog}/raw_share/landing/"):
        raise ValueError("Upload the CSV into this demo's landing Volume")
    raw = spark.read.option("header", True).option("inferSchema", False).csv(source_ref)
elif mode == "table":
    source_ref = table(p["source_table"])
    raw = spark.read.table(source_ref)
elif mode == "open_sharing":
    # Add delta-sharing to the notebook Environment before selecting this optional mode.
    # Pandas avoids reliance on installing a Spark connector JAR on serverless.
    import delta_sharing
    profile = p["profile_path"]
    if not profile.startswith(f"/Volumes/{catalog}/raw_share/credentials/"):
        raise ValueError("Store the profile in the private credentials Volume")
    shared = table(p["share_table"])
    # Keep profile paths and tokens out of table metadata / displayed exceptions.
    source_ref = shared
    try:
        pdf = delta_sharing.load_as_pandas(profile + "#" + shared, limit=limit + 1)
    except Exception:
        raise RuntimeError("Open share read failed. Check profile validity and egress; use table/CSV mode if blocked.") from None
    if len(pdf) == 0:
        raise ValueError("Source is empty")
    records = json.loads(pdf.to_json(orient="records", date_format="iso"))
    # Explicit string schema also handles columns containing only NULL.
    from pyspark.sql.types import StructType, StructField, StringType
    source_schema = StructType([StructField(str(k), StringType(), True) for k in pdf.columns])
    raw = spark.createDataFrame([
        tuple(None if row.get(k) is None else str(row[k]) for k in pdf.columns)
        for row in records
    ], source_schema)
else:
    raise ValueError("source_mode must be marketplace, sample, csv, table, or open_sharing")

# Check before writes. Do not silently take an arbitrary sample from larger sources.
count = raw.limit(limit + 1).count()
if count == 0 or count > limit:
    raise ValueError(f"Source must contain 1..{limit} rows. Select a small provider table or prepare a bounded export.")
if len(raw.columns) != len(set(n.lower() for n in raw.columns)):
    raise ValueError("Source has duplicate or case-colliding column names")

# Preserve original payload before mapping; no untrusted SQL expressions are evaluated.
payload = F.to_json(F.struct(*[F.col("`" + k.replace("`", "``") + "`") for k in raw.columns]))
canonical = []
for name in COLUMNS:
    src = mapping.get(name, name)
    if not isinstance(src, str):
        raise ValueError("Mapping values must be source column names")
    if src in raw.columns:
        col = F.col("`" + src.replace("`", "``") + "`").cast("string")
    elif name in OPTIONAL and name not in mapping:
        col = F.lit(OPTIONAL[name]).cast("string")
    else:
        raise ValueError(f"Missing source field for {name}; set column_mapping")
    canonical.append(col.alias(name))
frame = raw.select(*canonical, payload.alias("source_payload"))
frame = frame.withColumn("_row_hash", F.sha2(F.to_json(F.struct(*COLUMNS)), 256))
ingest_ts = datetime.now(timezone.utc).replace(tzinfo=None)
frame = (frame.withColumn("ingest_ts", F.lit(ingest_ts))
    .withColumn("source_kind", F.lit(mode)).withColumn("source_ref", F.lit(source_ref)))

# Complete snapshot replacement: reruns do not accumulate duplicates.
# Solely owns this demo table; provider data remains read-only.
frame.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{catalog}.bronze.orders_raw")
print(f"Ingested {count} rows from {mode}; source snapshot replaced")
