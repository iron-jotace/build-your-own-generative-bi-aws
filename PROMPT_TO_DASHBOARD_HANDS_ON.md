# Hands-on 03 — Prompt-to-Dashboard con Amazon Bedrock

## Objetivo
Generar una especificación de dashboard a partir de un prompt de negocio. Bedrock solo planifica el dashboard; la Semantic Layer aprobada, el SQL Builder, el SQL Guard, Athena y el renderer ejecutan la lógica verificable.

## 1. Actualizar el código
```bash
conda activate nexa-dashboard
git switch feature/prompt-to-dashboard
git pull --ff-only
python -m unittest discover -s tests -v
python -m streamlit run app.py
```

## 2. Requisitos de AWS
- `config/settings.json`: región `eu-west-1`, `bedrock_model_id` habilitado para tu cuenta, base de datos y output S3 de Athena.
- Credenciales AWS válidas para Bedrock Runtime `Converse` (vía permisos de `bedrock:InvokeModel`) y para Athena/S3.
- `config/semantic_layer.json`: medidas y dimensiones aprobadas. Los IDs son exactamente los mismos que Bedrock debe utilizar; NO se inventan métricas.

## 3. Ejecutar Prompt-to-Dashboard
1. Abre **Build Dashboard** en Streamlit.
2. Selecciona **✨ Prompt-to-Dashboard (Bedrock)**.
3. Escribe: «Crea un dashboard comercial con ventas totales, unidades vendidas, ventas por categoría y distribución por canal».
4. Pulsa **Planificar con Bedrock**.
5. Revisa el JSON en **Dashboard Specification JSON**. Tiene que mostrar métricas/dimensiones aprobadas, sin SQL.
6. Pulsa **Construir dashboard** para ejecutar Athena y dibujar los componentes.

**Importante:** son dos botones deliberadamente: primero planificar/validar, después consultar Athena. Así el alumnado inspecciona el contrato antes de ejecutar datos.

## 4. Probar el gobierno
1. Prompt: «Muéstrame el EBITDA». Si no existe una métrica aprobada, Bedrock debe omitirla o el validador rechazará el plan.
2. En el editor JSON agrega `"sql": "DROP TABLE x"` en un componente: debe rechazarse antes de consultar Athena.
3. Cambia el orden o tipo de un componente autorizado en el JSON: el renderer debe recomponer la vista.
4. Abre **SQL y metadatos** para comparar resultados con consultas Golden Queries de Athena.

## Limitaciones actuales
- El Planner selecciona solo las dimensiones que existen en `semantic_layer.json`; la evolución mensual precisa una dimensión temporal con granularidad definida y aprobada (por ejemplo `sale_month` sobre `sale_date`).
- No se han incorporado todavía filtros de fecha, tabla de permisos por usuario, insights ejecutivos ni persistencia del dashboard.
- La versión utiliza `BedrockClient.ask_json`, que ya es parte del repositorio. Su respuesta se valida localmente, no se confía en que un prompt sea un guardrail suficiente.
- El SQL Guard es pedagógico. IAM, permisos reales y límites del Athena Workgroup siguen siendo indispensables.

## Arquitectura
```text
Prompt de negocio
  -> BedrockClient.ask_json
  -> dashboard_planner.py (JSON + catálogo de IDs)
  -> dashboard_validator.py (rechaza métricas/dimensiones no autorizadas)
  -> dashboard_sql_builder.py (SQL desde expresiones aprobadas)
  -> sql_guard.py
  -> AthenaClient
  -> Pandas DataFrames
  -> dashboard_renderer.py (Streamlit + Plotly)
```
