# Source contract and sharing decision tree

Checked against official documentation on 2026-11-10. A source must represent
order **lines**, with a stable `(order_id, line_id)` key and USD prices.
Do not substitute a demographics, clickstream, or weather listing merely to
claim Delta Sharing: it cannot support these retail metrics.

The first path succeeded in this workspace: Databricks' Simulated Retail Customer
Data was installed as `retail_provider`. The `dev` target selects `marketplace` mode;
its explicit nested-order adapter is documented in [provider-adapter.md](provider-adapter.md).
The remaining paths below are implemented fallbacks, not claims of additional runs.

## Try in this order

1. In Marketplace, filter for **Free** and **Instantly available** retail/order
   listings. Record provider, listing URL, license, access result, and column list.
   Free samples may be incomplete. Marketplace normally installs a separate,
   read-only catalog; it is not a schema inside `retail_demo`. Use `source_mode=table`
   and its full `catalog.schema.table`. No particular listing is guaranteed here.
2. For a provider credential, use Catalog Explorer → Sharing/OpenSharing/Delta Sharing
   → Shared with me → Import provider (labels vary). Select the provider share and
   create a catalog; read it with the same `table` mode. This requires provider/catalog
   privileges and may be unavailable in a particular Free workspace.
3. If import is unavailable, add `delta-sharing` to the ingest notebook's Environment
   dependencies, upload the profile to the **credentials** Volume, and select
   `open_sharing`. Set `profile_path` and `share_table=share.schema.table`.
   The code reads at most `max_rows+1` rows with `load_as_pandas`; a larger source
   is rejected rather than reporting misleading partial totals. This path is a small
   demo workaround, still dependent on network access and package availability.
   `load_as_spark` needs the Spark connector as well as the Python package; installing
   a connector JAR is not a supported general serverless customization.
4. If egress, permissions, or source suitability block sharing, upload a licensed
   CSV to `/Volumes/retail_demo/raw_share/landing/` and choose `csv`, or use the
   included fictional `sample`. Record that it **simulates** a provider. Neither CSV
   nor sample mode demonstrates an actual Delta Sharing transfer. No Kaggle dataset
   has been downloaded, licensed, or verified by this project.

The schema `raw_share` owns landing and credential Volumes. Shared catalogs remain
separate. Bronze stores the canonical fields plus `source_payload` (original columns
as JSON), `source_kind`, `source_ref`, `ingest_ts`, and a deterministic row hash.
Keep credential files out of Git and landing datasets. No profile content is printed.

## Column mapping

`column_mapping` is a JSON object of **canonical name → existing source column name**.
For example `{"order_id":"Order ID","unit_price":"Price"}`. It accepts names,
not SQL expressions. Missing required fields cause ingestion to fail before writes.
If a provider has a different grain, timestamp format, status vocabulary, currency,
or a discount percentage expressed as 10 instead of 0.10, prepare an explicit adapter
table first. Do not invent missing customer/order IDs or fabricate order lines.

| Field | Required/default | Meaning |
| --- | --- | --- |
| order_id, line_id | required | Stable line-level business key |
| order_ts | required | ISO timestamp; source uses UTC |
| customer_id | required | Provider identifier; restricted data |
| customer_email | null | Optional PII; sample uses example.invalid |
| product_id | required | Product identifier |
| product_name, category, region | Unknown | Descriptive attributes |
| quantity | required | Positive integral units, at most 1,000,000 |
| unit_price | required | Nonnegative USD amount, cents precision, at most 1,000,000 |
| discount_pct | 0 | Fraction in [0,1] |
| status | completed | completed, cancelled, or returned |
| updated_at | order_ts | Source update timestamp, UTC |
| currency | required | USD; other currencies quarantined |

## Semantics

- Bronze is the latest **complete, bounded snapshot**, not an incremental CDC feed
  or an append-only audit log. Each successful ingest atomically overwrites it.
- Casts use `TRY_CAST` under ANSI mode. Blank dimensions become `Unknown`; missing
  customer/product IDs quarantine the latest line. Invalid emails are retained in
  restricted data; the demo does not implement email validation.
- Deduplication chooses latest `updated_at`, then descending content hash as a stable
  tie-breaker. Conflicting payloads with identical timestamps have no business ordering;
  obtain a provider sequence number for a production CDC design.
- Deduplication precedes quality filtering. A newer invalid correction quarantines
  that key instead of resurrecting its older valid state. Invalid update timestamps
  fall back to order time; preserve a reliable source timestamp in real adapters.
- Revenue = `round(quantity * unit_price * (1-discount_pct), 2)` per accepted completed
  line, summed in fixed decimal arithmetic. Cancelled and returned lines remain in
  silver but contribute no revenue. This is completed-sales revenue, not accounting
  net revenue after refunds. No tax, freight, FX conversion, or returns ledger.
- AOV = revenue / distinct completed orders, never mean of daily AOV. Customer metrics
  use source customer IDs internally; public view hashes them. Hashes remain linkable
  pseudonymous identifiers, not a guarantee of anonymization.
- Counts at product/category/region grains are not necessarily additive across groups.
  The sample has order-consistent dates/regions/customers. External sources must too;
  order totals summed over days assume each order has one order date.

Sources: [Marketplace consumer workflow](https://docs.databricks.com/aws/en/marketplace/get-started-consumer),
[sharing recipients](https://docs.databricks.com/aws/en/opensharing/recipient),
[bearer-token reads](https://docs.databricks.com/aws/en/opensharing/read-data-open),
[official connector](https://github.com/delta-io/delta-sharing),
[serverless restrictions](https://docs.databricks.com/aws/en/compute/serverless/limitations).
