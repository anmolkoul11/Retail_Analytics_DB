"""Execute shared SQL in DuckDB; Databricks acceptance checks are separate."""
import csv
import hashlib
import importlib.util
from pathlib import Path
import unittest

import duckdb
import yaml

from retail.model import COLUMNS, PUBLIC_GOLD, identifier, literal, masked_view_sql, model_queries

ROOT = Path(__file__).resolve().parents[1]


def connect(rows):
    db = duckdb.connect(config={"threads": 1})
    db.execute("ATTACH ':memory:' AS retail_demo")
    for schema in ("bronze", "silver", "gold"):
        db.execute(f"CREATE SCHEMA retail_demo.{schema}")
    fields = ', '.join(f'{n} VARCHAR' for n in COLUMNS)
    db.execute(f"CREATE TABLE retail_demo.bronze.orders_raw ({fields}, ingest_ts TIMESTAMP, source_kind VARCHAR, source_ref VARCHAR, _row_hash VARCHAR)")
    values = []
    for row in rows:
        raw = [row.get(n) for n in COLUMNS]
        digest = hashlib.sha256(str(raw).encode()).hexdigest()
        values.append(raw + ["2026-04-10 00:00:00", "sample", "fixture", digest])
    # Fixture literals avoid optional pandas/numpy discovery during Python binding.
    def fixture_literal(value):
        return 'NULL' if value is None else "'" + value.replace("'", "''") + "'"
    db.execute('INSERT INTO retail_demo.bronze.orders_raw VALUES ' + ','.join(
        '(' + ','.join(fixture_literal(v) for v in row) + ')' for row in values))
    for target, query in model_queries("retail_demo").items():
        db.execute(f"CREATE TABLE retail_demo.{target} AS {query}")
    return db


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (ROOT / 'data/sample_orders.csv').open(encoding='utf-8', newline='') as f:
            cls.rows = list(csv.DictReader(f))
        cls.db = connect(cls.rows)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def scalar(self, sql):
        return self.db.execute(sql).fetchone()[0]

    def test_sample_counts_and_latest_invalid_update(self):
        self.assertEqual(len(self.rows), 1211)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM retail_demo.silver.orders'), 1199)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM retail_demo.silver.orders_quarantine'), 9)
        self.assertEqual(self.scalar("SELECT quantity FROM retail_demo.silver.orders WHERE order_id = 'O00000' AND line_id = '2'"), 4)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM retail_demo.silver.orders WHERE order_id = 'O00001' AND line_id = '1'"), 0)

    def test_no_duplicate_keys(self):
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM (SELECT order_id, line_id FROM retail_demo.silver.orders GROUP BY ALL HAVING COUNT(*) > 1)'), 0)

    def test_all_gold_revenue_reconciles(self):
        expected = self.scalar("SELECT SUM(net_amount) FROM retail_demo.silver.orders WHERE status = 'completed'")
        for name, metric in [('daily_revenue','revenue'), ('product_metrics','revenue'), ('category_revenue','revenue'), ('regional_revenue','revenue'), ('customer_metrics','lifetime_revenue')]:
            self.assertEqual(self.scalar(f'SELECT SUM({metric}) FROM retail_demo.gold.{name}'), expected)

    def test_snapshot_replays_and_input_order_do_not_change_results(self):
        db = connect(list(reversed(self.rows)) + self.rows)
        try:
            for name in ('silver.orders', 'gold.daily_revenue'):
                # Ingestion metadata is fixed in fixtures; raw duplicates cannot inflate metrics.
                expected = self.db.execute(f'SELECT * FROM retail_demo.{name} ORDER BY ALL').fetchall()
                self.assertEqual(db.execute(f'SELECT * FROM retail_demo.{name} ORDER BY ALL').fetchall(), expected)
        finally:
            db.close()

    def test_null_handling_and_line_rounding(self):
        row = {**self.rows[10], 'order_id': 'EDGE', 'quantity': '3', 'unit_price': '0.05',
               'discount_pct': '0.1', 'category': '', 'region': '', 'status': 'completed', 'customer_email': ''}
        db = connect([row])
        try:
            actual = db.execute('SELECT category, region, customer_email, net_amount FROM retail_demo.silver.orders').fetchone()
            self.assertEqual(actual[:3], ('Unknown', 'Unknown', None))
            self.assertEqual(str(actual[3]), '0.14')
        finally:
            db.close()

    def test_masking_defaults_and_account_group(self):
        # Only function dialect substitutions; the CASE, joins, and columns are unchanged.
        query = masked_view_sql('retail_demo').replace('SHA2(m.customer_id, 256)', 'sha256(m.customer_id)')
        emails = self.db.execute(query).fetchall()
        self.assertTrue(emails)
        self.assertTrue(all(row[1] == '***MASKED***' for row in emails))
        for member in (True, False):
            sql = masked_view_sql('retail_demo', 'retail_pii_readers').replace('SHA2(m.customer_id, 256)', 'sha256(m.customer_id)')
            sql = sql.replace("is_account_group_member('retail_pii_readers')", str(member).upper())
            result = self.db.execute(sql).fetchall()
            self.assertTrue(all((row[1].endswith('@example.invalid') if member else row[1] == '***MASKED***') for row in result))
        self.assertNotIn('customer_metrics', PUBLIC_GOLD)

    def test_rejects_unsafe_identifiers_and_literals(self):
        for bad in ('x; DROP TABLE t', 'x.y', 'x`', ''):
            with self.assertRaises(ValueError):
                identifier(bad)
        self.assertEqual(literal("O'Brien"), "'O''Brien'")
        with self.assertRaises(ValueError):
            literal('a\\b')

    def test_job_dependencies_and_paths(self):
        config = yaml.safe_load((ROOT / 'resources/retail.yml').read_text())
        jobs = config['resources']['jobs']
        self.assertEqual(jobs['retail_demo']['schedule']['pause_status'], 'PAUSED')
        self.assertTrue(config['resources']['pipelines']['retail_pipeline']['serverless'])
        for job in jobs.values():
            seen = set()
            for task in job['tasks']:
                self.assertTrue(all(d['task_key'] in seen for d in task.get('depends_on', [])))
                seen.add(task['task_key'])
                if 'notebook_task' in task:
                    self.assertTrue((ROOT / 'resources' / task['notebook_task']['notebook_path']).is_file())
                self.assertNotIn('new_cluster', task)


if __name__ == '__main__':
    unittest.main()
