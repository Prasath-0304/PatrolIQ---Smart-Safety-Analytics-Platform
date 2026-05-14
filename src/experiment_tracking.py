"""MLflow experiment tracking utilities for PatrolIQ."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient

from src.utils import DATA_DIR, PROJECT_ROOT, ensure_directory, get_logger


LOGGER = get_logger(__name__)
MLFLOW_DB_PATH = PROJECT_ROOT / "mlflow.db"
MLARTIFACTS_DIR = PROJECT_ROOT / "mlartifacts"


def configure_mlflow(experiment_name: str = "PatrolIQ") -> str:
    """Configure MLflow to track runs locally using SQLite and file artifacts."""
    ensure_directory(MLARTIFACTS_DIR)
    tracking_uri = f"sqlite:///{MLFLOW_DB_PATH.resolve().as_posix()}"
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient()
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        client.create_experiment(
            experiment_name,
            artifact_location=MLARTIFACTS_DIR.resolve().as_uri(),
        )
    mlflow.set_experiment(experiment_name)
    LOGGER.info("MLflow configured with tracking URI %s", tracking_uri)
    return tracking_uri


def log_params(params: dict[str, Any]) -> None:
    """Log flat parameters to the active MLflow run."""
    clean_params = {key: value for key, value in params.items() if value is not None}
    if clean_params:
        mlflow.log_params(clean_params)


def log_metrics(metrics: dict[str, Any]) -> None:
    """Log numeric metrics to the active MLflow run."""
    clean_metrics: dict[str, float] = {}
    for key, value in metrics.items():
        if value is None:
            continue
        try:
            clean_metrics[key] = float(value)
        except (TypeError, ValueError):
            continue
    if clean_metrics:
        mlflow.log_metrics(clean_metrics)


def write_json_artifact(filename: str, payload: dict[str, Any]) -> Path:
    """Write a JSON artifact into the data directory."""
    ensure_directory(DATA_DIR)
    output_path = DATA_DIR / filename
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def log_artifact(path: Path | str, artifact_path: str | None = None) -> None:
    """Log a file artifact if it exists."""
    artifact = Path(path)
    if artifact.exists():
        mlflow.log_artifact(str(artifact), artifact_path=artifact_path)


def log_sklearn_model(
    model: Any,
    artifact_path: str,
    registered_model_name: str | None = None,
) -> None:
    """Log a scikit-learn-compatible model and optionally register it."""
    model_name = artifact_path.replace("/", "_").replace("\\", "_").replace(".", "_")
    mlflow.sklearn.log_model(
        sk_model=model,
        name=model_name,
        registered_model_name=registered_model_name,
    )
