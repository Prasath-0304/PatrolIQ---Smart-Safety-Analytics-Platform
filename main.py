"""Main orchestration script for the PatrolIQ analytics pipeline."""

from __future__ import annotations

from pathlib import Path

import mlflow

from src.clustering import evaluate_clusters, run_clustering, temporal_clustering
from src.dimensionality import run_pca, run_tsne
from src.eda import run_eda
from src.experiment_tracking import (
    configure_mlflow,
    log_artifact,
    log_metrics,
    log_params,
    log_sklearn_model,
)
from src.feature_engineering import create_features
from src.preprocessing import load_data, preprocess_data
from src.utils import (
    DEFAULT_DENDROGRAM_PATH,
    DEFAULT_ELBOW_PLOT_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_SCREE_PLOT_PATH,
    configure_logging,
    ensure_directory,
    get_logger,
    resolve_dataset_path,
)


LOGGER = get_logger(__name__)


def run_pipeline(dataset_path: str | None = None) -> Path:
    """Execute the PatrolIQ pipeline end to end and save the final dataset."""
    configure_logging()
    tracking_uri = configure_mlflow()
    resolved_dataset_path = resolve_dataset_path(dataset_path)
    ensure_directory(DEFAULT_OUTPUT_PATH.parent)

    with mlflow.start_run(run_name="patroliq_pipeline"):
        LOGGER.info("Using dataset: %s", resolved_dataset_path)
        log_params(
            {
                "dataset_path": str(resolved_dataset_path),
                "target_sample_size": 500000,
                "tracking_uri": tracking_uri,
            }
        )

        dataframe = load_data(str(resolved_dataset_path))
        dataframe = preprocess_data(dataframe)
        run_eda(dataframe)

        dataframe = create_features(dataframe)
        dataframe, clustering_models = run_clustering(dataframe)
        cluster_metrics = evaluate_clusters(dataframe)
        dataframe, temporal_model = temporal_clustering(dataframe)
        dataframe, explained_variance, pca_model = run_pca(dataframe)
        dataframe, tsne_model = run_tsne(dataframe)

        dataframe.to_csv(DEFAULT_OUTPUT_PATH, index=False)
        log_metrics(
            {
                "processed_row_count": len(dataframe),
                "processed_column_count": len(dataframe.columns),
                "pca_variance_total_2_components": explained_variance[:2].sum(),
                "pca_variance_total_3_components": explained_variance.sum(),
            }
        )
        log_artifact(DEFAULT_OUTPUT_PATH, artifact_path="datasets")
        log_sklearn_model(
            clustering_models["kmeans"],
            artifact_path="models/geographic_kmeans",
            registered_model_name="PatrolIQGeographicKMeans",
        )
        log_sklearn_model(
            temporal_model,
            artifact_path="models/temporal_kmeans",
            registered_model_name="PatrolIQTemporalKMeans",
        )
        log_sklearn_model(
            pca_model,
            artifact_path="models/pca_model",
            registered_model_name="PatrolIQPCA",
        )
        for artifact_name in [
            "eda_top_crime_types.png",
            "eda_crimes_by_hour.png",
            "eda_crimes_by_month.png",
            "eda_arrest_status.png",
            "model_metrics.json",
            "pca_feature_importance.csv",
        ]:
            log_artifact(DEFAULT_OUTPUT_PATH.parent / artifact_name, artifact_path="reports")
        for artifact_path in [DEFAULT_ELBOW_PLOT_PATH, DEFAULT_DENDROGRAM_PATH, DEFAULT_SCREE_PLOT_PATH]:
            log_artifact(artifact_path, artifact_path="reports")
        LOGGER.info("Cluster metrics summary: %s", cluster_metrics)
        LOGGER.info("Processed data saved to %s", DEFAULT_OUTPUT_PATH)
    return DEFAULT_OUTPUT_PATH


if __name__ == "__main__":
    output_path = run_pipeline()
    print(f"Pipeline completed successfully. Output saved to: {output_path}")
