"""Canonical command line entrypoint for the V3 pipeline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
ROOT_DIR = PROJECT_DIR.parent

STAGES = [
    "01_load_and_audit.py",
    "02_build_entity_table.py",
    "03_build_issue_matrix.py",
    "04_umap_layout.py",
    "05_community_detection.py",
    "06_gap_analysis.py",
    "07_revolving_door_vectors.py",
    "08_temporal_series.py",
    "09_build_reliable_payload.py",
]

REQUIRED_RAW_FILES = [
    "stats.json",
    "trends.json",
    "industries.json",
    "top-firms.json",
    "top-clients.json",
    "top-lobbyists.json",
    "revolving-door.json",
    "network-analysis.json",
    "firm-concentration.json",
    "gov-entities.json",
    "filing-activity.json",
    "lobbying-vs-contracts.json",
    "text-analysis.json",
]

OPTIONAL_RAW_FILES = [
    "revolving-door-premium.json",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def build_env(raw_dir: Path, out_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "RDL_RAW_DATA_DIR": str(raw_dir.resolve()),
            "RDL_DATA_DIR": str(out_dir.resolve()),
            "RDL_AUDIT_DIR": str((out_dir / "audit").resolve()),
            "RDL_PROCESSED_DIR": str((out_dir / "processed").resolve()),
            "RDL_LAYOUT_DIR": str((out_dir / "layout").resolve()),
            "RDL_RELIABLE_DIR": str((out_dir / "reliable").resolve()),
            "RDL_FRONTEND_DIR": str((out_dir / "frontend").resolve()),
        }
    )
    pythonpath_parts = [str(ROOT_DIR), env.get("PYTHONPATH", "")]
    env["PYTHONPATH"] = os.pathsep.join(part for part in pythonpath_parts if part)
    return env


def validate_raw_dir(raw_dir: Path) -> list[str]:
    missing = [name for name in REQUIRED_RAW_FILES if not (raw_dir / name).exists()]
    if missing:
        raise SystemExit(f"Missing required raw files in {raw_dir}: {', '.join(missing)}")
    return missing


def run_stage(stage: str, env: dict[str, str]) -> None:
    script = SCRIPT_DIR / stage
    print(f"\n=== {stage} ===")
    subprocess.run([sys.executable, str(script)], cwd=str(SCRIPT_DIR), env=env, check=True)


def load_manifest_inputs(raw_dir: Path) -> dict[str, Any]:
    files = {}
    for name in REQUIRED_RAW_FILES + OPTIONAL_RAW_FILES:
        path = raw_dir / name
        files[name] = {
            "required": name in REQUIRED_RAW_FILES,
            "present": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
            "sha256": sha256_file(path) if path.exists() else None,
        }
    return files


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def validate_outputs(out_dir: Path, *, strict: bool) -> dict[str, Any]:
    processed = out_dir / "processed"
    reliable = out_dir / "reliable"
    frontend = out_dir / "frontend"
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: Any = None) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    required = [
        processed / "entities.csv",
        processed / "edges.csv",
        processed / "issue_matrix_aggregate.csv",
        processed / "umap_coords.csv",
        processed / "clusters.csv",
        processed / "embedding_manifest.json",
        processed / "graph_metrics.json",
        processed / "adjacency_topk.json",
        processed / "gap_leads.json",
        processed / "revolving_vectors.json",
        reliable / "entities.csv",
        reliable / "edges.csv",
        reliable / "entity_year_metrics.csv",
        reliable / "issue_profiles.csv",
        reliable / "quality_report.json",
        reliable / "validation_report.json",
        reliable / "visual_payload.json",
        reliable / "scene_payload.json",
        reliable / "search_index.json",
        reliable / "adjacency_topk.json",
        reliable / "frontend_manifest.json",
        frontend / "reliable_visual_payload.json",
        frontend / "scene_payload.json",
        frontend / "search_index.json",
        frontend / "adjacency_topk.json",
        frontend / "frontend_manifest.json",
    ]
    missing = [str(path) for path in required if not path.exists() or path.stat().st_size == 0]
    check("required_outputs_exist", not missing, missing)

    if (reliable / "validation_report.json").exists():
        validation = read_json(reliable / "validation_report.json")
        check("reliable_validation_passed", bool(validation.get("passed")), validation.get("checks", [])[:5])

    if (reliable / "visual_payload.json").exists():
        payload = read_json(reliable / "visual_payload.json")
        entities = payload.get("entities", [])
        edges = payload.get("edges", [])
        vectors = payload.get("revolving_vectors", [])
        entity_ids = {row.get("id") for row in entities}
        check("frontend_entities_nonempty", len(entities) > 0, len(entities))
        check("frontend_edges_nonempty", len(edges) > 0, len(edges))
        check(
            "payload_edge_endpoints_exist",
            all(edge.get("source_id") in entity_ids and edge.get("target_id") in entity_ids for edge in edges),
            len(edges),
        )
        bogus = [
            vector
            for vector in vectors
            if str(vector.get("source_name", "")).strip().upper() in {"Y", "N"}
            or str(vector.get("target_name", "")).strip().upper() in {"Y", "N"}
        ]
        check("revolving_vectors_no_singleton_endpoints", not bogus, bogus[:3])
        check("payload_uses_meta_years", bool(payload.get("meta", {}).get("years")), list(payload.get("meta", {}).keys()))

    if (processed / "embedding_manifest.json").exists():
        manifest = read_json(processed / "embedding_manifest.json")
        check("embedding_manifest_has_seed", "random_state" in manifest, manifest)
        check("embedding_manifest_has_row_count", int(manifest.get("row_count", 0)) > 0, manifest.get("row_count"))
        check(
            "embedding_used_umap_in_strict_release",
            manifest.get("method") == "umap" and not bool(manifest.get("fallback")),
            {"method": manifest.get("method"), "fallback": manifest.get("fallback")},
        )

    matrix_path = processed / "issue_matrix_aggregate.csv"
    if matrix_path.exists():
        rows = read_csv_rows(matrix_path)
        fieldnames = list(rows[0]) if rows else []
        feature_cols = [col for col in fieldnames if col not in {"entity_id", "name"}]
        issue_cols = [col for col in feature_cols if col.startswith("issue_")]
        feature_sum = 0.0
        issue_sum = 0.0
        finite_values = True
        for row in rows:
            for col in feature_cols:
                value = safe_float(row.get(col))
                if not math.isfinite(value):
                    finite_values = False
                    continue
                feature_sum += abs(value)
                if col in issue_cols:
                    issue_sum += abs(value)
        check("issue_matrix_nonempty", bool(rows) and bool(feature_cols), {"rows": len(rows), "features": len(feature_cols)})
        check("issue_matrix_values_finite", finite_values, None)
        check("issue_matrix_not_all_zero", feature_sum > 0, round(feature_sum, 6))
        check("issue_block_not_all_zero", bool(issue_cols) and issue_sum > 0, {"issue_features": len(issue_cols), "issue_sum": round(issue_sum, 6)})

    coords_path = processed / "umap_coords.csv"
    if coords_path.exists():
        coord_rows = read_csv_rows(coords_path)
        coords = []
        for row in coord_rows:
            x = safe_float(row.get("x"))
            y = safe_float(row.get("y"))
            if math.isfinite(x) and math.isfinite(y):
                coords.append((x, y))
        if coords:
            xs = [x for x, _ in coords]
            ys = [y for _, y in coords]
            mean_x = sum(xs) / len(xs)
            mean_y = sum(ys) / len(ys)
            var_x = sum((x - mean_x) ** 2 for x in xs) / len(xs)
            var_y = sum((y - mean_y) ** 2 for y in ys) / len(ys)
            unique_ratio = len(set(coords)) / len(coords)
            radii = [round(math.hypot(x, y), 2) for x, y in coords]
            most_common_radius_share = Counter(radii).most_common(1)[0][1] / len(radii)
        else:
            var_x = var_y = unique_ratio = most_common_radius_share = 0.0
        check(
            "embedding_coordinates_non_degenerate",
            len(coords) == len(coord_rows) and var_x > 1e-4 and var_y > 1e-4 and unique_ratio > 0.5,
            {
                "rows": len(coord_rows),
                "finite_rows": len(coords),
                "var_x": round(var_x, 8),
                "var_y": round(var_y, 8),
                "unique_ratio": round(unique_ratio, 4),
            },
        )
        check(
            "embedding_coordinates_not_ring_layout",
            most_common_radius_share < 0.15,
            {"most_common_radius_share": round(most_common_radius_share, 4)},
        )

    passed = all(row["passed"] for row in checks)
    report = {"passed": passed, "strict": strict, "checks": checks}
    if strict and not passed:
        failed = [row["name"] for row in checks if not row["passed"]]
        raise SystemExit(f"Strict validation failed: {', '.join(failed)}")
    return report


def run_pipeline(args: argparse.Namespace) -> int:
    raw_dir = Path(args.raw_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    validate_raw_dir(raw_dir)
    env = build_env(raw_dir, out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc).isoformat()
    manifest = {
        "started_at": started_at,
        "command": " ".join(sys.argv),
        "raw_dir": str(raw_dir),
        "out_dir": str(out_dir),
        "python": sys.version,
        "inputs": load_manifest_inputs(raw_dir),
        "stages": STAGES,
    }
    write_json(out_dir / "run_manifest.json", manifest)

    for stage in STAGES:
        run_stage(stage, env)

    validation = validate_outputs(out_dir, strict=args.strict)
    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    manifest["validation_passed"] = validation["passed"]
    manifest["outputs"] = {
        "processed": str(out_dir / "processed"),
        "reliable": str(out_dir / "reliable"),
        "frontend": str(out_dir / "frontend"),
    }
    write_json(out_dir / "run_manifest.json", manifest)
    write_json(out_dir / "pipeline_validation.json", validation)
    print(f"\nPipeline complete. validation_passed={validation['passed']} out_dir={out_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the canonical V3 RDL pipeline.")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Run all canonical stages.")
    run.add_argument("--raw-dir", default=str(ROOT_DIR / "Raw Data"))
    run.add_argument("--out-dir", default=str(PROJECT_DIR / "data"))
    run.add_argument("--strict", action="store_true", help="Fail on validation warnings that block deployment.")
    run.set_defaults(func=run_pipeline)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
