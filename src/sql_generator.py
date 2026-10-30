import re
import unicodedata


SQL_SYSTEM_PROMPT = """
You are the NL-to-SQL component of a governed
Business Intelligence application.

The application may provide a FORCED SEMANTIC METRIC.

If a forced metric is provided:
- You MUST use exactly its approved SQL expression.
- You MUST NOT replace it with another metric.
- You MUST NOT reinterpret its business meaning.
- The metric name is a semantic concept, not a physical column.

General rules:
- Generate exactly one SELECT statement.
- Query ONLY the allowed view.
- Never use SELECT *.
- Never invent columns.
- Never modify data.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER,
  CREATE, TRUNCATE, MERGE, GRANT or REVOKE.
- Do not add dimensions unless required by the question.
- If the question asks for one KPI only, return one KPI only.
- Add GROUP BY only when the user requests a breakdown,
  comparison, ranking, trend or dimension.
- Prefer explicit aliases.
- Use LIMIT 100 for ranked or tabular results.

Return SQL ONLY.

Do not return JSON.
Do not explain the SQL.
Markdown SQL fences are allowed.
"""


def normalize_text(text):
    """
    Normalize text for semantic matching.

    Example:
    'Facturación' -> 'facturacion'
    """
    text = text.lower().strip()

    text = unicodedata.normalize(
        "NFD",
        text,
    )

    text = "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"
    )

    text = re.sub(
        r"[^a-z0-9_% ]+",
        " ",
        text,
    )

    return " ".join(text.split())


def resolve_semantic_metric(question, semantic_layer):
    """
    Resolve the business metric BEFORE calling the LLM.

    Priority:
    1. Explicit measure synonyms.
    2. Measure label/name.
    3. Governed ambiguity defaults.

    Returns None when no metric can be determined
    deterministically.
    """

    normalized_question = normalize_text(question)

    matches = []

    measures = semantic_layer.get(
        "measures",
        {},
    )

    # --------------------------------------------------
    # 1. Search measure names, labels and synonyms
    # --------------------------------------------------

    for metric_name, metric in measures.items():

        candidates = [
            metric_name.replace("_", " "),
            metric.get("label", ""),
            *metric.get("synonyms", []),
        ]

        for candidate in candidates:

            if not candidate:
                continue

            normalized_candidate = normalize_text(
                candidate
            )

            if (
                normalized_candidate
                and normalized_candidate
                in normalized_question
            ):
                matches.append(
                    {
                        "metric_name": metric_name,
                        "metric": metric,
                        "matched_term": candidate,
                        "match_length": len(
                            normalized_candidate
                        ),
                        "source": "synonym",
                    }
                )

    # Prefer the longest / most specific match.
    if matches:

        matches.sort(
            key=lambda item: item["match_length"],
            reverse=True,
        )

        return matches[0]

    # --------------------------------------------------
    # 2. Governed ambiguities/defaults
    # --------------------------------------------------

    ambiguities = semantic_layer.get(
        "ambiguities",
        {},
    )

    for term, rule in ambiguities.items():

        normalized_term = normalize_text(term)

        if normalized_term in normalized_question:

            default_metric = rule.get(
                "approved_default"
            )

            if (
                default_metric
                and default_metric in measures
            ):
                return {
                    "metric_name": default_metric,
                    "metric": measures[
                        default_metric
                    ],
                    "matched_term": term,
                    "match_length": len(
                        normalized_term
                    ),
                    "source": "approved_default",
                }

    return None


def extract_sql(text):
    """
    Extract SQL from either plain text or a Markdown
    SQL code block.
    """

    if text is None:
        raise ValueError(
            "Bedrock returned no SQL."
        )

    cleaned = text.strip()

    if not cleaned:
        raise ValueError(
            "Bedrock returned empty SQL."
        )

    # Remove Markdown fence.
    cleaned = re.sub(
        r"^```(?:sql)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
    )

    return cleaned.strip()


def generate_sql(
    bedrock_client,
    question,
    semantic_layer,
):
    """
    Resolve governed semantics first, then ask Bedrock
    to generate SQL using those semantics.
    """

    resolved = resolve_semantic_metric(
        question,
        semantic_layer,
    )

    allowed_view = semantic_layer[
        "allowed_view"
    ]

    # --------------------------------------------------
    # Semantic metric context
    # --------------------------------------------------

    if resolved:

        metric_name = resolved[
            "metric_name"
        ]

        metric = resolved["metric"]

        metric_sql = metric["sql"]

        semantic_context = f"""
FORCED SEMANTIC METRIC

Metric key:
{metric_name}

Business label:
{metric.get("label", metric_name)}

Approved SQL expression:
{metric_sql}

Matched business term:
{resolved["matched_term"]}

IMPORTANT:
You MUST use this exact SQL expression.

Do NOT substitute another metric.
Do NOT treat "{metric_name}" as a physical column.
"""

        interpretation = (
            f'"{resolved["matched_term"]}" '
            f'→ {metric.get("label", metric_name)}'
        )

        semantic_rule = (
            f"Semantic Layer resolved "
            f"{resolved['matched_term']} "
            f"to {metric_name}"
        )

    else:

        metric_name = None

        semantic_context = """
NO FORCED METRIC WAS RESOLVED.

Use the approved semantic layer and business rules
to interpret the question.

Do not invent business definitions.
"""

        interpretation = (
            "No deterministic metric match; "
            "Bedrock interpretation required."
        )

        semantic_rule = (
            "No direct semantic synonym matched."
        )

    # --------------------------------------------------
    # Prompt
    # --------------------------------------------------

    user_prompt = f"""
ALLOWED VIEW

{allowed_view}


APPROVED SEMANTIC LAYER

{semantic_layer}


{semantic_context}


BUSINESS QUESTION

{question}


Generate the SQL query.
"""

    raw_sql = bedrock_client.ask(
        system_prompt=SQL_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=1000,
        temperature=0,
    )

    sql = extract_sql(raw_sql)

    return {
        "status": "ok",
        "interpretation": interpretation,
        "metric_used": metric_name,
        "semantic_rule_applied": semantic_rule,
        "sql": sql,
        "clarification_question": None,
    }