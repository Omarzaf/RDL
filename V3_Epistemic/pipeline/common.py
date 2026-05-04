from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / 'Raw Data'
PROCESSED_DIR = ROOT / 'V3_Epistemic' / 'data' / 'processed'
FRONTEND_DIR = ROOT / 'V3_Epistemic' / 'data' / 'frontend'

INPUT_FILES = {
    'stats': 'stats.json',
    'trends': 'trends.json',
    'industries': 'industries.json',
    'top_firms': 'top-firms.json',
    'top_clients': 'top-clients.json',
    'top_lobbyists': 'top-lobbyists.json',
    'revolving_door': 'revolving-door.json',
    'network_analysis': 'network-analysis.json',
    'firm_concentration': 'firm-concentration.json',
    'gov_entities': 'gov-entities.json',
    'filing_activity': 'filing-activity.json',
    'lobbying_vs_contracts': 'lobbying-vs-contracts.json',
    'text_analysis': 'text-analysis.json',
}


def ensure_dirs():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)


def load_json(name: str) -> Any:
    path = RAW_DIR / INPUT_FILES[name]
    if not path.exists():
        print(f'[WARN] Missing input file: {path}')
        return None
    with path.open() as f:
        return json.load(f)


def slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')
