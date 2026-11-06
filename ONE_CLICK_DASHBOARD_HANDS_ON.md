# Hands-on 06 — Prompt-to-Dashboard en una sola acción

## Objetivo
Una instrucción de negocio desencadena Bedrock Planner → JSON gobernado → SQL Builder → SQL Guard → Athena → KPIs y gráficos → Executive Insights.

## Preparación
```bash
conda activate nexa-dashboard
git switch feature/prompt-to-dashboard
git pull --ff-only
python -m unittest discover -s tests -v
python -m streamlit run app.py
```

La aplicación necesita `config/settings.json`, `config/semantic_layer.json`, permisos AWS y `eu-west-1`.

## Ejecución
1. Entra en **Build Dashboard**.
2. Selecciona **✨ Prompt-to-Dashboard**.
3. Escribe «Construye un dashboard ejecutivo de NEXA Retail con ventas, pedidos, ticket promedio, margen, evolución mensual, ventas por categoría y ventas por canal».
4. Pulsa **✨ Generar dashboard completo**.
5. Verifica los componentes y los hallazgos. En **⚙️ Opciones y trazabilidad** puedes activar SQL, metadatos y selección de insights.
6. Abre **Dashboard Specification JSON** para inspeccionar el plan declarativo, sin SQL ni Python.
7. Para pruebas didácticas, utiliza **🧩 Laboratorio JSON** y ejecuta una especificación editada.

## Comportamiento esperado
- En modo Prompt-to-Dashboard, una sola acción encadena planificación, validación, Athena y visualización.
- La validación semántica prohíbe métricas inexistentes.
- Bedrock solo puede proponer componentes y seleccionar IDs de hechos verificables.
- Los resultados mostrados pertenecen a Athena y no son calculados por el LLM.

## Nota
Este incremento requiere validación funcional en el entorno del docente. No se ha ejecutado en su cuenta desde GitHub. Las consultas pueden consumir recursos AWS y los permisos deben restringirse con IAM/Workgroup. No se han añadido filtros por fecha ni controles de completitud mensual.
