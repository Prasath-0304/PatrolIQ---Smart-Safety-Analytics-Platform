"""Artifact and report generation helpers for PatrolIQ."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, linkage

from src.utils import (
    DEFAULT_DENDROGRAM_PATH,
    DEFAULT_ELBOW_PLOT_PATH,
    DEFAULT_SCREE_PLOT_PATH,
    get_logger,
)


LOGGER = get_logger(__name__)


def save_elbow_plot(elbow_points: Iterable[dict[str, float]]) -> Path:
    """Save the KMeans elbow curve as a line plot."""
    elbow_df = pd.DataFrame(elbow_points)
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.plot(elbow_df["k"], elbow_df["inertia"], marker="o", color="#c0392b")
    axis.set_title("KMeans Elbow Curve")
    axis.set_xlabel("Number of Clusters (k)")
    axis.set_ylabel("Inertia")
    figure.tight_layout()
    figure.savefig(DEFAULT_ELBOW_PLOT_PATH, dpi=300, bbox_inches="tight")
    plt.close(figure)
    LOGGER.info("Saved elbow plot to %s", DEFAULT_ELBOW_PLOT_PATH)
    return DEFAULT_ELBOW_PLOT_PATH


def save_scree_plot(explained_variance: Iterable[float]) -> Path:
    """Save the PCA scree plot."""
    values = list(explained_variance)
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.bar(range(1, len(values) + 1), values, color="#2c7a7b")
    axis.plot(range(1, len(values) + 1), values, color="#1d1d1d", marker="o")
    axis.set_title("PCA Scree Plot")
    axis.set_xlabel("Principal Component")
    axis.set_ylabel("Explained Variance Ratio")
    figure.tight_layout()
    figure.savefig(DEFAULT_SCREE_PLOT_PATH, dpi=300, bbox_inches="tight")
    plt.close(figure)
    LOGGER.info("Saved scree plot to %s", DEFAULT_SCREE_PLOT_PATH)
    return DEFAULT_SCREE_PLOT_PATH


def save_dendrogram(features: pd.DataFrame, sample_size: int = 1000) -> Path:
    """Save a hierarchical clustering dendrogram from a sampled feature set."""
    sampled = features.sample(n=min(sample_size, len(features)), random_state=42)
    linkage_matrix = linkage(sampled, method="ward")
    figure, axis = plt.subplots(figsize=(12, 5))
    dendrogram(linkage_matrix, no_labels=True, color_threshold=None, ax=axis)
    axis.set_title("Hierarchical Crime Zone Dendrogram")
    axis.set_xlabel("Sampled Crime Records")
    axis.set_ylabel("Distance")
    figure.tight_layout()
    figure.savefig(DEFAULT_DENDROGRAM_PATH, dpi=300, bbox_inches="tight")
    plt.close(figure)
    LOGGER.info("Saved dendrogram to %s", DEFAULT_DENDROGRAM_PATH)
    return DEFAULT_DENDROGRAM_PATH
