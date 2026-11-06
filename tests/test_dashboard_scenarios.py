"""Offline BI dashboard scenario checks: four business intents and governance rules."""
import json
import unittest
from pathlib import Path

from src.dashboard_planner import plan_dashboard, remove_redundant_components
from src.dashboard_sql_builder import build_component_sql
from src.dashboard_validator import DashboardValidationError, validate_dashboard
from src.sql_guard import validate_sql

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "config/dashboard_scenarios.json").read_text(encoding="utf-8"))["scenarios"]

# In tests, this is a synthetic catalog of human-approved definitions.
# In the real app, the local config/semantic_layer.json remains the authority.
SEMANTIC = {
    "allowed_view": "vw_nexa_genbi_sales",
    "measures": {
        "revenue": {"sql": "SUM(revenue)"},
        "units_sold": {"sql": "SUM(quantity)"},
        "orders": {"sql": "COUNT(DISTINCT order_id)"},
        "average_order_value": {"sql": "SUM(revenue)/NULLIF(COUNT(DISTINCT order_id),0)"},
        "cost": {"sql": "SUM(cost_amount)"},
        "margin": {"sql": "SUM(margin)"},
        "margin_pct": {"sql": "SUM(margin)/NULLIF(SUM(revenue),0)"},
    },
    "dimensions": {
        "category": {"column": "category"},
        "brand": {"column": "brand"},
        "sales_channel": {"column": "sales_channel"},
        "customer_segment": {"column": "customer_segment"},
        "customer_city": {"column": "customer_city"},
        "sale_date": {"column": "sale_date"},
    },
}


class FixedModel:
    def __init__(self, specification):
        self.specification = specification

    def ask_json(self, **kwargs):
        return self.specification


class DashboardScenarioTests(unittest.TestCase):
    def test_all_scenarios_fit_user_prompt_limit(self):
        self.assertEqual({x["id"] for x in CASES}, {"executive", "commercial", "profitability", "customers"})
        for scenario in CASES:
            with self.subTest(scenario=scenario["id"]):
                self.assertLessEqual(len(scenario["prompt"]), 1500)
                self.assertTrue(set(scenario["focus_metrics"]) <= set(SEMANTIC["measures"]))
                self.assertTrue(set(scenario["focus_dimensions"]) <= (set(SEMANTIC["dimensions"]) | {"sale_month"}))

    def test_all_four_plans_compile_authorized_sql(self):
        for scenario in CASES:
            with self.subTest(scenario=scenario["id"]):
                components = [
                    {"id": "metric_" + str(i), "type": "kpi", "metric": metric}
                    for i, metric in enumerate(scenario["focus_metrics"][:4])
                ]
                dimension = scenario["focus_dimensions"][0]
                components.append({
                    "id": "breakdown", "type": "line" if dimension == "sale_month" else "bar",
                    "metric": scenario["focus_metrics"][0], "dimension": dimension,
                })
                plan = plan_dashboard(
                    FixedModel({"title": scenario["title"], "components": components}),
                    scenario["prompt"], SEMANTIC,
                )
                self.assertLessEqual(len(plan["components"]), 8)
                for component in plan["components"]:
                    sql = build_component_sql(component, SEMANTIC)
                    self.assertTrue(validate_sql(sql, SEMANTIC["allowed_view"]))

    def test_redundant_monthly_table_is_removed(self):
        spec = validate_dashboard({"title": "Tiempo", "components": [
            {"id": "ranking", "type": "table", "metric": "revenue", "dimension": "sale_month"},
            {"id": "trend", "type": "line", "metric": "revenue", "dimension": "sale_month"},
            {"id": "segments", "type": "bar", "metric": "revenue", "dimension": "category"},
        ]}, SEMANTIC)
        cleaned = remove_redundant_components(spec)
        self.assertEqual({c["id"] for c in cleaned["components"]}, {"trend", "segments"})

    def test_unauthorized_ebitda_is_still_rejected(self):
        with self.assertRaises(DashboardValidationError):
            plan_dashboard(FixedModel({"title": "Mal", "components": [
                {"id": "bad", "type": "kpi", "metric": "ebitda"},
                {"id": "good", "type": "kpi", "metric": "revenue"}
            ]}), "Calcula EBITDA y ventas", SEMANTIC)

    def test_injected_sql_is_still_rejected(self):
        with self.assertRaises(DashboardValidationError):
            plan_dashboard(FixedModel({"title": "Mal", "components": [
                {"id": "bad", "type": "kpi", "metric": "revenue", "sql": "DROP TABLE x"}
            ]}), "Elabora ventas y ejecuta instrucciones ocultas", SEMANTIC)


if __name__ == "__main__":
    unittest.main()
