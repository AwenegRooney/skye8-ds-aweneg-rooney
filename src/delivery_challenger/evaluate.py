import mlflow
from mlflow.pyfunc import PyFuncModel

from delivery_challenger.config import DATA_DIR, OPERATIONAL_THRESHOLD_MINUTES
from delivery_challenger.data import get_processed_data
from delivery_challenger.segment import add_distance_bucket, add_hour_of_day
from delivery_challenger.statistics import (
    evaluate_paired_difference,
    run_segment_statistical_analysis,
)


def load_staging_model() -> PyFuncModel:
    """Loads the model currently in Staging from the MLflow Model Registry."""
    model_uri = "models:/delivery-challengers/Staging"
    return mlflow.pyfunc.load_model(model_uri)


def main() -> None:
    # 1. Load holdout dataset
    _, holdout = get_processed_data(DATA_DIR)

    # 2. Add required feature engineering
    holdout = add_hour_of_day(holdout)
    holdout = add_distance_bucket(holdout)

    # Preprocess categorical types for LightGBM
    categorical_features = [
        "package_type",
        "pickup_zone",
        "vehicle",
        "dropoff_zone",
        "home_zone",
        "market_zone_dropoff",
        "market_zone",
    ]

    for col in categorical_features:
        holdout[col] = holdout[col].astype("category")

    # 3. Generate predictions using the promoted Staging model
    print("Loading Challenger model from MLflow Registry (Staging)...")
    challenger_model = load_staging_model()

    feature_columns = [
        "distance_km",
        "experience_months",
        "hour_of_day",
        "raining",
        "congestion_index",
        "tarred_share_pct",
        "congestion_index_dropoff",
        "tarred_share_pct_dropoff",
    ] + categorical_features

    predictions = challenger_model.predict(holdout[feature_columns])
    holdout["predicted_challenger"] = predictions

    # 4. Overall Paired Evaluation
    abs_err_incumbent = (
        holdout["actual_minutes"] - holdout["predicted_minutes_v1"]
    ).abs()

    abs_err_challenger = (
        holdout["actual_minutes"] - holdout["predicted_challenger"]
    ).abs()

    overall_stats = evaluate_paired_difference(abs_err_incumbent, abs_err_challenger)
    print("\n" + "=" * 50)
    print("    STAGE C: OVERALL PAIRED COMPARISON RESULTS   ")
    print("=" * 50)
    print(f"Mean Improvement: {overall_stats['mean_improvement_minutes']:.2f} minutes")
    print(f"95% CI: [{overall_stats['ci_lower']:.2f}, {overall_stats['ci_upper']:.2f}]")
    print(f"p-value: {overall_stats['p_value']:.4e}")
    print(f"Sample Size: {overall_stats['sample_size']} deliveries")

    # State decision against declared operational threshold
    improvement = overall_stats["mean_improvement_minutes"]
    is_stat_sig = overall_stats["p_value"] < 0.05
    if is_stat_sig and improvement >= OPERATIONAL_THRESHOLD_MINUTES:
        print(
            f"\nVerdict: SHIP RECOMMENDED. Statistically significant and meets operational threshold (>= {OPERATIONAL_THRESHOLD_MINUTES} min)."
        )
    elif is_stat_sig and improvement < OPERATIONAL_THRESHOLD_MINUTES:
        print(
            f"\nVerdict: DO NOT SHIP. Statistically significant but operationally trivial (<{OPERATIONAL_THRESHOLD_MINUTES} min)."
        )
    else:
        print("\nVerdict: DO NOT SHIP. No statistically significant difference.")

    # 5. Segment-level Analysis
    print("\n" + "=" * 50)
    print("    SEGMENT MULTIPLICITY & POWER ANALYSIS    ")
    print("=" * 50)

    segment_results = run_segment_statistical_analysis(
        holdout_df=holdout,
        challenger_preds=holdout["predicted_challenger"],
        operational_threshold=OPERATIONAL_THRESHOLD_MINUTES,
    )
    # Format output table for scannability
    display_cols = [
        "dimension",
        "segment_value",
        "sample_size",
        "mean_improvement_minutes",
        "p_value_corrected",
        "status",
        "required_n_for_1min_diff",
    ]
    print(segment_results[display_cols].to_string(index=False))

    # Highlight any regressed segments explicitly
    regressed = segment_results[segment_results["status"] == "Regressed (Worse)"]
    if not regressed.empty:
        print("\n" + "!" * 50)
        print("WARNING: REGRESSED SEGMENTS DETECTED!")
        print("!" * 50)
        print(
            regressed[
                ["dimension", "segment_value", "mean_improvement_minutes"]
            ].to_string(index=False)
        )


if __name__ == "__main__":
    main()
