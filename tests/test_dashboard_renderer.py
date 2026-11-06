"""Format tests do not need AWS or Streamlit runtime."""
import unittest

from src.dashboard_renderer import _format_value


class DashboardFormatTests(unittest.TestCase):
    def test_cost_currency_and_margin_percentage(self):
        semantic = {"business_context": {"currency_symbol": "S/"}}
        self.assertEqual(_format_value(368865.37, "cost", semantic), "S/368,865.37")
        self.assertEqual(_format_value(0.35925, "margin_pct", semantic), "35.93%")

    def test_not_presenting_units_as_currency(self):
        semantic = {"business_context": {"currency_symbol": "S/"}}
        self.assertEqual(_format_value(916, "orders", semantic), "916")


if __name__ == "__main__":
    unittest.main()
