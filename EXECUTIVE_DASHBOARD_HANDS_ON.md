# Hands-on 04 — Executive Dashboard (métricas aprobadas + evolución mensual)

## Cambios
- Se incorporó un ejemplo ejecutivo de 7 componentes: revenue, orders, average_order_value, margin, revenue por mes, por categoría y por canal.
- `sale_month` es una dimensión virtual **derivada de la dimensión aprobada `sale_date`**. No hace falta editar tu `config/semantic_layer.json`. El motor usa su columna física y compila `date_trunc('month', sale_date)`.
- Bedrock recibe la lista de métricas existentes y las dimensiones disponibles, incluyendo sale_month cuando existe sale_date. No recibe fórmulas SQL.
- El JSON es declarativo; el SQL se compila desde las expresiones del Semantic Layer local.

## 1. Actualización
```bash
conda activate nexa-dashboard
git switch feature/prompt-to-dashboard
git pull --ff-only
python -m unittest discover -s tests -v
python -m streamlit run app.py
```

## 2. Prueba determinista antes de Bedrock
1. Entra en **Build Dashboard**.
2. En **Ejemplo preparado**, selecciona **Ejecutivo (7 componentes)**.
3. Pulsa **Cargar ejemplo en JSON**.
4. Inspecciona la especificación en el desplegable y pulsa **Construir dashboard**.
5. Esperamos 4 KPI, una línea mensual y dos gráficos de barras, todos consultados en Athena.
6. Comprueba con Golden Queries que revenue, orders y average_order_value coinciden. El margen también debe validarse con la consulta de referencia.

## 3. Prueba de lenguaje natural
En Prompt-to-Dashboard escribe:
«Construye un dashboard ejecutivo de NEXA Retail con ventas totales, número de pedidos, ticket promedio, margen, evolución mensual de ventas, ventas por categoría y ventas por canal».
Pulsa **Planificar con Bedrock**, inspecciona el JSON y luego **Construir dashboard**.
Nota: el LLM puede proponer un subconjunto o distribución distinta; el JSON validado determina la visualización real.

## 4. Verificación de evolución mensual
En detalles técnicos de la línea, el SQL debe contener `date_trunc('month', sale_date)` y `ORDER BY dimension_value ASC`.
Este componente muestra **meses calendario**, no necesariamente una serie continua con meses de valor cero. No se inventan meses faltantes.

## 5. Restricciones
- La existencia de los IDs de medidas no garantiza la validación de sus fórmulas: confirma el SQL del archivo local aprobado y que la vista funciona.
- No hay filtros temporales en esta versión; todas las KPI consideran el conjunto completo de la vista.
- Esta fase no incluye insights narrativos, permisos por usuario ni un mecanismo de caching de consultas. Eso se abordará después.
- No se han realizado consultas reales de AWS desde el entorno del asistente: la ejecución debe validarse en la cuenta del docente.
