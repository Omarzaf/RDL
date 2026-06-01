from __future__ import annotations

import collections
import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / "V3_Epistemic"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def test_run_script_uses_canonical_cli() -> None:
    script = read(ROOT / "run_pipeline.sh")
    assert "-m V3_Epistemic.pipeline.cli run" in script
    assert "--raw-dir" in script
    assert "--out-dir" in script
    assert "--strict" in script


def test_downstream_stages_read_canonical_entities() -> None:
    for stage in [
        "03_build_issue_matrix.py",
        "05_community_detection.py",
        "06_gap_analysis.py",
        "07_revolving_door_vectors.py",
        "09_build_reliable_payload.py",
    ]:
        text = read(V3 / "pipeline" / stage)
        assert "entities.csv" in text
        assert "entity_nodes.csv" not in text
    for stage in ["04_umap_layout.py", "08_temporal_series.py"]:
        assert "entity_nodes.csv" not in read(V3 / "pipeline" / stage)


def test_revolving_door_stage_rejects_legacy_endpoint_fallbacks() -> None:
    text = read(V3 / "pipeline" / "07_revolving_door_vectors.py")
    assert "len(key) <= 1" in text
    assert "transition_year = 2021" not in text
    assert "or 2021" not in text
    assert "source_name == \"Y\"" not in text


def test_static_frontend_loads_split_payloads_and_dynamic_years() -> None:
    html = read(V3 / "output" / "reliable_influence_map.html")
    assert 'const DATA_URL = "../data/frontend/scene_payload.json"' in html
    assert 'const SEARCH_URL = "../data/frontend/search_index.json"' in html
    assert "reliable_visual_payload.json" not in html
    assert "payload.meta?.years" in html
    assert "vectorTransitionYear" in html
    assert "safeNumber(vector.transition_year, 2021)" not in html
    assert "coordinateSources.neighbor_inferred" in html
    assert "coordinateSources.deterministic_unplaced_ring" in html
    assert "inferred_sector_cluster ?? 0" not in html
    assert 'projectionMode = "2d"' in html
    assert 'id="theme-toggle"' in html
    assert 'aria-pressed="false"' in html
    assert "body.theme-dark" in html
    assert "themeBackgroundColor" in html
    assert 'body class="mode-briefing controls-closed details-closed legend-closed"' in html
    assert 'id="show-identifiers" type="checkbox"><span>Type identifiers' in html
    assert "renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.35))" in html


def test_generated_payload_contract() -> None:
    reliable = V3 / "data" / "reliable"
    frontend = V3 / "data" / "frontend"
    for name in [
        "scene_payload.json",
        "search_index.json",
        "adjacency_topk.json",
        "frontend_manifest.json",
    ]:
        assert (reliable / name).exists(), name
        assert (frontend / name).exists(), name
    assert (reliable / "visual_payload.json").exists()
    assert (frontend / "reliable_visual_payload.json").exists()

    payload = load_json(reliable / "visual_payload.json")
    scene = load_json(reliable / "scene_payload.json")
    search = load_json(reliable / "search_index.json")
    manifest = load_json(reliable / "frontend_manifest.json")
    frontend_manifest = load_json(frontend / "frontend_manifest.json")

    meta = payload["meta"]
    for key in [
        "years",
        "partial_years",
        "performance_caps",
        "data_issues",
        "entity_count_full",
        "entity_count_visible_initial",
        "edge_count_full",
        "edge_count_visual_payload",
    ]:
        assert key in meta

    assert scene["meta"]["years"] == meta["years"]
    assert len(scene["entities"]) <= len(payload["entities"])
    assert len(search["entities"]) == len(payload["entities"])
    assert manifest["counts"]["scene_entities"] == len(scene["entities"])
    for root, manifest_payload in [(reliable, manifest), (frontend, frontend_manifest)]:
        for name in manifest_payload["files"].values():
            assert (root / name).exists(), f"{root / name} missing from manifest"
    assert payload["gap_grid"].get("semantics") == "model_derived_gap_lead_not_direct_observation"

    entity_ids = {entity["id"] for entity in payload["entities"]}
    assert entity_ids
    assert all(edge["source_id"] in entity_ids and edge["target_id"] in entity_ids for edge in payload["edges"])
    assert not [
        vector
        for vector in payload.get("revolving_vectors", [])
        if str(vector.get("source_name", "")).strip().upper() in {"Y", "N"}
        or str(vector.get("target_name", "")).strip().upper() in {"Y", "N"}
    ]
    valid_years = set(meta["years"])
    for vector in payload.get("revolving_vectors", []):
        transition_year = vector.get("transition_year")
        if transition_year is None:
            assert vector.get("temporal_scope") == "unknown_transition_year"
            assert not vector.get("transition_year_estimated")
        else:
            assert transition_year in valid_years
            assert vector.get("temporal_scope") in {"observed_transition_year", "estimated_transition_year"}
    assert not [vector for vector in payload.get("revolving_vectors", []) if vector.get("transition_year") == 0]

    coord_dist = meta["data_quality_summary"]["coordinate_source_distribution"]
    assert sum(coord_dist.values()) == meta["entity_count_full"]
    assert "unknown_revolving_vectors" in meta["data_quality_summary"]


def test_processed_analytics_are_non_degenerate() -> None:
    processed = V3 / "data" / "processed"
    entities = pd.read_csv(processed / "entities.csv")
    edges = pd.read_csv(processed / "edges.csv")
    issue_matrix = pd.read_csv(processed / "issue_matrix_aggregate.csv")
    coords = pd.read_csv(processed / "umap_coords.csv")
    clusters = pd.read_csv(processed / "clusters.csv")
    graph_metrics = load_json(processed / "graph_metrics.json")
    embedding_manifest = load_json(processed / "embedding_manifest.json")

    assert not entities.empty
    assert not edges.empty
    assert len(issue_matrix) == len(entities)
    feature_cols = [col for col in issue_matrix.columns if col not in {"entity_id", "name", "entity_type", "industry"}]
    issue_cols = [col for col in feature_cols if col.startswith("issue_")]
    assert feature_cols
    assert issue_cols
    assert issue_matrix[feature_cols].to_numpy().sum() > 0
    assert issue_matrix[issue_cols].to_numpy().sum() > 0
    assert embedding_manifest["method"] == "umap"
    assert embedding_manifest["fallback"] is False
    assert coords[["x", "y"]].notna().all().all()
    assert coords[["x", "y"]].nunique().min() > 1
    unique_ratio = len(set(zip(coords["x"], coords["y"]))) / len(coords)
    assert unique_ratio > 0.5
    assert coords["x"].var() > 1e-4
    assert coords["y"].var() > 1e-4
    radius_counts = collections.Counter(round(math.hypot(row.x, row.y), 2) for row in coords.itertuples())
    assert radius_counts.most_common(1)[0][1] / len(coords) < 0.15
    assert {"issue_community_id", "relationship_community_id"}.issubset(clusters.columns)
    assert graph_metrics.get("top_brokers")
    assert graph_metrics.get("entity_metrics")


def test_public_language_avoids_overclaim_terms() -> None:
    banned = ["corruption", "covert", "uncontested", "bribery"]
    paths = [
        ROOT / "README.md",
        ROOT / "ROADMAP.md",
        V3 / "output" / "reliable_influence_map.html",
        V3 / "output" / "METHODOLOGY.md",
        *(sorted((ROOT / "docs").glob("*.md")) if (ROOT / "docs").exists() else []),
    ]
    offenders = []
    for path in paths:
        text = read(path).lower()
        for term in banned:
            if term in text:
                offenders.append(f"{path.relative_to(ROOT)}:{term}")
    assert not offenders
