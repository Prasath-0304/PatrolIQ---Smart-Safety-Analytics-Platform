"""Model metrics and dimensionality reduction page."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils import (
    DEFAULT_DENDROGRAM_PATH,
    DEFAULT_ELBOW_PLOT_PATH,
    DEFAULT_METRICS_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_PCA_FEATURES_PATH,
    DEFAULT_SCREE_PLOT_PATH,
    PROJECT_ROOT as ROOT_DIR,
)


@st.cache_data
def load_processed_data(file_path: str) -> pd.DataFrame:
    return pd.read_csv(file_path)


@st.cache_data
def load_metrics(file_path: str) -> dict[str, object]:
    path = Path(file_path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data
def load_feature_importance(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    if not path.exists():
        return pd.DataFrame(columns=["feature", "importance"])
    return pd.read_csv(path)


def plot_pca_scatter(df: pd.DataFrame) -> None:
    figure, axis = plt.subplots(figsize=(9, 6))
    scatter = axis.scatter(
        df["PCA_1"],
        df["PCA_2"],
        c=df["Cluster_KMeans"],
        cmap="tab10",
        s=8,
        alpha=0.5,
    )
    axis.set_title("PCA Cluster Projection")
    axis.set_xlabel("PCA 1")
    axis.set_ylabel("PCA 2")
    figure.colorbar(scatter, ax=axis, label="KMeans Cluster")
    st.pyplot(figure)
    plt.close(figure)


def plot_tsne_scatter(df: pd.DataFrame) -> None:
    tsne_df = df.dropna(subset=["TSNE_1", "TSNE_2"]).copy()
    figure, axis = plt.subplots(figsize=(9, 6))
    scatter = axis.scatter(
        tsne_df["TSNE_1"],
        tsne_df["TSNE_2"],
        c=tsne_df["Time_Cluster"],
        cmap="viridis",
        s=10,
        alpha=0.55,
    )
    axis.set_title("t-SNE Crime Pattern View")
    axis.set_xlabel("t-SNE 1")
    axis.set_ylabel("t-SNE 2")
    figure.colorbar(scatter, ax=axis, label="Temporal Cluster")
    st.pyplot(figure)
    plt.close(figure)


st.title("Model Analysis")

if not DEFAULT_OUTPUT_PATH.exists():
    st.error("Processed dataset not found. Run `python main.py` first.")
    st.stop()

dataframe = load_processed_data(str(DEFAULT_OUTPUT_PATH))
metrics = load_metrics(str(DEFAULT_METRICS_PATH))
feature_importance = load_feature_importance(str(DEFAULT_PCA_FEATURES_PATH))

metric_left, metric_mid, metric_right = st.columns(3)
metric_left.metric("Best Algorithm", metrics.get("best_algorithm", "Unavailable"))
metric_mid.metric(
    "KMeans Silhouette",
    f"{metrics['kmeans_silhouette']:.3f}" if metrics.get("kmeans_silhouette") is not None else "N/A",
)
metric_right.metric(
    "DBSCAN Davies-Bouldin",
    f"{metrics['dbscan_davies_bouldin']:.3f}" if metrics.get("dbscan_davies_bouldin") is not None else "N/A",
)

plots_left, plots_right = st.columns(2)
with plots_left:
    plot_pca_scatter(dataframe.sample(n=min(25000, len(dataframe)), random_state=42))
with plots_right:
    plot_tsne_scatter(dataframe)

st.subheader("Top PCA Drivers")
st.dataframe(feature_importance.head(10), use_container_width=True)

artifact_left, artifact_mid, artifact_right = st.columns(3)
with artifact_left:
    st.subheader("Scree Plot")
    if DEFAULT_SCREE_PLOT_PATH.exists():
        st.image(str(DEFAULT_SCREE_PLOT_PATH))
with artifact_mid:
    st.subheader("Elbow Plot")
    if DEFAULT_ELBOW_PLOT_PATH.exists():
        st.image(str(DEFAULT_ELBOW_PLOT_PATH))
with artifact_right:
    st.subheader("Dendrogram")
    if DEFAULT_DENDROGRAM_PATH.exists():
        st.image(str(DEFAULT_DENDROGRAM_PATH))

st.subheader("MLflow Tracking")
st.code(str((ROOT_DIR / "mlflow.db").resolve()), language="text")
st.caption("Registered models: PatrolIQGeographicKMeans, PatrolIQTemporalKMeans, PatrolIQPCA")
if metrics:
    st.json(metrics)
