from src.athena import AthenaClient
from src.bedrock import BedrockClient
from src.config import load_json, load_settings
from src.insight import generate_insight
from src.sql_generator import generate_sql
from src.sql_guard import validate_sql
from src.visualization import choose_chart


def main():

    settings = load_settings()

    semantic = load_json(
        "config/semantic_layer.json"
    )

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

    question = input(
        "Business question: "
    ).strip()

    # ----------------------------------
    # 1. Semantic Layer + NL-to-SQL
    # ----------------------------------

    generated = generate_sql(
        bedrock,
        question,
        semantic,
    )

    sql = generated["sql"]

    print("\n--- SEMANTIC INTERPRETATION ---")

    print(
        generated["interpretation"]
    )

    print("\nMetric:")

    print(
        generated["metric_used"]
    )

    print("\n--- GENERATED SQL ---")

    print(sql)

    # ----------------------------------
    # 2. SQL Guard
    # ----------------------------------

    validate_sql(
        sql,
        settings["allowed_view"],
    )

    print("\nSQL Guard: PASSED")

    # ----------------------------------
    # 3. Athena
    # ----------------------------------

    df, metadata = athena.run(sql)

    print("\n--- ATHENA RESULT ---")

    print(
        df.to_string(index=False)
    )

    # ----------------------------------
    # 4. Business Insight
    # ----------------------------------

    print(
        "\nGenerating business insight..."
    )

    insight = generate_insight(
        bedrock,
        question,
        df,
        semantic_layer=semantic,
    )

    print("\n--- BUSINESS INSIGHT ---")

    print(
        insight.get(
            "headline",
            "Business Insight",
        )
    )

    print(
        insight.get(
            "insight",
            ""
        )
    )

    if insight.get("caveat"):

        print("\nCaveat:")

        print(
            insight["caveat"]
        )

    # ----------------------------------
    # 5. Visualization decision
    # ----------------------------------

    figure, chart_type = choose_chart(df)

    print("\n--- VISUALIZATION ---")

    print(
        "Recommended chart:",
        chart_type,
    )

    if figure is not None:

        figure.show()

    # ----------------------------------
    # 6. Athena metadata
    # ----------------------------------

    scanned = metadata.get(
        "data_scanned_bytes"
    )

    print("\n--- QUERY METADATA ---")

    print(
        "Query ID:",
        metadata[
            "query_execution_id"
        ],
    )

    print(
        "Execution time:",
        metadata.get(
            "total_execution_ms"
        ),
        "ms",
    )

    if scanned is not None:

        print(
            "Data scanned:",
            round(
                scanned / 1024 / 1024,
                4,
            ),
            "MB",
        )


if __name__ == "__main__":
    main()