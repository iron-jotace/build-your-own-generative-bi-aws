import streamlit as st

from src.athena import AthenaClient
from src.bedrock import BedrockClient
from src.config import load_json, load_settings
from src.insight import generate_insight
from src.sql_generator import generate_sql
from src.sql_guard import (
    SQLValidationError,
    validate_sql,
)
from src.visualization import choose_chart


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="NEXA Retail - Generative BI",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# LOAD CONFIGURATION
# ============================================================

try:

    settings = load_settings()

    semantic = load_json(
        "config/semantic_layer.json"
    )

except Exception as exc:

    st.error(
        f"Configuration error: {exc}"
    )

    st.stop()


# ============================================================
# AWS CLIENTS
# ============================================================

bedrock = BedrockClient(
    region=settings["aws_region"],
    model_id=settings["bedrock_model_id"],
)

athena = AthenaClient(
    region=settings["aws_region"],
    database=settings["athena_database"],
    output_s3=settings["athena_output_s3"],
    workgroup=settings.get(
        "athena_workgroup",
        "primary",
    ),
)


# ============================================================
# HEADER
# ============================================================

st.title(
    "📊 NEXA Retail — Generative BI"
)

st.caption(
    "Athena + Semantic Layer + Amazon Bedrock + Streamlit"
)

st.divider()


# ============================================================
# BUSINESS QUESTION
# ============================================================

question = st.text_input(
    "Pregunta de negocio",
    placeholder=(
        "Ej.: ¿Qué categoría generó más ventas?"
    ),
)


col1, col2 = st.columns(
    [1, 4]
)

with col1:

    analyze = st.button(
        "🔎 Analizar",
        type="primary",
        use_container_width=True,
        disabled=not question,
    )


with col2:

    show_details = st.checkbox(
        "Mostrar detalles técnicos",
        value=False,
    )


# ============================================================
# ANALYSIS
# ============================================================

if analyze:

    try:

        # ----------------------------------------------------
        # 1. SEMANTIC RESOLUTION + NL-TO-SQL
        # ----------------------------------------------------

        with st.spinner(
            "Interpretando la pregunta..."
        ):

            generated = generate_sql(
                bedrock,
                question,
                semantic,
            )

        sql = generated["sql"]


        # ----------------------------------------------------
        # 2. SQL SAFETY GATE
        # ----------------------------------------------------

        try:

            validate_sql(
                sql,
                settings["allowed_view"],
            )

        except SQLValidationError as exc:

            st.error(
                f"SQL Guard bloqueó la consulta: {exc}"
            )

            st.stop()


        # ----------------------------------------------------
        # 3. EXECUTE ATHENA
        # ----------------------------------------------------

        with st.spinner(
            "Consultando Athena..."
        ):

            df, metadata = athena.run(
                sql
            )


        # ----------------------------------------------------
        # 4. GENERATE BUSINESS INSIGHT
        # ----------------------------------------------------

        with st.spinner(
            "Generando insight..."
        ):

            insight = generate_insight(
                bedrock,
                question,
                df,
                semantic_layer=semantic,
            )


        # ----------------------------------------------------
        # 5. BUSINESS ANSWER
        # ----------------------------------------------------

        st.subheader(
            insight.get(
                "headline",
                "Business Insight",
            )
        )

        st.write(
            insight.get(
                "insight",
                ""
            )
        )

        caveat = insight.get(
            "caveat"
        )

        if caveat:

            st.caption(
                f"ℹ️ {caveat}"
            )


        # ----------------------------------------------------
        # 6. VISUALIZATION
        # ----------------------------------------------------

        figure, chart_type = choose_chart(
            df
        )

        if figure is not None:

            st.plotly_chart(
                figure,
                use_container_width=True,
            )


        # ----------------------------------------------------
        # 7. RESULT TABLE
        # ----------------------------------------------------

        st.subheader(
            "Resultado"
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )


        # ----------------------------------------------------
        # 8. TECHNICAL DETAILS
        # ----------------------------------------------------

        if show_details:

            st.divider()

            st.subheader(
                "🔧 Detalles técnicos"
            )

            col_a, col_b, col_c = st.columns(
                3
            )

            with col_a:

                st.metric(
                    "Métrica interpretada",
                    generated.get(
                        "metric_used"
                    )
                    or "LLM interpretation",
                )

            with col_b:

                execution_time = (
                    metadata.get(
                        "total_execution_ms"
                    )
                )

                st.metric(
                    "Athena execution",
                    (
                        f"{execution_time} ms"
                        if execution_time
                        else "N/A"
                    ),
                )

            with col_c:

                scanned = metadata.get(
                    "data_scanned_bytes"
                )

                if scanned is not None:

                    scanned_mb = (
                        scanned
                        / 1024
                        / 1024
                    )

                    st.metric(
                        "Data scanned",
                        f"{scanned_mb:.4f} MB",
                    )

                else:

                    st.metric(
                        "Data scanned",
                        "N/A",
                    )


            # -----------------------------------------------
            # Semantic interpretation
            # -----------------------------------------------

            st.markdown(
                "### Semantic Interpretation"
            )

            st.info(
                generated.get(
                    "interpretation",
                    ""
                )
            )


            # -----------------------------------------------
            # Semantic Rule
            # -----------------------------------------------

            st.markdown(
                "### Semantic Rule Applied"
            )

            st.code(
                generated.get(
                    "semantic_rule_applied",
                    "No deterministic rule applied",
                )
            )


            # -----------------------------------------------
            # Generated SQL
            # -----------------------------------------------

            st.markdown(
                "### Generated SQL"
            )

            st.code(
                sql,
                language="sql",
            )


            # -----------------------------------------------
            # SQL Guard
            # -----------------------------------------------

            st.markdown(
                "### SQL Governance"
            )

            st.success(
                "✅ SQL Guard: PASSED"
            )


            # -----------------------------------------------
            # Visualization decision
            # -----------------------------------------------

            st.markdown(
                "### Visualization Decision"
            )

            st.write(
                f"Selected visualization: **{chart_type}**"
            )


            # -----------------------------------------------
            # Athena Metadata
            # -----------------------------------------------

            st.markdown(
                "### Athena Metadata"
            )

            st.json(
                metadata
            )


    except Exception as exc:

        st.error(
            "Se produjo un error durante "
            "el análisis."
        )

        st.exception(
            exc
        )


# ============================================================
# EXAMPLE QUESTIONS
# ============================================================

st.divider()

st.subheader(
    "Preguntas de ejemplo"
)

st.markdown(
    """
- ¿Cuánto vendimos en total?
- ¿Cuántos pedidos tuvimos?
- ¿Cuál fue el ticket promedio?
- ¿Qué categoría generó más ventas?
- ¿Qué canal fue el mejor?
- ¿Cuál fue el margen total?
"""
)