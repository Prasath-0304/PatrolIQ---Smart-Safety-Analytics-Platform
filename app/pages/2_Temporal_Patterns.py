"""Temporal crime pattern analysis page."""

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


def plot_hourly_heatmap(df: pd.DataFrame) -> None:
    heatmap = (
        df.pivot_table(
            index="Day_of_Week",
            columns="Hour",
            values="ID",
            aggfunc="count",
            fill_value=0,
        )
        .reindex(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        )
    )
    figure, axis = plt.subplots(figsize=(12, 4.5))
    image = axis.imshow(heatmap.values, aspect="auto", cmap="YlOrRd")
    axis.set_yticks(range(len(heatmap.index)))
    axis.set_yticklabels(heatmap.index)
    axis.set_xticks(range(len(heatmap.columns)))
    axis.set_xticklabels(heatmap.columns)
    axis.set_title("Hourly Crime Heatmap")
    axis.set_xlabel("Hour")
    axis.set_ylabel("Day of Week")
    figure.colorbar(image, ax=axis, label="Crime Count")
    st.pyplot(figure)
    plt.close(figure)


st.title("Temporal Patterns")

if not DEFAULT_OUTPUT_PATH.exists():
    st.error("Processed dataset not found. Run `python main.py` first.")
    st.stop()

dataframe = load_processed_data(str(DEFAULT_OUTPUT_PATH))

stats_left, stats_mid, stats_right = st.columns(3)
peak_hour = int(dataframe["Hour"].mode().iat[0])
peak_month = dataframe["Month_Name"].mode().iat[0]
weekend_rate = float(dataframe["Is_Weekend"].mean())
stats_left.metric("Peak Hour", f"{peak_hour}:00")
stats_mid.metric("Peak Month", peak_month)
stats_right.metric("Weekend Share", f"{weekend_rate:.1%}")

plot_hourly_heatmap(dataframe.sample(n=min(100000, len(dataframe)), random_state=42))

trend_left, trend_right = st.columns(2)
with trend_left:
    st.subheader("Temporal Cluster Mix")
    st.bar_chart(dataframe["Time_Cluster"].value_counts().sort_index())

with trend_right:
    st.subheader("Seasonal Crime Totals")
    seasonal_counts = (
        dataframe["Season"]
        .value_counts()
        .reindex(["Winter", "Spring", "Summer", "Fall"], fill_value=0)
    )
    st.bar_chart(seasonal_counts)
