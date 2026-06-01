"""
03_build_issue_matrix.py

Builds the canonical feature matrix consumed by layout and clustering. The
stage intentionally uses `embedding_matrix.csv` from stage 02 because that file
contains the real issue vectors, propagated client issue profiles, government
target vectors, and numeric weights. It no longer reconstructs a smaller stale
matrix from an old `entities.csv`.
"""

from __future__ import annotations

import json
import math
import re

import numpy as np
import pandas as pd

from config import PROCESSED_DIR, YEARS


OUT = PROCESSED_DIR


INDUSTRY_KEYWORDS = {
    "Healthcare & Pharma": [
        "HEALTH", "PHARMA", "MEDICAL", "HOSPITAL", "BIOTECH", "PFIZER",
        "MERCK", "ABBVIE", "AMGEN", "LILLY", "PATIENT", "DRUG",
    ],
    "Defense & Aerospace": [
        "DEFENSE", "AEROSPACE", "BOEING", "LOCKHEED", "RAYTHEON",
        "NORTHROP", "MILITARY", "PENTAGON", "SECURITY",
    ],
    "Finance & Banking": [
        "BANK", "FINANCIAL", "CAPITAL", "INVESTMENT", "SECURITIES",
        "JPMORGAN", "GOLDMAN", "CITIGROUP", "BLACKROCK",
    ],
    "Energy & Environment": [
        "ENERGY", "OIL", "GAS", "PETROLEUM", "COAL", "POWER",
        "ELECTRIC", "RENEWABLE", "CLIMATE", "CARBON",
    ],
    "Technology & Telecom": [
        "TECHNOLOGY", "SOFTWARE", "DIGITAL", "DATA", "TELECOM",
        "GOOGLE", "META", "AMAZON", "APPLE", "MICROSOFT", "AI",
    ],
    "Agriculture & Food": [
        "AGRICULTURE", "FARM", "FOOD", "CORN", "WHEAT", "SOYBEAN",
        "CATTLE", "DAIRY", "GROCERY",
    ],
    "Transportation & Auto": [
        "TRANSPORT", "AIRLINE", "RAILROAD", "SHIPPING", "AUTO",
        "AVIATION", "FORD", "GM", "TESLA", "PORT",
    ],
    "Real Estate & Construction": [
        "REAL ESTATE", "PROPERTY", "HOUSING", "CONSTRUCTION",
        "DEVELOPER", "BUILDER", "INFRASTRUCTURE",
    ],
    "Education & Research": [
        "UNIVERSITY", "COLLEGE", "SCHOOL", "EDUCATION", "RESEARCH",
        "FOUNDATION", "THINK TANK", "INSTITUTE",
    ],
    "Legal & Lobbying": [
        "LAW FIRM", "LLP", "CONSULTING", "ADVISORS", "STRATEGIES",
        "GOVERNMENT AFFAIRS", "LOBBYIST", "BROWNSTEIN", "AKIN GUMP",
    ],
    "Government & Nonprofit": [
        "DEPARTMENT OF", "FEDERAL", "BUREAU OF", "OFFICE OF",
        "ADMINISTRATION", "COMMISSION", "AGENCY", "ASSOCIATION",
    ],
}


def classify_industry(name: str) -> str:
    name_up = str(name or "").upper()
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        if any(keyword in name_up for keyword in keywords):
            return industry
    return "Other / Multi-sector"


def l2_normalize_frame(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    values = df[feature_cols].fillna(0.0).astype(float).to_numpy()
    norms = np.linalg.norm(values, axis=1)
    norms[norms == 0] = 1.0
    df.loc[:, feature_cols] = values / norms[:, None]
    return df


def main() -> None:
    entities_path = OUT / "entities.csv"
    embedding_path = OUT / "embedding_matrix.csv"
    if not entities_path.exists():
        raise FileNotFoundError(f"Missing canonical entity table: {entities_path}")
    if not embedding_path.exists():
        raise FileNotFoundError(f"Missing canonical embedding matrix: {embedding_path}")

    entities = pd.read_csv(entities_path)
    embedding = pd.read_csv(embedding_path)
    if len(entities) != len(embedding):
        raise ValueError(
            f"Entity/embedding row mismatch: entities={len(entities)} embedding={len(embedding)}"
        )

    merged = embedding.merge(entities[["entity_id", "name", "entity_type"]], on="entity_id", how="left")
    missing_names = int(merged["name"].isna().sum())
    if missing_names:
        raise ValueError(f"Embedding matrix has {missing_names} rows without entity metadata")

    feature_cols = [col for col in merged.columns if col not in {"entity_id", "name", "entity_type"}]
    issue_cols = [col for col in feature_cols if col.startswith("issue_")]
    gov_cols = [col for col in feature_cols if col.startswith("gov_")]
    numeric_cols = [col for col in feature_cols if col.startswith("num_")]

    issue_values = merged[issue_cols].fillna(0.0).astype(float) if issue_cols else pd.DataFrame(index=merged.index)
    no_issue_data = issue_values.abs().sum(axis=1) == 0 if issue_cols else pd.Series(True, index=merged.index)

    matrix = merged[["entity_id", "name"] + feature_cols].copy()
    matrix = l2_normalize_frame(matrix, feature_cols)
    matrix.to_csv(OUT / "issue_matrix_aggregate.csv", index=False)

    year_rows = []
    for year in YEARS:
        year_df = matrix.copy()
        year_df.insert(2, "year", year)
        year_rows.append(year_df)
    pd.concat(year_rows, ignore_index=True).to_csv(OUT / "issue_matrix_by_year.csv", index=False)

    entity_industries = entities[["entity_id", "name", "entity_type"]].copy()
    entity_industries["industry_label"] = entity_industries["name"].apply(classify_industry)
    entity_industries.to_csv(OUT / "entity_industries.csv", index=False)

    feature_report = {
        "row_count": int(len(matrix)),
        "feature_count": int(len(feature_cols)),
        "issue_feature_count": int(len(issue_cols)),
        "gov_feature_count": int(len(gov_cols)),
        "numeric_feature_count": int(len(numeric_cols)),
        "rows_without_issue_data": int(no_issue_data.sum()),
        "pct_without_issue_data": round(float(no_issue_data.mean() * 100), 4) if len(no_issue_data) else 0.0,
        "feature_source": "embedding_matrix.csv",
        "normalization": "row_l2_after_stage_02_block_weights",
        "features": feature_cols,
    }
    with open(OUT / "issue_vocab.json", "w", encoding="utf-8") as f:
        json.dump(feature_cols, f, indent=2)
    with open(OUT / "issue_feature_coverage.json", "w", encoding="utf-8") as f:
        json.dump(feature_report, f, indent=2)

    print(
        f"Feature matrix: {len(matrix)} rows x {len(feature_cols)} features "
        f"({feature_report['rows_without_issue_data']} rows without direct issue data)"
    )
    print("Saved: issue_matrix_aggregate.csv, issue_matrix_by_year.csv, entity_industries.csv")


if __name__ == "__main__":
    main()
