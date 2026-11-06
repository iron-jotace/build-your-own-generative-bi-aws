"""Deterministic SELECT compiler; never interpolates LLM-produced SQL."""
import re
from src.dashboard_validator import DashboardValidationError

SAFE_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
SAFE_METRIC_SQL = re.compile(
    r"^(?:SUM|COUNT|AVG|MIN|MAX)\\([A-Za-z_][A-Za-z0-9_]*\\)$"
)
# Trusted semantic definitions may use composed aggregates, such as AOV.
# Expressions originate only from the human-approved local file, never Bedrock.
FORBIDDEN = re.compile(r";|--|/\\*|\\*/|\\b(?:FROM|JOIN|UNION|SELECT|INSERT|DROP|DELETE|UPDATE|ALTER)\\b", re.I)


def build_component_sql(component, semantic):
    metric_name = component["metric"]
    metric_sql = semantic["measures"][metric_name]["sql"].strip()
    if FORBIDDEN.search(metric_sql):
        raise DashboardValidationError("Unsafe semantic SQL expression.")
    if not re.fullmatch(r"[a-zA-Z0-9_(),.\\s+*/-]+", metric_sql):
        raise DashboardValidationError("Unexpected characters in metric expression.")
    view = semantic["allowed_view"]
    if not SAFE_NAME.fullmatch(view):
        raise DashboardValidationError("Invalid approved view name.")
    dimension = component["dimension"]
    if dimension is None:
        return f"SELECT {metric_sql} AS metric_value FROM {view}"
    dim_info = semantic["dimensions"][dimension]
    col = dim_info.get("column")
    if not isinstance(col, str) or not SAFE_NAME.fullmatch(col):
        raise DashboardValidationError("Invalid approved dimension column.")
    dim_expr = f"date_trunc('month', {col})" if dimension == "sale_month" else col
    descending = " ORDER BY metric_value DESC" if component["type"] in {"bar", "table"} else " ORDER BY dimension_value ASC"
    limit = component["limit"]
    return (
        f"SELECT {dim_expr} AS dimension_value, {metric_sql} AS metric_value "
        f"FROM {view} GROUP BY 1" + descending + f" LIMIT {limit}"
    )
