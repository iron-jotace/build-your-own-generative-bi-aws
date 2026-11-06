# USMP 2026-II · Hands-on final: Governed Prompt-to-Dashboard

**Curso:** Business Intelligence — Ingeniería de Computación y Sistemas, USMP  
**Caso:** NEXA Retail  
**Región AWS:** \`eu-west-1\` (Irlanda)  
**Rama:** \`feature/prompt-to-dashboard\`

> Este laboratorio extiende el GenBI de una pregunta NL-to-SQL a un dashboard completo creado desde un único prompt. El modelo no genera Python ni SQL ejecutable; propone un JSON declarativo, el sistema valida la semántica, Python compila el SQL y Athena calcula los datos.

## 0. Resultado esperado

En la página **Build Dashboard**, escribir una instrucción de negocio y pulsar **✨ Generar dashboard completo**. El resultado puede contener KPI Cards, líneas temporales, barras horizontales, tablas y Executive Insights, según lo propuesto por Bedrock y autorizado por la Semantic Layer.

La generación es **dinámica**: los componentes se eligen por prompt, no son gráficos fijos hardcodeados. Los hechos ejecutivos se calculan desde Athena. Bedrock **prioriza IDs de evidencia**, sin inventar cifras.

## 1. Arquitectura que explicamos en clase

\`\`\`text
S3 -> Glue Catalog -> Athena Data Mart / GenBI View
                           |
Usuario --prompt--> Bedrock Dashboard Planner
                           |
                   Dashboard JSON (hasta 8)
                           |
                   Schema + Semantic Validator
                           |
                   Deduplicación analítica
                           |
                  Deterministic SQL Builder
                           |
                 SQL Guard -> IAM/Workgroup
                           |
                       Athena
                           |
                 DataFrames con resultados
                    /                \
             Streamlit/Plotly     Evidence Builder
                    |                |
                    |          Bedrock ID Selector
                    \                /
                     Dashboard + Insights
\`\`\`

**Separación de responsabilidades:**
- Bedrock: selecciona componentes, métricas aprobadas, dimensiones y gráfico (JSON), después selecciona hechos para destacar.
- Semantic Layer: define el grano, columnas permitidas, definiciones aprobadas y contexto monetario.
- SQL Builder: genera SQL desde expresiones locales aprobadas; no ejecuta fragmentos de SQL del modelo.
- SQL Guard / AWS: restringen consultas. El SQL Guard regex es didáctico y NO sustituye permisos IAM/Lake Formation, límites Athena, aislamiento por usuario ni análisis SQL real.
- Athena: calcula KPI, desgloses y series.
- Renderer: visualiza resultados, sin ejecutar código generado por Bedrock.
- Insights: hechos redactados deterministicamente desde DataFrames; modelo escoge identificadores existentes.

## 2. Prerrequisitos

- AWS CLI autenticado, permisos adecuados para Athena, consulta de la vista, resultado S3 y Bedrock Runtime.
- Base de datos \`nexa_master\` y vista \`vw_nexa_genbi_sales\` creadas (ver \`sql/01_create_genbi_view.sql\`).
- Modelo Bedrock habilitado en la cuenta; se utiliza el \`bedrock_model_id\` configurado y la API Converse.
- Python 3.11 preferido.
- Mantener \`config/settings.json\` y \`config/semantic_layer.json\` **locales**, no subir credenciales ni configuraciones sensibles al repositorio público.

Verificar AWS y región:
\`\`\`bash
aws sts get-caller-identity
aws configure get region
\`\`\`
La región efectiva utilizada por la aplicación es \`aws_region\` de \`config/settings.json\`: debe ser \`eu-west-1\`.

### Configuración local

Copiar \`config/settings.example.json\` como \`config/settings.json\`; ajustar:
- \`aws_region\`: \`eu-west-1\`
- \`athena_database\`: \`nexa_master\`
- \`allowed_view\`: \`vw_nexa_genbi_sales\`
- \`athena_output_s3\`: bucket S3 real y carpeta de resultados Athena
- \`athena_workgroup\`: workgroup disponible
- \`bedrock_model_id\`: modelo autorizado por la cuenta

**Importante:** \`config/semantic_layer.example.json\` es solo una plantilla y NO contiene todas las medidas de la clase. Antes de ejecutar, crear/usar la capa **aprobada** \`config/semantic_layer.json\`. No editar fórmulas para que “cuadren”: corroborarlas con el Data Mart.

## 3. Instalar y lanzar en Mac/Linux

\`\`\`bash
git clone https://github.com/iron-jotace/build-your-own-generative-bi-aws.git
cd build-your-own-generative-bi-aws
git fetch origin
git switch feature/prompt-to-dashboard

conda create -n nexa-dashboard python=3.11 -y
conda activate nexa-dashboard
python -m pip install -r requirements.txt

python -m unittest discover -s tests -v
python -m streamlit run app.py
\`\`\`

Si ya tienes la carpeta clonada: \`git switch feature/prompt-to-dashboard\` y \`git pull --ff-only\` en lugar de \`git clone\`.

Streamlit se abre localmente, normalmente en \`http://localhost:8501\`. En el menú lateral seleccionar **Build Dashboard**.

## 4. Modo principal: un prompt, un dashboard

1. Selecciona **✨ Prompt-to-Dashboard**.
2. Escribe el escenario de negocio elegido.
3. Pulsa **✨ Generar dashboard completo**.
4. Observa el resultado de Athena y los insights. Si un componente falla, el dashboard puede ser parcial y mostrará advertencia.
5. Abre **Dashboard Specification JSON (auditoría)**: verás los componentes propuestos. No hay Python ni SQL generado por el modelo en ese contrato.
6. Abre **⚙️ Opciones y trazabilidad**: activa SQL y metadatos cuando quieras enseñar la gobernanza.

Hay un botón adicional **Solo planificar** para el ejercicio docente: genera y valida JSON sin consultar Athena.

## 5. Modo JSON para aislar problemas

1. Selecciona **🧩 Laboratorio JSON**.
2. En **Ejemplo preparado**, selecciona **Comercial** o **Ejecutivo**.
3. Pulsa **Cargar ejemplo** y revisa el JSON.
4. Pulsa **Construir desde JSON**.
5. El motor debe producir exactamente los componentes declarados.

Ejecutar primero en modo JSON es útil para distinguir entre errores del Planner y del motor de consultas.

## 6. Cuatro escenarios de negocio

Los prompts completos están también en \`config/dashboard_scenarios.json\`, junto a sus métricas y dimensiones esperadas como **focos de evaluación** (no como garantías de salida).

### A. Ejecutivo

«Construye un dashboard ejecutivo de NEXA Retail para dirección. Prioriza ventas totales, pedidos únicos, ticket promedio y margen total. Añade evolución mensual de ventas, comparativa por categoría y ventas por canal. Incluye insights basados en los resultados de Athena. Evita duplicar la misma métrica y dimensión. No infieras causas ni inventes resultados.»

**Observar:** KPI revenue/orders/AOV/margin, línea \`sale_month\`, comparación categoría y canal; hasta 8 componentes.

### B. Comercial

«Construye un dashboard comercial de NEXA Retail centrado en ingresos y unidades vendidas. Compara ventas por categoría, marca y canal, y añade evolución mensual. Incluye los KPI necesarios sin repetir gráficos de la misma métrica y dimensión. Destaca las categorías y canales líderes usando únicamente hechos de Athena. No inventes cifras ni razones del desempeño.»

**Observar:** dimensiones category, brand y sales_channel, más tendencia mensual si existe espacio.

### C. Rentabilidad

«Construye un dashboard de rentabilidad para NEXA Retail. Prioriza ingresos, coste, margen monetario y porcentaje de margen. Compara rentabilidad por categoría y canal. Distingue claramente ingresos de margen y muestra dónde se concentra el resultado. Usa solo métricas aprobadas; no inventes EBITDA ni atribuyas causas a las diferencias.»

**Observar:** métricas aprobadas \`cost\`, \`margin\` y \`margin_pct\`. Verificar unidades y escala de \`margin_pct\` con la fórmula aprobada.

### D. Clientes

«Construye un dashboard de clientes de NEXA Retail. Analiza ingresos y pedidos por segmento de cliente y por ciudad, junto con KPI generales de ventas y ticket promedio. Selecciona gráficos o tablas según los resultados. No confundas pedidos con clientes únicos, y no calcules churn, retención ni lifetime value si no están aprobados en la Semantic Layer. Destaca hallazgos sustentados en Athena.»

**Observar:** \`customer_segment\`, \`customer_city\`, sin inferir métricas que no estén definidas.

## 7. Validación cuantitativa de NEXA

Los siguientes son **valores de referencia del laboratorio docente**, no deben hardcodearse en el renderer:

| Métrica | Referencia |
|---|---:|
| Ventas totales | S/ 575,672.45 |
| Pedidos únicos | 916 |
| Ticket promedio | S/ 628.46 aprox. |
| Margen monetario observado en la validación docente | S/ 206,807.08 |

Verifica con \`config/reference_queries.json\` y \`scripts/05_validate_reference.py\` (GQ01, GQ02, GQ03, GQ04). Solo comparar cifras si son la misma vista y el mismo conjunto de datos/filtros.

Los resultados por categoría y canal deben reconciliar con el total cuando se hayan incluido TODOS los grupos. Un top-N incompleto no debe interpretarse como el 100%.

**Aviso sobre la serie temporal:** un descenso en el último mes puede deberse a cobertura parcial; no atribuirlo automáticamente a peor desempeño ni comparar meses incompletos sin validar calendario/cobertura.

## 8. Matriz de pruebas de gobierno

| Prueba | Entrada | Resultado esperado |
|---|---|---|
| Métrica no aprobada | Cambiar KPI a \`ebitda\` | Rechazo previo a Athena |
| SQL inyectado | Añadir \`"sql":"DROP TABLE x"\` al JSON | Rechazo de esquema |
| Tabla ajena | SQL manual hacia tabla no permitida | Bloqueo por guard/permisos |
| Dimensión inexistente | \`dimension: "unknown"\` | Rechazo previo a Athena |
| Línea sin tiempo | \`type:"line"\` con \`category\` | Rechazo |
| Duplicación | \`revenue\` / \`sale_month\` tanto en tabla como línea | Planner conserva la línea preferentemente |
| Mes inexistente | Consulta sin filas | Sin resultados inventados |
| Dashboard amplio | Más de 8 componentes en modo Bedrock | Rechazo del plan |
| Insight inventado | Bedrock selecciona un ID que no existe | Rechazo; fallback a hechos verificados |

Ejecutar las pruebas:
\`\`\`bash
python -m unittest discover -s tests -v
\`\`\`

Las pruebas unitarias con modelos y Athena simulados **no sustituyen** las verificaciones reales sobre la cuenta del profesor.

## 9. Problemas frecuentes

**Python 3.9 y boto3:** el requisito \`boto3>=1.43.0\` necesita Python 3.10 o superior. Usa Conda Python 3.11.

**Falta \`semantic_layer.json\`:** el archivo aprobado se genera/valida en la clase anterior y no está publicado en el repositorio. No confundas el ejemplo con la versión aprobada.

**\`Unapproved metric\`:** el modelo propuso un identificador que no existe en \`measures\` o falta la definición local. No añadir fórmulas inventadas para evitar el error.

**Permisos o S3:** comprueba \`aws sts get-caller-identity\`, Workgroup, OutputLocation de Athena, catálogo y permisos.

**Falla Bedrock:** revisa \`bedrock_model_id\`, acceso al modelo y permisos de invocación en \`eu-west-1\`; usa modo JSON para verificar Athena por separado.

**Dashboard parcial:** revisar la sección de SQL/metadatos y el mensaje del componente; no presentar el dashboard como completo.

## 10. Explicación breve del código para alumnos

- \`src/dashboard_planner.py\`: describe el catálogo y convierte prompt → plan JSON, validado y sin duplicaciones exactas.
- \`src/dashboard_validator.py\`: comprueba IDs y tipos; deriva \`sale_month\` si \`sale_date\` está aprobada.
- \`src/dashboard_sql_builder.py\`: combina SQL de métricas aprobadas con columnas permitidas y agrupaciones.
- \`src/dashboard_runtime.py\`: SQL Guard + Athena + conversión a DataFrames.
- \`src/dashboard_renderer.py\`: tarjetas y gráficos Plotly/Streamlit sin ejecutar código del LLM.
- \`src/dashboard_insights.py\`: genera evidencia desde Athena y deja que Bedrock seleccione IDs.
- \`pages/1_Build_Dashboard.py\`: interfaz de una acción + modo laboratorio JSON.
- \`tests/\`: tests de validación, SQL, evidencias y escenarios.

## 11. Reto final por equipos

Cada grupo adapta el patrón a su **propio Data Mart** y entrega:
1. Semantic Layer aprobada: al menos cuatro métricas y tres dimensiones cuando los datos lo permitan.
2. Dos prompts distintos que generen composiciones diferentes.
3. Reconciliación de dos KPI contra SQL de referencia.
4. Una prueba negativa que demuestre bloqueo.
5. Explicación de qué decidió Bedrock, qué validó la aplicación y qué calculó Athena.

**Pregunta de cierre:** *¿Qué parte de vuestro dashboard ha decidido la IA y cuál está respaldada por reglas de negocio y cálculos verificables?*

## 12. Límites de esta versión

- Solo una vista autorizada por configuración; no existe aún un modelo completo de permisos por usuario, filtro temporal global ni aislamiento multi-tenant.
- La validación SQL con expresiones regulares es pedagógica, no un firewall empresarial.
- Los gráficos reflejan grupos existentes, sin rellenar meses faltantes.
- Los insights son hechos verificables seleccionados por Bedrock, **no análisis causales ni recomendaciones libres**.
- La normalización del Planner elimina componentes redundantes por el par métrica/dimensión; no inventa sustitutos.
- Mantener un workgroup Athena y permisos IAM apropiados, con control de costes y protección de datos.

## 13. Criterio de finalización de la práctica

El alumno puede demostrar: **un prompt**, un **JSON auditable**, métricas de Semantic Layer, SQL validado, resultados reales de Athena, **dashboard diferente al cambiar la intención**, insights sin alucinaciones y una prueba negativa.

> **Bedrock interpreta. La Semantic Layer gobierna. Athena calcula. Streamlit presenta.**
