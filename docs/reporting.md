# Dashboard and Genie

The dashboard and Genie space are already saved in the original workspace folder.
Their links are in the [run results](implementation-status.md). This guide covers
the layout, metric choices, and steps for rebuilding them elsewhere.

## Sales Pulse dashboard

The dashboard uses four gold aggregate datasets on the existing serverless SQL
warehouse. Its layout is deliberately simple:

1. Total revenue, completed order count, and average order value at the top.
2. A daily revenue trend across the page.
3. Category and region comparisons side by side.
4. An all-time top-products table at the bottom.

The caption identifies the Marketplace source, fictional records, and USD values.
The original shared-source run covers August–November 2019. If using the local
fixture, update the caption to describe the sample and its January–March 2026
date range.

`reporting/dashboard_queries.sql` has standalone queries for the chart datasets.
For the notebook fallback, replace `retail_demo` with `retail_demo_notebooks`.

AOV comes from total revenue divided by completed orders, rather than an average
of daily AOV. Product totals are all-time. If adding a date filter, either keep
that label or build a dated product dataset so the filter applies consistently.

The published dashboard uses viewer credentials. Keep that setting when testing
reader permissions; embedding publisher credentials would change the access
being demonstrated. There is no automatic dashboard refresh schedule, which
helps conserve Free Edition quota.

## Retail Orders Analyst in Genie

The space uses these four tables:

- `retail_demo.gold.daily_revenue`
- `retail_demo.gold.product_metrics`
- `retail_demo.gold.category_revenue`
- `retail_demo.gold.regional_revenue`

Its instructions define revenue, AOV, table grain, and the source assumptions.
Genie should use the table that fits the question, since joining aggregates on
date alone can multiply revenue. It also needs to know that daily active
customers cannot be summed into period-level distinct customers.

The provider has no order status, so its purchase orders are assumed completed.
Region means latest-known customer region; category comes from a name lookup.
Those qualifications belong with the metrics rather than being left to inference.

Three benchmark questions are saved with reference SQL:

- What is total completed-sales revenue?
- Which three products generated the most revenue?
- Which region had the most revenue?

Use `reporting/genie_benchmarks.sql` to compare answers against the same data
snapshot. The total-revenue question was tested successfully. A separate shipping
question also confirmed that Genie explained the missing metric instead of
inventing a value. The other two questions are saved for later checks.

Only add `customer_metrics_masked` if customer analysis is needed and the view is
supported in the space. Keep bronze, silver, and the backing customer table out
of the reporting space.

## Rebuild the definitions

The dashboard and Genie definitions are checked in as `reporting/*.json`.
Regenerate them with:

```powershell
uv run python tools/build_reporting.py --warehouse-id YOUR_WAREHOUSE_ID
```

The script also writes API request bodies into `.cache`; it does not deploy them.
Update the existing dashboard or space when reusing a workspace, so repeated
imports do not create duplicates. Review the source caption if changing modes.

## A short walkthrough

Start with the shared source and show how it reaches bronze. Open quarantine to
explain a line-count mismatch, then follow the accepted lines into a gold revenue
table. Show the pipeline graph and its expectations before opening the dashboard.

In Catalog Explorer, open a gold object, choose Lineage, and expand upstream.
Capture the graph that the workspace actually shows. Shared-table reads can add
provider edges; file-based runs may begin at bronze or a Volume. A Catalog
Explorer screenshot is still a manual evidence item for this project.

Finish with the masked view and its object-level grants, then ask Genie for total
revenue and for shipping revenue. Explain the paused schedule and the remaining
access tests so the walkthrough reflects what has been tested.

## References

- [AI/BI dashboards](https://docs.databricks.com/aws/en/dashboards/)
- [Genie](https://docs.databricks.com/aws/en/genie/)
- [Unity Catalog lineage](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage)
