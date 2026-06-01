"""Shared paths and constants for the V3 epistemic influence pipeline."""

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = PROJECT_DIR.parent

DATA_DIR = Path(os.environ.get("RDL_DATA_DIR", PROJECT_DIR / "data")).resolve()
RAW_DATA_DIR = Path(os.environ.get("RDL_RAW_DATA_DIR", ROOT_DIR / "Raw Data")).resolve()
AUDIT_DIR = Path(os.environ.get("RDL_AUDIT_DIR", DATA_DIR / "audit")).resolve()
PROCESSED_DIR = Path(os.environ.get("RDL_PROCESSED_DIR", DATA_DIR / "processed")).resolve()
LAYOUT_DIR = Path(os.environ.get("RDL_LAYOUT_DIR", DATA_DIR / "layout")).resolve()
RELIABLE_DIR = Path(os.environ.get("RDL_RELIABLE_DIR", DATA_DIR / "reliable")).resolve()
FRONTEND_DIR = Path(os.environ.get("RDL_FRONTEND_DIR", DATA_DIR / "frontend")).resolve()
LEGACY_GRAPH_DIR = PROJECT_DIR / "processed"

YEARS = list(range(2018, 2026))  # Update this when data is refreshed.
PARTIAL_YEARS = [2025]

VISIBLE_ENTITY_CAP = int(os.environ.get("RDL_VISIBLE_ENTITY_CAP", "3000"))
PAYLOAD_EDGE_CAP = int(os.environ.get("RDL_PAYLOAD_EDGE_CAP", "10000"))
REVOLVING_VECTOR_CAP = int(os.environ.get("RDL_REVOLVING_VECTOR_CAP", "500"))
