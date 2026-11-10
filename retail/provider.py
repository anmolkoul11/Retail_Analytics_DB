"""Flatten Databricks' CC BY 4.0 retail sample into order lines.

Keep the original order JSON and split partial promotions into two price tiers
so regular-price units do not receive the discount.
"""
from retail.model import identifier


def provider_adapter_sql(provider_catalog="retail_provider"):
    """Build the adapter view over the shared orders and lookup tables."""
    p = identifier(provider_catalog)
    line_schema = 'ARRAY<STRUCT<curr:STRING,id:STRING,name:STRING,price:STRING,qty:STRING,promotion_info:STRUCT<promo_disc:STRING,promo_qty:STRING>>>'
    return f"""
    WITH parsed AS (
      SELECT *, from_json(ordered_products, '{line_schema}') AS products
      FROM {p}.v01.sales_orders
    ), lines AS (
      SELECT o.order_number, o.customer_id, o.order_datetime,
        o.ordered_products AS provider_ordered_products,
        o.number_of_line_items AS provider_declared_lines,
        size(o.products) AS provider_actual_lines, x.pos, x.item
      FROM parsed o LATERAL VIEW posexplode_outer(o.products) x AS pos, item
    ), typed AS (
      SELECT *, TRY_CAST(item.qty AS BIGINT) AS units,
        TRY_CAST(item.promotion_info.promo_qty AS BIGINT) AS promo_units,
        TRY_CAST(item.promotion_info.promo_disc AS DECIMAL(5,4)) AS promo_discount
      FROM lines
    ), tiers AS (
      SELECT *, 'regular' AS tier,
        CASE WHEN item.promotion_info IS NULL THEN units ELSE units - promo_units END AS tier_units,
        CAST(0 AS DECIMAL(5,4)) AS tier_discount FROM typed
      WHERE item.promotion_info IS NULL OR units - promo_units > 0
      UNION ALL
      SELECT *, 'promo' AS tier, promo_units AS tier_units, promo_discount AS tier_discount
      FROM typed WHERE item.promotion_info IS NOT NULL
    ), customer_region AS (
      SELECT customer_id, region, ROW_NUMBER() OVER (
        PARTITION BY customer_id ORDER BY valid_from DESC NULLS LAST, region DESC
      ) AS rn FROM {p}.v01.customers
    ), category_lookup AS (
      SELECT product_name,
        CASE WHEN COUNT(DISTINCT product_category) = 1 THEN MAX(product_category)
          ELSE 'Unknown' END AS category
      FROM {p}.v01.sales GROUP BY product_name
    )
    SELECT CAST(t.order_number AS STRING) AS order_id,
      CONCAT(COALESCE(CAST(t.pos AS STRING), 'unparsed'), ':', t.tier) AS line_id,
      CAST(timestamp_seconds(t.order_datetime) AS STRING) AS order_ts,
      CAST(t.customer_id AS STRING) AS customer_id, CAST(NULL AS STRING) AS customer_email,
      t.item.id AS product_id, t.item.name AS product_name,
      COALESCE(k.category, 'Unknown') AS category, COALESCE(c.region, 'Unknown') AS region,
      CASE WHEN t.provider_declared_lines = t.provider_actual_lines
        AND (t.item.promotion_info IS NULL OR (t.promo_units BETWEEN 0 AND t.units))
        THEN CAST(t.tier_units AS STRING) ELSE CAST(NULL AS STRING) END AS quantity,
      t.item.price AS unit_price, CAST(t.tier_discount AS STRING) AS discount_pct,
      'completed' AS status, CAST(timestamp_seconds(t.order_datetime) AS STRING) AS updated_at,
      t.item.curr AS currency, t.provider_ordered_products,
      t.provider_declared_lines, t.provider_actual_lines,
      CASE WHEN t.provider_declared_lines <> t.provider_actual_lines THEN 'line_count_mismatch'
        WHEN t.item.id IS NULL THEN 'unparsed_line'
        WHEN t.item.promotion_info IS NOT NULL AND NOT (t.promo_units BETWEEN 0 AND t.units)
          THEN 'invalid_promotion_quantity' ELSE 'check_canonical_fields' END AS provider_quality_reason
    FROM tiers t LEFT JOIN customer_region c ON t.customer_id = c.customer_id AND c.rn = 1
      LEFT JOIN category_lookup k ON t.item.name = k.product_name
    """
