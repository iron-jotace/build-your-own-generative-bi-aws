"""NEXA Retail — dashboard built from a declarative JSON specification."""
import json
import streamlit as st

from src.athena import AthenaClient
from src.config import load_json, load_settings
from src.dashboard_runtime import execute_dashboard
from src.dashboard_renderer import render_dashboard
from src.dashboard_validator import DashboardValidationError

st.set_page_config(page_title="NEXA | Build Dashboard", page_icon="📈", layout="wide")
st.title("📈 NEXA Retail — Build Dashboard")
st.caption("Etapa 2 · JSON → Semantic Layer → SQL Guard → Athena → Streamlit/Plotly")
st.info("En esta etapa editamos la especificación JSON. El Planner de Bedrock llegará después.")

try:
    settings = load_settings()
    semantic = load_json("config/semantic_layer.json")
    default_spec = load_json("config/dashboard_examples.json")
except Exception as exc:
    st.error(f"Error de configuración: {exc}")
    st.stop()

example = json.dumps(default_spec, indent=2, ensure_ascii=False)
spec_text = st.text_area("Dashboard Specification JSON", value=example, height=300)
details = st.checkbox("Mostrar SQL y metadatos Athena", value=True)

if st.button("🚀 Construir dashboard", type="primary"):
    try:
        specification = json.loads(spec_text)
        # No AWS query is made before JSON and semantic validation succeeds.
        from src.dashboard_validator import validate_dashboard
        validated = validate_dashboard(specification, semantic)
    except (ValueError, DashboardValidationError) as exc:
        st.error(f"Especificación rechazada: {exc}")
        st.stop()

    athena = AthenaClient(
        region=settings["aws_region"],
        database=settings["athena_database"],
        output_s3=settings["athena_output_s3"],
        workgroup=settings.get("athena_workgroup", "primary"),
    )
    with st.spinner("Consultando Athena y construyendo componentes..."):
        try:
            final_spec, results = execute_dashboard(validated, semantic, athena)
        except Exception as exc:
            st.error(f"Dashboard bloqueado antes de ejecutarse: {exc}")
            st.stop()
    render_dashboard(final_spec, results, semantic, show_details=details)
    if any(result["error"] for result in results):
        st.warning("Dashboard parcial: algunos componentes no pudieron consultarse.")
