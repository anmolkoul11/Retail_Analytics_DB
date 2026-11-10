"""Register the shared retail queries as Lakeflow materialized views."""
import sys
from pyspark import pipelines as dp

sys.path.insert(0, spark.conf.get("retail.project_root"))
from retail.model import identifier, model_queries

catalog = identifier(spark.conf.get("retail.catalog"))


def register(target, query):
    """Bind each query before registering it with the pipeline."""
    def dataset():
        return spark.sql(query)
    dataset.__name__ = target.replace(".", "_")
    # Stop publication if a future change lets bad rows into accepted silver data.
    if target == "silver.orders":
        dataset = dp.expect_all_or_fail({
            "positive_quantity": "quantity > 0",
            "valid_discount": "discount_pct BETWEEN 0 AND 1",
            "nonnegative_amount": "net_amount >= 0",
            "usd_only": "currency = 'USD'",
            "required_keys": "order_id IS NOT NULL AND line_id IS NOT NULL AND customer_id IS NOT NULL",
        })(dataset)
    dp.materialized_view(name=f"{catalog}.{target}")(dataset)


for target, query in model_queries(catalog).items():
    register(target, query)
