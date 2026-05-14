"""Geographic hotspot analysis page."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils import DEFAULT_OUTPUT_PATH


@st.cache_data
def load_processed_data(file_path: str) -> pd.DataFrame:
    return pd.read_csv(file_path)


def plot_geographic_clusters(df: pd.DataFrame, cluster_column: str) -> None:
    figure, axis = plt.subplots(figsize=(10, 7))
    scatter = axis.scatter(
        df["Longitude"],
        df["Latitude"],
        c=df[cluster_column],
        cmap="RdYlGn_r",
        s=9,
        alpha=0.55,
    )
    axis.set_title(f"{cluster_column} Hotspot Map")
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    figure.colorbar(scatter, ax=axis, label="Cluster")
    st.pyplot(figure)
    plt.close(figure)


def plot_risk_heatmap(df: pd.DataFrame) -> None:
    figure, axis = plt.subplots(figsize=(10, 7))
    heatmap = axis.hexbin(
        df["Longitude"],
        df["Latitude"],
        gridsize=45,
        cmap="YlOrRd",
        mincnt=1,
    )
    axis.set_title("Geographic Crime Heatmap")
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    figure.colorbar(heatmap, ax=axis, label="Incident Density")
    st.pyplot(figure)
    plt.close(figure)


st.title("Geographic Hotspots")

if not DEFAULT_OUTPUT_PATH.exists():
    st.error("Processed dataset not found. Run `python main.py` first.")
    st.stop()

dataframe = load_processed_data(str(DEFAULT_OUTPUT_PATH))
sampled_df = dataframe.sample(n=min(25000, len(dataframe)), random_state=42)

cluster_choice = st.selectbox(
    "Cluster algorithm",
    ["Cluster_KMeans", "Cluster_DBSCAN", "Cluster_HC"],
)

map_left, map_right = st.columns([1.5, 1])
with map_left:
    st.subheader("Patrol Risk Map")
    st.map(
        sampled_df[["Latitude", "Longitude"]].rename(
            columns={"Latitude": "lat", "Longitude": "lon"}
        )
    )

with map_right:
    st.subheader("Risk Zone Summary")
    cluster_summary = (
        dataframe.groupby(cluster_choice)
        .agg(
            total_crimes=("ID", "count"),
            arrest_rate=("Arrest", lambda s: pd.Series(s).astype(str).str.lower().eq("true").mean()),
            dominant_crime=("Primary Type", lambda s: s.mode().iat[0] if not s.mode().empty else "Unknown"),
        )
        .sort_values("total_crimes", ascending=False)
    )
    st.dataframe(cluster_summary.head(10), use_container_width=True)

st.subheader("Cluster Boundaries")
plot_geographic_clusters(sampled_df, cluster_choice)

st.subheader("Density Heatmap")
plot_risk_heatmap(sampled_df)
