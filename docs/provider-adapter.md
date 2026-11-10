# Adapting the Marketplace data

The source is Databricks' **Simulated Retail Customer Data** listing, installed as
the read-only catalog `retail_provider`. Its records are fictional; access to the
catalog uses a real Delta Sharing connection.

| Source detail | Value |
| --- | --- |
| Provider | Databricks |
| Listing ID | `a82597f6-5ada-49d5-b934-d6c9dece16a1` |
| Share | `dbacademy_dataset_retail` |
| Catalog | `retail_provider` |
| License | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |

Attribution: **Simulated Retail Customer Data, provided by Databricks through
Databricks Marketplace.** This project's adapter expands nested orders, adds
lookup dimensions, separates promotion quantities, and flags inconsistent orders.
The provider's dataset is not redistributed in this repository.

## How the adapter works

`retail/provider.py` builds a view called `raw_share.provider_order_lines` in the
demo catalog. It reads three shared tables without changing them.

### Orders and product lines

`v01.sales_orders` contained 4,074 orders in the inspected snapshot. Each row has
an `ordered_products` JSON array. The adapter expands that array and takes each
product's ID, name, price, quantity, and currency directly from its fields.
`order_datetime` is an epoch-second value converted to a UTC timestamp.

Line IDs combine the array position with a `regular` or `promo` suffix. Together
with the provider order number, this gives each price tier a key within the full
snapshot. These structural keys are not intended for tracking CDC changes.

`promotion_info` supplies a discount fraction and the number of units it applies
to. If only some units are discounted, the adapter creates separate regular-price
and discounted records. The source had one partial promotion, so 8,137 nested
product lines became 8,138 bronze records.

The source has no order-status field. The adapter treats purchase orders as
completed, so the revenue represents modeled purchase-order value rather than
verified settlement revenue. There is also no email field; `customer_email`
remains NULL. The separate local fixture contains fictional emails for testing
the masking logic.

### Region and category lookups

Customer region comes from `v01.customers`. The adapter takes one latest record
per customer using `valid_from`. This is a latest-known-region lookup, not an
as-of join at order time. Names, tax IDs, addresses, and coordinates from that
table are not copied into the output.

Categories come from `v01.sales`, joined by `product_name`. The JSON in
`sales.product` did not consistently describe the product named on that same row,
so using it as an ID lookup would assign the wrong categories.

The name lookup matched 4,697 source lines. Missing or conflicting name/category
matches become `Unknown`; no conflicting mappings were found in the inspected
snapshot. The source's category labels often look like brand names and are kept
as supplied.

### Quality checks

An order's declared `number_of_line_items` must match the length of its products
array. The source had 147 orders with a mismatch, covering 273 expanded lines
before deduplication. The adapter leaves their quantity NULL so silver sends them
to quarantine.

Bronze preserves the original product JSON, both line counts, and a provider
quality reason in `source_payload`. The usual key, quantity, price, discount, and
currency checks still apply afterward. Final counts are in the
[run results](implementation-status.md).

## Installation and reuse

The `dev` target uses `source_mode=marketplace` and
`provider_catalog=retail_provider`. Install the listing under that catalog name
before running in another workspace, or change the provider_catalog variable.
Review the listing's license and terms during installation.

For the original installation, the API required consumer terms version
`2023-01`, matching the linked
[Marketplace consumer terms](https://cms.databricks.com/sites/default/files/2023-01/marketplace-consumer-terms_0.pdf).
Requests without a version, or with `1.0`, were rejected. That version records
what worked on November 10, 2026; check the current listing when installing again.

To use the small local fixture instead, deploy with `--var source_mode=sample`.
The sharing connection is then replaced by a CSV-based source for that run.
