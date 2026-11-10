# Source fields and metric definitions

The pipeline expects one record per order line, identified by `(order_id, line_id)`,
with prices in USD. The configured Marketplace adapter turns nested purchase
orders into that format. Its mapping is in [provider-adapter.md](provider-adapter.md).

## Available sources

| Mode | Input | Setup |
| --- | --- | --- |
| `marketplace` | Installed Databricks retail share | Install the listing as `retail_provider` |
| `table` | Any compatible Unity Catalog table or view | Set `source_table=catalog.schema.table` |
| `sample` | Included fictional CSV | No external source needed |
| `csv` | Uploaded CSV | Put it in the demo's landing Volume and set `source_path` |
| `open_sharing` | Provider credential file | Add `delta-sharing` to the notebook Environment and set the profile/share widgets |

Marketplace succeeded in the original workspace, so the other sharing paths were
not needed. A listing normally appears as its own read-only catalog, separate from
`retail_demo`. The `raw_share` schema holds local landing files, credentials, and
the adapter view.

For another provider, try installing its Marketplace listing or importing its
credential through Catalog Explorer's sharing page first. Once the shared catalog
is available, use `table` mode. Check that the source actually contains order data
at the right grain before adapting it.

The direct `open_sharing` option uses `load_as_pandas` with a row limit. It avoids
installing a Spark connector JAR, but still needs network access to the provider.
Store its profile in `/Volumes/<catalog>/raw_share/credentials/`; credential content
is not printed or written into table metadata. The bundled job does not include
this optional dependency or the profile parameters by default.

If sharing is unavailable, a licensed CSV or the included fixture can stand in for
the source. Label that run as a simulated provider. No Kaggle dataset is included.

## Mapping external columns

`column_mapping` maps each expected field to a source column name. For example:

```json
{"order_id": "Order ID", "unit_price": "Price"}
```

Values are column names, not SQL expressions. Ingestion stops before writing if a
required field is missing. For different date formats, currencies, status values,
or discount conventions, prepare an adapter table or view first. A discount of
10% must arrive as `0.10`, not `10`.

| Field | Required or default | Meaning |
| --- | --- | --- |
| `order_id`, `line_id` | Required | Order-line key |
| `order_ts` | Required | ISO timestamp, interpreted as UTC |
| `customer_id` | Required | Source customer identifier; kept restricted |
| `customer_email` | NULL | Optional email |
| `product_id` | Required | Source product identifier |
| `product_name`, `category`, `region` | `Unknown` | Descriptive fields |
| `quantity` | Required | Whole number from 1 to 1,000,000 |
| `unit_price` | Required | Nonnegative USD amount, cents precision, at most 1,000,000 |
| `discount_pct` | `0` | Discount fraction between 0 and 1 |
| `status` | `completed` | `completed`, `cancelled`, or `returned` |
| `updated_at` | `order_ts` | Source update time, UTC |
| `currency` | Required | USD; other currencies go to quarantine |

Bronze keeps these fields plus the original input columns as `source_payload`
JSON, `source_kind`, `source_ref`, `ingest_ts`, and a deterministic row hash.

## Cleaning and deduplication

Each ingest replaces bronze with a complete source snapshot. This makes a rerun
easy to reason about, but it is not an append-only audit log or a CDC process.
Inputs must contain between 1 and 50,000 rows; larger inputs are rejected rather
than silently sampled.

Silver uses `TRY_CAST` for typed values. Blank descriptions become `Unknown`;
missing keys, invalid quantities, invalid discounts, and non-USD rows fail the
quality checks. Email format is not validated.

For each order-line key, the latest `updated_at` wins. A content hash breaks ties
consistently when timestamps match. An invalid update timestamp falls back to
order time. A production CDC source would need a reliable timestamp or sequence
number to give conflicting updates a business ordering.

Deduplication happens **before** quality filtering. If the newest correction is
bad, that key goes to quarantine; the pipeline does not quietly restore its older
valid version. The local fixture includes this case.

## Revenue and customer metrics

Revenue for each accepted completed line is:

```text
round(quantity × unit_price × (1 − discount_pct), 2)
```

Amounts use fixed decimal arithmetic and are rounded before aggregation.
Cancelled and returned lines remain in silver but do not contribute revenue.
Taxes, shipping, currency conversion, and a refund ledger are not modeled.
The Marketplace adapter assumes purchase orders are completed because that source
has no status field.

Average order value is revenue divided by distinct completed orders. For a period,
use `SUM(revenue) / SUM(order_count)` from daily_revenue, not the average of daily
AOV. This assumes each order has one order date.

Customer metrics use the source customer ID internally. The reporting view hashes
that ID and masks email unless the querying user belongs to the configured PII
group. The hash is still a linkable pseudonymous identifier.

Order counts by product, category, or region may overlap and should not be added
across groups without checking the grain. Daily active-customer counts cannot be
summed to get a period's distinct customers.

## References

- [Marketplace consumer workflow](https://docs.databricks.com/aws/en/marketplace/get-started-consumer)
- [Sharing recipients](https://docs.databricks.com/aws/en/opensharing/recipient)
- [Reading bearer-token shares](https://docs.databricks.com/aws/en/opensharing/read-data-open)
- [Delta Sharing connector](https://github.com/delta-io/delta-sharing)
- [Serverless restrictions](https://docs.databricks.com/aws/en/compute/serverless/limitations)
