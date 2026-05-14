"""Feature engineering helpers for PatrolIQ."""

from __future__ import annotations

import pandas as pd

from src.utils import get_logger, get_season, validate_columns


LOGGER = get_logger(__name__)

CRIME_SEVERITY_MAP = {
    "HOMICIDE": 10,
    "KIDNAPPING": 9,
    "CRIM SEXUAL ASSAULT": 9,
    "ROBBERY": 8,
    "ARSON": 8,
    "ASSAULT": 7,
    "BATTERY": 7,
    "BURGLARY": 6,
    "MOTOR VEHICLE THEFT": 6,
    "WEAPONS VIOLATION": 6,
    "THEFT": 5,
    "CRIMINAL DAMAGE": 5,
    "CRIMINAL TRESPASS": 4,
    "DECEPTIVE PRACTICE": 4,
    "NARCOTICS": 3,
}


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create calendar-based features used by downstream analytics."""
    validate_columns(df, ["Date", "Month", "Primary Type", "Latitude", "Longitude"])
    feature_df = df.copy()

    feature_df["Is_Weekend"] = feature_df["Date"].dt.dayofweek >= 5
    feature_df["Season"] = feature_df["Month"].apply(get_season)
    feature_df["Crime_Severity_Score"] = (
        feature_df["Primary Type"].astype(str).str.upper().map(CRIME_SEVERITY_MAP).fillna(2)
    )
    feature_df["Latitude_Bin"] = pd.cut(feature_df["Latitude"], bins=8, include_lowest=True)
    feature_df["Longitude_Bin"] = pd.cut(feature_df["Longitude"], bins=8, include_lowest=True)
    feature_df["Geo_Bin"] = (
        feature_df["Latitude_Bin"].astype(str) + " | " + feature_df["Longitude_Bin"].astype(str)
    )

    if "District" in feature_df.columns:
        numeric_district = pd.to_numeric(feature_df["District"], errors="coerce")
        feature_df["District_Cluster"] = pd.cut(
            numeric_district,
            bins=[0, 6, 12, 18, 25],
            labels=["North", "West", "Central", "South"],
            include_lowest=True,
        ).astype(str)
    else:
        feature_df["District_Cluster"] = "Unknown"

    LOGGER.info("Feature engineering completed.")
    return feature_df
