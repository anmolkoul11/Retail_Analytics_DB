# Running and troubleshooting the demo

## Deploy with a bundle

The original deployment uses a `RETAIL_DEMO` CLI profile and the `dev` target.
For a new workspace, update the host in `databricks.yml` first and install the
retail listing as `retail_provider`, or choose `source_mode=sample`.

1. Sign in with `databricks auth login --host <workspace-url> --profile RETAIL_DEMO`.
2. Run `.\tools\bootstrap.ps1 -Profile RETAIL_DEMO`. It uses an existing SQL
   warehouse to create the catalog and schemas before the pipeline is deployed.
3. Run `databricks bundle validate -t dev -p RETAIL_DEMO --strict`.
4. Deploy with `databricks bundle deploy -t dev -p RETAIL_DEMO`.
5. Start the job with `databricks bundle run retail_demo -t dev -p RETAIL_DEMO`.

Deployment creates one pipeline and two jobs. A job run starts processing; the
daily schedule remains paused. Check that all five tasks succeed, then inspect
the quarantine, gold totals, and pipeline expectations.

If the CLI is installed under `.tools`, use `.\.tools\databricks.exe` in place of
`databricks`. OAuth credentials are stored by the CLI, outside the repository.

Changing `catalog` requires redeployment so the pipeline and job use the same
name. Overriding just the job parameter leaves the pipeline pointing at its old
catalog. The notebook-only job has a separate `fallback_catalog` setting.

## Choose a source

The installed retail share uses `source_mode=marketplace`. For a different source
that already has compatible columns, redeploy with:

```powershell
databricks bundle deploy -t dev -p RETAIL_DEMO --var source_mode=table --var source_table=CATALOG.SCHEMA.TABLE
```

Use `column_mapping` for renamed fields; `BUNDLE_VAR_column_mapping` is useful for
passing JSON through a shell. The [source contract](source-contract.md) explains
which fields are required and when a separate adapter is needed.

For an uploaded CSV, run setup first, upload the file into the landing Volume,
and set `source_mode=csv` with its absolute Volume path in `source_path`.

For `open_sharing`, add `delta-sharing` to the ingest notebook's Environment,
store the provider profile in the credentials Volume, and set `profile_path` and
`share_table`. Run ingestion, refresh the pipeline, then run governance and
validation. Scheduling that option needs a job Environment with the dependency
and those parameters; they are not part of the default job configuration.

## Run through a Git folder or notebooks

The original project is in
`/Workspace/Users/anmolkoul11@gmail.com/Databricks_Demo`, a regular workspace folder.
The GitHub remote is `https://github.com/anmolkoul11/Retail_Analytics_DB.git`.
To work from a Databricks Git folder, clone that repository through the Git folders
UI. Pushing local changes alone does not sync the existing workspace folder.

For manual file import, keep the directory structure: `retail` contains Python
modules, `data` contains files, `pipelines` contains pipeline source, and
`notebooks` contains Databricks source-format notebooks. Set `project_root` to
the absolute `/Workspace/...` folder containing `retail/model.py`.

To use the pipeline:

1. Run `00_setup`, then `01_ingest`, with `catalog=retail_demo`. Set source_mode
   explicitly when running ingestion by hand; its notebook default is `sample`.
2. Create a triggered serverless Lakeflow Declarative Pipeline with catalog
   `retail_demo`, schema `silver`, and Advanced edition for expectations. Add
   `pipelines/retail_pipeline.py` as a source file and use default publishing mode.
3. Set `retail.catalog=retail_demo` and
   `retail.project_root=/Workspace/.../Databricks_Demo` in pipeline configuration.
4. Run an update, followed by `03_governance` and `04_validate`.

For notebooks only, run `00`, `01`, `02`, `03`, and `04` in order with
`catalog=retail_demo_notebooks`. The separate catalog keeps notebook writes away
from pipeline-owned materialized views. Run one path at a time to save quota.

## Check access

Use a fresh demo catalog where possible. Setup does not remove grants inherited
from an existing catalog or metastore. Check effective permissions in Catalog
Explorer and with `SHOW GRANTS` before adding readers.

The governance notebook defaults to the current user, with every email masked.
For a separate reader identity, check that:

- The four gold aggregates and `customer_metrics_masked` are readable.
- The view returns `***MASKED***` unless that identity belongs to the configured
  account PII group.
- Bronze, silver, the raw customer metrics table, and both raw_share Volumes are
  not accessible through the reader's grants.

Readers need USE privileges on the parent catalog and schema as well as SELECT
on the reporting objects. Use an account group or individual user, since the
workspace-local `users` and `admins` groups cannot receive Unity Catalog grants.

Granting SELECT on the whole gold schema would expose the backing customer table.
Keep grants at the reporting-object level. The view evaluates the querying user's
membership, but owners still have access to the underlying data. An owner-only
test cannot demonstrate reader isolation. Free Edition may limit the available
identities and account-group setup.

## Outbound sharing

The original workspace has `retail_demo_gold_share`, with daily_revenue added as
an active materialized view. No recipients have been granted access. Inspect the
existing share before adding the same asset again.

For the pipeline output, the sharing API request uses its actual object type:

```json
{
  "updates": [{
    "action": "ADD",
    "data_object": {
      "name": "retail_demo.gold.daily_revenue",
      "data_object_type": "MATERIALIZED_VIEW"
    }
  }]
}
```

Save that request to a file and pass it to `databricks shares update
retail_demo_gold_share --json '@request.json' -p RETAIL_DEMO`. The optional SQL in
`governance/outbound_share.sql` creates and describes the share; adding a recipient
is a separate step.

If another workspace cannot share materialized views, a managed Delta export is
an alternative:

```sql
CREATE OR REPLACE TABLE retail_demo.gold.daily_revenue_export USING DELTA AS
SELECT * FROM retail_demo.gold.daily_revenue;
CREATE SHARE IF NOT EXISTS retail_demo_gold_share;
ALTER SHARE retail_demo_gold_share ADD TABLE retail_demo.gold.daily_revenue_export;
DESCRIBE SHARE retail_demo_gold_share;
```

That export needs its own refresh. Creating a share and adding an asset confirm
provider setup; a recipient read is still needed to test consumption.

## Common issues

| Issue | What to check |
| --- | --- |
| Catalog missing during deployment | Run bootstrap before creating the pipeline |
| Catalog creation asks for a storage root | Use SQL `CREATE CATALOG` on serverless compute for Free Edition default storage |
| Source column missing | Check the source schema and column_mapping before retrying |
| Unexpected quarantine rows | Compare silver values with source_payload in bronze; the newest bad correction stays quarantined |
| Pipeline failure | Inspect its graph and event log, then use the separate notebook catalog if needed |
| Compute quota reached | Leave schedules paused and wait for the quota reset rather than retrying repeatedly |
| Dates shift | Confirm the session uses UTC; set `spark.sql.session.timeZone=UTC` if it was changed |

Writes across the whole medallion are not one transaction. Wait for a successful
job before comparing reports across layers, especially on the notebook path.

Between demos, keep schedules paused and stop active updates or warehouse use.
`bundle destroy` can remove managed resources and data; it is not the same as
stopping compute.

## References

- [Bundle examples](https://docs.databricks.com/aws/en/dev-tools/bundles/examples)
- [Publishing to multiple schemas](https://docs.databricks.com/aws/en/ldp/target-schema)
- [Materialized views](https://docs.databricks.com/aws/en/ldp/developer/ldp-python-ref-materialized-view)
