-- OPTIONAL, MANUAL stretch goal; not executed by either job.
-- Run statement-by-statement only after inspecting the provider privileges.
-- No recipient is created and no recipient access is granted here.
CREATE SHARE IF NOT EXISTS retail_demo_gold_share;
-- The verified API operation for pipeline output uses data_object_type=MATERIALIZED_VIEW:
-- databricks shares update retail_demo_gold_share --json @request.json
-- {"updates":[{"action":"ADD","data_object":{"name":"retail_demo.gold.daily_revenue","data_object_type":"MATERIALIZED_VIEW"}}]}
-- For notebook fallback Delta tables, ADD TABLE is the appropriate SQL operation.
-- An existing share may already contain the asset; an already-added error is benign.
DESCRIBE SHARE retail_demo_gold_share;
