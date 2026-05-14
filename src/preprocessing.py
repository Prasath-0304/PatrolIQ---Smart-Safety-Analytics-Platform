"""Chunk-based loading and preprocessing for the PatrolIQ dataset."""

from __future__ import annotations

import pandas as pd

from src.utils import REQUIRED_COLUMNS, get_logger, log_dataframe_shape, validate_columns


LOGGER = get_logger(__name__)


def load_data(
    file_path: str,
    sample_size: int = 500_000,
    chunksize: int = 100_000,
) -> pd.DataFrame:
    """Load exactly ``sample_size`` rows from a very large CSV using chunks."""
    if sample_size <= 0:
        raise ValueError("sample_size must be greater than zero.")
    if chunksize <= 0:
        raise ValueError("chunksize must be greater than zero.")

    sampled_chunks: list[pd.DataFrame] = []
    loaded_rows = 0

    try:
        for chunk_number, chunk in enumerate(
            pd.read_csv(file_path, chunksize=chunksize, low_memory=False), start=1
        ):
            remaining_rows = sample_size - loaded_rows
            if remaining_rows <= 0:
                break

            current_chunk = chunk.head(remaining_rows).copy()
            sampled_chunks.append(current_chunk)
            loaded_rows += len(current_chunk)

            LOGGER.info(
                "Loaded chunk %s with %s rows. Current sampled rows: %s/%s",
                chunk_number,
                len(current_chunk),
                loaded_rows,
                sample_size,
            )

            if loaded_rows >= sample_size:
                break
    except Exception as exc:
        raise RuntimeError(f"Failed while loading data from {file_path}: {exc}") from exc

    if loaded_rows < sample_size:
        raise ValueError(
            f"Dataset contains only {loaded_rows} rows. At least {sample_size} rows are required."
        )

    dataframe = pd.concat(sampled_chunks, ignore_index=True)
    validate_columns(dataframe, REQUIRED_COLUMNS)
    log_dataframe_shape(LOGGER, "Loaded sample", dataframe)
    return dataframe


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and enrich the raw sample with temporal columns."""
    validate_columns(df, REQUIRED_COLUMNS)
    processed_df = df.copy()

    try:
        processed_df["Date"] = pd.to_datetime(
            processed_df["Date"],
            format="%m/%d/%Y %I:%M:%S %p",
            errors="coerce",
        )
    except Exception as exc:
        raise RuntimeError(f"Unable to parse the Date column: {exc}") from exc

    processed_df = processed_df.dropna(subset=["Date", "Latitude", "Longitude"]).copy()
    processed_df["Latitude"] = pd.to_numeric(processed_df["Latitude"], errors="coerce")
    processed_df["Longitude"] = pd.to_numeric(processed_df["Longitude"], errors="coerce")
    processed_df = processed_df.dropna(subset=["Latitude", "Longitude"]).copy()

    processed_df["Hour"] = processed_df["Date"].dt.hour
    processed_df["Day"] = processed_df["Date"].dt.day_name()
    processed_df["Day_of_Week"] = processed_df["Day"]
    processed_df["Month"] = processed_df["Date"].dt.month
    processed_df["Month_Name"] = processed_df["Date"].dt.month_name()
    processed_df["Year"] = processed_df["Date"].dt.year
    processed_df["Data_Quality_Flag"] = "Validated"

    log_dataframe_shape(LOGGER, "Preprocessed data", processed_df)
    return processed_df.reset_index(drop=True)
