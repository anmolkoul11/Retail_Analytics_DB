# Dashboard, Genie, and presentation script

The dashboard and Genie space have already been created in your project folder;
use the links in [implementation-status.md](implementation-status.md). This guide
also describes rebuilding them. Native definitions are in `reporting/*.json` and
can be regenerated with `tools/build_reporting.py --warehouse-id <id>`.
Use update/import on existing resources rather than creating duplicate dashboards
or spaces. The current source caption identifies actual Marketplace sharing and
fictional records; its dates are August–November 2019.

## AI/BI dashboard

After the job passes validation, create an AI/BI dashboard named **Retail Orders —
Sales Pulse** on the existing serverless SQL warehouse. Add each statement in
`reporting/dashboard_queries.sql` as a separate dataset. For notebook fallback,
replace `retail_demo` with `retail_demo_notebooks` throughout the queries.

Use a clean one-page layout:

1. Top row: total revenue (USD), completed order count, weighted AOV.
2. Full-width line chart: daily completed-sales revenue, chronological x-axis.
3. Two half-width horizontal bar charts: top categories and regions.
4. Bottom: top ten products, with revenue and units.

Add a caption: **Fictional sample • USD • completed sales only • Jan–Mar 2026**
when running sample mode. Use the actual source/date range for other modes. Use
a dashboard-level date filter bound to dated datasets if desired; product totals
are all-time, so label that widget accordingly or add a dated product dataset first.

Publishing with embedded publisher credentials can change the effective data access
for viewers. For the governance demo, use viewer credentials where available and
verify with a reader identity. The default single-user owner is not a proof of
multi-user security. No automatic dashboard refresh is configured: it would spend
quota beyond the ingestion schedule.

## Genie space

Create **Retail Orders Analyst**, select the same warehouse, and add only:

- `retail_demo.gold.daily_revenue`
- `retail_demo.gold.product_metrics`
- `retail_demo.gold.category_revenue`
- `retail_demo.gold.regional_revenue`

Optionally add `gold.customer_metrics_masked` after reviewing privacy and confirming
the view is supported in your space. Do not add bronze, silver, or raw customer metrics.

Paste these instructions into the space:

> Revenue means completed-sales revenue in USD after discounts, rounded per order
> line. Cancelled and returned orders are excluded; refunds, taxes and shipping are
> not modeled. daily_revenue is one row per date and currency; category_revenue and
> regional_revenue add their respective dimension. product_metrics is all-time per
> product/name/category/currency. Never join these aggregate tables on date alone:
> doing so multiplies revenue. Use the single table whose grain answers the question.
> AOV equals SUM(revenue)/SUM(order_count) from daily_revenue. Active customer counts
> cannot be summed across days to get distinct customers for a period. Counts by
> product/category are not additive. Explain unavailable metrics instead of inventing
> a join or field. The included sample contains fictional customers and transactions.

Save benchmark questions and compare answers to `reporting/genie_benchmarks.sql`:
total completed-sales revenue, top three products, and the leading region. Also ask "How much
shipping did we collect?"; Genie should explain that shipping is not modeled.
Keep SQL/answer screenshots as evidence rather than assuming a fluent answer is right.

## Five-minute demo

1. Show source provenance and state whether the run used an actual share or simulated provider.
2. In Catalog Explorer show four schemas, the landing Volume, and bronze metadata.
3. Show the job/pipeline graph, silver quarantine, and the invalid latest correction.
4. Show gold lineage in Catalog Explorer → a gold object → Lineage, expand upstream,
   and save a real screenshot. File ingestion starts lineage at bronze or the Volume
   as supported; shared-table reads may expose a provider-table edge. Do not claim
   cross-provider lineage unless it is actually shown.
5. Show the masked view and its explicit grants. Explain that owner/admin access to
   underlying data bypasses this view; verify a separate reader if the account permits.
6. Show the dashboard, then ask Genie a benchmark and the unsupported shipping question.
7. Finish with paused scheduling, quota choices, and an honest feature-attempt log.

Sources: [AI/BI dashboards](https://docs.databricks.com/aws/en/dashboards/),
[Genie](https://docs.databricks.com/aws/en/genie/),
[Unity Catalog lineage](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage).
