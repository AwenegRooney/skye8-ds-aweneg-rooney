import mlflow

model_ids = [
    ("c4d99ef40430487aa4776435414b21ba", "lightgbm"),
    ("96e911975db949dab8c632d07341cec3", "random_forest"),
    ("84529a29de684980bd7d6d2d75ea3d8d", "linear_model"),
]
lightgbm_version = None

for run_id, model_name in model_ids:
    registered_model = mlflow.register_model(
        f"runs:/{run_id}/model", "delivery-challengers"
    )

    if model_name == "lightgbm":
        lightgbm_version = registered_model.version

client = mlflow.tracking.MlflowClient()
client.transition_model_version_stage(
    name="delivery-challengers",
    version=lightgbm_version,
    stage="Staging",
    archive_existing_versions=False,
)
