import unittest
import pandas as pd
from src.dashboard_runtime import execute_dashboard

SEMANTIC = {
    "allowed_view": "vw_nexa_genbi_sales",
    "measures": {"revenue": {"sql": "SUM(revenue)"}},
    "dimensions": {"category": {"column": "category"}},
}

class FakeAthena:
    def __init__(self):
        self.queries = []
    def run(self, sql):
        self.queries.append(sql)
        return pd.DataFrame([{"metric_value": "123.50"}]), {"query_execution_id": "fake"}

class RuntimeTests(unittest.TestCase):
    def test_queries_are_compiled_and_results_typed(self):
        fake = FakeAthena()
        spec, results = execute_dashboard({
            "title": "Test", "components": [
                {"id": "total", "type": "kpi", "metric": "revenue"}
            ]
        }, SEMANTIC, fake)
        self.assertEqual(len(fake.queries), 1)
        self.assertEqual(float(results[0]["data"].iloc[0]["metric_value"]), 123.50)
        self.assertIsNone(results[0]["error"])

    def test_invalid_metric_never_reaches_athena(self):
        fake = FakeAthena()
        with self.assertRaises(ValueError):
            execute_dashboard({
                "title": "Test", "components": [
                    {"type": "kpi", "metric": "ebitda"}
                ]
            }, SEMANTIC, fake)
        self.assertEqual(fake.queries, [])


if __name__ == "__main__":
    unittest.main()
