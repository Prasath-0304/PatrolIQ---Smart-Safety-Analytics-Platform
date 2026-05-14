"""Dimensionality reduction for PatrolIQ."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import StandardScaler

from src.experiment_tracking import log_metrics
from src.reporting import save_scree_plot
from src.utils import DEFAULT_PCA_FEATURES_PATH, get_logger


LOGGER = get_logger(__name__)


def _build_modeling_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Create a compact numeric feature matrix for dimensionality reduction."""

    def _encode(series: pd.Series) -> pd.Series:
        encoder = LabelEncoder()
        values = series.astype(str).fillna("Unknown")
        return pd.Series(encoder.fit_transform(values), index=series.index)

    modeling_matrix = pd.DataFrame(
        {
            "Latitude": pd.to_numeric(df["Latitude"], errors="coerce"),
            "Longitude": pd.to_numeric(df["Longitude"], errors="coerce"),
            "Hour": pd.to_numeric(df["Hour"], errors="coerce"),
            "Month": pd.to_numeric(df["Month"], errors="coerce"),
            "District": pd.to_numeric(df["District"], errors="coerce")
            if "District" in df.columns
            else 0,
            "Ward": pd.to_numeric(df["Ward"], errors="coerce") if "Ward" in df.columns else 0,
            "Community_Area": pd.to_numeric(df["Community Area"], errors="coerce")
            if "Community Area" in df.columns
            else 0,
            "Crime_Severity_Score": pd.to_numeric(df["Crime_Severity_Score"], errors="coerce")
            if "Crime_Severity_Score" in df.columns
            else 0,
            "Primary_Type_Code": _encode(df["Primary Type"]) if "Primary Type" in df.columns else 0,
            "Location_Code": _encode(df["Location Description"])
            if "Location Description" in df.columns
            else 0,
            "Season_Code": _encode(df["Season"]) if "Season" in df.columns else 0,
            "Day_Code": _encode(df["Day_of_Week"]) if "Day_of_Week" in df.columns else 0,
            "Arrest_Flag": df["Arrest"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": 1, "false": 0})
            .fillna(0),
            "Domestic_Flag": df["Domestic"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": 1, "false": 0})
            .fillna(0)
            if "Domestic" in df.columns
            else 0,
            "Weekend_Flag": df["Is_Weekend"].astype(int) if "Is_Weekend" in df.columns else 0,
        }
    )

    modeling_matrix = modeling_matrix.replace([np.inf, -np.inf], np.nan)
    modeling_matrix = modeling_matrix.fillna(modeling_matrix.median(numeric_only=True))
    return modeling_matrix


def run_pca(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, PCA]:
    """Run PCA and append the first three principal components to the dataframe."""
    pca_df = df.copy()
    modeling_matrix = _build_modeling_matrix(pca_df)
    pca = PCA(n_components=3, random_state=42)
    transformed = pca.fit_transform(modeling_matrix)
    explained_variance = pca.explained_variance_ratio_

    pca_df["PCA_1"] = transformed[:, 0]
    pca_df["PCA_2"] = transformed[:, 1]
    pca_df["PCA_3"] = transformed[:, 2]

    component_weights = np.abs(pca.components_[:3]).mean(axis=0)
    feature_importance = (
        pd.DataFrame(
            {
                "feature": modeling_matrix.columns,
                "importance": component_weights,
            }
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    feature_importance.to_csv(DEFAULT_PCA_FEATURES_PATH, index=False)
    save_scree_plot(explained_variance)
    log_metrics(
        {
            "pca_component_1_variance": explained_variance[0],
            "pca_component_2_variance": explained_variance[1],
            "pca_component_3_variance": explained_variance[2],
            "pca_variance_total_3_components": explained_variance.sum(),
        }
    )

    LOGGER.info("PCA explained variance ratios: %s", explained_variance)
    print(f"PCA explained variance ratios: {explained_variance}")
    return pca_df, explained_variance, pca


def run_tsne(
    df: pd.DataFrame,
    sample_size: int = 5_000,
    perplexity: int = 30,
) -> tuple[pd.DataFrame, TSNE]:
    """Run t-SNE on a manageable subset and store the 2D embedding."""
    tsne_df = df.copy()
    modeling_matrix = _build_modeling_matrix(tsne_df)

    effective_sample_size = min(sample_size, len(tsne_df))
    sampled_matrix = modeling_matrix.sample(n=effective_sample_size, random_state=42)

    scaler = StandardScaler()
    scaled_matrix = scaler.fit_transform(sampled_matrix)

    tsne = TSNE(
        n_components=2,
        random_state=42,
        init="pca",
        perplexity=min(perplexity, max(5, effective_sample_size // 10)),
        learning_rate="auto",
        max_iter=1_000,
    )
    embedding = tsne.fit_transform(scaled_matrix)

    tsne_df["TSNE_1"] = np.nan
    tsne_df["TSNE_2"] = np.nan
    tsne_df.loc[sampled_matrix.index, "TSNE_1"] = embedding[:, 0]
    tsne_df.loc[sampled_matrix.index, "TSNE_2"] = embedding[:, 1]

    LOGGER.info("t-SNE completed for %s sampled rows.", effective_sample_size)
    log_metrics({"tsne_sample_size": effective_sample_size})
    return tsne_df, tsne
