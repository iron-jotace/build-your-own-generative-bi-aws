"""Deterministic Streamlit + Plotly dashboard renderer."""
import pandas as pd
import plotly.express as px
import streamlit as st


def _format_value(value, metric, semantic):
    if pd.isna(value):
        return "Sin datos"
    context = semantic.get("business_context", {})
    currency = context.get("currency_symbol", "")
    if metric in {"revenue", "margin", "cost_amount", "average_order_value"}:
        return f"{currency}{float(value):,.2f}"
    if metric in {"orders", "units_sold", "customers"}:
        return f"{float(value):,.0f}"
    return f"{float(value):,.2f}"


def render_component(result, semantic, show_details=False):
    component = result["component"]
    st.markdown(f"**{component['title']}**")
    if result["error"]:
        st.error(f"No se pudo ejecutar: {result['error']}")
        return
    df = result["data"]
    if df.empty or "metric_value" not in df:
        st.info("No existen resultados para este componente.")
        return
    kind = component["type"]
    if kind == "kpi":
        value = df.iloc[0]["metric_value"]
        st.metric(component["title"], _format_value(value, component["metric"], semantic))
    elif kind == "table":
        st.dataframe(df.rename(columns={
            "dimension_value": component["dimension"],
            "metric_value": component["metric"],
        }), hide_index=True, use_container_width=True)
    elif kind == "bar":
        fig = px.bar(df, x="dimension_value", y="metric_value",
                     labels={"dimension_value": component["dimension"],
                             "metric_value": component["metric"]})
        st.plotly_chart(fig, use_container_width=True, key=component["id"])
    elif kind == "line":
        chart_df = df.sort_values("dimension_value")
        fig = px.line(chart_df, x="dimension_value", y="metric_value",
                      markers=True, labels={"dimension_value": component["dimension"],
                                            "metric_value": component["metric"]})
        st.plotly_chart(fig, use_container_width=True, key=component["id"])
    if show_details:
        with st.expander(f"SQL y metadatos: {component['id']}"):
            st.code(result["sql"], language="sql")
            st.json(result["metadata"])


def render_dashboard(spec, results, semantic, show_details=False):
    st.header(spec["title"])
    successful = sum(item["error"] is None for item in results)
    st.caption(f"Componentes ejecutados: {successful}/{len(results)} · "
               "Resultados procedentes de Amazon Athena")
    # Layout depends on JSON component order and count; no hardcoded KPI names.
    kpis = [item for item in results if item["component"]["type"] == "kpi"]
    others = [item for item in results if item["component"]["type"] != "kpi"]
    for offset in range(0, len(kpis), 4):
        group = kpis[offset: offset + 4]
        for col, result in zip(st.columns(len(group)), group):
            with col:
                render_component(result, semantic, show_details)
    for offset in range(0, len(others), 2):
        group = others[offset: offset + 2]
        for col, result in zip(st.columns(len(group)), group):
            with col:
                render_component(result, semantic, show_details)
