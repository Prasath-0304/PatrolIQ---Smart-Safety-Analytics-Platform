"""Spatial and temporal clustering for PatrolIQ."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, DBSCAN, KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

from src.experiment_tracking import log_metrics, write_json_artifact
from src.reporting import save_dendrogram, save_elbow_plot
from src.utils import get_logger, validate_columns


LOGGER = get_logger(__name__)


def _prepare_scaled_features(df: pd.DataFrame, columns: list[str]) -> tuple[np.ndarray, StandardScaler]:
    """Build a scaled numeric feature matrix from selected columns."""
    feature_frame = df[columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    scaler = StandardScaler()
    scaled_matrix = scaler.fit_transform(feature_frame)
    return scaled_matrix, scaler


def _predict_full_labels_from_sample(
    scaled_sample: np.ndarray,
    sample_labels: np.ndarray,
    scaled_full: np.ndarray,
    default_label: int = -1,
) -> np.ndarray:
    """Train a simple classifier on sample labels and extend labels to the full dataset."""
    labeled_mask = sample_labels != -1
    if labeled_mask.sum() < 2 or len(np.unique(sample_labels[labeled_mask])) < 2:
        LOGGER.warning(
            "Sampled clustering did not produce enough labeled clusters. Returning default label %s.",
            default_label,
        )
        return np.full(shape=len(scaled_full), fill_value=default_label, dtype=int)

    classifier = KNeighborsClassifier(n_neighbors=5)
    classifier.fit(scaled_sample[labeled_mask], sample_labels[labeled_mask])
    predicted_labels = classifier.predict(scaled_full)
    return predicted_labels.astype(int)


def run_clustering(
    df: pd.DataFrame,
    kmeans_clusters: int = 7,
    dbscan_eps: float = 0.05,
    dbscan_min_samples: int = 20,
    sample_size_for_heavy_models: int = 5_000,
    hierarchical_clusters: int = 7,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Run KMeans, DBSCAN, and hierarchical clustering on geographic coordinates."""
    validate_columns(df, ["Latitude", "Longitude"])
    cluster_df = df.copy()
    raw_geo = cluster_df[["Latitude", "Longitude"]].apply(pd.to_numeric, errors="coerce").fillna(0)
    scaled_geo, _ = _prepare_scaled_features(cluster_df, ["Latitude", "Longitude"])

    kmeans = KMeans(n_clusters=kmeans_clusters, random_state=42, n_init=10)
    cluster_df["Cluster_KMeans"] = kmeans.fit_predict(raw_geo)
    LOGGER.info("KMeans clustering completed with %s clusters.", kmeans_clusters)

    effective_sample_size = min(sample_size_for_heavy_models, len(cluster_df))
    sampled_df = cluster_df.sample(n=effective_sample_size, random_state=42)
    sampled_geo = scaled_geo[sampled_df.index]

    dbscan = DBSCAN(eps=dbscan_eps, min_samples=dbscan_min_samples)
    sampled_dbscan_labels = dbscan.fit_predict(sampled_geo)
    cluster_df["Cluster_DBSCAN"] = _predict_full_labels_from_sample(
        sampled_geo,
        sampled_dbscan_labels,
        scaled_geo,
    )
    LOGGER.info(
        "DBSCAN completed on %s sampled rows and labels were extended to the full dataset.",
        effective_sample_size,
    )

    hierarchical = AgglomerativeClustering(n_clusters=hierarchical_clusters)
    sampled_hc_labels = hierarchical.fit_predict(sampled_geo)
    cluster_df["Cluster_HC"] = _predict_full_labels_from_sample(
        sampled_geo,
        sampled_hc_labels,
        scaled_geo,
    )
    LOGGER.info(
        "Agglomerative clustering completed on %s sampled rows and labels were extended to the full dataset.",
        effective_sample_size,
    )
    return cluster_df, {
        "kmeans": kmeans,
        "dbscan": dbscan,
        "hierarchical": hierarchical,
        "dbscan_params": {"eps": dbscan_eps, "min_samples": dbscan_min_samples},
        "hierarchical_clusters": hierarchical_clusters,
    }


def _safe_cluster_metrics(features: pd.DataFrame, labels: pd.Series) -> dict[str, float | None]:
    """Compute cluster metrics when at least two clusters are present."""
    unique_labels = pd.Series(labels).nunique()
    if unique_labels < 2:
        return {"silhouette": None, "davies_bouldin": None}
    return {
        "silhouette": silhouette_score(features, labels),
        "davies_bouldin": davies_bouldin_score(features, labels),
    }


def _dbscan_metrics(features: pd.DataFrame, labels: pd.Series) -> dict[str, float | None]:
    """Evaluate DBSCAN while excluding noise points."""
    filtered = pd.DataFrame(features).copy()
    filtered["label"] = labels
    filtered = filtered[filtered["label"] != -1]
    if filtered["label"].nunique() < 2:
        return {"silhouette": None, "davies_bouldin": None}
    return {
        "silhouette": silhouette_score(filtered[["Latitude", "Longitude"]], filtered["label"]),
        "davies_bouldin": davies_bouldin_score(filtered[["Latitude", "Longitude"]], filtered["label"]),
    }


def evaluate_clusters(
    df: pd.DataFrame,
    sample_size: int = 5_000,
    dbscan_eps: float = 0.05,
    dbscan_min_samples: int = 20,
    hierarchical_clusters: int = 7,
) -> dict[str, float | list[dict[str, float]] | str | None]:
    """Compute comparative metrics for all clustering outputs and select the best algorithm."""
    validate_columns(df, ["Latitude", "Longitude"])
    evaluation_df = df.copy()

    effective_sample_size = min(sample_size, len(evaluation_df))
    sampled_df = evaluation_df.sample(n=effective_sample_size, random_state=42)
    features = sampled_df[["Latitude", "Longitude"]].apply(pd.to_numeric, errors="coerce").fillna(0)

    kmeans_model = KMeans(n_clusters=7, random_state=42, n_init=10)
    kmeans_labels = kmeans_model.fit_predict(features)
    kmeans_metrics = _safe_cluster_metrics(features, pd.Series(kmeans_labels, index=sampled_df.index))

    hierarchical_model = AgglomerativeClustering(n_clusters=hierarchical_clusters)
    hierarchical_labels = hierarchical_model.fit_predict(features)
    hierarchical_metrics = _safe_cluster_metrics(
        features,
        pd.Series(hierarchical_labels, index=sampled_df.index),
    )

    scaled_features = StandardScaler().fit_transform(features)
    dbscan_model = DBSCAN(eps=dbscan_eps, min_samples=dbscan_min_samples)
    dbscan_labels = dbscan_model.fit_predict(scaled_features)
    dbscan_metrics = _dbscan_metrics(
        features,
        pd.Series(dbscan_labels, index=sampled_df.index),
    )

    elbow_points: list[dict[str, float]] = []
    for k in range(2, 11):
        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        model.fit(features)
        elbow_points.append({"k": float(k), "inertia": float(model.inertia_)})

    metric_summary: dict[str, float | list[dict[str, float]] | str | None] = {
        "sample_size": float(effective_sample_size),
        "kmeans_silhouette": kmeans_metrics["silhouette"],
        "kmeans_davies_bouldin": kmeans_metrics["davies_bouldin"],
        "dbscan_silhouette": dbscan_metrics["silhouette"],
        "dbscan_davies_bouldin": dbscan_metrics["davies_bouldin"],
        "hierarchical_silhouette": hierarchical_metrics["silhouette"],
        "hierarchical_davies_bouldin": hierarchical_metrics["davies_bouldin"],
        "elbow_curve": elbow_points,
    }

    candidates = {
        "KMeans": kmeans_metrics["silhouette"],
        "DBSCAN": dbscan_metrics["silhouette"],
        "Hierarchical": hierarchical_metrics["silhouette"],
    }
    ranked_candidates = {name: score for name, score in candidates.items() if score is not None}
    best_algorithm = max(ranked_candidates, key=ranked_candidates.get) if ranked_candidates else "KMeans"
    metric_summary["best_algorithm"] = best_algorithm

    save_elbow_plot(elbow_points)
    save_dendrogram(features)
    write_json_artifact("model_metrics.json", metric_summary)
    log_metrics(
        {
            "kmeans_silhouette": kmeans_metrics["silhouette"],
            "kmeans_davies_bouldin": kmeans_metrics["davies_bouldin"],
            "dbscan_silhouette": dbscan_metrics["silhouette"],
            "dbscan_davies_bouldin": dbscan_metrics["davies_bouldin"],
            "hierarchical_silhouette": hierarchical_metrics["silhouette"],
            "hierarchical_davies_bouldin": hierarchical_metrics["davies_bouldin"],
        }
    )
    LOGGER.info("Best geographic clustering algorithm: %s", best_algorithm)
    return metric_summary


def temporal_clustering(
    df: pd.DataFrame,
    temporal_clusters: int = 4,
) -> tuple[pd.DataFrame, KMeans]:
    """Cluster crime records by time using hour and month features."""
    validate_columns(df, ["Hour", "Month", "Day_of_Week"])
    temporal_df = df.copy()
    temporal_df["Day_Index"] = pd.Categorical(temporal_df["Day_of_Week"]).codes
    scaled_time, _ = _prepare_scaled_features(temporal_df, ["Hour", "Month", "Day_Index"])

    kmeans = KMeans(n_clusters=temporal_clusters, random_state=42, n_init=10)
    temporal_df["Time_Cluster"] = kmeans.fit_predict(scaled_time)
    LOGGER.info("Temporal clustering completed with %s clusters.", temporal_clusters)
    return temporal_df, kmeans
