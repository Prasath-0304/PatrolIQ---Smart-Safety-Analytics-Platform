"""Streamlit landing page for PatrolIQ."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils import DEFAULT_METRICS_PATH, DEFAULT_OUTPUT_PATH


st.set_page_config(
    page_title="PatrolIQ Command Center",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_processed_data(file_path: str) -> pd.DataFrame:
    """Load the processed PatrolIQ dataset."""
    return pd.read_csv(file_path)


@st.cache_data
def load_metrics(file_path: str) -> dict[str, object]:
    """Load saved model metrics if available."""
    metrics_path = Path(file_path)
    if not metrics_path.exists():
        return {}
    return json.loads(metrics_path.read_text(encoding="utf-8"))


st.title("PatrolIQ Command Center")
st.caption("Urban safety intelligence for crime hotspots, temporal patterns, and patrol planning.")

if not DEFAULT_OUTPUT_PATH.exists():
    st.error("Processed dataset not found. Run `python main.py` before launching the dashboard.")
    st.stop()

dataframe = load_processed_data(str(DEFAULT_OUTPUT_PATH))
metrics = load_metrics(str(DEFAULT_METRICS_PATH))

hero_left, hero_mid, hero_right = st.columns(3)
hero_left.metric("Processed Records", f"{len(dataframe):,}")
hero_mid.metric("Geographic Clusters", int(dataframe["Cluster_KMeans"].nunique()))
hero_right.metric("Temporal Profiles", int(dataframe["Time_Cluster"].nunique()))

st.markdown(
    """
    Use the pages in the sidebar to inspect:

    - geographic hotspot clusters and patrol risk zones
    - temporal crime patterns by hour, weekday, and season
    - PCA, t-SNE, and model evaluation summaries with MLflow-ready outputs
    """
)

overview_left, overview_right = st.columns([1.2, 1])

with overview_left:
    st.subheader("Top Crime Categories")
    top_crimes = dataframe["Primary Type"].value_counts().head(10)
    st.bar_chart(top_crimes)

with overview_right:
    st.subheader("Model Snapshot")
    if metrics:
        snapshot = {
            "Best Algorithm": metrics.get("best_algorithm", "Unavailable"),
            "KMeans Silhouette": metrics.get("kmeans_silhouette", "Unavailable"),
            "DBSCAN Silhouette": metrics.get("dbscan_silhouette", "Unavailable"),
            "Hierarchical Silhouette": metrics.get("hierarchical_silhouette", "Unavailable"),
        }
        st.json(snapshot)
    else:
        st.info("Model metrics will appear after the pipeline writes `data/model_metrics.json`.")
