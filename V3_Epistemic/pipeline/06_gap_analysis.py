"""
06_gap_analysis.py

Computes model-derived gap leads. A gap lead is an exploratory signal where
spending/exposure density is high relative to observed actor density. It is not
evidence of absence, misconduct, or causal influence.
"""

from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde

from config import PROCESSED_DIR


OUT = PROCESSED_DIR
GRID = 80


def normalize_grid(values: np.ndarray) -> np.ndarray:
    span = values.max() - values.min()
    return (values - values.min()) / span if span > 0 else np.zeros_like(values)


def main() -> None:
    coords = pd.read_csv(OUT / "umap_coords.csv")
    entities = pd.read_csv(OUT / "entities.csv")
    clusters = pd.read_csv(OUT / "clusters.csv")

    merged = coords.merge(entities[["entity_id", "total_spending", "entity_type", "top_issue"]], on="entity_id")
    merged = merged.merge(clusters[["entity_id", "cluster_id", "cluster_label"]], on="entity_id", how="left")

    XY = merged[["x", "y"]].to_numpy().T
    spending_series = merged["total_spending"].where(merged["entity_type"] != "gov_agency", 0)
    spending = spending_series.fillna(0).to_numpy(dtype=float)

    xi = np.linspace(-1, 1, GRID)
    yi = np.linspace(-1, 1, GRID)
    gx, gy = np.meshgrid(xi, yi)
    grid_pts = np.vstack([gx.ravel(), gy.ravel()])

    positive_spending = spending[spending > 0]
    if len(positive_spending):
        spend_clipped = np.clip(spending, 0, np.percentile(positive_spending, 97))
    else:
        spend_clipped = spending
    spend_norm = spend_clipped / spend_clipped.max() if spend_clipped.max() > 0 else np.zeros_like(spend_clipped)

    if XY.shape[1] < 2:
        density_spend = np.zeros((GRID, GRID))
        density_entity = np.zeros((GRID, GRID))
    else:
        kde_spend = gaussian_kde(XY, weights=spend_norm + 1e-6, bw_method=0.15)
        kde_entity = gaussian_kde(XY, bw_method=0.15)
        density_spend = kde_spend(grid_pts).reshape(GRID, GRID)
        density_entity = kde_entity(grid_pts).reshape(GRID, GRID)

    ds = normalize_grid(density_spend)
    de = normalize_grid(density_entity)
    coverage_gap = np.clip(ds - de, 0, None)
    if coverage_gap.max() < 0.001:
        warnings.warn("Gap grid is near-uniform; emitting an explicit no-gap explanation.")
    gap_norm = coverage_gap / coverage_gap.max() if coverage_gap.max() > 0 else np.zeros_like(coverage_gap)

    grid_out = {
        "x_range": [-1.0, 1.0],
        "y_range": [-1.0, 1.0],
        "grid_size": GRID,
        "spending_density": ds.tolist(),
        "entity_density": de.tolist(),
        "gap_score": gap_norm.tolist(),
        "semantics": "model_derived_gap_lead_not_direct_observation",
        "formula": "max(normalized_spending_density - normalized_actor_density, 0)",
        "no_gap_explanation": (
            "No nonzero coverage gap was detected by this metric."
            if gap_norm.max() == 0
            else ""
        ),
    }
    with open(OUT / "gap_grid.json", "w", encoding="utf-8") as f:
        json.dump(grid_out, f)

    flat_gap = gap_norm.ravel()
    top_indices = np.argsort(flat_gap)[::-1][:200]

    def cell_to_xy(idx: int) -> tuple[float, float]:
        row, col = divmod(idx, GRID)
        return float(xi[col]), float(yi[row])

    regions = []
    used = set()
    for idx in top_indices:
        if idx in used or float(flat_gap[idx]) <= 0:
            continue
        cx, cy = cell_to_xy(int(idx))
        gap_val = float(flat_gap[idx])
        dists = np.sqrt((merged["x"] - cx) ** 2 + (merged["y"] - cy) ** 2)
        nearby = merged[dists < 0.15].nlargest(8, "total_spending")
        nearby_clusters = nearby["cluster_label"].dropna().value_counts().index.tolist()[:3]
        top_issues = nearby["top_issue"].dropna().astype(str).value_counts().index.tolist()[:5]
        for jdx in top_indices:
            jx, jy = cell_to_xy(int(jdx))
            if abs(jx - cx) < 0.12 and abs(jy - cy) < 0.12:
                used.add(int(jdx))
        regions.append(
            {
                "gap_id": f"coverage_gap_{len(regions) + 1:02d}",
                "gap_type": "coverage_gap",
                "score": round(gap_val, 4),
                "gap_score": round(gap_val, 4),
                "centroid_x": round(cx, 3),
                "centroid_y": round(cy, 3),
                "explanation": (
                    "Model-derived lead: high lobbying spend/exposure density relative "
                    "to observed actor density in this issue/profile neighborhood."
                ),
                "formula_components": {
                    "normalized_spending_density": round(float(ds.ravel()[idx]), 4),
                    "normalized_actor_density": round(float(de.ravel()[idx]), 4),
                },
                "nearby_clusters": nearby_clusters,
                "top_issues": top_issues,
                "affected_agencies": [],
                "confidence": "model_derived_exploratory",
            }
        )
        if len(regions) >= 10:
            break

    if not regions:
        regions.append(
            {
                "gap_id": "coverage_gap_none",
                "gap_type": "coverage_gap",
                "score": 0.0,
                "gap_score": 0.0,
                "centroid_x": 0.0,
                "centroid_y": 0.0,
                "explanation": "No nonzero model-derived gap lead was detected by this metric.",
                "formula_components": {
                    "normalized_spending_density": 0.0,
                    "normalized_actor_density": 0.0,
                },
                "nearby_clusters": [],
                "top_issues": [],
                "affected_agencies": [],
                "confidence": "no_gap_detected",
            }
        )

    with open(OUT / "top_gaps.json", "w", encoding="utf-8") as f:
        json.dump(regions, f, indent=2)
    with open(OUT / "gap_leads.json", "w", encoding="utf-8") as f:
        json.dump(regions, f, indent=2)

    print(f"Saved: gap_grid.json ({GRID}x{GRID} grid)")
    print(f"Saved: gap_leads.json ({len(regions)} model-derived leads)")


if __name__ == "__main__":
    main()
