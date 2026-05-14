"""Utility helpers for the PatrolIQ analytics pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd


matplotlib.use("Agg")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_OUTPUT_PATH = DATA_DIR / "processed_data.csv"
DEFAULT_METRICS_PATH = DATA_DIR / "model_metrics.json"
DEFAULT_PCA_FEATURES_PATH = DATA_DIR / "pca_feature_importance.csv"
DEFAULT_ELBOW_PATH = DATA_DIR / "kmeans_elbow.csv"
DEFAULT_SCREE_PLOT_PATH = DATA_DIR / "pca_scree_plot.png"
DEFAULT_DENDROGRAM_PATH = DATA_DIR / "hierarchical_dendrogram.png"
DEFAULT_ELBOW_PLOT_PATH = DATA_DIR / "kmeans_elbow_plot.png"
DEFAULT_DATASET_NAME = "Crimes.csv"
FALLBACK_DATASET_PATTERN = "Crimes*.csv"

REQUIRED_COLUMNS = [
    "Date",
    "Primary Type",
    "Arrest",
    "Latitude",
    "Longitude",
]


def configure_logging() -> None:
    """Configure a simple project-wide logger."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the provided module name."""
    return logging.getLogger(name)


def ensure_directory(path: Path) -> None:
    """Create a directory if it does not already exist."""
    path.mkdir(parents=True, exist_ok=True)


def resolve_dataset_path(explicit_path: str | None = None) -> Path:
    """Resolve the dataset path from an explicit path or local fallbacks."""
    if explicit_path:
        dataset_path = Path(explicit_path)
        if dataset_path.exists():
            return dataset_path
        raise FileNotFoundError(f"Dataset path does not exist: {dataset_path}")

    default_path = PROJECT_ROOT / DEFAULT_DATASET_NAME
    if default_path.exists():
        return default_path

    matches = sorted(PROJECT_ROOT.glob(FALLBACK_DATASET_PATTERN))
    if matches:
        return matches[0]

    raise FileNotFoundError(
        "No dataset file was found. Expected 'Crimes.csv' or a matching crimes CSV "
        f"in {PROJECT_ROOT}."
    )


def validate_columns(df: pd.DataFrame, required_columns: Sequence[str]) -> None:
    """Raise a clear error if required columns are missing."""
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")


def save_figure(figure: plt.Figure, filename: str) -> Path:
    """Persist a matplotlib figure in the data directory."""
    ensure_directory(DATA_DIR)
    output_path = DATA_DIR / filename
    figure.tight_layout()
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return output_path


def get_season(month_value: int) -> str:
    """Map a month number to a season label."""
    season_map = {
        12: "Winter",
        1: "Winter",
        2: "Winter",
        3: "Spring",
        4: "Spring",
        5: "Spring",
        6: "Summer",
        7: "Summer",
        8: "Summer",
        9: "Fall",
        10: "Fall",
        11: "Fall",
    }
    return season_map.get(int(month_value), "Unknown")


def log_dataframe_shape(logger: logging.Logger, label: str, df: pd.DataFrame) -> None:
    """Write a consistent dataframe shape message to the logs."""
    logger.info("%s shape: rows=%s, columns=%s", label, len(df), len(df.columns))


def safe_bool_to_label(series: pd.Series) -> pd.Series:
    """Convert mixed boolean-like values into consistent categorical labels."""
    normalized = (
        series.astype(str).str.strip().str.lower().map({"true": True, "false": False})
    )
    return normalized.map({True: "Arrest", False: "Non-Arrest"}).fillna("Unknown")


def select_existing_columns(df: pd.DataFrame, columns: Iterable[str]) -> list[str]:
    """Return only columns that are present in the dataframe."""
    return [column for column in columns if column in df.columns]
