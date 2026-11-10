# Installed Marketplace source

Provider: **Databricks**. Listing: **Simulated Retail Customer Data**.
Listing ID: `a82597f6-5ada-49d5-b934-d6c9dece16a1`.
Share: `dbacademy_dataset_retail`; installed as read-only catalog `retail_provider`.
The user explicitly approved installation and its terms on 2026-11-10.

License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Attribution: Simulated Retail Customer Data, provided by Databricks through
Databricks Marketplace. The adapter transforms nested orders into line/price-tier
records, adds lookup dimensions, and excludes inconsistent orders from analytics.
No provider dataset is redistributed in this Git repository. Records are fictional;
the actual provider catalog and Delta Sharing connection are real.

The installation API requires `accepted_consumer_terms.version="2023-01"`, matching
the listing's linked [Marketplace consumer terms](https://cms.databricks.com/sites/default/files/2023-01/marketplace-consumer-terms_0.pdf).
The API rejected a missing version and `1.0`; the `2023-01` installation succeeded.
Do not automatically accept these terms on another user's behalf; each user should
review the listing and agree before installation.

## Mapping

`retail/provider.py` defines a local **view** in `retail_demo.raw_share` over three
shared tables. It does not modify the provider catalog.

- `v01.sales_orders`: 4,074 orders in the inspected snapshot. `ordered_products` is
  a JSON array, expanded with its zero-based position. Epoch-second `order_datetime`
  becomes a UTC timestamp. Structural keys combine provider order number, array
  position, and `regular`/`promo` price tier; they support a full snapshot, not CDC.
- Product `id`, `name`, `price`, `qty`, and `curr` come from each nested line.
  `promotion_info.promo_disc` is a discount fraction applying to `promo_qty` units.
  A partial promotion becomes two price tiers so the discount is not applied to
  unpromoted units. The inspected snapshot has one such partial promotion.
- A purchase order has no supplied status; the adapter explicitly assumes
  `completed`. Revenue is therefore a modeled purchase-order value, not independently
  verified settlement revenue. No emails are supplied: `customer_email` stays NULL.
  The separate included sample demonstrates masking with fictional email values.
- `v01.customers`: one latest-known region per customer, chosen by `valid_from`
  descending. This is **not** an as-of region join. No names, tax IDs, addresses,
  or coordinates are copied from this dimension into canonical columns.
- `v01.sales`: product categories are looked up by **product_name**. The embedded
  `sales.product` JSON does not reliably correspond to the row's product name, so
  it is not used as a product-ID lookup. Conflicting name/category mappings yield
  `Unknown`; there were zero conflicts in the inspected snapshot. Missing mappings
  yield `Unknown`. Provider category labels are brand-like values and retain their
  original business meaning.
- `number_of_line_items` must equal the actual JSON array size. In the inspected
  source, 147 orders (273 expanded source lines) disagree. Their canonical quantity
  is NULL so the latest lines enter quarantine. `source_payload` retains the
  original ordered-products JSON, declared/actual count, and quality reason.

The initial source contains 8,137 nested product lines; the category lookup matches
4,697 of them. The adapter adds a price tier for the single partial promotion.
See [implementation-status.md](implementation-status.md) for actual final acceptance
counts after the shared-source job runs.

Use `source_mode=marketplace` and `provider_catalog=retail_provider`. The configured
`dev` target now selects this mode. To replay the small deliberate-error fixture,
deploy with `--var source_mode=sample`; the 1,211-row CSV remains available.
