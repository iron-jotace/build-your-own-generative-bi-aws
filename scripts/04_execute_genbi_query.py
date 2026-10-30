from src.athena import AthenaClient
from src.bedrock import BedrockClient
from src.config import load_json, load_settings
from src.sql_generator import generate_sql
from src.sql_guard import validate_sql


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

    # -----------------------------------------
    # 1. Natural Language → SQL
    # -----------------------------------------

    result = generate_sql(
        bedrock,
        question,
        semantic,
    )

    sql = result["sql"]

    print("\nInterpretation:")
    print(result["interpretation"])

    print("\nMetric:")
    print(result["metric_used"])

    print("\nGenerated SQL:")
    print(sql)

    # -----------------------------------------
    # 2. SQL Safety Gate
    # -----------------------------------------

    validate_sql(
        sql,
        settings["allowed_view"],
    )

    print("\nSQL Guard: PASSED")

    # -----------------------------------------
    # 3. Execute Athena
    # -----------------------------------------

    print("\nExecuting in Athena...")

    df, metadata = athena.run(sql)

    # -----------------------------------------
    # 4. Results
    # -----------------------------------------

    print("\n--- RESULT ---")
    print(df.to_string(index=False))

    print("\n--- ATHENA METADATA ---")

    print(
        "Query ID:",
        metadata["query_execution_id"],
    )

    print(
        "Execution time (ms):",
        metadata["total_execution_ms"],
    )

    scanned = metadata.get(
        "data_scanned_bytes"
    )

    if scanned is not None:
        scanned_mb = scanned / 1024 / 1024

        print(
            "Data scanned (MB):",
            round(scanned_mb, 4),
        )


if __name__ == "__main__":
    main()