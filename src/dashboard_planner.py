"""Bedrock plans declarative dashboard layouts; it never produces SQL or executable Python."""
import json

from src.dashboard_validator import validate_dashboard


PLANNER_SYSTEM_PROMPT = """
Eres un diseñador de dashboards de Business Intelligence para NEXA Retail.
Tu única función es proponer una especificación DECLARATIVA de dashboard.
Devuelve ÚNICAMENTE un objeto JSON válido con estas claves:
{
 "title": "titulo de negocio",
 "components": [
   {"id": "identificador_unico", "type": "kpi|bar|line|table",
    "metric": "clave_aprobada", "dimension": "clave_aprobada_o_null",
    "title": "titulo claro", "limit": 20}
 ]
}
Reglas:
- Usa EXCLUSIVAMENTE los identificadores de métricas y dimensiones del catálogo.
- No inventes columnas, métricas, fórmulas, resultados, fechas, filtros ni cifras.
- No escribas SQL, Python, texto Markdown ni explicaciones fuera del JSON.
- No más de 8 componentes, al menos 1. No repitas identificadores.
- Cada KPI tiene dimension: null. Para barras o tablas, usa una dimensión aprobada.
- Usa line SOLO si el catálogo contiene sale_month o sale_date, con una de esas dimensiones.
- Si la petición incluye métricas no disponibles, omítelas; no las sustituyas por otras sin sentido.
- Selecciona componentes diversos, relacionados con la pregunta.
- Utiliza ids únicos en minúsculas con letras, dígitos o guiones bajos.
"""


def catalog_for_planner(semantic):
    """Expose names and human labels, not SQL expressions or private configurations."""
    return {
        "dataset": semantic.get("dataset", "Business Intelligence"),
        "grain": semantic.get("grain", ""),
        "metrics": {
            key: {
                "label": value.get("label", key),
                "synonyms": value.get("synonyms", [])[:8],
            }
            for key, value in semantic.get("measures", {}).items()
            if isinstance(value, dict) and value.get("sql")
        },
        "dimensions": {
            key: {"label": value.get("label", key)}
            for key, value in semantic.get("dimensions", {}).items()
            if isinstance(value, dict) and value.get("column")
        },
    }


def plan_dashboard(bedrock_client, user_request, semantic):
    if not isinstance(user_request, str) or not 5 <= len(user_request.strip()) <= 1500:
        raise ValueError("Escribe una petición de negocio de 5 a 1500 caracteres.")
    catalog = catalog_for_planner(semantic)
    if not catalog["metrics"]:
        raise ValueError("No hay métricas aprobadas disponibles.")
    request = (
        "CATÁLOGO SEMÁNTICO APROBADO (los identificadores son obligatorios):\n"
        + json.dumps(catalog, ensure_ascii=False, indent=2)
        + "\n\nPETICIÓN DEL USUARIO:\n"
        + user_request.strip()
        + "\n\nGenera un Dashboard Specification JSON ajustado a este catálogo."
    )
    proposed = bedrock_client.ask_json(
        system_prompt=PLANNER_SYSTEM_PROMPT,
        user_prompt=request,
        max_tokens=2400,
    )
    # The local semantic validator, not the model, authorizes the proposal.
    return validate_dashboard(proposed, semantic, max_components=8)
