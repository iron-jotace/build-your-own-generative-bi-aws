"""Executive insights: deterministic facts from Athena plus optional Bedrock curation.

Bedrock never invents numbers or writes free-form claims: it selects evidence IDs.
"""
import json
import math

import pandas as pd


def _number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _amount(value, metric, semantic):
    symbol = semantic.get("business_context", {}).get("currency_symbol", "")
    if metric in {"orders", "units_sold"}:
        return f"{value:,.0f}"
    if metric in {"revenue", "margin", "cost", "gross_sales", "average_order_value"}:
        return f"{symbol}{value:,.2f}"
    if metric == "margin_pct":
        return f"{value:,.2f}" + ("% " if abs(value) > 1 else " (ratio)")
    return f"{value:,.2f}"


def evidence_from_results(results, semantic):
    """Only use actual queried DataFrames; skip failed, empty and null results."""
    evidence = []
    # A segment share is reported only when its complete group sum reconciles
    # with the corresponding unfiltered KPI in the same dashboard.
    totals = {}
    for item in results:
        if item.get("error"):
            continue
        frame = item.get("data")
        if frame is None or frame.empty or "metric_value" not in frame:
            continue
        component = item["component"]
        if component["type"] == "kpi":
            value = _number(frame.iloc[0]["metric_value"])
            if value is not None:
                totals[component["metric"]] = value
    for result in results:
        if result.get("error") or result.get("data") is None:
            continue
        frame = result["data"]
        if frame.empty or "metric_value" not in frame:
            continue
        component = result["component"]
        metric = component["metric"]
        kind = component["type"]
        if kind == "kpi":
            value = _number(frame.iloc[0]["metric_value"])
            if value is None:
                continue
            evidence.append({
                "id": component["id"], "title": component["title"],
                "fact": f"{component['title']}: {_amount(value, metric, semantic)}.",
                "source": component["id"],
            })
            continue
        if "dimension_value" not in frame or not frame["metric_value"].notna().any():
            continue
        valid = frame[["dimension_value", "metric_value"]].copy()
        valid["metric_value"] = pd.to_numeric(valid["metric_value"], errors="coerce")
        valid = valid.dropna(subset=["dimension_value", "metric_value"])
        if valid.empty:
            continue
        if component.get("dimension") == "sale_month":
            valid = valid.sort_values("dimension_value")
            top = valid.loc[valid["metric_value"].idxmax()]
            label = str(top["dimension_value"])[:10]
            fact = (
                f"El mayor valor mensual observado de {component['title'].lower()} "
                f"corresponde a {label}: {_amount(float(top['metric_value']), metric, semantic)}. "
                "No se ha verificado la completitud de los meses."
            )
        else:
            top = valid.loc[valid["metric_value"].idxmax()]
            top_value = float(top["metric_value"])
            fact = (
                f"Lidera {component['title'].lower()}: {top['dimension_value']} "
                f"con {_amount(top_value, metric, semantic)}."
            )
            # Only show percent of whole if every observed group reconciles
            # with the KPI. A LIMIT or missing group can invalidate the share.
            total = totals.get(metric)
            group_sum = float(valid["metric_value"].sum())
            if (total is not None and total > 0
                    and math.isclose(group_sum, total, rel_tol=0.00001, abs_tol=0.02)):
                fact += f" Representa el {100 * top_value / total:.1f}% del total validado."
        evidence.append({
            "id": component["id"], "title": component["title"],
            "fact": fact, "source": component["id"],
        })
    return evidence


INSIGHTS_SYSTEM_PROMPT = """Eres analista de Business Intelligence.
Recibes hechos de Athena con identificadores y debes seleccionar hasta 4 hechos útiles
para un resumen ejecutivo. Devuelve SOLO JSON: {"selected_ids":["id1","id2"]}.
Elige exclusivamente IDs presentes, sin inventarlos ni escribir resultados, números,
comentarios adicionales, causas, predicciones o métricas.
Prioriza diversidad: al menos un desglose dimensional o temporal si existe. Evita seleccionar solamente KPIs que repitan las tarjetas visibles. No repitas IDs.
"""


def curate_insights(bedrock_client, business_request, evidence):
    """Model selects fact IDs only; displayed text is always calculated in Python."""
    if not evidence:
        return []
    if bedrock_client is None:
        return evidence[:4]
    response = bedrock_client.ask_json(
        system_prompt=INSIGHTS_SYSTEM_PROMPT,
        user_prompt=(
            "SOLICITUD ORIGINAL:\n" + str(business_request or "Resumen ejecutivo")[:1500]
            + "\nHECHOS VERIFICADOS:\n"
            + json.dumps(evidence, ensure_ascii=False, default=str)
        ),
        max_tokens=450,
    )
    selected = response.get("selected_ids") if isinstance(response, dict) else None
    if not isinstance(selected, list) or not selected or len(selected) > 4:
        raise ValueError("Bedrock did not return valid evidence identifiers.")
    indexed = {item["id"]: item for item in evidence}
    if any(not isinstance(key, str) or key not in indexed for key in selected):
        raise ValueError("Bedrock selected unverified evidence.")
    seen = set()
    final = []
    for key in selected:
        if key not in seen:
            final.append(indexed[key])
            seen.add(key)
    return final
