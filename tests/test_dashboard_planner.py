import unittest

from src.dashboard_planner import catalog_for_planner, plan_dashboard
from src.dashboard_validator import DashboardValidationError

SEMANTIC = {
    "dataset": "NEXA",
    "grain": "order line",
    "allowed_view": "vw_nexa_genbi_sales",
    "measures": {
        "revenue": {"label": "Revenue", "sql": "SUM(revenue)", "synonyms": ["ventas"]},
        "orders": {"label": "Pedidos", "sql": "COUNT(DISTINCT order_id)"},
    },
    "dimensions": {"category": {"column": "category", "label": "Categoria"}},
}


class FakeBedrock:
    def __init__(self, response):
        self.response = response
        self.calls = []
    def ask_json(self, system_prompt, user_prompt, max_tokens):
        self.calls.append((system_prompt, user_prompt))
        return self.response


class PlannerTests(unittest.TestCase):
    def test_catalog_excludes_sql(self):
        catalog = catalog_for_planner(SEMANTIC)
        self.assertIn("revenue", catalog["metrics"])
        self.assertNotIn("sql", catalog["metrics"]["revenue"])

    def test_planner_validated(self):
        model = FakeBedrock({"title": "NEXA Ventas", "components": [
            {"id": "sales", "type": "kpi", "metric": "revenue", "dimension": None}
        ]})
        result = plan_dashboard(model, "Ventas generales para dirección", SEMANTIC)
        self.assertEqual(result["components"][0]["metric"], "revenue")
        self.assertEqual(len(model.calls), 1)

    def test_rejects_unapproved_metric(self):
        model = FakeBedrock({"title": "NEXA", "components": [
            {"id": "bad", "type": "kpi", "metric": "ebitda"}
        ]})
        with self.assertRaises(DashboardValidationError):
            plan_dashboard(model, "Quiero un dashboard con EBITDA", SEMANTIC)

    def test_rejects_llm_sql(self):
        model = FakeBedrock({"title": "NEXA", "components": [
            {"id": "bad", "type": "kpi", "metric": "revenue",
             "sql": "SELECT * FROM secrets"}
        ]})
        with self.assertRaises(DashboardValidationError):
            plan_dashboard(model, "Quiero un dashboard financiero", SEMANTIC)



    def test_retry_kpi_with_invalid_dimension(self):
        class FirstInvalidThenValid:
            def __init__(self):
                self.calls = []
            def ask_json(self, system_prompt, user_prompt, max_tokens):
                self.calls.append(user_prompt)
                if len(self.calls) == 1:
                    return {"title": "Clientes", "components": [
                        {"id": "segment_sales", "type": "kpi", "metric": "revenue",
                         "dimension": "category"}]}
                return {"title": "Clientes", "components": [
                    {"id": "segment_sales", "type": "bar", "metric": "revenue",
                     "dimension": "category"}]}
        model = FirstInvalidThenValid()
        plan = plan_dashboard(model, "Analiza ingresos por segmentos", SEMANTIC)
        self.assertEqual(plan["components"][0]["type"], "bar")
        self.assertEqual(len(model.calls), 2)
        self.assertIn("KPI cannot have a grouping dimension", model.calls[1])

    def test_retry_still_rejects_second_invalid_plan(self):
        model = FakeBedrock({"title": "Clientes", "components": [
            {"id": "bad", "type": "kpi", "metric": "revenue",
             "dimension": "category"}]})
        with self.assertRaises(DashboardValidationError):
            plan_dashboard(model, "Analiza ingresos por segmentos", SEMANTIC)
        self.assertEqual(len(model.calls), 2)

if __name__ == "__main__":
    unittest.main()
