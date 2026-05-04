from __future__ import annotations
import json
import re
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


def ensure_dirs() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)


def require_raw_inputs() -> None:
    missing = [RAW_DIR / filename for filename in INPUT_FILES.values() if not (RAW_DIR / filename).exists()]
    if missing:
        names = '\n'.join(f'- {p}' for p in missing)
        raise FileNotFoundError(f'Missing required Raw Data files:\n{names}')


def load_json(name: str) -> Any:
    path = RAW_DIR / INPUT_FILES[name]
    with path.open() as f:
        return json.load(f)


def slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', (s or '').lower()).strip('_')
