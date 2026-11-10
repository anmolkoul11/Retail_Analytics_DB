# Setup and operational runbook

## Bundle route

1. Authenticate with the official CLI through OAuth. `RETAIL_DEMO` is a new profile
   name. The local CLI uses normal Databricks authentication; browser session cookies
   are not reused or extracted.
2. Run `tools/bootstrap.ps1 -Profile RETAIL_DEMO` to create the catalog and schemas
   through SQL on the existing serverless warehouse. The pipeline requires its catalog
   to exist at deployment time. Then run `bundle validate --strict`, `bundle deploy`, and `bundle run retail_demo`
   with `-t dev -p RETAIL_DEMO`. Deployment creates one pipeline and two jobs, but only
   running a job starts processing. Do not run both jobs simultaneously for a demo.
3. Confirm the five tasks succeed. Inspect `silver.orders_quarantine`, gold totals,
   the pipeline graph and expectations, and the validation task output.
4. Choose real sharing using [source-contract.md](source-contract.md). For a catalog
   source, redeploy with `--var source_mode=table --var source_table=CATALOG.SCHEMA.TABLE`.
   Use `BUNDLE_VAR_column_mapping` for JSON that needs shell quoting. For CSV set
   `source_mode=csv` and the absolute Volume `source_path` after setup created the Volume.
5. Configure dashboard and Genie using [reporting.md](reporting.md). Capture lineage
   and the actual run output; record URLs and feature results in the status log.

Changing `catalog` requires redeployment so both the pipeline configuration and job
parameters agree. Do not override just the job `catalog` parameter on the pipeline
job. Use `fallback_catalog` for the notebook-only job.

`open_sharing` is deliberately a manual notebook option: add its Python dependency
in the Environment panel and run `01_ingest.py` with the credential widgets, then
refresh the pipeline and run governance/validation. The default bundled ingest task
does not include that optional package or credential path. To schedule this mode,
configure a supported job Environment and its profile/share parameters first. Never
commit a profile or install a Spark connector JAR into serverless compute.

## Git-folder / manual route

The existing workspace folder is
`/Workspace/Users/anmolkoul11@gmail.com/Databricks_Demo`. It started empty.
To use a Git folder, push this local repository to your own remote and clone it in
Databricks with the Git folders UI. A normal workspace folder does not become a Git
folder merely because a local repository exists. No remote URL has been supplied.

Alternatively import the source files preserving directory structure. Keep `retail`
as Python modules, `data` as files, `pipelines` as pipeline source, and `notebooks`
as Databricks source-format notebooks. Set each notebook's `project_root` widget
to the **absolute** `/Workspace/...` folder containing `retail/model.py`.

For the pipeline path:

1. Run `00_setup`, then `01_ingest`, both with `catalog=retail_demo`.
2. Create one serverless, triggered Lakeflow Declarative Pipeline. Use the default
   publishing mode (no legacy LIVE target), catalog `retail_demo`, schema `silver`,
   and Advanced edition for expectations. Add `pipelines/retail_pipeline.py`.
3. Add configuration `retail.catalog=retail_demo` and
   `retail.project_root=/Workspace/.../Databricks_Demo`, then run one update.
4. Run `03_governance` and `04_validate`. Defaults grant only the current user and
   mask every email. A named reader user/group can be passed separately.
5. Create sequential job tasks with the same paths/parameters as the YAML. Use
   serverless notebook tasks, pipeline update task in the middle, max concurrent
   runs 1, no automatic retries, and a paused daily schedule at 08:00 New York time.

For notebooks only: run `00`, `01`, `02`, `03`, `04` in that order, all with
`catalog=retail_demo_notebooks`. Do not create a second active pipeline.

## Governance checks

Use a new demo catalog. Setup creates no general reader grants, but it does not
remove privileges already inherited from the metastore/catalog. Inspect effective
grants in Catalog Explorer and `SHOW GRANTS` on catalog, schemas, tables and view.

Test a separate reader, if available:

- SELECT on four gold aggregate objects and `customer_metrics_masked` succeeds.
- Masked view returns `***MASKED***` unless the session belongs to the configured
  account PII group. The view uses the **querying** user's membership.
- SELECT on `bronze.orders_raw`, `silver.orders`, `gold.customer_metrics`, and both
  raw_share Volumes fails for that reader. USE privileges on parents are also needed.
- Querying as the owner/admin cannot prove isolation: owners retain underlying
  access. Free Edition may not offer the account/group administration needed to
  demonstrate multiple roles. Record the limitation rather than creating a fictitious
  group or claiming a successful test.

Dynamic views protect the view interface only. Do not grant a reader SELECT at the
catalog/gold schema level, ownership of the view/backing objects, or unrelated broad
data privileges. Do not set `pii_group=account users`; that would reveal email to
every account member. Customer hashes remain pseudonymous data.

## Stretch: outbound share

**Verified in this workspace:** the share was created, and `daily_revenue` was added
successfully using the sharing API's `data_object_type=MATERIALIZED_VIEW`. No external
recipient access was granted. The TABLE type was rejected for this object. Inspect
the existing share instead of recreating or adding the asset again.

Inspect provider/share permissions first. The optional SQL in
`governance/outbound_share.sql` creates a share and attempts to add the aggregate;
it does **not** create recipients or grant external access. Execute statement by
statement and log the exact success/error without tokens or activation links.

Pipeline outputs are materialized views; use their actual type in the API. If a
different workspace rejects sharing that type,
make an explicit Delta export (only when ready to test):

```sql
CREATE OR REPLACE TABLE retail_demo.gold.daily_revenue_export USING DELTA AS
SELECT * FROM retail_demo.gold.daily_revenue;
CREATE SHARE IF NOT EXISTS retail_demo_gold_share;
ALTER SHARE retail_demo_gold_share ADD TABLE retail_demo.gold.daily_revenue_export;
DESCRIBE SHARE retail_demo_gold_share;
```

The export is a snapshot requiring manual refresh. Adding an asset to an existing
share may duplicate an earlier successful attempt; inspect `SHOW ALL IN SHARE`
before rerunning. If blocked, record the actual feature/privilege error. Creating a
share is not proof that a recipient could consume it. No external recipient or
credential is provisioned by this repo. Free Edition's Marketplace-provider ban is
not evidence that direct share creation is categorically unavailable.

## Recovery and quota

- Quota exhaustion: pause schedules, keep code, wait for compute reset. Avoid repeated
  retries or full refreshes. Sample ingestion makes no external network requests.
- Pipeline failure: inspect the event log/graph first; use notebook fallback in its
  separate catalog if needed. Do not overwrite pipeline-managed objects.
- Catalog creation denied: check CREATE CATALOG and managed storage availability.
  If only an existing catalog is writable, use it deliberately, inspect inherited
  access first, and redeploy with that catalog variable.
- Source mapping errors: inspect source schema, adapt fields explicitly, rerun ingest.
  No source error silently switches data provenance to a fictional sample.
- Invalid casts: inspect quarantine and source payload in bronze. Dedupe occurs
  before filtering; latest invalid corrections intentionally remove stale silver rows.
- Timestamp handling: sample and adapters assume UTC. Serverless defaults to UTC;
  set `spark.sql.session.timeZone=UTC` explicitly if you change session settings.
- Notebook runs replace outputs independently; neither execution path is an atomic
  transaction across the whole medallion. Readers should wait for successful job
  completion to avoid mixing intermediate snapshots.
- To stop: pause both job schedules, stop any active update, and stop warehouse
  usage. No continuous pipeline is configured. Do not run `bundle destroy` casually:
  it can remove managed resources/data. Catalog removal is a separate deliberate step.

References: [bundle examples](https://docs.databricks.com/aws/en/dev-tools/bundles/examples),
[multi-schema pipelines](https://docs.databricks.com/aws/en/ldp/target-schema),
[materialized views](https://docs.databricks.com/aws/en/ldp/developer/ldp-python-ref-materialized-view).
