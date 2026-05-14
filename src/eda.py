"""Exploratory analysis plots for PatrolIQ."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.utils import get_logger, safe_bool_to_label, save_figure, validate_columns


LOGGER = get_logger(__name__)
sns.set_theme(style="whitegrid")


def _build_count_plot(series: pd.Series, title: str, xlabel: str, filename: str) -> None:
    """Create and save a simple bar chart from a series."""
    figure, axis = plt.subplots(figsize=(12, 6))
    series.plot(kind="bar", ax=axis, color="#1f77b4")
    axis.set_title(title)
    axis.set_xlabel(xlabel)
    axis.set_ylabel("Count")
    axis.tick_params(axis="x", rotation=45)
    output_path = save_figure(figure, filename)
    LOGGER.info("Saved EDA figure to %s", output_path)


def run_eda(df: pd.DataFrame) -> None:
    """Generate core crime distribution plots for operational review."""
    validate_columns(df, ["Primary Type", "Hour", "Month_Name", "Arrest"])

    top_crimes = df["Primary Type"].value_counts().head(10)
    _build_count_plot(
        top_crimes,
        title="Top 10 Crime Types",
        xlabel="Primary Type",
        filename="eda_top_crime_types.png",
    )

    crimes_by_hour = df.groupby("Hour").size().sort_index()
    _build_count_plot(
        crimes_by_hour,
        title="Crimes by Hour",
        xlabel="Hour of Day",
        filename="eda_crimes_by_hour.png",
    )

    crimes_by_month = df["Month_Name"].value_counts().reindex(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        fill_value=0,
    )
    _build_count_plot(
        crimes_by_month,
        title="Crimes by Month",
        xlabel="Month",
        filename="eda_crimes_by_month.png",
    )

    arrest_counts = safe_bool_to_label(df["Arrest"]).value_counts()
    _build_count_plot(
        arrest_counts,
        title="Arrest vs Non-Arrest",
        xlabel="Arrest Status",
        filename="eda_arrest_status.png",
    )
