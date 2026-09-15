import subprocess
from typing import Any

import mlflow
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from delivery_challenger.config import DATA_DIR, DATA_VERSION
from delivery_challenger.data import get_chronological_split, get_processed_data
from delivery_challenger.evaluation import get_metrics
from delivery_challenger.segment import add_hour_of_day


def get_git_hash() -> str:
    hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("ascii").strip()
    return hash


def build_pipeline(
    model: Any, numeric_features: list[str], categorical_features: list[str]
) -> Pipeline:

    preprocessor = ColumnTransformer(
        [
            ("numeric", "passthrough", numeric_features),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                categorical_features,
            ),
        ]
    )

    return Pipeline([("preprocessor", preprocessor), ("model", model)])


def train_and_evaluate(
    pipeline: Pipeline,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_columns: list[str],
    target_col: str = "actual_minutes",
) -> tuple[Pipeline, pd.Series]:
    X_train, y_train = train_df[feature_columns], train_df[target_col]
    X_test, y_test = test_df[feature_columns], test_df[target_col]

    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)

    results = pd.DataFrame({target_col: y_test, "predicted": predictions})

    metrics = get_metrics(results, target_col, "predicted")

    return pipeline, metrics


def run_experiment(
    model_name: str,
    pipeline: Pipeline,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_columns: list[str],
    params: dict[str, Any],
    git_commit_hash: str,
    data_version: str,
) -> None:

    with mlflow.start_run(run_name=model_name):
        mlflow.log_params(params)

        mlflow.set_tag("model_type", model_name)
        mlflow.set_tag("description", f"Candidate model: {model_name}")
        mlflow.set_tag("git_commit", git_commit_hash)
        mlflow.set_tag("data_version", DATA_VERSION)

        fitted_pipeline, metrics = train_and_evaluate(
            pipeline, train_df, test_df, feature_columns
        )

        clean_metrics = {str(v): float(k) for v, k in metrics.to_dict().items()}

        mlflow.log_metrics(clean_metrics)

        mlflow.sklearn.log_model(
            fitted_pipeline,
            "model",
            skops_trusted_types=[
                "collections.OrderedDict",
                "lightgbm.basic.Booster",
                "lightgbm.sklearn.LGBMRegressor",
            ],
        )


def main() -> None:
    mlflow.set_experiment(experiment_name="delivery-challenger")
    history, _ = get_processed_data(DATA_DIR)

    numeric_features = [
        "distance_km",
        "experience_months",
        "hour_of_day",
        "raining",
        "congestion_index",
        "tarred_share_pct",
        "congestion_index_dropoff",
        "tarred_share_pct_dropoff",
    ]

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
        history[col] = history[col].astype("category")

    train, test = get_chronological_split(history, 0.3)

    train = add_hour_of_day(train)
    test = add_hour_of_day(test)

    feature_columns = numeric_features + categorical_features

    l_params: dict[str, Any] = {"objective": "regression", "metric": "rmse"}

    linear_model = LinearRegression()
    random_forest_model = RandomForestRegressor()
    l_model = LGBMRegressor(**l_params)

    linear_pipeline = build_pipeline(
        linear_model, numeric_features, categorical_features
    )
    random_forest_pipeline = build_pipeline(
        random_forest_model, numeric_features, categorical_features
    )
    l_pipeline = build_pipeline(l_model, numeric_features, categorical_features)

    run_experiment(
        "linear_model",
        linear_pipeline,
        train,
        test,
        feature_columns,
        {},
        get_git_hash(),
        DATA_VERSION,
    )
    run_experiment(
        "randome_forest",
        random_forest_pipeline,
        train,
        test,
        feature_columns,
        {},
        get_git_hash(),
        DATA_VERSION,
    )
    run_experiment(
        "lightgbm",
        l_pipeline,
        train,
        test,
        feature_columns,
        l_params,
        get_git_hash(),
        DATA_VERSION,
    )


if __name__ == "__main__":
    main()
