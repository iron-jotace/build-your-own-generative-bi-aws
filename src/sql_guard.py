\
import re


FORBIDDEN = {
    "insert", "update", "delete", "drop", "alter", "create",
    "truncate", "merge", "grant", "revoke", "unload", "call",
}


class SQLValidationError(ValueError):
    pass


def validate_sql(sql, allowed_view):
    """
    Pedagogical guardrail, not a production SQL firewall.
    Production should also rely on IAM/Lake Formation/workgroup controls
    and preferably a real SQL parser.
    """
    if not sql or not isinstance(sql, str):
        raise SQLValidationError("SQL is empty.")

    normalized = " ".join(sql.strip().lower().split())
    normalized = normalized.rstrip(";").strip()

    if ";" in normalized:
        raise SQLValidationError("Multiple SQL statements are not allowed.")

    if not normalized.startswith("select"):
        raise SQLValidationError("Only SELECT statements are allowed.")

    if "--" in normalized or "/*" in normalized or "*/" in normalized:
        raise SQLValidationError("SQL comments are not allowed.")

    if re.search(r"\bselect\s+\*", normalized):
        raise SQLValidationError("SELECT * is not allowed.")

    for word in FORBIDDEN:
        if re.search(rf"\b{word}\b", normalized):
            raise SQLValidationError(f"Forbidden SQL operation: {word}")

    # Capture FROM/JOIN relations. This is intentionally simple for class.
    tables = re.findall(
        r'\b(?:from|join)\s+["`]?([a-zA-Z0-9_.-]+)["`]?',
        normalized,
    )

    if not tables:
        raise SQLValidationError("No FROM relation was detected.")

    expected = allowed_view.lower()

    for table in tables:
        short_name = table.split(".")[-1].strip('"`').lower()
        if short_name != expected:
            raise SQLValidationError(
                f"Unauthorized relation '{table}'. Allowed: {allowed_view}"
            )

    return True
