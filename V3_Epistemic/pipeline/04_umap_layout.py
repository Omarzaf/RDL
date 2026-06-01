"""
04_umap_layout.py

Builds deterministic 2D issue/profile coordinates. UMAP is preferred, but the
stage falls back to TruncatedSVD/PCA with an honest coordinate source when UMAP
is unavailable. The embedding manifest records parameters and coverage.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA, TruncatedSVD

from config import PROCESSED_DIR


OUT = PROCESSED_DIR
RANDOM_STATE = 42


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_coords(coords: np.ndarray) -> np.ndarray:
    x = coords[:, 0]
    y = coords[:, 1]
    x_range = x.max() - x.min()
    y_range = y.max() - y.min()
    x_norm = (2 * (x - x.min()) / x_range - 1) if x_range > 0 else np.zeros_like(x)
    y_norm = (2 * (y - y.min()) / y_range - 1) if y_range > 0 else np.zeros_like(y)
    return np.column_stack([x_norm, y_norm])


def run_embedding(X: np.ndarray) -> tuple[np.ndarray, dict]:
    try:
        import umap  # type: ignore

        reducer = umap.UMAP(
            n_components=2,
            n_neighbors=min(30, max(2, X.shape[0] - 1)),
            min_dist=0.10,
            metric="cosine",
            random_state=RANDOM_STATE,
            transform_seed=RANDOM_STATE,
            low_memory=False,
        )
        return reducer.fit_transform(X), {
            "method": "umap",
            "fallback": False,
            "metric": "cosine",
            "n_neighbors": min(30, max(2, X.shape[0] - 1)),
            "min_dist": 0.10,
            "umap_version": package_version("umap-learn"),
        }
    except Exception as exc:
        n_components = min(2, X.shape[1], X.shape[0])
        if n_components < 2:
            return np.zeros((X.shape[0], 2), dtype=float), {
                "method": "constant_zero",
                "fallback": True,
                "fallback_reason": repr(exc),
            }
        if np.count_nonzero(X) and X.shape[1] > 2:
            coords = TruncatedSVD(n_components=2, random_state=RANDOM_STATE).fit_transform(X)
            method = "truncated_svd_fallback"
        else:
            coords = PCA(n_components=2, random_state=RANDOM_STATE).fit_transform(X)
            method = "pca_fallback"
        return coords, {"method": method, "fallback": True, "fallback_reason": repr(exc)}


def main() -> None:
    random.seed(RANDOM_STATE)
    np.random.seed(RANDOM_STATE)

    matrix_path = OUT / "issue_matrix_aggregate.csv"
    coverage_path = OUT / "issue_feature_coverage.json"
    if not matrix_path.exists():
        raise FileNotFoundError(f"Missing issue matrix: {matrix_path}")

    agg = pd.read_csv(matrix_path)
    ids = agg["entity_id"].astype(str).to_numpy()
    names = agg["name"].astype(str).to_numpy()
    feature_cols = [col for col in agg.columns if col not in {"entity_id", "name"}]
    X = agg[feature_cols].fillna(0.0).astype(np.float32).to_numpy()
    issue_cols = [idx for idx, col in enumerate(feature_cols) if col.startswith("issue_")]
    zero_issue_rows = (np.abs(X[:, issue_cols]).sum(axis=1) == 0) if issue_cols else np.ones(X.shape[0], dtype=bool)

    print(f"Embedding matrix shape: {X.shape[0]} rows x {X.shape[1]} features")
    raw_embedding, params = run_embedding(X)
    coords = normalize_coords(raw_embedding)
    coordinate_source = "umap" if params["method"] == "umap" else params["method"]

    result = pd.DataFrame(
        {
            "entity_id": ids,
            "name": names,
            "x": np.round(coords[:, 0], 4),
            "y": np.round(coords[:, 1], 4),
            "coordinate_source": coordinate_source,
            "quality_flags": ["no_issue_data" if flag else "" for flag in zero_issue_rows],
        }
    )
    result.to_csv(OUT / "umap_coords.csv", index=False)

    coverage = {}
    if coverage_path.exists():
        with coverage_path.open(encoding="utf-8") as f:
            coverage = json.load(f)
    manifest = {
        **params,
        "random_state": RANDOM_STATE,
        "row_count": int(X.shape[0]),
        "feature_count": int(X.shape[1]),
        "feature_columns": feature_cols,
        "rows_without_issue_data": int(zero_issue_rows.sum()),
        "input_file": str(matrix_path),
        "input_sha256": file_sha256(matrix_path),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "sklearn_version": package_version("scikit-learn"),
        "coverage": coverage,
    }
    with (OUT / "embedding_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(
        f"Layout complete using {params['method']}. "
        f"X=[{coords[:, 0].min():.2f},{coords[:, 0].max():.2f}] "
        f"Y=[{coords[:, 1].min():.2f},{coords[:, 1].max():.2f}]"
    )
    print("Saved: umap_coords.csv, embedding_manifest.json")


if __name__ == "__main__":
    main()
