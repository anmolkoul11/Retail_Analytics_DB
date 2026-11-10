"""Build importable native AI/BI and Genie definitions; no remote mutations."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from retail.model import identifier


def chart(name, dataset, title, kind, x, y, position, temporal=False):
    return {
        "widget": {
            "name": name,
            "queries": [{"name": "main_query", "query": {
                "datasetName": dataset,
                "fields": [{"name": x, "expression": f"`{x}`"},
                           {"name": y, "expression": f"SUM(`{y}`)"}],
                "disaggregated": False,
            }}],
            "spec": {"version": 3, "widgetType": kind,
                "frame": {"showTitle": True, "title": title},
                "encodings": {
                    "x": {"fieldName": x, "scale": {"type": "temporal" if temporal else "categorical"}},
                    "y": {"fieldName": y, "scale": {"type": "quantitative"}, "displayName": "Revenue (USD)"},
                }},
        },
        "position": dict(zip(("x", "y", "width", "height"), position)),
    }


def build(catalog):
    c = identifier(catalog)
    datasets = [
        {"name": "daily", "displayName": "Daily sales", "queryLines": [f"SELECT * FROM {c}.gold.daily_revenue"]},
        {"name": "categories", "displayName": "Category sales", "queryLines": [f"SELECT * FROM {c}.gold.category_revenue"]},
        {"name": "regions", "displayName": "Regional sales", "queryLines": [f"SELECT * FROM {c}.gold.regional_revenue"]},
        {"name": "products", "displayName": "Product sales", "queryLines": [f"SELECT product_id, product_name, category, revenue, units FROM {c}.gold.product_metrics ORDER BY revenue DESC, product_id LIMIT 10"]},
    ]
    layout = [{"widget": {"name": "intro", "multilineTextboxSpec": {"lines": [
        "# Retail Orders | Sales Pulse\n",
        "Databricks Marketplace | Fictional retail records | Real Delta Sharing | USD\n",
        "Cancelled and returned lines excluded. Shipping, tax and refund accounting are not modeled.\n",
    ]}}, "position": {"x": 0, "y": 0, "width": 12, "height": 3}}]
    for idx, (name, expression, title) in enumerate([
        ("revenue", "SUM(`revenue`)", "Completed-sales revenue (USD)"),
        ("orders", "SUM(`order_count`)", "Completed orders"),
        ("aov", "SUM(`revenue`)/NULLIF(SUM(`order_count`),0)", "Average order value (USD)"),
    ]):
        layout.append({"widget": {"name": name,
            "queries": [{"name": "main_query", "query": {"datasetName": "daily",
                "fields": [{"name": "value", "expression": expression}], "disaggregated": False}}],
            "spec": {"version": 2, "widgetType": "counter",
                "encodings": {"value": {"fieldName": "value"}},
                "frame": {"showTitle": True, "title": title}}},
            "position": {"x": idx * 4, "y": 3, "width": 4, "height": 3}})
    layout.extend([
        chart("trend", "daily", "Daily completed-sales revenue", "line", "order_date", "revenue", (0, 6, 12, 6), True),
        chart("category", "categories", "Revenue by category", "bar", "category", "revenue", (0, 12, 6, 6)),
        chart("region", "regions", "Revenue by region", "bar", "region", "revenue", (6, 12, 6, 6)),
    ])
    fields = ["product_id", "product_name", "category", "revenue", "units"]
    layout.append({"widget": {"name": "top_products",
        "queries": [{"name": "main_query", "query": {"datasetName": "products",
            "fields": [{"name": n, "expression": f"`{n}`"} for n in fields], "disaggregated": True}}],
        "spec": {"version": 2, "widgetType": "table",
            "encodings": {"columns": [{"fieldName": n, "displayName": n.replace('_',' ').title()} for n in fields]},
            "frame": {"showTitle": True, "title": "Top products — all time"}}},
        "position": {"x": 0, "y": 18, "width": 12, "height": 6}})
    dashboard = {"datasets": datasets, "pages": [{"name": "sales_pulse",
        "displayName": "Sales Pulse", "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": layout}]}
    questions = [
        ("What is total completed-sales revenue?", f"SELECT SUM(revenue) AS revenue FROM {c}.gold.daily_revenue"),
        ("Which three products generated the most revenue?", f"SELECT product_id, product_name, revenue FROM {c}.gold.product_metrics ORDER BY revenue DESC, product_id LIMIT 3"),
        ("Which region had the most revenue?", f"SELECT region, SUM(revenue) AS revenue FROM {c}.gold.regional_revenue GROUP BY region ORDER BY revenue DESC, region LIMIT 1"),
    ]
    instructions = (
        "Revenue means completed-sales revenue in USD after discounts and rounding per line. "
        "Cancelled and returned lines are excluded; tax, shipping and refund accounting are not modeled. "
        "daily_revenue is daily; category_revenue and regional_revenue add their respective dimension. "
        "product_metrics is all-time per product/name/category/currency. "
        "Never join these aggregate tables on date alone: this multiplies revenue. Use one suitable table. "
        "AOV is SUM(revenue)/SUM(order_count) from daily_revenue, not AVG(average_order_value). "
        "Active customers cannot be summed across days as period distinct customers. "
        "Product and region order counts may not be additive. Explain unavailable metrics instead of inventing fields. "
        "All records are fictional data from the Databricks Marketplace Simulated Retail Customer Data listing. "
        "The adapter assumes source purchase orders are completed because no order status is supplied. "
        "Region is latest-known customer region. Category uses provider sales.product_category mapped by product name; "
        "unmatched names are Unknown. Orders whose declared line count disagrees with their JSON array are quarantined."
    )
    genie = {"version": 2,
        "config": {"sample_questions": [{"id": f"{i+1:032x}", "question": [q]} for i,(q,_) in enumerate(questions)]},
        "data_sources": {"tables": [{"identifier": f"{c}.gold.{t}"} for t in
            sorted(("daily_revenue", "product_metrics", "category_revenue", "regional_revenue"))]},
        "instructions": {"text_instructions": [{"id": "00000000000000000000000000000100", "content": [instructions]}],
            "example_question_sqls": [{"id": f"{i+512:032x}", "question": [q], "sql": [sql]} for i,(q,sql) in enumerate(questions)]},
        "benchmarks": {"questions": [{"id": f"{i+1024:032x}", "question": [q],
            "answer": [{"format": "SQL", "content": [sql]}]} for i,(q,sql) in enumerate(questions)]},
    }
    return dashboard, genie


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', default='retail_demo')
    parser.add_argument('--warehouse-id', required=True)
    parser.add_argument('--parent-path', default='/Workspace/Users/anmolkoul11@gmail.com/Databricks_Demo')
    args = parser.parse_args()
    dashboard, genie = build(args.catalog)
    (ROOT / '.cache').mkdir(exist_ok=True)
    for name, obj in [('retail_dashboard.lvdash.json', dashboard), ('retail_genie.geniespace.json', genie)]:
        (ROOT / 'reporting' / name).write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    requests = {
        'create-dashboard.json': {'display_name': 'Retail Orders — Sales Pulse',
            'warehouse_id': args.warehouse_id, 'parent_path': args.parent_path,
            'serialized_dashboard': json.dumps(dashboard)},
        'create-genie.json': {'title': 'Retail Orders Analyst', 'warehouse_id': args.warehouse_id,
            'parent_path': args.parent_path, 'description': 'Fictional retail completed-sales analytics, USD, governed gold aggregates.',
            'serialized_space': json.dumps(genie)},
    }
    for name, obj in requests.items():
        (ROOT / '.cache' / name).write_text(json.dumps(obj), encoding='utf-8')
    print('Built native dashboard and Genie definitions plus API request files in .cache')
