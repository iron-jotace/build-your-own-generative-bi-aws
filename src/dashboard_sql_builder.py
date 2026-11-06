"""Deterministic SELECT compiler from trusted, human-approved semantic definitions."""
import re
from src.dashboard_validator import DashboardValidationError

SAFE_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
FORBIDDEN = re.compile(r";|--|/\*|\*/|\b(?:FROM|JOIN|UNION|SELECT|INSERT|DROP|DELETE|UPDATE|ALTER)\b", re.I)


def build_component_sql(component, semantic):
    """Build read-only SQL; no SQL fragment comes from the LLM's dashboard JSON."""
    metric_sql = semantic["measures"][component["metric"]]["sql"].strip()
    if FORBIDDEN.search(metric_sql):
        raise DashboardValidationError("Unsafe semantic SQL expression.")
    if not re.fullmatch(r"[a-zA-Z0-9_(),.\s+*/-]+", metric_sql):
        raise DashboardValidationError("Unexpected characters in approved metric expression.")
    view = semantic["allowed_view"]
    if not SAFE_NAME.fullmatch(view):
        raise DashboardValidationError("Invalid approved view name.")
    dimension = component["dimension"]
    if dimension is None:
        return f"SELECT {metric_sql} AS metric_value FROM {view}"
    column = semantic["dimensions"][dimension].get("column")
    if not isinstance(column, str) or not SAFE_NAME.fullmatch(column):
        raise DashboardValidationError("Invalid approved dimension column.")
    dim_expr = f"date_trunc('month', {column})" if dimension == "sale_month" else column
    ordering = "metric_value DESC" if component["type"] in {"bar", "table"} else "dimension_value ASC"
    return (f"SELECT {dim_expr} AS dimension_value, {metric_sql} AS metric_value "
            f"FROM {view} GROUP BY 1 ORDER BY {ordering} LIMIT {component['limit']}")
