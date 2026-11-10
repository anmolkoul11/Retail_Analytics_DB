"""Build the silver, gold, and masking queries used by both execution paths."""
import re

COLUMNS = (
    "order_id", "line_id", "order_ts", "customer_id", "customer_email",
    "product_id", "product_name", "category", "region", "quantity",
    "unit_price", "discount_pct", "status", "updated_at", "currency",
)
OPTIONAL = {
    "customer_email": None, "product_name": "Unknown", "category": "Unknown",
    "region": "Unknown", "discount_pct": "0", "status": "completed",
    "updated_at": None,
}


def identifier(value):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Use a simple SQL identifier: {value!r}")
    return value


def table(value):
    parts = value.split(".")
    if len(parts) != 3:
        raise ValueError("Expected catalog.schema.table")
    return ".".join(identifier(p) for p in parts)


def literal(value):
    # Keep quoted values consistent in Spark SQL and the local DuckDB tests.
    if any(ord(c) < 32 or c == "\\" for c in value):
        raise ValueError("Control characters and backslashes are not allowed")
    return "'" + value.replace("'", "''") + "'"


def typed_sql(catalog):
    c = identifier(catalog)
    return f"""
    WITH typed AS (
      SELECT NULLIF(TRIM(order_id), '') AS order_id,
        NULLIF(TRIM(line_id), '') AS line_id,
        TRY_CAST(order_ts AS TIMESTAMP) AS order_ts,
        NULLIF(TRIM(customer_id), '') AS customer_id,
        LOWER(NULLIF(TRIM(customer_email), '')) AS customer_email,
        NULLIF(TRIM(product_id), '') AS product_id,
        COALESCE(NULLIF(TRIM(product_name), ''), 'Unknown') AS product_name,
        COALESCE(NULLIF(TRIM(category), ''), 'Unknown') AS category,
        COALESCE(NULLIF(TRIM(region), ''), 'Unknown') AS region,
        TRY_CAST(quantity AS DECIMAL(12,3)) AS quantity,
        TRY_CAST(unit_price AS DECIMAL(12,2)) AS unit_price,
        TRY_CAST(COALESCE(NULLIF(TRIM(discount_pct), ''), '0') AS DECIMAL(5,4)) AS discount_pct,
        LOWER(COALESCE(NULLIF(TRIM(status), ''), 'completed')) AS status,
        COALESCE(TRY_CAST(updated_at AS TIMESTAMP), TRY_CAST(order_ts AS TIMESTAMP)) AS updated_at,
        UPPER(NULLIF(TRIM(currency), '')) AS currency,
        ingest_ts, source_kind, source_ref, _row_hash
      FROM {c}.bronze.orders_raw
    )
    SELECT *, COALESCE(
      order_id IS NOT NULL AND line_id IS NOT NULL AND order_ts IS NOT NULL
      AND customer_id IS NOT NULL AND product_id IS NOT NULL
      AND quantity > 0 AND quantity <= 1000000 AND quantity = FLOOR(quantity)
      AND unit_price >= 0 AND unit_price <= 1000000
      AND discount_pct BETWEEN 0 AND 1
      AND status IN ('completed', 'cancelled', 'returned')
      AND currency = 'USD', FALSE) AS is_valid
    FROM typed
    """


def ranked_sql(catalog):
    """Rank updates before filtering so a bad correction cannot revive stale data."""
    c = identifier(catalog)
    return f"""SELECT *, ROW_NUMBER() OVER (
      PARTITION BY order_id, line_id ORDER BY updated_at DESC NULLS LAST,
        _row_hash DESC) AS version_rank
      FROM {c}.silver.orders_typed"""


def orders_sql(catalog):
    c = identifier(catalog)
    return f"""SELECT order_id, line_id, order_ts, CAST(order_ts AS DATE) AS order_date,
      customer_id, customer_email, product_id, product_name, category, region,
      CAST(quantity AS BIGINT) AS quantity, unit_price, discount_pct, status,
      updated_at, currency, ingest_ts, source_kind,
      CAST(ROUND(quantity * unit_price * (1 - discount_pct), 2) AS DECIMAL(18,2)) AS net_amount
      FROM {c}.silver.orders_ranked WHERE version_rank = 1 AND is_valid"""


def model_queries(catalog):
    """Return the silver and gold queries in dependency order."""
    c = identifier(catalog)
    sales = f"{c}.silver.orders"
    return {
        "silver.orders_typed": typed_sql(c),
        "silver.orders_ranked": ranked_sql(c),
        "silver.orders_quarantine": f"SELECT * FROM {c}.silver.orders_ranked WHERE version_rank = 1 AND NOT is_valid",
        "silver.orders": orders_sql(c),
        "gold.daily_revenue": f"""SELECT order_date, currency, SUM(net_amount) AS revenue,
          COUNT(DISTINCT order_id) AS order_count, SUM(quantity) AS units,
          COUNT(DISTINCT customer_id) AS active_customers,
          CAST(SUM(net_amount) / COUNT(DISTINCT order_id) AS DECIMAL(18,2)) AS average_order_value
          FROM {sales} WHERE status = 'completed' GROUP BY order_date, currency""",
        "gold.product_metrics": f"""SELECT product_id, product_name, category, currency,
          SUM(net_amount) AS revenue, SUM(quantity) AS units,
          COUNT(DISTINCT order_id) AS order_count
          FROM {sales} WHERE status = 'completed'
          GROUP BY product_id, product_name, category, currency""",
        "gold.category_revenue": f"""SELECT order_date, category, currency,
          SUM(net_amount) AS revenue, SUM(quantity) AS units
          FROM {sales} WHERE status = 'completed' GROUP BY order_date, category, currency""",
        "gold.regional_revenue": f"""SELECT order_date, region, currency,
          SUM(net_amount) AS revenue, COUNT(DISTINCT order_id) AS order_count
          FROM {sales} WHERE status = 'completed' GROUP BY order_date, region, currency""",
        "gold.customer_metrics": f"""SELECT customer_id, currency,
          MIN(order_date) AS first_order_date, MAX(order_date) AS last_order_date,
          COUNT(DISTINCT order_id) AS order_count, SUM(net_amount) AS lifetime_revenue,
          CAST(SUM(net_amount) / COUNT(DISTINCT order_id) AS DECIMAL(18,2)) AS average_order_value
          FROM {sales} WHERE status = 'completed' GROUP BY customer_id, currency""",
    }


def masked_view_sql(catalog, pii_group=""):
    """Mask email unless the querying user belongs to the configured account group."""
    c = identifier(catalog)
    allowed = f"is_account_group_member({literal(pii_group)})" if pii_group else "FALSE"
    return f"""WITH emails AS (
      SELECT customer_id, customer_email, ROW_NUMBER() OVER (
        PARTITION BY customer_id ORDER BY updated_at DESC, order_id DESC, line_id DESC
      ) AS rn FROM {c}.silver.orders
    )
    SELECT SHA2(m.customer_id, 256) AS customer_key,
      CASE WHEN {allowed} THEN e.customer_email ELSE '***MASKED***' END AS customer_email,
      m.currency, m.first_order_date, m.last_order_date, m.order_count,
      m.lifetime_revenue, m.average_order_value
    FROM {c}.gold.customer_metrics m LEFT JOIN emails e
      ON m.customer_id = e.customer_id AND e.rn = 1"""


# The raw customer table stays out of reader grants, even though it lives in gold.
PUBLIC_GOLD = ("daily_revenue", "product_metrics", "category_revenue",
               "regional_revenue", "customer_metrics_masked")
