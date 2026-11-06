import unittest

from src.dashboard_planner import catalog_for_planner
from src.dashboard_sql_builder import build_component_sql
from src.dashboard_validator import DashboardValidationError, validate_dashboard


SEMANTIC = {
    "allowed_view": "vw_nexa_genbi_sales",
    "measures": {
        "revenue": {"sql": "SUM(revenue)"},
        "orders": {"sql": "COUNT(DISTINCT order_id)"},
        "average_order_value": {"sql": "SUM(revenue) / NULLIF(COUNT(DISTINCT order_id), 0)"},
        "margin": {"sql": "SUM(margin)"},
    },
    "dimensions": {
        "sale_date": {"column": "sale_date"},
        "category": {"column": "category"},
        "sales_channel": {"column": "sales_channel"},
    },
}


class MonthlyDashboardTests(unittest.TestCase):
    def test_sale_month_is_derived_from_approved_date(self):
        self.assertIn("sale_month", catalog_for_planner(SEMANTIC)["dimensions"])
        plan = validate_dashboard({"title": "Mensual", "components": [
            {"id": "trend", "type": "line", "metric": "revenue",
             "dimension": "sale_month"}
        ]}, SEMANTIC)
        sql = build_component_sql(plan["components"][0], SEMANTIC)
        self.assertIn("date_trunc('month', sale_date)", sql)
        self.assertIn("ORDER BY dimension_value ASC", sql)

    def test_no_sale_month_without_date_dimension(self):
        without_date = dict(SEMANTIC, dimensions={"category": {"column": "category"}})
        with self.assertRaises(DashboardValidationError):
            validate_dashboard({"title": "Mensual", "components": [
                {"id": "trend", "type": "line", "metric": "revenue",
                 "dimension": "sale_month"}
            ]}, without_date)

    def test_order_and_aov_use_approved_formulas(self):
        for metric, expression in [
            ("orders", "COUNT(DISTINCT order_id)"),
            ("average_order_value", "SUM(revenue) / NULLIF(COUNT(DISTINCT order_id), 0)"),
        ]:
            plan = validate_dashboard({"title": "Financiero", "components": [
                {"type": "kpi", "metric": metric}
            ]}, SEMANTIC)
            self.assertIn(expression, build_component_sql(plan["components"][0], SEMANTIC))


if __name__ == "__main__":
    unittest.main()
