"""Bedrock proposes dashboard structure; the application validates and executes it."""
import json

from src.dashboard_validator import available_dimensions, validate_dashboard


PLANNER_SYSTEM_PROMPT = """
Eres un diseñador de dashboards de Business Intelligence para NEXA Retail.
Devuelve ÚNICAMENTE un objeto JSON (sin código, SQL, cifras ni explicaciones):
{
 "title": "título de negocio",
 "components": [
   {"id": "identificador_unico", "type": "kpi|bar|line|table",
    "metric": "métrica aprobada", "dimension": null,
    "title": "título claro", "limit": 20}
 ]
}
REGLAS:
- Solo utiliza identificadores exactos del catálogo. Nunca inventes métricas, fórmulas, dimensiones ni cifras.
- No generes SQL, Python, filtros de fecha ni explicaciones de negocio.
- Entre 1 y 8 componentes; cada identificador debe ser único y usar minúsculas y guiones bajos.
- Los KPI deben tener dimension: null. Los gráficos y tablas necesitan una dimensión aprobada.
- Para EVOLUCIÓN MENSUAL elige dimension: "sale_month" y type: "line" si sale_month está en el catálogo.
- No uses sale_date para evolución mensual si existe sale_month.
- Para ventas, elige revenue; para pedidos, orders; para ticket promedio, average_order_value.
- Para margen monetario, margin; para margen porcentual, margin_pct, si el catálogo los aprueba.
- Para categorías y canales usa category y sales_channel respectivamente, si están disponibles.
- Omite métricas no autorizadas; nunca sustituyas una métrica ausente por otra incongruente.
- Diseña el dashboard para responder específicamente a la petición del usuario.
"""


def catalog_for_planner(semantic):
    """Expose approved business identifiers and labels, but not SQL expressions."""
    dimensions = available_dimensions(semantic)
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
            for key, value in dimensions.items()
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
        "CATÁLOGO SEMÁNTICO APROBADO (identificadores obligatorios):\n"
        + json.dumps(catalog, ensure_ascii=False, indent=2)
        + "\n\nPETICIÓN DE NEGOCIO:\n"
        + user_request.strip()
        + "\n\nGenera el Dashboard Specification JSON."
    )
    proposed = bedrock_client.ask_json(
        system_prompt=PLANNER_SYSTEM_PROMPT,
        user_prompt=request,
        max_tokens=2800,
    )
    return validate_dashboard(proposed, semantic, max_components=8)
