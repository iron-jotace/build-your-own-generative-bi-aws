import unittest
from src.dashboard_validator import validate_dashboard, DashboardValidationError
from src.dashboard_sql_builder import build_component_sql

SEMANTIC = {
    "allowed_view": "vw_nexa_genbi_sales",
    "measures": {"revenue": {"sql": "SUM(revenue)"}, "orders": {"sql": "COUNT(DISTINCT order_id)"}},
    "dimensions": {"category": {"column": "category"}, "sale_month": {"column": "sale_date"}},
}


class DashboardTests(unittest.TestCase):
    def test_valid_build(self):
        spec = validate_dashboard({"title": "Ventas", "components": [
            {"type": "bar", "metric": "revenue", "dimension": "category"}
        ]}, SEMANTIC)
        sql = build_component_sql(spec["components"][0], SEMANTIC)
        self.assertIn("SUM(revenue)", sql)
        self.assertIn("FROM vw_nexa_genbi_sales", sql)
        self.assertIn("GROUP BY 1", sql)

    def test_reject_unknown_metric(self):
        with self.assertRaises(DashboardValidationError):
            validate_dashboard({"title": "X", "components": [{"type": "kpi", "metric": "ebitda"}]}, SEMANTIC)

    def test_reject_extra_sql(self):
        with self.assertRaises(DashboardValidationError):
            validate_dashboard({"title": "X", "components": [{"type": "kpi", "metric": "revenue", "sql": "DROP TABLE x"}]}, SEMANTIC)


if __name__ == "__main__":
    unittest.main()
