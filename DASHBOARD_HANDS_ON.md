# Hands-on 02 — Build Dashboard (sin Bedrock Planner todavía)

Este incremento reutiliza `src/athena.py`, `src/sql_guard.py` y la Semantic Layer aprobada.
No modifica el flujo NL-to-SQL de `app.py`.

## Requisitos

- Credenciales AWS locales con permisos para consultar la vista aprobada de Athena y escribir resultados en el bucket configurado.
- Región `eu-west-1`.
- `config/settings.json` y `config/semantic_layer.json` locales. Estos archivos no deben contenerse en el commit.
- La capa semántica debe incluir las métricas `revenue`, `units_sold` y las dimensiones `category`, `sales_channel` para ejecutar el ejemplo incluido.

## 1. Actualizar rama

```bash
git switch feature/prompt-to-dashboard
git pull --ff-only
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## 2. Revisar configuración local

Verifica que `config/settings.json` tenga `aws_region: eu-west-1`, base de datos, vista, S3 de resultados y workgroup correctos.

Verifica que `config/semantic_layer.json` contenga los identificadores de métricas y dimensiones del ejemplo. Si un ID no existe, el validador lo bloqueará antes de consultar Athena.

## 3. Abrir la aplicación

```bash
python -m streamlit run app.py
```

En el menú de navegación de Streamlit abre **Build Dashboard** (la página en `pages/1_Build_Dashboard.py`).

Revisa el JSON mostrado, activa **Mostrar SQL y metadatos** y pulsa **Construir dashboard**.

El sistema procesa la lista de componentes y produce tarjetas KPI, gráficos o tablas según el JSON. Si falla una consulta, el componente informa del error, sin inventar un valor.

## 4. Pruebas sugeridas

1. Ejecuta el ejemplo sin modificaciones y revisa el SQL generado para cada componente.
2. Quita el componente `channels`, vuelve a ejecutar y comprueba que cambia el dashboard.
3. Duplica el componente `categories` con `id` diferente y `type: "table"`; verifica la composición.
4. Cambia una métrica a `ebitda`: debe rechazarse si no existe en `measures`.
5. Introduce un campo `sql` en un componente: la especificación debe rechazarse.
6. Contrasta la tarjeta `revenue` sin filtros con GQ01 en Athena.

## Arquitectura

```text
Dashboard Specification JSON
  -> dashboard_validator.py (JSON + Semantic Layer)
  -> dashboard_sql_builder.py (SQL determinista)
  -> sql_guard.py
  -> AthenaClient
  -> pandas DataFrame
  -> dashboard_renderer.py (Streamlit + Plotly)
```

**Aviso docente:** esta implementación es pedagógica. El SQL Guard basado en expresiones regulares no reemplaza IAM, los permisos de datos, la configuración del Athena Workgroup ni controles de producción. No se incluye el Bedrock Dashboard Planner en este incremento.
