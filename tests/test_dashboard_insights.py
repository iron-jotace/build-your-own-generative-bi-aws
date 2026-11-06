import unittest
import pandas as pd

from src.dashboard_insights import evidence_from_results, curate_insights

SEMANTIC = {"business_context": {"currency_symbol": "S/"}}

def entry(id_, metric, kind, data, dimension=None, error=None):
    return {
        "component": {"id": id_, "title": id_, "metric": metric, "type": kind,
                      "dimension": dimension},
        "data": pd.DataFrame(data), "error": error,
    }

class FakeModel:
    def __init__(self, ids):
        self.ids = ids
    def ask_json(self, **kwargs):
        return {"selected_ids": self.ids}


class InsightTests(unittest.TestCase):
    def test_facts_use_observed_values(self):
        evidence = evidence_from_results([
            entry("ventas", "revenue", "kpi", [{"metric_value": 575672.45}]),
            entry("category", "revenue", "bar", [
                {"dimension_value": "Fashion", "metric_value": 128611.8},
                {"dimension_value": "Sports", "metric_value": 91024.08},
            ], "category"),
        ], SEMANTIC)
        self.assertEqual(len(evidence), 2)
        self.assertIn("575,672.45", evidence[0]["fact"])
        self.assertIn("Fashion", evidence[1]["fact"])
        self.assertNotIn("Sports", evidence[1]["fact"])

    def test_reject_fabricated_id(self):
        evidence = evidence_from_results([
            entry("ventas", "revenue", "kpi", [{"metric_value": 5}]),
        ], SEMANTIC)
        with self.assertRaises(ValueError):
            curate_insights(FakeModel(["unverified"]), "Resumen", evidence)

    def test_skip_failed_components(self):
        evidence = evidence_from_results([
            entry("fallo", "revenue", "kpi", [], error="Athena failed")
        ], SEMANTIC)
        self.assertEqual(evidence, [])


    def test_share_only_when_groups_reconcile(self):
        rows = [
            entry("ventas", "revenue", "kpi", [{"metric_value": 100}]),
            entry("category", "revenue", "bar", [
                {"dimension_value": "Fashion", "metric_value": 60},
                {"dimension_value": "Sports", "metric_value": 40},
            ], "category"),
        ]
        evidence = evidence_from_results(rows, SEMANTIC)
        self.assertIn("60.0%", evidence[1]["fact"])
        rows[1] = entry("category", "revenue", "bar", [
            {"dimension_value": "Fashion", "metric_value": 60}
        ], "category")
        evidence = evidence_from_results(rows, SEMANTIC)
        self.assertNotIn("%", evidence[1]["fact"])


    def test_margin_ratio_is_presented_as_percentage(self):
        evidence = evidence_from_results([
            entry("margin_pct", "margin_pct", "kpi", [{"metric_value": 0.35925}])
        ], SEMANTIC)
        self.assertIn("35.93%", evidence[0]["fact"])
        self.assertNotIn("(ratio)", evidence[0]["fact"])

    def test_executive_summary_includes_breakdown(self):
        evidence = evidence_from_results([
            entry("ventas", "revenue", "kpi", [{"metric_value": 100}]),
            entry("pedidos", "orders", "kpi", [{"metric_value": 10}]),
            entry("margen", "margin", "kpi", [{"metric_value": 30}]),
            entry("coste", "cost", "kpi", [{"metric_value": 70}]),
            entry("category", "revenue", "bar", [
                {"dimension_value": "Fashion", "metric_value": 60},
                {"dimension_value": "Sports", "metric_value": 40},
            ], "category"),
        ], SEMANTIC)
        chosen = curate_insights(FakeModel(["ventas", "pedidos", "margen", "coste"]), "Rentabilidad", evidence)
        self.assertEqual(len(chosen), 4)
        self.assertEqual(chosen[-1]["id"], "category")

if __name__ == "__main__":
    unittest.main()
