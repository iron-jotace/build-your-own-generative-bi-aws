# NEXA Retail — Build Your Own Generative BI

> **Última clase — Prompt-to-Dashboard:** la evolución del hands-on hacia dashboards dinámicos gobernados está documentada en [README_PROMPT_TO_DASHBOARD.md](README_PROMPT_TO_DASHBOARD.md). Incluye los cuatro escenarios ejecutivos y el paso a paso en AWS eu-west-1. Se desarrolla en la rama `feature/prompt-to-dashboard`.

---

Hands-on del curso de **Business Intelligence — Ingeniería de Computación y Sistemas, USMP**.

---

# 1. Objetivo del laboratorio

En este laboratorio construiremos una solución propia de **Generative Business Intelligence (GenBI)** utilizando:

- Amazon S3
- AWS Glue Data Catalog
- Amazon Athena
- Amazon Bedrock
- Python
- boto3
- pandas
- Plotly
- Streamlit

El objetivo **no es construir un chatbot ni aprender un framework de IA**.

El objetivo es extender un Data Mart tradicional con una interfaz de lenguaje natural gobernada.

La arquitectura trabajada será:

```text
Data Mart
   ↓
GenBI View
   ↓
Technical Profiling
   ↓
Bedrock Semantic Discovery
   ↓
Semantic Layer Draft
   ↓
Human Validation
   ↓
Approved Semantic Layer
   ↓
Natural Language Question
   ↓
Semantic Resolver
   ↓
Bedrock NL-to-SQL
   ↓
SQL Guard
   ↓
Athena
   ↓
Result
   ├── Business Insight
   └── Visualization
   ↓
Streamlit
```

Principio fundamental:

> **Bedrock interpreta. La Semantic Layer gobierna. Athena calcula.**

---

# 2. Estructura del proyecto

La carpeta del laboratorio tiene aproximadamente esta estructura:

```text
nexa_genbi_hands_on/
│
├── app.py
├── requirements.txt
├── README.md
│
├── config/
│   ├── business_context.json
│   ├── settings.example.json
│   ├── settings.json
│   ├── dataset_profile.json
│   ├── semantic_layer.example.json
│   ├── semantic_layer_draft.json
│   ├── semantic_layer.json
│   └── reference_queries.json
│
├── scripts/
│   ├── 01_profile.py
│   ├── 02_build_semantic_draft.py
│   ├── 03_test_nl2sql.py
│   ├── 04_execute_genbi_query.py
│   ├── 05_validate_reference.py
│   └── 06_genbi_result.py
│
├── sql/
│   └── 01_create_genbi_view.sql
│
├── src/
│   ├── athena.py
│   ├── bedrock.py
│   ├── config.py
│   ├── insight.py
│   ├── profiler.py
│   ├── semantic_builder.py
│   ├── sql_generator.py
│   ├── sql_guard.py
│   └── visualization.py
│
└── tests/
    └── test_sql_guard.py
```

No todos los archivos aparecerán desde el comienzo: algunos se generan durante el laboratorio.

---

# 3. Prerrequisitos

Antes de comenzar verificar:

- Python **3.10 o superior**.
- Recomendado: **Python 3.11**.
- AWS CLI configurado.
- Credenciales AWS válidas.
- Acceso a Amazon Athena.
- Acceso a Amazon Bedrock.
- Permisos de lectura/escritura sobre el bucket S3 del laboratorio.
- Acceso a la base de datos `nexa_master`.

Comprobar Python:

```bash
python --version
```

Comprobar las credenciales AWS:

```bash
aws sts get-caller-identity
```

Debe devolver información de la cuenta y del usuario/rol utilizado.

---

# 4. Crear un entorno Python

Se recomienda trabajar en un entorno aislado.

## Opción A — Conda

```bash
conda create -n genbi python=3.11 -y
```

Activar:

```bash
conda activate genbi
```

El terminal debería mostrar:

```text
(genbi)
```

## Opción B — Python venv

```bash
python -m venv .venv
```

En macOS/Linux:

```bash
source .venv/bin/activate
```

En Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

# 5. Verificar soporte para Amazon Bedrock

Ejecutar:

```bash
python -c "import boto3; print(boto3.__version__); print('bedrock-runtime' in boto3.Session().get_available_services())"
```

El último resultado debe ser:

```text
True
```

Si aparece `False`, actualizar boto3:

```bash
pip install --upgrade boto3 botocore
```

---

# 6. Revisar el Data Mart NEXA

El laboratorio utiliza la base:

```text
nexa_master
```

Las principales tablas dimensionales son:

```text
fact_sales
dim_product
dim_customer
dim_store
dim_channel
dim_date
```

Antes de comenzar con IA debemos comprender el **grano** del modelo.

En NEXA:

> Una fila de `fact_sales` representa una línea de producto perteneciente a un pedido completado.

Esto significa que:

```text
una fila ≠ un pedido
```

Un pedido puede contener varias líneas.

Ejemplo real del dataset:

```text
2,250 líneas de venta
916 pedidos únicos
```

Por tanto:

```sql
COUNT(order_id)
```

no representa correctamente el número de pedidos.

La definición correcta es:

```sql
COUNT(DISTINCT order_id)
```

Este concepto será importante durante la construcción de la Semantic Layer.

---

# 7. GenBI View

El LLM **no debe consultar directamente las tablas físicas del Data Mart**.

Utilizaremos una vista controlada:

```text
nexa_master.vw_nexa_genbi_sales
```

Esta vista actúa como contrato entre el Data Mart y la aplicación GenBI.

Podemos inspeccionarla en Athena con:

```sql
SELECT *
FROM nexa_master.vw_nexa_genbi_sales
LIMIT 10;
```

También podemos consultar su estructura:

```sql
SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'nexa_master'
  AND table_name = 'vw_nexa_genbi_sales'
ORDER BY ordinal_position;
```

La vista contiene dimensiones y medidas como:

```text
sale_date
product_name
category
brand

customer_id
customer_segment
customer_city

store_name
store_region

sales_channel

quantity
unit_price
discount
unit_cost
revenue
margin
gross_sales
cost_amount
```

---

# 8. Algunas relaciones del modelo

En los datos de NEXA verificamos que:

```text
gross_sales = quantity × unit_price
```

Además:

```text
revenue = gross_sales - discount
```

y:

```text
margin = revenue - cost_amount
```

Importante:

`discount` representa **un importe monetario**, no un porcentaje.

Estas reglas no deben asumirse solamente por el nombre de las columnas. Deben validarse mediante los datos y posteriormente formar parte del conocimiento gobernado.

---

# 9. Configurar el proyecto

Copiar:

```text
config/settings.example.json
```

como:

```text
config/settings.json
```

Ejemplo:

```json
{
  "aws_region": "eu-west-1",
  "athena_database": "nexa_master",
  "allowed_view": "vw_nexa_genbi_sales",
  "athena_output_s3": "s3://usmp-bigdata-2026-2-jcv/athena-results/",
  "athena_workgroup": "primary",
  "bedrock_model_id": "eu.amazon.nova-micro-v1:0"
}
```

Cada alumno deberá adaptar principalmente:

```text
athena_output_s3
```

al bucket S3 que tenga disponible.

---

# 10. Fase 1 — Technical Profiling

Ahora construiremos automáticamente un perfil técnico del dataset.

Desde la **raíz del proyecto**, ejecutar:

```bash
PYTHONPATH=. python scripts/01_profile.py
```

No ejecutar el comando desde dentro de la carpeta `scripts`.

Resultado esperado:

```text
Created: .../config/dataset_profile.json
```

El archivo generado será:

```text
config/dataset_profile.json
```

Este archivo contiene:

- nombre del dataset;
- database;
- GenBI View permitida;
- grano;
- columnas;
- tipos de datos;
- algunas filas de ejemplo.

Todavía **no contiene una Semantic Layer aprobada**.

---

# 11. ¿Qué representa `dataset_profile.json`?

Este archivo contiene **evidencia técnica**.

Por ejemplo:

```json
{
  "name": "revenue",
  "type": "double"
}
```

o:

```json
{
  "name": "order_id",
  "type": "varchar"
}
```

También contiene pequeñas muestras de los datos.

Bedrock puede utilizar esta información para proponer posibles dimensiones y medidas.

Pero todavía no hemos definido:

```text
¿Qué significa "ventas"?

¿Qué significa "mejor"?

¿Cómo se calculan los pedidos?

¿Qué significa margen?

¿Qué significa ticket promedio?
```

Estas son decisiones de negocio.

---

# 12. Fase 2 — AI-Assisted Semantic Discovery

Ahora utilizaremos Amazon Bedrock para analizar el perfil técnico.

Ejecutar:

```bash
PYTHONPATH=. python scripts/02_build_semantic_draft.py
```

Resultado esperado:

```text
Created: .../config/semantic_layer_draft.json

NEXT STEP: Human validation.
Do NOT use the draft as the approved semantic layer without review.
```

Se creará:

```text
config/semantic_layer_draft.json
```

---

# 13. Revisar el Semantic Draft

Abrir:

```text
config/semantic_layer_draft.json
```

Bedrock propondrá elementos como:

- dimensiones;
- posibles métricas;
- agregaciones;
- nombres de negocio;
- sinónimos;
- campos no aditivos;
- ambigüedades;
- preguntas que requieren validación.

Ejemplos de propuestas correctas:

```text
Revenue → SUM(revenue)

Quantity Sold → SUM(quantity)

Gross Sales → SUM(gross_sales)

Margin → SUM(margin)
```

Pero el modelo también puede cometer errores o dejar decisiones incompletas.

---

# 14. Ejemplo de problema: Orders

Bedrock puede detectar que:

```text
order_id
```

no debe sumarse.

Pero eso no significa que automáticamente comprenda que:

```text
Orders = COUNT(DISTINCT order_id)
```

Recordar el grano:

```text
1 fila = 1 línea del pedido
```

Por eso:

```sql
COUNT(order_id)
```

puede contar varias veces el mismo pedido.

Definición aprobada:

```sql
COUNT(DISTINCT order_id)
```

---

# 15. Ejemplo de problema: Average Price

Bedrock puede sugerir:

```sql
AVG(unit_price)
```

como precio promedio.

Pero esa medida puede ser engañosa porque no pondera por unidades.

Una definición más adecuada para precio neto medio sería:

```sql
SUM(revenue) / NULLIF(SUM(quantity), 0)
```

Este es un ejemplo importante:

> Una agregación SQL válida no necesariamente representa una métrica BI válida.

---

# 16. Ejemplo de problema: Margin

La columna:

```text
margin
```

en NEXA representa un **importe monetario**.

No representa un porcentaje.

Tenemos:

```text
margin = revenue - cost_amount
```

Por tanto:

```text
Margin Amount = SUM(margin)
```

Si queremos porcentaje:

```sql
SUM(margin) / NULLIF(SUM(revenue), 0)
```

La Semantic Layer debe distinguir ambos conceptos.

---

# 17. Fase 3 — Human Validation

El borrador generado por IA **no se utiliza directamente**.

Debemos crear:

```text
config/semantic_layer.json
```

Podemos comenzar copiando:

```text
config/semantic_layer.example.json
```

Ejemplo:

```bash
cp config/semantic_layer.example.json config/semantic_layer.json
```

Luego debemos revisar y adaptar el contenido.

---

# 18. Semantic Layer aprobada

La Semantic Layer debe definir de forma explícita conceptos como:

```text
Revenue
Gross Sales
Units Sold
Orders
Discount
Cost
Margin
Margin %
Average Order Value
Average Net Selling Price
Average Unit Cost
```

Ejemplos:

```json
"revenue": {
  "label": "Revenue",
  "sql": "SUM(revenue)",
  "synonyms": [
    "ventas",
    "venta",
    "vendimos",
    "ventas totales",
    "sales",
    "ingresos",
    "facturacion"
  ]
}
```

Pedidos:

```json
"orders": {
  "label": "Orders",
  "sql": "COUNT(DISTINCT order_id)",
  "synonyms": [
    "pedidos",
    "ordenes",
    "orders"
  ]
}
```

Ticket promedio:

```json
"average_order_value": {
  "label": "Average Order Value",
  "sql": "SUM(revenue) / NULLIF(COUNT(DISTINCT order_id), 0)",
  "synonyms": [
    "ticket medio",
    "ticket promedio",
    "average order value"
  ]
}
```

---

# 19. Ambigüedad semántica

La Semantic Layer también gobierna términos ambiguos.

Ejemplo:

```text
ventas
```

podría significar:

- revenue;
- gross sales;
- unidades vendidas;
- número de pedidos.

NEXA define como regla:

```text
ventas → Revenue
```

salvo que el usuario especifique otra métrica.

Otro ejemplo:

```text
mejor canal
```

¿Mejor por qué?

Puede ser:

- revenue;
- pedidos;
- unidades;
- margen.

La regla aprobada puede ser:

```text
mejor → Revenue
```

cuando el usuario no especifica otra métrica.

---

# 20. Business Context

La Semantic Layer también puede contener contexto empresarial.

Por ejemplo:

```json
"business_context": {
  "currency": "PEN",
  "currency_symbol": "S/",
  "locale": "es-PE"
}
```

Esto evita que Bedrock invente unidades o monedas.

Por ejemplo, el modelo no debe convertir:

```text
128611.80
```

automáticamente en:

```text
$128,611.80
```

si el sistema nunca declaró USD.

---

# 21. Principio de gobierno

El flujo correcto es:

```text
Technical Metadata
       ↓
Bedrock
       ↓
Semantic Draft
       ↓
Human Review
       ↓
Approved Semantic Layer
```

Principio:

> **AI can discover structure. Business governs meaning.**

---

# 22. Fase 4 — Probar NL-to-SQL

Ejecutar:

```bash
PYTHONPATH=. python scripts/03_test_nl2sql.py
```

El script solicitará:

```text
Business question:
```

Probar:

```text
¿Qué categoría generó más ventas?
```

Resultado esperado:

```text
Interpretation:
"ventas" → Revenue
```

SQL aproximado:

```sql
SELECT
    category,
    SUM(revenue) AS revenue
FROM vw_nexa_genbi_sales
GROUP BY category
ORDER BY revenue DESC
LIMIT 100;
```

Al final:

```text
SQL Guard: PASSED
```

---

# 23. Semantic Resolver

Antes de enviar la pregunta a Bedrock, la aplicación intenta resolver métricas conocidas utilizando la Semantic Layer.

Por ejemplo:

```text
ticket promedio
       ↓
Average Order Value
       ↓
SUM(revenue) /
COUNT(DISTINCT order_id)
```

Esto evita que el modelo pueda cambiar arbitrariamente la definición de una métrica aprobada.

Principio:

> **Las métricas gobernadas no se negocian con el LLM.**

---

# 24. Ejemplo — Ticket promedio

Ejecutar:

```bash
PYTHONPATH=. python scripts/03_test_nl2sql.py
```

Pregunta:

```text
¿Cuál fue el ticket promedio?
```

Resultado esperado:

```text
Interpretation:
"ticket promedio" → Average Order Value
```

SQL:

```sql
SELECT
    SUM(revenue)
    / NULLIF(COUNT(DISTINCT order_id), 0)
    AS ticket_promedio
FROM vw_nexa_genbi_sales;
```

---

# 25. SQL Safety Gate

Antes de ejecutar una query, pasa por:

```text
src/sql_guard.py
```

El SQL Guard valida reglas como:

```text
✓ Solo SELECT
✓ Solo la GenBI View autorizada
✓ No SELECT *
✓ No INSERT
✓ No UPDATE
✓ No DELETE
✓ No DROP
✓ No ALTER
✓ No comentarios SQL
✓ No múltiples sentencias
```

Importante:

> El SQL Guard del laboratorio es pedagógico. No representa un SQL firewall completo de producción.

---

# 26. Fase 5 — Ejecutar GenBI contra Athena

Una vez comprobado el NL-to-SQL, ejecutamos realmente la consulta.

```bash
PYTHONPATH=. python scripts/04_execute_genbi_query.py
```

Ejemplo:

```text
Business question:
cual fue el ticket promedio?
```

Resultado esperado:

```text
Interpretation:
"ticket promedio" → Average Order Value

Metric:
average_order_value

Generated SQL:
SELECT ...

SQL Guard: PASSED

Executing in Athena...

--- RESULT ---

ticket_promedio
628.463373362445
```

También se mostrarán estadísticas de Athena:

```text
Query ID
Execution time
Data scanned
```

---

# 27. Athena sigue siendo la fuente de verdad

Es importante distinguir responsabilidades.

Bedrock:

```text
interpreta lenguaje
genera SQL
genera insights
```

Athena:

```text
ejecuta las consultas
calcula las métricas
devuelve los datos
```

Por tanto:

> **Bedrock no calcula las ventas. Athena calcula las ventas.**

---

# 28. Fase 6 — Golden Queries

Una aplicación GenBI no debe considerarse correcta únicamente porque sus respuestas parecen razonables.

Necesitamos consultas de referencia.

Archivo:

```text
config/reference_queries.json
```

Ejemplo:

```json
{
  "id": "GQ02",
  "question": "cuantos pedidos tuvimos?",
  "metric": "orders",
  "reference_sql": "SELECT COUNT(DISTINCT order_id) AS orders FROM vw_nexa_genbi_sales"
}
```

---

# 29. Ejecutar las Golden Queries

Ejecutar:

```bash
PYTHONPATH=. python scripts/05_validate_reference.py
```

El proceso será:

```text
Natural Language Question
       ↓
Generated SQL
       ↓
Athena
       ↓
Generated Result
```

y paralelamente:

```text
Reference SQL
       ↓
Athena
       ↓
Reference Result
```

Luego se comparan los valores.

No se comparan las cadenas SQL.

---

# 30. Ejemplo de validación

Podemos tener:

```sql
SELECT COUNT(DISTINCT order_id)
FROM vw_nexa_genbi_sales;
```

y otro SQL equivalente con alias diferentes.

Ambos son correctos si producen el mismo resultado.

Por eso validamos:

```text
Generated Result
       versus
Reference Result
```

no:

```text
Generated SQL string
       versus
Reference SQL string
```

Resultado esperado del laboratorio:

```text
==============================
 VALIDATION SUMMARY
==============================

Passed: 4/4
Accuracy: 100.0%
```

Esto significa:

> 100% de las Golden Queries incluidas en esta batería han producido el resultado esperado.

No significa que cualquier pregunta posible tenga 100% de precisión.

---

# 31. Fase 7 — Insight + Visualization

Ahora ejecutamos:

```bash
PYTHONPATH=. python scripts/06_genbi_result.py
```

Pregunta recomendada:

```text
¿Qué categoría generó más ventas?
```

El flujo será:

```text
Question
   ↓
Semantic Layer
   ↓
Bedrock NL-to-SQL
   ↓
SQL Guard
   ↓
Athena
   ↓
DataFrame
   ├── Bedrock → Business Insight
   └── Plotly → Visualization
```

---

# 32. Business Insight

Bedrock recibe únicamente:

- pregunta original;
- contexto empresarial aprobado;
- resultado de Athena.

El modelo no debe inventar:

- causas;
- explicaciones no presentes en los datos;
- tendencias inexistentes;
- benchmarks;
- monedas;
- información externa.

Por ejemplo, puede afirmar:

```text
Fashion fue la categoría con mayor revenue.
```

si el resultado de Athena lo demuestra.

Pero no debería afirmar:

```text
Fashion creció gracias a una campaña de marketing.
```

si esa información no existe en la query.

---

# 33. Visualization Engine

La visualización no se construye ejecutando código Python generado por el LLM.

La aplicación utiliza reglas deterministas.

Ejemplos:

```text
1 KPI
→ KPI / Table
```

```text
Dimensión + métrica
→ Bar Chart
```

```text
Tiempo + métrica
→ Line Chart
```

Esto reduce riesgo y hace el comportamiento de la aplicación más predecible.

---

# 34. Probar comparación por categoría

Ejecutar:

```bash
PYTHONPATH=. python scripts/06_genbi_result.py
```

Pregunta:

```text
¿Qué categoría generó más ventas?
```

El sistema debería seleccionar:

```text
Bar Chart
```

---

# 35. Probar evolución temporal

Ejecutar una pregunta como:

```text
¿Cómo evolucionaron las ventas por mes?
```

El sistema debería producir una consulta agrupada temporalmente y seleccionar:

```text
Line Chart
```

La aplicación puede generar también un insight resumido sobre la evolución observada.

---

# 36. Fase 8 — Aplicación Streamlit

Una vez probados los componentes individuales, ejecutamos la aplicación completa.

Desde la raíz:

```bash
streamlit run app.py
```

Normalmente aparecerá:

```text
Local URL:
http://localhost:8501
```

Abrir esa dirección en el navegador.

---

# 37. Interfaz NEXA Generative BI

La aplicación permite introducir una pregunta como:

```text
¿Qué categoría generó más ventas?
```

La pantalla mostrará:

```text
Business Insight

Visualization

Athena Result
```

Además puede activarse:

```text
Mostrar detalles técnicos
```

---

# 38. Detalles técnicos

Al activar esa opción aparecerán elementos como:

```text
Métrica interpretada

Semantic Interpretation

Semantic Rule Applied

Generated SQL

SQL Governance

Visualization Decision

Athena Metadata
```

Esto permite observar qué ocurrió detrás de la respuesta.

Ejemplo:

```text
"ventas" → Revenue
```

Luego:

```sql
SUM(revenue)
```

y finalmente:

```text
SQL Guard: PASSED
```

---

# 39. Preguntas recomendadas

Probar diferentes tipos de preguntas.

## KPI

```text
¿Cuánto vendimos en total?
```

```text
¿Cuántos pedidos tuvimos?
```

```text
¿Cuál fue el ticket promedio?
```

```text
¿Cuál fue el margen total?
```

## Comparación

```text
¿Qué categoría generó más ventas?
```

```text
¿Qué canal vendió más?
```

## Ambigüedad

```text
¿Qué canal fue el mejor?
```

La Semantic Layer debe aplicar:

```text
mejor → Revenue
```

si no se especifica otra métrica.

## Serie temporal

```text
¿Cómo evolucionaron las ventas por mes?
```

---

# 40. Qué debe observar el alumno

No debemos mirar solamente si aparece una respuesta.

Para cada prueba revisar:

```text
1. ¿Qué entendió de la pregunta?

2. ¿Qué métrica seleccionó?

3. ¿Qué regla semántica aplicó?

4. ¿Qué SQL generó?

5. ¿Pasó el SQL Guard?

6. ¿Qué respondió Athena?

7. ¿Qué insight generó Bedrock?

8. ¿Qué visualización seleccionó?

9. ¿El resultado tiene sentido desde BI?
```

---

# 41. Qué NO forma parte de este laboratorio

Deliberadamente no utilizamos:

```text
LangChain
RAG
Vector Databases
Agents
AgentCore
Lambda
API Gateway
Knowledge Bases
Orquestación compleja
```

No son necesarios para demostrar el patrón de GenBI trabajado en esta asignatura.

El objetivo sigue siendo **Business Intelligence**.

---

# 42. Security Note

`sql_guard.py` está diseñado para ser comprensible durante la clase.

No debe considerarse un mecanismo completo de seguridad de producción.

En un entorno empresarial real deberían considerarse además:

- IAM de mínimo privilegio;
- Lake Formation;
- Athena Workgroups;
- permisos S3;
- límites de coste y escaneo;
- logging y auditoría;
- SQL parser;
- políticas de acceso por usuario;
- control de datos sensibles.

---

# 43. Actividad posterior — cada grupo

NEXA es el caso guiado.

Cada grupo deberá replicar el patrón utilizando **su propio Data Mart**.

No deberán copiar simplemente la Semantic Layer de NEXA.

Cada grupo deberá construir:

```text
SU DATA MART
      ↓
SU GENBI VIEW
      ↓
SU DATASET PROFILE
      ↓
SU SEMANTIC DRAFT
      ↓
HUMAN VALIDATION
      ↓
SU SEMANTIC LAYER
      ↓
NL-to-SQL
      ↓
SQL GUARD
      ↓
ATHENA
      ↓
INSIGHT
      ↓
VISUALIZATION
      ↓
STREAMLIT
```

---

# 44. Entregables mínimos por grupo

Cada proyecto debe incluir:

### Data Mart

Modelo dimensional correctamente diseñado.

### GenBI View

Una vista controlada que exponga solamente la información necesaria para GenBI.

### Dataset Profile

Generado automáticamente a partir de la GenBI View.

### Semantic Layer Draft

Generado con asistencia de Bedrock.

### Human Validation

Explicar qué elementos propuestos por Bedrock fueron:

```text
aceptados
corregidos
rechazados
```

y por qué.

### Approved Semantic Layer

Debe incluir como mínimo:

```text
5 dimensiones
4 métricas
5 sinónimos
5 reglas de negocio
3 ambigüedades
```

### NL-to-SQL

Preguntas de negocio convertidas a SQL.

### SQL Governance

El SQL debe pasar un mecanismo de validación antes de llegar a Athena.

### Streamlit

Debe mostrar:

```text
Pregunta
Interpretación
Resultado
Insight
Visualización
```

### Golden Queries

Mínimo:

```text
10 preguntas de referencia
```

con SQL validado manualmente.

---

# 45. Mejoras opcionales

Una vez que el pipeline obligatorio funcione, cada grupo puede mejorar:

- diseño de Streamlit;
- KPI Cards;
- formato de moneda;
- formato de números;
- nuevos tipos de gráficos;
- mejores mensajes de error;
- nuevas reglas semánticas;
- más Golden Queries;
- validación adicional de SQL;
- filtros;
- branding;
- experiencia de usuario.

Estas mejoras son secundarias respecto a la correcta definición del modelo BI.

---

# 46. Principios que deben quedar claros

## Principio 1

> Un LLM no sustituye al Data Mart.

## Principio 2

> Una columna no define automáticamente una métrica de negocio.

## Principio 3

> AI can discover structure. Business governs meaning.

## Principio 4

> Las métricas aprobadas deben controlar al LLM, no al revés.

## Principio 5

> SQL seguro no significa necesariamente SQL semánticamente correcto.

## Principio 6

> Athena sigue siendo la fuente de verdad para los cálculos.

## Principio 7

> Un insight generativo debe basarse únicamente en evidencia disponible.

## Principio 8

> Una solución GenBI no está terminada cuando responde.

Está terminada cuando podemos **demostrar que responde correctamente**.

---

# 47. Resultado final esperado

Al finalizar el laboratorio tendremos construido:

```text
NEXA Retail Generative BI
```

capaz de recibir preguntas en lenguaje natural como:

```text
¿Qué categoría generó más ventas?

¿Cuántos pedidos tuvimos?

¿Cuál fue el ticket promedio?

¿Qué canal fue el mejor?

¿Cómo evolucionaron las ventas por mes?
```

y ejecutar de forma gobernada:

```text
Natural Language
      ↓
Semantic Layer
      ↓
Bedrock
      ↓
SQL
      ↓
SQL Guard
      ↓
Athena
      ↓
Validated Data
      ↓
Insight + Visualization
```

Ese es el patrón que posteriormente deberá adaptarse al Data Mart de cada proyecto.