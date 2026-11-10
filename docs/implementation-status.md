# Run results and remaining checks

These results were recorded on **November 10, 2026**. They describe the original
workspace runs; they are not a fresh test of later code changes. The raw summary
is checked in as [evidence.json](evidence.json).

## Workspace links

- [Project folder](https://dbc-52ad64ac-9d22.cloud.databricks.com/browse/folders/1985546061667892?o=7474646606974334)
- [Published Sales Pulse dashboard](https://dbc-52ad64ac-9d22.cloud.databricks.com/dashboardsv3/01f1dd3854d21e60b53a9f1db75729e5/published?o=7474646606974334)
- [Retail Orders Analyst in Genie](https://dbc-52ad64ac-9d22.cloud.databricks.com/genie/rooms/01f1dd387b6d163d91f8a1ad05a52a56?o=7474646606974334)
- [Successful Marketplace run](https://dbc-52ad64ac-9d22.cloud.databricks.com/jobs/941905938262771/runs/89815997261296?o=7474646606974334)
- [Pipeline](https://dbc-52ad64ac-9d22.cloud.databricks.com/pipelines/5b32315d-33ee-4cfb-8ce3-57e3321f8cfd?o=7474646606974334)
- [Successful local-fixture run](https://dbc-52ad64ac-9d22.cloud.databricks.com/jobs/941905938262771/runs/421584245088319?o=7474646606974334)

## What passed

The Marketplace listing installed as `retail_provider`, and both source modes
completed the full serverless job: setup, ingest, medallion, governance, and
validation. The pipeline used Advanced edition for data-quality expectations.

| Area | Result |
| --- | --- |
| Unity Catalog | retail_demo with four schemas and separate landing/credential Volumes |
| Ingestion | Shared orders adapted into bronze with original order JSON and source details |
| Transformations | Typed and deduplicated silver lines, quarantine, and five gold models |
| Governance | Masked customer view and explicit grants on reporting objects |
| Reporting | AI/BI dashboard published with viewer credentials; Genie limited to four aggregates |
| Sharing | daily_revenue added to retail_demo_gold_share as an active MATERIALIZED_VIEW |
| Validation | Eight local tests and strict authenticated bundle validation passed |
| Scheduling | Daily 08:00 America/New_York schedule saved in PAUSED state |

## Shared-source totals

| Metric | Result |
| --- | ---: |
| Bronze line/price-tier records | 8,138 |
| Accepted latest silver lines | 7,643 |
| Quarantined latest lines | 355 |
| Older or replayed records removed | 140 |
| Accepted completed orders | 3,808 |
| Modeled sales revenue (USD) | $10,062,538.04 |
| Accepted dates | 2019-08-01 through 2019-11-14 |
| Unmasked email values in the default view | 0 |

Daily, category, product, region, and customer revenue each totaled
**$10,062,538.04**. Bronze recorded `source_kind=marketplace`. The local CSV is a
different fixture, so its row counts and revenue should not be compared with
these figures.

Genie returned **$10,062,538.04** for the total-revenue question using
`SUM(revenue)` from daily_revenue. When asked about shipping revenue, it explained
that the metric was unavailable and generated no shipping query. The product and
region benchmarks were saved but were not separately asked in chat.

## Still to check

- **Lineage screenshot and dashboard appearance.** The console reported that
  automated browser control was unsupported, so deployment continued through the
  official CLI/API. The dashboard was saved and published, but its rendering and
  Catalog Explorer lineage graph still need a manual review and screenshot.
- **A separate reader identity.** Default masking and grants were checked as the
  owner. Denied access to backing tables and the live PII-group branch still need
  a different identity; owners retain access to underlying data.
- **Email from a live source.** The shared dataset has no email field. The local
  fixture exercises both masking branches with fictional emails, but a live
  authorized-reader test has not been done.
- **Outbound consumption.** The share and asset are active, but no recipient was
  created or granted access, and no external read was attempted.
- **The full notebook fallback.** Its setup task ran during bootstrap, and its
  SQL is covered by local tests. A second full medallion run was skipped to save
  quota.
- **The optional CSV and credential paths.** These are implemented but were not
  needed after Marketplace succeeded. No Kaggle dataset was downloaded.
- **A Databricks Git folder.** The project has a local Git repository with a
  GitHub origin. The existing Databricks project remains a regular workspace
  folder until it is separately cloned through the Git folders UI.

## Setup details worth remembering

The pipeline could not be created until its catalog existed. SQL `CREATE CATALOG`
on serverless compute successfully used Free Edition default storage, while the
plain catalog REST call asked for a metastore storage root. The bootstrap script
uses the SQL route for that reason.

Marketplace installation required consumer terms version `2023-01`. Adding the
gold output to a share also required the correct object type: `TABLE` failed for
the pipeline materialized view, and `MATERIALIZED_VIEW` succeeded. Neither issue
required changing the source data or creating an export table.
