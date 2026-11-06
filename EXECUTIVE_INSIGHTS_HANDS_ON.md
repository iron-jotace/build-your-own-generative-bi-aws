# Hands-on 05 — Executive Insights fundamentados en Athena

Objetivo: mostrar hallazgos ejecutivos junto al dashboard, sin permitir que Bedrock invente valores.

## Arquitectura

```text
Dashboard validado -> Athena -> DataFrames
                        |
                        v
              evidence_from_results()
                (hechos deterministas)
                        |
                        v
              Bedrock selecciona IDs
                        |
                        v
              Renderer: hechos exactos
```

El modelo **no redacta cifras ni causas**: elige identificadores de hechos existentes. Si el modelo falla, se muestran hasta cuatro hechos deterministas.

## Ejecución

```bash
conda activate nexa-dashboard
git switch feature/prompt-to-dashboard
git pull --ff-only
python -m unittest discover -s tests -v
python -m streamlit run app.py
```

1. Abre Build Dashboard.
2. Genera un dashboard ejecutivo con Bedrock o carga el ejemplo de siete componentes.
3. Deja marcada la casilla **Executive Insights (selección con Bedrock)**.
4. Construye el dashboard. Al final verás **Executive Insights** con hechos derivados de Athena.
5. Desmarca la casilla y vuelve a ejecutar: verás hechos deterministas sin segunda llamada a Bedrock.

## Validaciones del docente

- Ventas: S/575,672.45; pedidos: 916; AOV: ~S/628.46, siempre que la vista mantenga los mismos registros y definiciones.
- El margen monetario observado debe reconciliarse con la fórmula aprobada y Athena.
- Si hay un gráfico mensual, el sistema podrá señalar el mes de mayor valor observado, pero **no afirmará** que la caída de otro mes se debe a una causa o que el último mes está completo.
- Con datos vacíos o consulta fallida, no se inventan cifras ni hallazgos.
- Cambia la selección del modelo por un ID inexistente en una prueba unitaria: debe rechazarse.

## Limitaciones

- Los insights de esta versión son hechos verificados **priorizados** por IA, no explicaciones causales generadas libremente.
- No se aplican filtros globales de fecha, ni se evalúan períodos completos/incompletos con una tabla calendario.
- Los controles de IAM y Athena Workgroup siguen siendo necesarios; el SQL Guard es pedagógico.
- Antes de afirmar que esta fase funciona en AWS, ejecutar las pruebas y comprobar la interfaz en la cuenta del docente.
