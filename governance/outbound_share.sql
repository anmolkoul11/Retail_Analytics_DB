-- Run these manually to inspect the outbound sharing setup.
-- The jobs do not run this file, and it does not grant access to recipients.
CREATE SHARE IF NOT EXISTS retail_demo_gold_share;
-- Add the pipeline output through the API with its materialized-view type.
-- Save the JSON below as request.json, then run:
-- databricks shares update retail_demo_gold_share --json '@request.json'
-- {"updates":[{"action":"ADD","data_object":{"name":"retail_demo.gold.daily_revenue","data_object_type":"MATERIALIZED_VIEW"}}]}
-- For a Delta table from the notebook path, use ALTER SHARE ... ADD TABLE instead.
-- Inspect the share before adding an asset that may already be present.
DESCRIBE SHARE retail_demo_gold_share;
