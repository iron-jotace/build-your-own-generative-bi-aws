"""NEXA Retail — governed Prompt-to-Dashboard and editable JSON lab."""
import json
import streamlit as st

from src.athena import AthenaClient
from src.bedrock import BedrockClient
from src.config import load_json, load_settings
from src.dashboard_planner import plan_dashboard
from src.dashboard_runtime import execute_dashboard
from src.dashboard_renderer import render_dashboard
from src.dashboard_validator import validate_dashboard

st.set_page_config(page_title="NEXA | Build Dashboard", page_icon="📈", layout="wide")
st.title("📈 NEXA Retail — Build Dashboard")
st.caption("Prompt → Bedrock Planner → JSON → Semantic Layer → SQL Guard → Athena → Plotly")

try:
    settings = load_settings()
    semantic = load_json("config/semantic_layer.json")
    default_spec = load_json("config/dashboard_examples.json")
    executive_spec = load_json("config/dashboard_executive.json")
except Exception as exc:
    st.error(f"Error de configuración: {exc}")
    st.stop()

if "dashboard_spec_text" not in st.session_state:
    st.session_state.dashboard_spec_text = json.dumps(default_spec, indent=2, ensure_ascii=False)

mode = st.radio("Modo de construcción", ["✨ Prompt-to-Dashboard (Bedrock)", "🧩 JSON manual"], horizontal=True)
details = st.checkbox("Mostrar SQL y metadatos Athena", value=False)
preset = st.selectbox("Ejemplo preparado", ["Comercial (4 componentes)", "Ejecutivo (7 componentes)"])
if st.button("📋 Cargar ejemplo en JSON"):
    selected = executive_spec if preset.startswith("Ejecutivo") else default_spec
    st.session_state.dashboard_spec_text = json.dumps(selected, indent=2, ensure_ascii=False)
    st.success("Ejemplo cargado. Revisa la especificación y pulsa Construir dashboard.")

if mode.startswith("✨"):
    prompt = st.text_area(
        "¿Qué dashboard necesita tu negocio?",
        value="Construye un dashboard ejecutivo de NEXA Retail con ventas, pedidos, ticket promedio, margen, evolución mensual de ventas, ventas por categoría y distribución por canal.",
        height=110,
        max_chars=1500,
    )
    if st.button("✨ Planificar con Bedrock", type="primary", disabled=not prompt.strip()):
        try:
            bedrock = BedrockClient(
                region=settings["aws_region"],
                model_id=settings["bedrock_model_id"],
            )
            with st.spinner("Bedrock está proponiendo los componentes..."):
                validated = plan_dashboard(bedrock, prompt, semantic)
            st.session_state.dashboard_spec_text = json.dumps(validated, indent=2, ensure_ascii=False)
            st.success("Especificación generada y validada. Revisa el JSON y construye el dashboard.")
        except Exception as exc:
            st.error(f"No se pudo planificar un dashboard autorizado: {exc}")
    st.caption("Bedrock solo propone componentes. Los cálculos y el SQL provienen de la Semantic Layer aprobada.")

with st.expander("🔧 Dashboard Specification JSON (auditoría y edición)", expanded=mode.startswith("🧩")):
    st.text_area(
        "Especificación",
        key="dashboard_spec_text",
        height=310,
        help="Puedes editar el JSON y volver a construir el dashboard.",
    )

if st.button("🚀 Construir dashboard", type="primary"):
    try:
        proposal = json.loads(st.session_state.dashboard_spec_text)
        validated = validate_dashboard(proposal, semantic)
    except (ValueError, TypeError, KeyError) as exc:
        st.error(f"Especificación rechazada: {exc}")
        st.stop()

    athena = AthenaClient(
        region=settings["aws_region"],
        database=settings["athena_database"],
        output_s3=settings["athena_output_s3"],
        workgroup=settings.get("athena_workgroup", "primary"),
    )
    try:
        with st.spinner("Consultando Athena y construyendo dashboard..."):
            final_spec, results = execute_dashboard(validated, semantic, athena)
    except Exception as exc:
        st.error(f"Dashboard bloqueado antes de ejecutarse: {exc}")
        st.stop()

    render_dashboard(final_spec, results, semantic, show_details=details)
    if any(item["error"] for item in results):
        st.warning("Dashboard parcial: algunas consultas no pudieron ejecutarse.")
