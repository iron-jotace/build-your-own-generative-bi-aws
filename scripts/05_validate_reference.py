import math

from src.athena import AthenaClient
from src.bedrock import BedrockClient
from src.config import load_json, load_settings
from src.sql_generator import generate_sql
from src.sql_guard import validate_sql


def to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compare_scalar_results(
    generated_df,
    reference_df,
    tolerance=0.01,
):
    """
    Compare one-row / one-value BI results.

    Column aliases do not need to match.
    We compare the actual business value.
    """

    if generated_df.shape != (1, 1):
        return False, (
            f"Generated result shape is "
            f"{generated_df.shape}, expected (1, 1)"
        )

    if reference_df.shape != (1, 1):
        return False, (
            f"Reference result shape is "
            f"{reference_df.shape}, expected (1, 1)"
        )

    generated_value = generated_df.iloc[0, 0]
    reference_value = reference_df.iloc[0, 0]

    generated_number = to_number(
        generated_value
    )

    reference_number = to_number(
        reference_value
    )

    # Numeric comparison
    if (
        generated_number is not None
        and reference_number is not None
    ):
        passed = math.isclose(
            generated_number,
            reference_number,
            rel_tol=1e-9,
            abs_tol=tolerance,
        )

        return passed, {
            "generated": generated_number,
            "reference": reference_number,
            "difference": abs(
                generated_number
                - reference_number
            ),
        }

    # Text fallback
    passed = (
        str(generated_value).strip()
        == str(reference_value).strip()
    )

    return passed, {
        "generated": generated_value,
        "reference": reference_value,
    }


def main():

    settings = load_settings()

    semantic = load_json(
        "config/semantic_layer.json"
    )

    golden_queries = load_json(
        "config/reference_queries.json"
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

    total = len(golden_queries)
    passed_count = 0

    print("\n==============================")
    print(" NEXA GENBI - GOLDEN QUERIES")
    print("==============================")

    for test in golden_queries:

        print("\n")
        print("=" * 60)
        print(
            f'{test["id"]} | '
            f'{test["question"]}'
        )
        print("=" * 60)

        # -----------------------------------
        # GenBI SQL
        # -----------------------------------

        generated = generate_sql(
            bedrock,
            test["question"],
            semantic,
        )

        generated_sql = generated["sql"]

        print("\nSemantic interpretation:")
        print(
            generated["interpretation"]
        )

        print("\nGenerated SQL:")
        print(generated_sql)

        # -----------------------------------
        # SQL Guard
        # -----------------------------------

        validate_sql(
            generated_sql,
            settings["allowed_view"],
        )

        print("\nSQL Guard: PASSED")

        # -----------------------------------
        # Execute generated SQL
        # -----------------------------------

        generated_df, _ = athena.run(
            generated_sql
        )

        # -----------------------------------
        # Execute reference SQL
        # -----------------------------------

        reference_df, _ = athena.run(
            test["reference_sql"]
        )

        # -----------------------------------
        # Compare results
        # -----------------------------------

        passed, details = (
            compare_scalar_results(
                generated_df,
                reference_df,
            )
        )

        print("\nGenerated result:")
        print(
            generated_df.to_string(
                index=False
            )
        )

        print("\nReference result:")
        print(
            reference_df.to_string(
                index=False
            )
        )

        if passed:

            passed_count += 1

            print("\nVALIDATION: ✅ PASS")

        else:

            print("\nVALIDATION: ❌ FAIL")

        print("\nComparison:")
        print(details)

    # -----------------------------------
    # Final score
    # -----------------------------------

    print("\n")
    print("==============================")
    print(" VALIDATION SUMMARY")
    print("==============================")

    print(
        f"Passed: {passed_count}/{total}"
    )

    score = (
        passed_count / total * 100
        if total
        else 0
    )

    print(
        f"Accuracy: {score:.1f}%"
    )


if __name__ == "__main__":
    main()