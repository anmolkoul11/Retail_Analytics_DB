# Verified implementation — 2026-11-10

## Open the demo

- [Workspace project folder](https://dbc-52ad64ac-9d22.cloud.databricks.com/browse/folders/1985546061667892?o=7474646606974334)
- [Published Sales Pulse dashboard](https://dbc-52ad64ac-9d22.cloud.databricks.com/dashboardsv3/01f1dd3854d21e60b53a9f1db75729e5/published?o=7474646606974334)
- [Retail Orders Analyst Genie space](https://dbc-52ad64ac-9d22.cloud.databricks.com/genie/rooms/01f1dd387b6d163d91f8a1ad05a52a56?o=7474646606974334)
- [Successful Marketplace-source job run](https://dbc-52ad64ac-9d22.cloud.databricks.com/jobs/941905938262771/runs/89815997261296?o=7474646606974334)
- [Pipeline](https://dbc-52ad64ac-9d22.cloud.databricks.com/pipelines/5b32315d-33ee-4cfb-8ce3-57e3321f8cfd?o=7474646606974334)
- [Successful initial sample-source run](https://dbc-52ad64ac-9d22.cloud.databricks.com/jobs/941905938262771/runs/421584245088319?o=7474646606974334)

## Completed and tested

| Area | Verified result |
| --- | --- |
| UC | `retail_demo` catalog; raw_share, bronze, silver, gold schemas; landing and credentials managed Volumes |
| Marketplace | User approved terms; listing installed as `retail_provider`; 4,074 fictional purchase orders accessed through actual sharing |
| Ingestion | `marketplace` adapter reads shared tables, retains original order JSON and source provenance in bronze |
| Medallion | Serverless Advanced Lakeflow pipeline succeeded for both sample and Marketplace sources |
| Quality | Latest-line deduplication, quarantine, positive quantity, valid discounts/keys, USD checks, and accepted-data expectations |
| Governance | Dynamic masked view created; explicit reader grants default to current user only; backing customer table excluded |
| Job | Setup, ingest, medallion, governance, validate all SUCCESS in run `89815997261296` |
| Dashboard | Native AI/BI dashboard created and published; viewer credentials (`embed_credentials=false`); no new public audience |
| Genie | Four aggregate tables, definitions, sample questions, SQL examples, and three benchmarks saved |
| Outbound share | `retail_demo_gold_share` created; `daily_revenue` added as MATERIALIZED_VIEW and ACTIVE; no recipients granted |
| Local | Eight shared-SQL/config tests pass; strict authenticated bundle validation passes; local Git repository initialized |
| Schedule | Daily 08:00 America/New_York definition, PAUSED; max concurrent runs 1; no automatic retries |

## Final Marketplace snapshot

| Metric | Result |
| --- | ---: |
| Bronze line/price-tier records | 8,138 |
| Accepted latest silver lines | 7,643 |
| Quarantined latest lines | 355 |
| Older/replayed records removed | 140 |
| Accepted distinct completed orders | 3,808 |
| Completed-sales revenue, USD | 10,062,538.04 |
| Accepted date range | 2019-08-01 through 2019-11-14 |
| Unmasked email values in default view | 0 |

The daily, category, product, region, and customer gold revenue totals independently
reconcile to **10,062,538.04**. Do not compare these figures with the small local
fixture's metrics: they are different sources. Bronze `source_kind` is `marketplace`.

Genie returned **$10,062,538.04** for "What is total completed-sales revenue?" using
`SUM(revenue)` from daily_revenue, matching SQL. Asked for shipping revenue, it
explained that shipping is not tracked and generated no invented shipping query.
The top-product and region benchmarks are saved but were not separately asked in chat.
Machine-readable, non-credential evidence is in [evidence.json](evidence.json).

## Boundaries and remaining manual evidence

- **Lineage screenshot:** source/table operations ran through Unity Catalog, but a
  Catalog Explorer screenshot has not been captured. The Databricks console explicitly
  reported that automated browser control is unsupported; all subsequent mutations
  used the official CLI/API. Manually open a gold object in Catalog Explorer, choose
  Lineage, expand upstream, and save a screenshot. No lineage graph was fabricated.
- **Reader isolation:** verified default masking and explicit grant design under the
  owner identity. No second reader/account-group identity was available to prove
  denied access or a PII-authorized membership branch. Underlying owner access remains.
- **Provider emails:** actual shared source contains no email field, so emails stay NULL
  internally. The included fictional fixture exercises both mask branches locally;
  a live PII-authorized test still needs a suitable identity and source.
- **Outbound consumption:** asset creation/addition succeeded, but no external recipient,
  activation link, or credential was created, and no recipient read was attempted.
- **Notebook fallback:** the source is implemented and shares tested SQL with the pipeline;
  only its setup task was executed during bootstrap. A full second medallion run was
  avoided to conserve quota.
- **Open-sharing credentials / CSV:** not needed after Marketplace succeeded. Optional
  paths are implemented but not workspace-tested. No Kaggle data was downloaded.
- **Dashboard visuals:** native definitions were saved/published and backing metrics
  queried; no automated console visual review was possible after its browser-control
  notice. Open the dashboard to review the actual rendering.
- **Git:** local repository only, per user preference. No remote was supplied or pushed,
  and the Databricks folder is a regular workspace folder, not a remote-backed Git folder.

## Platform findings

1. Fresh pipeline deployment failed until the catalog existed. The setup notebook
   successfully bootstrapped default storage; `tools/bootstrap.ps1` is the reusable
   SQL-warehouse bootstrap before a fresh deployment.
2. Plain catalog REST creation required a metastore storage root in this workspace;
   SQL `CREATE CATALOG` used the available Free Edition default storage successfully.
3. Marketplace installation required the listing's consumer terms version `2023-01`.
   The missing-version and `1.0` requests were rejected before successful installation.
4. Adding daily_revenue with sharing type TABLE failed because it is a materialized
   view. Repeating with MATERIALIZED_VIEW succeeded; no Delta export was necessary.
5. The workspace accepted one active serverless pipeline and the scheduled job. The
   schedule remains paused, as intended for a quota-conscious personal demo.
