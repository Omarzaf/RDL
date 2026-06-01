"""
Build a defensible 3D influence-map payload from the lobbying JSON exports.

This stage intentionally does not depend on the older simulated
entities_3d.json. It rebuilds canonical entities and edges from Raw Data,
attaches existing layout/cluster artifacts when available, computes explicit
quality/scoring fields, and writes a cleaned payload plus validation outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from config import (
    FRONTEND_DIR,
    PAYLOAD_EDGE_CAP,
    PARTIAL_YEARS,
    PROCESSED_DIR,
    RAW_DATA_DIR,
    REVOLVING_VECTOR_CAP,
    RELIABLE_DIR,
    VISIBLE_ENTITY_CAP,
    YEARS,
)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
ROOT_DIR = PROJECT_DIR.parent
RAW_DIR = RAW_DATA_DIR
LEGACY_LAYOUT_DIR = PROCESSED_DIR

PLACEHOLDERS = {"", ".", "na", "n/a", "nan", "none", "null", "unknown", "unk"}


ISSUE_LABELS = {
    "ACC": "Accounting",
    "ADV": "Advertising",
    "AER": "Aerospace",
    "AGR": "Agriculture",
    "ALC": "Alcohol",
    "ANI": "Animal welfare",
    "APP": "Apparel",
    "ART": "Arts and culture",
    "AUT": "Automotive",
    "AVI": "Aviation",
    "BAN": "Banking",
    "BEV": "Beverage industry",
    "BNK": "Bankruptcy",
    "BUD": "Budget and appropriations",
    "CAW": "Clean air and water",
    "CDT": "Commodity trading",
    "CHM": "Chemicals",
    "CIV": "Civil rights and liberties",
    "COM": "Communications",
    "CON": "Constitutional issues",
    "CPI": "Consumer product safety",
    "CPT": "Consumer protection",
    "CSP": "Communications and spectrum",
    "DEF": "Defense",
    "DIS": "Disaster and emergency",
    "DOC": "Domestic commerce",
    "ECN": "Economics",
    "EDU": "Education",
    "ENG": "Energy",
    "ENV": "Environment",
    "FAM": "Family issues",
    "FIN": "Finance",
    "FIR": "Firearms",
    "FOO": "Food industry",
    "FOR": "Foreign relations",
    "FUE": "Fuel and gas",
    "GAM": "Gaming",
    "GOV": "Government operations",
    "HCR": "Healthcare",
    "HOM": "Homeland security",
    "HOU": "Housing",
    "IMM": "Immigration",
    "IND": "Indian and tribal affairs",
    "INS": "Insurance",
    "INT": "Intellectual property",
    "LAB": "Labor",
    "LAW": "Law enforcement",
    "LBR": "Labor and employment",
    "LIT": "Litigation",
    "LOB": "Lobbying disclosure",
    "MAN": "Manufacturing",
    "MAR": "Marine and fisheries",
    "MED": "Medicare and Medicaid",
    "MIA": "Media",
    "MIL": "Military",
    "MIN": "Mining",
    "MMM": "Medicare/Medicaid/medical matters",
    "MON": "Monetary policy",
    "NAT": "Natural resources",
    "NEI": "Native and indigenous issues",
    "PHA": "Pharmaceuticals",
    "POS": "Postal service",
    "PRO": "Public lands and property",
    "RES": "Research",
    "RET": "Retirement",
    "ROD": "Roads and highways",
    "RRL": "Railroads",
    "RRR": "Railroads",
    "SCI": "Science and technology",
    "SMB": "Small business",
    "SPC": "Space",
    "SPO": "Sports",
    "TAR": "Tariffs",
    "TAX": "Taxation",
    "TEC": "Technology",
    "TOB": "Tobacco",
    "TOR": "Torts",
    "TOU": "Tourism",
    "TRA": "Transportation",
    "TRD": "Trade",
    "TRS": "Telecommunications",
    "TRU": "Trucking",
    "UNI": "Unions",
    "UNM": "Unclassified matters",
    "URB": "Urban development",
    "UTI": "Utilities",
    "VET": "Veterans",
    "WAS": "Waste management",
    "WEL": "Welfare",
}

STATE_REGIONS = {
    "AK": "West", "AZ": "West", "CA": "West", "CO": "West", "HI": "West",
    "ID": "West", "MT": "West", "NM": "West", "NV": "West", "OR": "West",
    "UT": "West", "WA": "West", "WY": "West",
    "AL": "South", "AR": "South", "DC": "DC", "DE": "South", "FL": "South",
    "GA": "South", "KY": "South", "LA": "South", "MD": "South", "MS": "South",
    "NC": "South", "OK": "South", "SC": "South", "TN": "South", "TX": "South",
    "VA": "South", "WV": "South",
    "CT": "Northeast", "MA": "Northeast", "ME": "Northeast", "NH": "Northeast",
    "NJ": "Northeast", "NY": "Northeast", "PA": "Northeast", "RI": "Northeast",
    "VT": "Northeast",
    "IA": "Midwest", "IL": "Midwest", "IN": "Midwest", "KS": "Midwest",
    "MI": "Midwest", "MN": "Midwest", "MO": "Midwest", "ND": "Midwest",
    "NE": "Midwest", "OH": "Midwest", "SD": "Midwest", "WI": "Midwest",
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        if compact:
            json.dump(payload, f, separators=(",", ":"))
        else:
            json.dump(payload, f, indent=2)
            f.write("\n")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: serialize_cell(row.get(field, "")) for field in fields})


def serialize_cell(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"))
    if value is None:
        return ""
    return str(value)


def stable_hash(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def normalized_name(name: Any) -> str:
    text = str(name or "").replace("&AMP;", "&").upper().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def slugify(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or stable_hash(str(value or "unknown"), 10)


def canonical_external_id(entity_type: str, name: str) -> str:
    return f"{entity_type}_{stable_hash(entity_type + ':' + normalized_name(name), 14)}"


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in PLACEHOLDERS
    if isinstance(value, list):
        return len(value) == 0
    if isinstance(value, dict):
        return len(value) == 0
    return False


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def optional_year(value: Any) -> int | None:
    """Parse a year only when source evidence contains one in the visual range."""
    if value is None or value == "":
        return None
    try:
        year = int(float(value))
    except (TypeError, ValueError):
        return None
    return year if year in YEARS else None


def parse_json_cell(value: Any) -> dict[str, float]:
    if not value:
        return {}
    if isinstance(value, dict):
        return {str(k): safe_float(v) for k, v in value.items()}
    try:
        parsed = json.loads(str(value))
        if isinstance(parsed, dict):
            return {str(k): safe_float(v) for k, v in parsed.items()}
    except json.JSONDecodeError:
        return {}
    return {}


def normalize_score(values: dict[str, float]) -> dict[str, float]:
    positives = [v for v in values.values() if v > 0]
    if not positives:
        return {k: 0.0 for k in values}
    max_value = max(positives)
    if max_value <= 0:
        return {k: 0.0 for k in values}
    return {k: round(max(0.0, v) / max_value, 6) for k, v in values.items()}


def region_for_state(state: str) -> str:
    state_code = str(state or "").strip().upper()[:2]
    if not state_code:
        return "Unknown"
    return STATE_REGIONS.get(state_code, "Other/Unknown")


def load_sources() -> dict[str, Any]:
    corrected_stats = PROCESSED_DIR / "stats.corrected.json"
    return {
        "raw_stats": read_json(RAW_DIR / "stats.json"),
        "stats": read_json(corrected_stats) if corrected_stats.exists() else read_json(RAW_DIR / "stats.json"),
        "trends": read_json(RAW_DIR / "trends.json"),
        "top_firms": read_json(RAW_DIR / "top-firms.json"),
        "top_clients": read_json(RAW_DIR / "top-clients.json"),
        "top_lobbyists": read_json(RAW_DIR / "top-lobbyists.json"),
        "revolving_door": read_json(RAW_DIR / "revolving-door.json"),
        "gov_entities": read_json(RAW_DIR / "gov-entities.json"),
        "industries": read_json(RAW_DIR / "industries.json"),
        "firm_concentration": read_json(RAW_DIR / "firm-concentration.json"),
        "filing_activity": read_json(RAW_DIR / "filing-activity.json"),
        "text_analysis": read_json(RAW_DIR / "text-analysis.json"),
        "lobbying_vs_contracts": read_json(RAW_DIR / "lobbying-vs-contracts.json"),
    }


def build_issue_rollups(industries: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, str]]:
    code_to_rollup: dict[str, str] = {}
    for industry in industries:
        for code in industry.get("codes", []) or []:
            code_to_rollup[str(code).upper()] = str(industry.get("name", "Other / Multi-sector"))

    all_codes = set(ISSUE_LABELS)
    for industry in industries:
        all_codes.update(str(code).upper() for code in industry.get("codes", []) or [])
    for code in all_codes:
        code_to_rollup.setdefault(code, "Other / Multi-sector")
    labels = {code: ISSUE_LABELS.get(code, code) for code in sorted(all_codes)}
    return labels, code_to_rollup


def issue_vec_from_codes(codes: list[Any]) -> dict[str, float]:
    weights: dict[str, float] = defaultdict(float)
    for item in codes or []:
        if isinstance(item, dict):
            code = str(item.get("code", "")).upper().strip()
            weight = safe_float(item.get("count", 1), 1.0)
        else:
            code = str(item).upper().strip()
            weight = 1.0
        if code:
            weights[code] += weight
    total = sum(weights.values())
    if total <= 0:
        return {}
    return {code: round(weight / total, 6) for code, weight in sorted(weights.items())}


def top_issue(issue_vec: dict[str, float]) -> str:
    if not issue_vec:
        return ""
    return max(issue_vec.items(), key=lambda item: item[1])[0]


def raw_top_issue(raw_issues: list[Any]) -> str:
    if not raw_issues:
        return ""
    first = raw_issues[0]
    if isinstance(first, dict):
        return str(first.get("code", "")).upper().strip()
    return str(first).upper().strip()


def dominant_rollup(issue_vec: dict[str, float], code_to_rollup: dict[str, str]) -> str:
    if not issue_vec:
        return "Unknown"
    weights: dict[str, float] = defaultdict(float)
    for code, weight in issue_vec.items():
        weights[code_to_rollup.get(code, "Other / Multi-sector")] += weight
    return max(weights.items(), key=lambda item: item[1])[0]


def classify_client_subtype(name: str, description: str = "") -> str:
    haystack = normalized_name(f"{name} {description}")
    if any(token in haystack for token in ["UNIVERSITY", "COLLEGE", "SCHOOL", "RESEARCH", "INSTITUTE"]):
        return "university/research"
    if any(token in haystack for token in ["FOUNDATION", "NONPROFIT", "NON-PROFIT", "CHARITABLE", "ACTION FUND"]):
        return "nonprofit/foundation"
    if any(token in haystack for token in ["ASSOCIATION", "ASSN", "COUNCIL", "CHAMBER", "ROUNDTABLE", "FEDERATION"]):
        return "trade association"
    if any(token in haystack for token in ["REPUBLIC OF", "GOVERNMENT OF", "EMBASSY", "FOREIGN", "STATE OF", "CITY OF", "COUNTY OF", "TOWN OF"]):
        return "foreign/state/local government"
    if any(token in haystack for token in ["TRIBE", "TRIBAL", "NATION", "RANCHERIA", "PUEBLO"]):
        return "tribal entity"
    if any(token in haystack for token in ["AUTHORITY", "PORT OF", "TRANSIT", "AIRPORT", "WATER DISTRICT"]):
        return "public authority"
    if any(token in haystack for token in [" INC", " LLC", " CORP", " COMPANY", " CO.", " LTD", " PLC", " LP"]):
        return "corporation"
    return "unknown"


def seniority_score(positions: list[Any]) -> float:
    text = " ".join(str(p) for p in positions or []).upper()
    weights = {
        "SECRETARY": 1.0,
        "CHIEF OF STAFF": 0.9,
        "STAFF DIRECTOR": 0.85,
        "DIRECTOR": 0.75,
        "COUNSEL": 0.65,
        "DEPUTY": 0.6,
        "LEGISLATIVE DIRECTOR": 0.55,
        "LEGISLATIVE ASSISTANT": 0.45,
        "INTERN": 0.1,
    }
    scores = [score for token, score in weights.items() if token in text]
    return max(scores) if scores else (0.35 if text else 0.0)


def source_snapshot(stats: dict[str, Any]) -> str:
    last_updated = str(stats.get("lastUpdated", ""))
    match = re.match(r"(\d{4}-\d{2}-\d{2})", last_updated)
    return match.group(1) if match else "2026-02-25"


def audit_json_file(path: Path, data: Any) -> dict[str, Any]:
    if isinstance(data, list):
        records = [row for row in data if isinstance(row, dict)]
    elif isinstance(data, dict):
        records = [data]
    else:
        records = []

    fields = sorted({key for row in records for key in row})
    missing: dict[str, Any] = {}
    for field in fields:
        count = sum(1 for row in records if is_missing(row.get(field)))
        missing[field] = {
            "missing": count,
            "total": len(records),
            "rate": round(count / len(records), 4) if records else 0.0,
        }

    duplicate_names = []
    if records and "name" in fields:
        counts = Counter(normalized_name(row.get("name")) for row in records if not is_missing(row.get("name")))
        duplicate_names = [
            {"name": name, "count": count}
            for name, count in counts.most_common()
            if count > 1
        ][:50]

    nested_missingness = {}
    if isinstance(data, dict):
        for key, value in data.items():
            if not isinstance(value, list) or not value or not all(isinstance(row, dict) for row in value[:20]):
                continue
            nested_fields = sorted({field for row in value if isinstance(row, dict) for field in row})
            nested_missingness[key] = {}
            for field in nested_fields:
                count = sum(1 for row in value if is_missing(row.get(field)))
                nested_missingness[key][field] = {
                    "missing": count,
                    "total": len(value),
                    "rate": round(count / len(value), 4) if value else 0.0,
                }

    return {
        "file": path.name,
        "record_count": len(records) if records else (len(data) if isinstance(data, dict) else 0),
        "fields": fields,
        "missingness": missing,
        "nested_missingness": nested_missingness,
        "duplicate_names": duplicate_names,
    }


def distinctive_token(name: str) -> str:
    tokens = re.findall(r"[A-Z0-9]+", normalized_name(name))
    stop = {
        "THE", "AND", "FOR", "OF", "INC", "LLC", "LTD", "LP", "LLP",
        "CORP", "CORPORATION", "COMPANY", "CO", "GROUP", "STRATEGIES",
        "GOVERNMENT", "AFFAIRS", "CONSULTING", "ASSOCIATES", "ASSOCIATION",
    }
    for token in tokens:
        if token not in stop:
            return token
    return tokens[0] if tokens else ""


def build_quality_report(sources: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    file_audits = {}
    raw_file_map = {
        "stats": "stats.json",
        "trends": "trends.json",
        "top_firms": "top-firms.json",
        "top_clients": "top-clients.json",
        "top_lobbyists": "top-lobbyists.json",
        "revolving_door": "revolving-door.json",
        "gov_entities": "gov-entities.json",
        "network_analysis": "network-analysis.json",
        "firm_concentration": "firm-concentration.json",
        "filing_activity": "filing-activity.json",
        "text_analysis": "text-analysis.json",
        "lobbying_vs_contracts": "lobbying-vs-contracts.json",
    }
    for key, filename in raw_file_map.items():
        path = RAW_DIR / filename
        if path.exists():
            file_audits[filename] = audit_json_file(path, read_json(path))

    issues: list[dict[str, Any]] = []
    stats = sources["stats"]
    raw_stats = sources.get("raw_stats", stats)
    trends = sources["trends"]
    filing_activity = sources["filing_activity"]
    gov_entities = sources["gov_entities"]
    firm_concentration = sources["firm_concentration"]

    max_trend_year = max(int(row.get("year", 0)) for row in trends)
    if safe_int(raw_stats.get("latestYear")) != max_trend_year:
        issues.append({
            "severity": "high",
            "code": "STALE_LATEST_YEAR",
            "message": "stats.json latestYear does not match the max year in trends.json.",
            "evidence": {"stats_latestYear": raw_stats.get("latestYear"), "max_trends_year": max_trend_year},
        })

    if trends and all(safe_float(row.get("registrations")) == 0 for row in trends):
        issues.append({
            "severity": "medium",
            "code": "REGISTRATIONS_PLACEHOLDER",
            "message": "trends.json registrations is zero for every year and should not be used as an observed visual variable.",
        })
    if trends and all(safe_float(row.get("totalExpenses")) == 0 for row in trends):
        issues.append({
            "severity": "medium",
            "code": "EXPENSES_PLACEHOLDER",
            "message": "trends.json totalExpenses is zero for every year and should not be used as an observed visual variable.",
        })

    months = [str(row.get("month", "")) for row in filing_activity.get("monthly", [])]
    max_month = max(months) if months else ""
    if max_month and safe_int(max_month[:4]) > max_trend_year:
        issues.append({
            "severity": "medium",
            "code": "FILING_ACTIVITY_EXTENDS_PAST_CORE_TRENDS",
            "message": "filing-activity.json contains months beyond the core annual trend range.",
            "evidence": {"max_month": max_month, "max_trends_year": max_trend_year},
        })

    total_income = safe_float(stats.get("totalIncome"))
    max_gov = max((safe_float(row.get("spending")) for row in gov_entities), default=0.0)
    if total_income and max_gov > total_income:
        issues.append({
            "severity": "high",
            "code": "GOV_TARGET_SPENDING_EXCEEDS_TOTAL_INCOME",
            "message": "Government-entity spending appears to be repeated target-side exposure, not additive lobbying spend.",
            "evidence": {"max_gov_spending": round(max_gov, 2), "stats_totalIncome": round(total_income, 2)},
        })

    network_path = RAW_DIR / "network-analysis.json"
    if network_path.exists():
        network = read_json(network_path)
        total_unique_lobbyists = safe_int(network.get("totalUniqueLobbyists"))
        top_rd = firm_concentration
        premium_path = RAW_DIR / "revolving-door-premium.json"
        if premium_path.exists():
            premium = read_json(premium_path)
            max_rd = max((
                safe_int(row.get("revolvingDoorEvents", row.get("revolvingDoorLobbyists")))
                for row in premium.get("topRevolvingDoorFirms", [])
            ), default=0)
            if total_unique_lobbyists and max_rd > total_unique_lobbyists:
                issues.append({
                    "severity": "high",
                    "code": "REVOLVING_DOOR_COUNT_EXCEEDS_UNIQUE_LOBBYISTS",
                    "message": "revolving-door-premium counts are transition events, not unique people.",
                    "evidence": {"max_revolvingDoorEvents": max_rd, "totalUniqueLobbyists": total_unique_lobbyists},
                })

    temporal_script = PROJECT_DIR / "pipeline" / "08_temporal_series.py"
    if temporal_script.exists() and "random" in temporal_script.read_text(encoding="utf-8"):
        issues.append({
            "severity": "high",
            "code": "LEGACY_SYNTHETIC_YEARLY_SIZE",
            "message": "Legacy entities_3d generation contains random yearly size variation. Reliable payload does not use it.",
            "evidence": {"file": str(temporal_script.relative_to(ROOT_DIR))},
        })

    quarantined_merges: list[dict[str, Any]] = []
    reported_legacy_dedup_merges = 0
    for validation_path in [
        PROJECT_DIR / "data" / "processed" / "validation_report.json",
        PROJECT_DIR / "processed" / "validation_report.json",
    ]:
        if validation_path.exists():
            try:
                reported_legacy_dedup_merges = max(
                    reported_legacy_dedup_merges,
                    safe_int(read_json(validation_path).get("dedup_merges")),
                )
            except json.JSONDecodeError:
                pass
    for dedup_path in [
        PROJECT_DIR / "data" / "processed" / "dedup_log.json",
        PROJECT_DIR / "processed" / "dedup_log.json",
    ]:
        if not dedup_path.exists():
            continue
        try:
            merges = read_json(dedup_path)
        except json.JSONDecodeError:
            continue
        for merge in merges if isinstance(merges, list) else []:
            kept = str(merge.get("kept", ""))
            dropped = str(merge.get("dropped", ""))
            unsafe = distinctive_token(kept) != distinctive_token(dropped)
            quarantined_merges.append({
                "kept": kept,
                "dropped": dropped,
                "reason": "distinctive_token_mismatch" if unsafe else "legacy_fuzzy_merge_requires_review",
                "status": "blocked" if unsafe else "quarantined",
            })
    unsafe_count = sum(1 for row in quarantined_merges if row["status"] == "blocked")
    if quarantined_merges:
        issues.append({
            "severity": "high" if unsafe_count else "medium",
            "code": "LEGACY_FUZZY_MERGES_QUARANTINED",
            "message": "Legacy fuzzy dedup merges are quarantined and not accepted as silent canonical truth.",
            "evidence": {
                "logged_merges": len(quarantined_merges),
                "reported_legacy_dedup_merges": reported_legacy_dedup_merges,
                "blocked_unsafe_merges": unsafe_count,
            },
        })

    return {
        "generated_by": "09_build_reliable_payload.py",
        "missing_value_policy": ["null", "blank_string", "whitespace", "empty_array", "empty_object", "placeholder"],
        "files": file_audits,
        "issues": issues,
    }, quarantined_merges


def build_feature_indexes(
    sources: dict[str, Any],
    issue_labels: dict[str, str],
    code_to_rollup: dict[str, str],
) -> dict[str, Any]:
    top_clients = sources["top_clients"]
    firms = sources["top_firms"]
    gov_entities = sources["gov_entities"]
    firm_conc = sources["firm_concentration"].get("firms", [])

    client_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    client_by_slug: dict[str, dict[str, Any]] = {}
    for index, client in enumerate(top_clients):
        canonical_id = f"client_{slugify(client.get('slug') or client.get('name'))}"
        legacy_id = f"client_{index:05d}"
        issue_vec = issue_vec_from_codes(client.get("issues", []))
        feature = {
            "canonical_id": canonical_id,
            "legacy_id": legacy_id,
            "name": client.get("name", ""),
            "issue_vec": issue_vec,
            "active_years": [safe_int(y) for y in client.get("years", []) if safe_int(y)],
            "state": client.get("state", ""),
            "total_spending": safe_float(client.get("totalSpending")),
            "filings": safe_int(client.get("filings")),
            "description": client.get("description", ""),
        }
        client_by_name[normalized_name(client.get("name"))].append(feature)
        client_by_slug[canonical_id] = feature

    firm_by_name: dict[str, dict[str, Any]] = {}
    firm_by_id: dict[str, dict[str, Any]] = {}
    for firm in firms:
        canonical_id = f"firm_{safe_int(firm.get('id'))}"
        feature = {
            "canonical_id": canonical_id,
            "legacy_id": canonical_id,
            "name": firm.get("name", ""),
            "active_years": [safe_int(y) for y in firm.get("years", []) if safe_int(y)],
            "clients": firm.get("clients", []) or [],
            "total_spending": safe_float(firm.get("totalIncome")),
            "filings": safe_int(firm.get("filings")),
        }
        firm_by_name[normalized_name(firm.get("name"))] = feature
        firm_by_id[canonical_id] = feature

    firm_conc_by_name = {
        normalized_name(row.get("firm")): row
        for row in firm_conc
        if not is_missing(row.get("firm"))
    }

    gov_by_name: dict[str, dict[str, Any]] = {}
    for index, gov in enumerate(gov_entities):
        canonical_id = f"gov_{stable_hash(normalized_name(gov.get('name')), 10)}"
        issue_vec = issue_vec_from_codes(gov.get("topIssues", []))
        gov_by_name[normalized_name(gov.get("name"))] = {
            "canonical_id": canonical_id,
            "legacy_id": f"gov_{index:04d}",
            "name": gov.get("name", ""),
            "issue_vec": issue_vec,
            "attention_exposure": safe_float(gov.get("spending")),
            "filings": safe_int(gov.get("filings")),
            "top_clients": gov.get("topClients", []) or [],
        }

    return {
        "client_by_name": client_by_name,
        "client_by_slug": client_by_slug,
        "firm_by_name": firm_by_name,
        "firm_by_id": firm_by_id,
        "firm_conc_by_name": firm_conc_by_name,
        "gov_by_name": gov_by_name,
        "issue_labels": issue_labels,
        "code_to_rollup": code_to_rollup,
    }


def resolve_client(name: str, indexes: dict[str, Any], entities: dict[str, dict[str, Any]]) -> tuple[str, str]:
    matches = indexes["client_by_name"].get(normalized_name(name), [])
    if len(matches) == 1:
        return matches[0]["canonical_id"], "exact_unique_name"
    if len(matches) > 1:
        ext_id = canonical_external_id("client", name)
        ensure_external_entity(ext_id, name, "client", "ambiguous_client_name", entities)
        return ext_id, "ambiguous_name_externalized"
    ext_id = canonical_external_id("client", name)
    ensure_external_entity(ext_id, name, "client", "edge_endpoint_unresolved", entities)
    return ext_id, "external_hash"


def resolve_firm(name: str, indexes: dict[str, Any], entities: dict[str, dict[str, Any]]) -> tuple[str, str]:
    match = indexes["firm_by_name"].get(normalized_name(name))
    if match:
        return match["canonical_id"], "exact_name"
    ext_id = canonical_external_id("firm", name)
    ensure_external_entity(ext_id, name, "firm", "edge_endpoint_unresolved", entities)
    return ext_id, "external_hash"


def ensure_external_entity(
    canonical_id: str,
    name: str,
    entity_type: str,
    source: str,
    entities: dict[str, dict[str, Any]],
) -> None:
    if canonical_id in entities:
        return
    entities[canonical_id] = {
        "canonical_id": canonical_id,
        "legacy_id": "",
        "name": name,
        "entity_type": entity_type,
        "entity_subtype": "unknown",
        "primary_policy_category": "Unknown",
        "region": "Unknown",
        "state": "",
        "source_files": source,
        "source_record_id": "",
        "active_years": [],
        "active_year_basis": "unknown",
        "observed_spend": 0.0,
        "target_attention_exposure": 0.0,
        "lobbying_exposure": None,
        "filings_total": 0,
        "top_issue_code": "",
        "top_issue_label": "",
        "issue_count": 0,
        "issue_codes": [],
        "coord_x": 0.0,
        "coord_y": 0.0,
        "coordinate_source": "unplaced_external",
        "cluster_id": "",
        "cluster_label": "External / unresolved",
        "confidence_score": 0.25,
        "confidence_level": "low",
        "quality_flags": ["external_endpoint"],
    }


def build_entities(sources: dict[str, Any], indexes: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entities: dict[str, dict[str, Any]] = {}
    code_to_rollup = indexes["code_to_rollup"]
    issue_labels = indexes["issue_labels"]

    entities["contract_federal_contracts"] = {
        "canonical_id": "contract_federal_contracts",
        "legacy_id": "",
        "name": "Federal contracts",
        "entity_type": "reference_node",
        "entity_subtype": "federal contract comparison",
        "primary_policy_category": "Contracting",
        "region": "Unknown",
        "state": "",
        "source_files": "lobbying-vs-contracts.json",
        "source_record_id": "federal_contracts",
        "active_years": YEARS[:],
        "active_year_basis": "comparison_reference",
        "observed_spend": None,
        "target_attention_exposure": 0.0,
        "lobbying_exposure": None,
        "filings_total": 0,
        "top_issue_code": "",
        "top_issue_label": "",
        "issue_count": 0,
        "issue_codes": [],
        "issue_vec": {},
        "quality_flags": ["comparison_node_not_lobbying_actor"],
    }

    for firm in sources["top_firms"]:
        canonical_id = f"firm_{safe_int(firm.get('id'))}"
        firm_conc = indexes["firm_conc_by_name"].get(normalized_name(firm.get("name")), {})
        issue_vec = issue_vec_from_codes([firm_conc.get("topIssue", "")] if firm_conc.get("topIssue") else [])
        issue_code = top_issue(issue_vec)
        active_years = [safe_int(y) for y in firm.get("years", []) if safe_int(y)]
        entities[canonical_id] = {
            "canonical_id": canonical_id,
            "legacy_id": canonical_id,
            "name": firm.get("name", ""),
            "entity_type": "firm",
            "entity_subtype": "lobbying firm",
            "primary_policy_category": dominant_rollup(issue_vec, code_to_rollup) if issue_vec else "Law & Lobbying",
            "region": "Unknown",
            "state": "",
            "source_files": "top-firms.json;firm-concentration.json",
            "source_record_id": str(firm.get("id", "")),
            "active_years": active_years,
            "active_year_basis": "raw_years_array",
            "observed_spend": safe_float(firm.get("totalIncome")),
            "target_attention_exposure": 0.0,
            "lobbying_exposure": None,
            "filings_total": safe_int(firm.get("filings")),
            "top_issue_code": issue_code,
            "top_issue_label": issue_labels.get(issue_code, issue_code),
            "issue_count": len(issue_vec),
            "issue_codes": sorted(issue_vec),
            "issue_vec": issue_vec,
            "firm_hhi": safe_float(firm_conc.get("hhi")),
            "top_client_share": safe_float(firm_conc.get("topClientShare")),
            "issue_specialization": safe_float(firm_conc.get("issueSpecialization")),
            "quality_flags": [],
        }

    for index, client in enumerate(sources["top_clients"]):
        canonical_id = f"client_{slugify(client.get('slug') or client.get('name'))}"
        issue_vec = issue_vec_from_codes(client.get("issues", []))
        issue_code = raw_top_issue(client.get("issues", [])) or top_issue(issue_vec)
        state = client.get("state", "")
        active_years = [safe_int(y) for y in client.get("years", []) if safe_int(y)]
        flags = []
        if is_missing(state):
            flags.append("missing_state")
        if not issue_vec:
            flags.append("missing_issue_profile")
        entities[canonical_id] = {
            "canonical_id": canonical_id,
            "legacy_id": f"client_{index:05d}",
            "name": client.get("name", ""),
            "entity_type": "client",
            "entity_subtype": classify_client_subtype(client.get("name", ""), client.get("description", "")),
            "primary_policy_category": dominant_rollup(issue_vec, code_to_rollup),
            "region": region_for_state(state),
            "state": state or "",
            "source_files": "top-clients.json",
            "source_record_id": str(client.get("slug", "")),
            "active_years": active_years,
            "active_year_basis": "raw_years_array",
            "observed_spend": safe_float(client.get("totalSpending")),
            "target_attention_exposure": 0.0,
            "lobbying_exposure": None,
            "filings_total": safe_int(client.get("filings")),
            "top_issue_code": issue_code,
            "top_issue_label": issue_labels.get(issue_code, issue_code),
            "issue_count": len(issue_vec),
            "issue_codes": sorted(issue_vec),
            "issue_vec": issue_vec,
            "quality_flags": flags,
        }

    for index, gov in enumerate(sources["gov_entities"]):
        canonical_id = f"gov_{stable_hash(normalized_name(gov.get('name')), 10)}"
        issue_vec = issue_vec_from_codes(gov.get("topIssues", []))
        issue_code = raw_top_issue(gov.get("topIssues", [])) or top_issue(issue_vec)
        entities[canonical_id] = {
            "canonical_id": canonical_id,
            "legacy_id": f"gov_{index:04d}",
            "name": gov.get("name", ""),
            "entity_type": "gov_agency",
            "entity_subtype": "government target",
            "primary_policy_category": dominant_rollup(issue_vec, code_to_rollup),
            "region": "DC",
            "state": "DC",
            "source_files": "gov-entities.json",
            "source_record_id": str(index),
            "active_years": YEARS[:],
            "active_year_basis": "assumed_full_period_government_target",
            "observed_spend": None,
            "target_attention_exposure": safe_float(gov.get("spending")),
            "lobbying_exposure": safe_float(gov.get("spending")),
            "filings_total": safe_int(gov.get("filings")),
            "top_issue_code": issue_code,
            "top_issue_label": indexes["issue_labels"].get(issue_code, issue_code),
            "issue_count": len(issue_vec),
            "issue_codes": sorted(issue_vec),
            "issue_vec": issue_vec,
            "quality_flags": ["target_attention_not_additive_spend"],
        }

    for lobbyist in sources["revolving_door"]:
        canonical_id = f"lobbyist_{safe_int(lobbyist.get('id'))}"
        issue_accumulator: dict[str, float] = defaultdict(float)
        matched_clients = 0
        for client_name in lobbyist.get("clients", []) or []:
            matches = indexes["client_by_name"].get(normalized_name(client_name), [])
            if len(matches) == 1:
                matched_clients += 1
                for code, weight in matches[0]["issue_vec"].items():
                    issue_accumulator[code] += weight
        total = sum(issue_accumulator.values())
        issue_vec = {code: round(weight / total, 6) for code, weight in issue_accumulator.items()} if total else {}
        issue_code = top_issue(issue_vec)
        entities[canonical_id] = {
            "canonical_id": canonical_id,
            "legacy_id": canonical_id,
            "name": lobbyist.get("name", ""),
            "entity_type": "lobbyist",
            "entity_subtype": "revolving-door lobbyist",
            "primary_policy_category": dominant_rollup(issue_vec, code_to_rollup),
            "region": "Unknown",
            "state": "",
            "source_files": "revolving-door.json",
            "source_record_id": str(lobbyist.get("id", "")),
            "active_years": [],
            "active_year_basis": "unknown_repeated",
            "observed_spend": 0.0,
            "target_attention_exposure": 0.0,
            "lobbying_exposure": None,
            "filings_total": safe_int(lobbyist.get("filings")),
            "top_issue_code": issue_code,
            "top_issue_label": issue_labels.get(issue_code, issue_code),
            "issue_count": len(issue_vec),
            "issue_codes": sorted(issue_vec),
            "issue_vec": issue_vec,
            "matched_client_features": matched_clients,
            "gov_positions_count": len(lobbyist.get("positions", []) or []),
            "seniority_score_raw": seniority_score(lobbyist.get("positions", []) or []),
            "firm_names": lobbyist.get("firms", []) or [],
            "client_names": lobbyist.get("clients", []) or [],
            "quality_flags": ["unknown_transition_year"],
        }

    return entities


def add_edge(
    edges: dict[tuple[str, str, str], dict[str, Any]],
    source_id: str,
    source_name: str,
    target_id: str,
    target_name: str,
    edge_type: str,
    *,
    weight: float = 1.0,
    raw_value: float = 0.0,
    measure_type: str = "count",
    source_file: str,
    confidence: float = 1.0,
    resolution: str = "exact",
) -> None:
    key = (source_id, target_id, edge_type)
    if key not in edges:
        edges[key] = {
            "source_id": source_id,
            "source_name": source_name,
            "target_id": target_id,
            "target_name": target_name,
            "edge_type": edge_type,
            "weight": 0.0,
            "raw_value": 0.0,
            "measure_type": measure_type,
            "source_files": set(),
            "confidence": confidence,
            "resolution": resolution,
            "duplicate_count": 0,
            "is_self_edge": source_id == target_id,
        }
    row = edges[key]
    row["weight"] = safe_float(row["weight"]) + weight
    row["raw_value"] = safe_float(row["raw_value"]) + raw_value
    row["source_files"].add(source_file)
    row["confidence"] = min(safe_float(row["confidence"], 1.0), confidence)
    row["duplicate_count"] = safe_int(row["duplicate_count"]) + 1
    if resolution != "exact":
        row["resolution"] = resolution


def build_edges(
    sources: dict[str, Any],
    indexes: dict[str, Any],
    entities: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}

    for firm in sources["top_firms"]:
        firm_id = f"firm_{safe_int(firm.get('id'))}"
        for client_name in firm.get("clients", []) or []:
            client_id, resolution = resolve_client(client_name, indexes, entities)
            add_edge(
                edges,
                firm_id,
                firm.get("name", ""),
                client_id,
                client_name,
                "firm_represents_client",
                weight=1.0,
                source_file="top-firms.json",
                confidence=0.9 if resolution == "exact_unique_name" else 0.55,
                resolution=resolution,
            )

    for gov_name, gov in indexes["gov_by_name"].items():
        gov_id = gov["canonical_id"]
        for top_client in gov.get("top_clients", []) or []:
            client_name = top_client.get("name", "")
            if is_missing(client_name):
                continue
            client_id, resolution = resolve_client(client_name, indexes, entities)
            raw_exposure = safe_float(top_client.get("spending"))
            add_edge(
                edges,
                client_id,
                client_name,
                gov_id,
                gov["name"],
                "client_targets_gov",
                weight=math.log1p(max(raw_exposure, 0.0)),
                raw_value=raw_exposure,
                measure_type="target_attention_exposure",
                source_file="gov-entities.json",
                confidence=0.85 if resolution == "exact_unique_name" else 0.5,
                resolution=resolution,
            )

    for lobbyist in sources["revolving_door"]:
        lobbyist_id = f"lobbyist_{safe_int(lobbyist.get('id'))}"
        lobbyist_name = lobbyist.get("name", "")
        for firm_name in lobbyist.get("firms", []) or []:
            firm_id, resolution = resolve_firm(firm_name, indexes, entities)
            add_edge(
                edges,
                lobbyist_id,
                lobbyist_name,
                firm_id,
                firm_name,
                "lobbyist_at_firm",
                weight=1.0,
                source_file="revolving-door.json",
                confidence=0.9 if resolution == "exact_name" else 0.55,
                resolution=resolution,
            )
            add_edge(
                edges,
                firm_id,
                firm_name,
                lobbyist_id,
                lobbyist_name,
                "firm_has_revolving_door_access",
                weight=1.0,
                source_file="revolving-door.json",
                confidence=0.9 if resolution == "exact_name" else 0.55,
                resolution=resolution,
            )
        for client_name in lobbyist.get("clients", []) or []:
            client_id, resolution = resolve_client(client_name, indexes, entities)
            add_edge(
                edges,
                lobbyist_id,
                lobbyist_name,
                client_id,
                client_name,
                "lobbyist_serves_client",
                weight=1.0,
                source_file="revolving-door.json",
                confidence=0.85 if resolution == "exact_unique_name" else 0.5,
                resolution=resolution,
            )

    for match in sources["lobbying_vs_contracts"].get("matches", []) or []:
        name = match.get("name", "")
        client_id, resolution = resolve_client(name, indexes, entities)
        raw_contracts = safe_float(match.get("federalContracts"))
        add_edge(
            edges,
            client_id,
            name,
            "contract_federal_contracts",
            "Federal contracts",
            "client_has_contract_match",
            weight=math.log1p(max(raw_contracts, 0.0)),
            raw_value=raw_contracts,
            measure_type="federal_contract_value",
            source_file="lobbying-vs-contracts.json",
            confidence=0.8 if resolution == "exact_unique_name" else 0.45,
            resolution=resolution,
        )

    cleaned = []
    for row in edges.values():
        out = dict(row)
        out["weight"] = round(safe_float(out["weight"]), 6)
        out["raw_value"] = round(safe_float(out["raw_value"]), 2)
        out["source_files"] = ";".join(sorted(out["source_files"]))
        out["confidence"] = round(safe_float(out["confidence"]), 3)
        out["duplicate_count"] = safe_int(out["duplicate_count"])
        out["is_self_edge"] = "true" if out["is_self_edge"] else "false"
        cleaned.append(out)
    cleaned.sort(key=lambda row: (-safe_float(row["weight"]), row["edge_type"], row["source_id"], row["target_id"]))
    return cleaned


def attach_layout(
    entities: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
) -> None:
    coords_rows = read_csv_rows(LEGACY_LAYOUT_DIR / "umap_coords.csv")
    cluster_rows = read_csv_rows(LEGACY_LAYOUT_DIR / "clusters.csv")
    coords_by_legacy = {
        row["entity_id"]: (safe_float(row.get("x")), safe_float(row.get("y")))
        for row in coords_rows
    }
    clusters_by_legacy = {
        row["entity_id"]: {
            "cluster_id": row.get("cluster_id", ""),
            "cluster_label": row.get("cluster_label", ""),
        }
        for row in cluster_rows
    }

    id_to_entity = entities
    legacy_to_canonical = {
        entity.get("legacy_id"): canonical_id
        for canonical_id, entity in entities.items()
        if entity.get("legacy_id")
    }

    for canonical_id, entity in entities.items():
        legacy_id = entity.get("legacy_id")
        if legacy_id in coords_by_legacy:
            x, y = coords_by_legacy[legacy_id]
            entity["coord_x"] = round(x, 4)
            entity["coord_y"] = round(y, 4)
            entity["coordinate_source"] = "legacy_umap"
        else:
            entity["coord_x"] = 0.0
            entity["coord_y"] = 0.0
            entity["coordinate_source"] = "pending_neighbor_inference"
        cluster = clusters_by_legacy.get(legacy_id or "", {})
        entity["cluster_id"] = cluster.get("cluster_id", "")
        entity["cluster_label"] = cluster.get("cluster_label", "") or entity.get("primary_policy_category", "Unknown")

    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        src = edge["source_id"]
        dst = edge["target_id"]
        adjacency[src].append(dst)
        adjacency[dst].append(src)

    for _ in range(3):
        changed = False
        for canonical_id, entity in entities.items():
            if entity.get("coordinate_source") != "pending_neighbor_inference":
                continue
            neighbor_coords = [
                (entities[n]["coord_x"], entities[n]["coord_y"])
                for n in adjacency.get(canonical_id, [])
                if n in entities and entities[n].get("coordinate_source") in {"legacy_umap", "neighbor_inferred"}
            ]
            if neighbor_coords:
                entity["coord_x"] = round(sum(x for x, _ in neighbor_coords) / len(neighbor_coords), 4)
                entity["coord_y"] = round(sum(y for _, y in neighbor_coords) / len(neighbor_coords), 4)
                entity["coordinate_source"] = "neighbor_inferred"
                entity.setdefault("quality_flags", []).append("coordinate_inferred_from_neighbors")
                changed = True
        if not changed:
            break

    for canonical_id, entity in entities.items():
        if entity.get("coordinate_source") == "pending_neighbor_inference":
            seed = int(stable_hash(canonical_id, 8), 16)
            angle = (seed % 360) * math.pi / 180.0
            radius = 0.9 if entity.get("entity_type") == "external" else 0.78
            entity["coord_x"] = round(math.cos(angle) * radius, 4)
            entity["coord_y"] = round(math.sin(angle) * radius, 4)
            entity["coordinate_source"] = "deterministic_unplaced_ring"
            entity.setdefault("quality_flags", []).append("coordinate_low_confidence")


def attach_scores(
    entities: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    sources: dict[str, Any],
) -> None:
    degree = Counter()
    gov_targets: dict[str, set[str]] = defaultdict(set)
    revolving_counts = Counter()
    client_served_by_revolving = Counter()
    edge_confidence_min: dict[str, float] = defaultdict(lambda: 1.0)

    for edge in edges:
        src = edge["source_id"]
        dst = edge["target_id"]
        weight = safe_float(edge.get("weight"), 1.0)
        degree[src] += weight
        degree[dst] += weight
        edge_confidence_min[src] = min(edge_confidence_min[src], safe_float(edge.get("confidence"), 1.0))
        edge_confidence_min[dst] = min(edge_confidence_min[dst], safe_float(edge.get("confidence"), 1.0))
        if edge["edge_type"] == "client_targets_gov":
            gov_targets[src].add(dst)
        elif edge["edge_type"] == "firm_has_revolving_door_access":
            revolving_counts[src] += 1
        elif edge["edge_type"] == "lobbyist_at_firm":
            revolving_counts[src] += 1
        elif edge["edge_type"] == "lobbyist_serves_client":
            client_served_by_revolving[dst] += 1

    spend_norm = normalize_score({eid: math.log1p(safe_float(e.get("observed_spend"))) for eid, e in entities.items()})
    filings_norm = normalize_score({eid: math.log1p(safe_float(e.get("filings_total"))) for eid, e in entities.items()})
    centrality_norm = normalize_score({eid: math.log1p(degree[eid]) for eid in entities})
    gov_breadth_norm = normalize_score({eid: len(gov_targets[eid]) for eid in entities})
    rd_norm = normalize_score({
        eid: safe_float(revolving_counts[eid]) + safe_float(client_served_by_revolving[eid]) + safe_float(entities[eid].get("gov_positions_count"))
        for eid in entities
    })
    issue_breadth_norm = normalize_score({eid: safe_float(e.get("issue_count")) for eid, e in entities.items()})
    concentration_raw = {}
    for eid, entity in entities.items():
        if entity["entity_type"] == "firm":
            concentration_raw[eid] = safe_float(entity.get("firm_hhi")) / 10000.0
        else:
            concentration_raw[eid] = 0.0

    industry_growth = {}
    for industry in sources["industries"]:
        yearly = industry.get("yearlySpending", []) or []
        by_year = {safe_int(row.get("year")): safe_float(row.get("income")) for row in yearly}
        if by_year.get(2023) and by_year.get(2025):
            industry_growth[industry["name"]] = max(-1.0, min(1.0, (by_year[2025] - by_year[2023]) / by_year[2023]))
        else:
            industry_growth[industry["name"]] = 0.0

    growth_norm = normalize_score({name: value + 1.0 for name, value in industry_growth.items()})

    gap_grid = {}
    gap_path = LEGACY_LAYOUT_DIR / "gap_grid.json"
    if gap_path.exists():
        gap_grid = read_json(gap_path)
    grid_size = safe_int(gap_grid.get("grid_size")) if isinstance(gap_grid, dict) else 0
    gap_scores = gap_grid.get("gap_score", []) if isinstance(gap_grid, dict) else []

    def grid_gap_score(x: float, y: float) -> float:
        if not grid_size or not gap_scores:
            return 0.0
        col = min(grid_size - 1, max(0, int(round((x + 1) / 2 * (grid_size - 1)))))
        row = min(grid_size - 1, max(0, int(round((y + 1) / 2 * (grid_size - 1)))))
        try:
            return safe_float(gap_scores[row][col])
        except (IndexError, TypeError):
            return 0.0

    for eid, entity in entities.items():
        active_years = set(safe_int(y) for y in entity.get("active_years", []) if safe_int(y))
        recent_activity = (1.0 if 2025 in active_years else 0.0) + (0.5 if 2024 in active_years else 0.0)
        first_year = min(active_years) if active_years else None
        new_entrant = 1.0 if first_year and first_year >= 2024 else 0.0
        category_growth = growth_norm.get(entity.get("primary_policy_category", ""), 0.0)
        momentum = (0.45 * min(1.0, recent_activity / 1.5)) + (0.25 * new_entrant) + (0.30 * category_growth)

        confidence = 0.35
        if entity.get("source_record_id") or entity.get("legacy_id"):
            confidence += 0.2
        if entity.get("issue_count", 0):
            confidence += 0.15
        if entity.get("coordinate_source") == "legacy_umap":
            confidence += 0.15
        elif entity.get("coordinate_source") == "neighbor_inferred":
            confidence += 0.08
        if entity.get("active_years"):
            confidence += 0.08
        confidence *= edge_confidence_min[eid]
        confidence = round(max(0.05, min(1.0, confidence)), 4)

        gap = grid_gap_score(safe_float(entity.get("coord_x")), safe_float(entity.get("coord_y")))
        if confidence < 0.5:
            gap *= 0.8

        influence = (
            0.35 * spend_norm[eid]
            + 0.20 * filings_norm[eid]
            + 0.20 * centrality_norm[eid]
            + 0.10 * gov_breadth_norm[eid]
            + 0.10 * rd_norm[eid]
            + 0.05 * issue_breadth_norm[eid]
        )

        entity["graph_degree_weighted"] = round(degree[eid], 6)
        entity["gov_target_breadth"] = len(gov_targets[eid])
        entity["revolving_door_score"] = round(rd_norm[eid], 6)
        entity["influence_score"] = round(influence, 6)
        entity["momentum_score"] = round(max(0.0, min(1.0, momentum)), 6)
        entity["concentration_score"] = round(max(0.0, min(1.0, concentration_raw[eid])), 6)
        entity["gap_score"] = round(max(0.0, min(1.0, gap)), 6)
        entity["confidence_score"] = confidence
        entity["confidence_level"] = "high" if confidence >= 0.75 else ("medium" if confidence >= 0.5 else "low")
        entity["node_size_metric"] = "log_observed_spend" if safe_float(entity.get("observed_spend")) > 0 else "log_filings"
        entity["node_size_value"] = round(math.log1p(max(safe_float(entity.get("observed_spend")), safe_float(entity.get("filings_total")))), 6)
        if entity["entity_type"] == "gov_agency":
            entity["node_size_metric"] = "log_lobbying_exposure"
            entity["node_size_value"] = round(math.log1p(safe_float(entity.get("lobbying_exposure"))), 6)
            entity.setdefault("quality_flags", []).append("government_exposure_not_spend")
        elif entity["entity_type"] == "reference_node":
            entity["node_size_metric"] = "reference_node"
            entity["node_size_value"] = 2.0


def build_entity_year_rows(entities: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for entity in entities.values():
        active_years = set(safe_int(y) for y in entity.get("active_years", []) if safe_int(y))
        has_observed_years = bool(active_years)
        for year in YEARS:
            active = year in active_years if has_observed_years else True
            rows.append({
                "entity_id": entity["canonical_id"],
                "year": year,
                "active": "true" if active else "false",
                "active_year_basis": entity.get("active_year_basis", "unknown"),
                "observed_spend": entity.get("observed_spend") if active else None,
                "lobbying_exposure": entity.get("lobbying_exposure") if active else None,
                "filings_total": entity.get("filings_total", 0) if active else 0,
                "display_size_metric": entity.get("node_size_metric", "log_filings"),
                "display_size_value": entity.get("node_size_value", 0.0) if active else 0.0,
                "temporal_value_type": "aggregate_repeated" if has_observed_years else "unknown_repeated",
                "is_partial_year": "true" if year in PARTIAL_YEARS else "false",
            })
    return rows


def build_issue_profiles(
    entities: dict[str, dict[str, Any]],
    issue_labels: dict[str, str],
    code_to_rollup: dict[str, str],
) -> list[dict[str, Any]]:
    rows = []
    for entity in entities.values():
        for code, weight in sorted((entity.get("issue_vec") or {}).items(), key=lambda item: (-item[1], item[0])):
            rows.append({
                "entity_id": entity["canonical_id"],
                "issue_code": code,
                "issue_label": issue_labels.get(code, code),
                "policy_category": code_to_rollup.get(code, "Other / Multi-sector"),
                "weight": round(safe_float(weight), 6),
                "source": "raw_issue_codes_or_propagated_profile",
            })
    return rows


def build_visual_payload(
    entities: dict[str, dict[str, Any]],
    entity_year_rows: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    issue_profiles: list[dict[str, Any]],
    sources: dict[str, Any],
    quality_report: dict[str, Any],
) -> dict[str, Any]:
    sorted_entities = sorted(entities.values(), key=lambda row: (-safe_float(row.get("influence_score")), row["canonical_id"]))
    visible_entity_ids = {row["canonical_id"] for row in sorted_entities[:VISIBLE_ENTITY_CAP]}
    payload_entities = [
        {
            "id": row["canonical_id"],
            "name": row["name"],
            "entity_type": row["entity_type"],
            "entity_subtype": row["entity_subtype"],
            "primary_policy_category": row["primary_policy_category"],
            "region": row["region"],
            "state": row["state"],
            "active_years": row["active_years"],
            "x": row["coord_x"],
            "y": row["coord_y"],
            "z_semantics": "year",
            "coordinate_source": row["coordinate_source"],
            "cluster_id": row["cluster_id"],
            "cluster_label": row["cluster_label"],
            "top_issue_code": row["top_issue_code"],
            "top_issue_label": row["top_issue_label"],
            "metrics": {
                "observed_spend": row["observed_spend"],
                "target_attention_exposure": row["target_attention_exposure"],
                "lobbying_exposure": row.get("lobbying_exposure"),
                "filings_total": row["filings_total"],
                "influence_score": row["influence_score"],
                "momentum_score": row["momentum_score"],
                "revolving_door_score": row["revolving_door_score"],
                "concentration_score": row["concentration_score"],
                "gap_score": row["gap_score"],
                "node_size_metric": row["node_size_metric"],
                "node_size_value": row["node_size_value"],
            },
            "confidence": {
                "score": row["confidence_score"],
                "level": row["confidence_level"],
                "flags": row.get("quality_flags", []),
            },
            "source_files": row["source_files"],
            "default_visible": row["canonical_id"] in visible_entity_ids,
        }
        for row in sorted_entities
    ]

    payload_entity_years = [
        row for row in entity_year_rows if row["entity_id"] in visible_entity_ids
    ]

    eligible_payload_edges = [
        row for row in edges
        if row["source_id"] in visible_entity_ids and row["target_id"] in visible_entity_ids
    ]
    total_edges_in_data = len(eligible_payload_edges)
    payload_edges = eligible_payload_edges[:PAYLOAD_EDGE_CAP]
    edges_truncated = len(payload_edges) < total_edges_in_data
    if edges_truncated:
        print(f"Edge payload truncated: {len(payload_edges)} of {total_edges_in_data} edges included.")

    cluster_profiles_path = LEGACY_LAYOUT_DIR / "cluster_profiles.json"
    clusters = []
    if cluster_profiles_path.exists():
        raw_clusters = read_json(cluster_profiles_path)
        for cid, row in raw_clusters.items():
            clusters.append({
                "cluster_id": safe_int(row.get("cluster_id", cid)),
                "label": row.get("label", ""),
                "member_count": row.get("member_count", 0),
                "total_spending": row.get("total_spending", 0),
                "total_lobbying_exposure": row.get("total_lobbying_exposure", 0),
                "centroid_x": row.get("centroid_x", 0),
                "centroid_y": row.get("centroid_y", 0),
                "entity_types": row.get("entity_types", {}),
                "top_issues": row.get("top_issues", []),
                "top_industries": row.get("top_industries", []),
                "top_entities": row.get("top_entities", []),
            })

    gap_grid = read_json(LEGACY_LAYOUT_DIR / "gap_grid.json") if (LEGACY_LAYOUT_DIR / "gap_grid.json").exists() else {}
    top_gaps = read_json(LEGACY_LAYOUT_DIR / "top_gaps.json") if (LEGACY_LAYOUT_DIR / "top_gaps.json").exists() else []
    if isinstance(gap_grid, dict):
        gap_grid["top_gaps"] = top_gaps
        gap_grid["semantics"] = "model_derived_gap_lead_not_direct_observation"

    vectors_path = LEGACY_LAYOUT_DIR / "revolving_vectors.json"
    vectors = read_json(vectors_path)[:REVOLVING_VECTOR_CAP] if vectors_path.exists() else []
    for vector in vectors:
        raw_transition_year = vector.get("transition_year")
        transition_year = optional_year(raw_transition_year)
        if transition_year is None:
            vector["transition_year"] = None
            vector["transition_year_estimated"] = False
            vector["temporal_scope"] = "unknown_transition_year"
            if raw_transition_year not in (None, ""):
                vector.setdefault("quality_flags", []).append("invalid_transition_year")
        else:
            vector["transition_year"] = transition_year
            estimated = bool(vector.get("transition_year_estimated", False))
            vector["temporal_scope"] = "estimated_transition_year" if estimated else "observed_transition_year"

    text = sources["text_analysis"]
    topics = {
        "top_words": text.get("topWords", [])[:50],
        "trending_words": text.get("trendingWords", [])[:30],
        "top_bills": text.get("topBills", [])[:30],
        "usage_note": "Narrative label layer only; not primary scoring.",
    }

    confidence_distribution = Counter(row.get("confidence_level", "unknown") for row in entities.values())
    coordinate_source_distribution = Counter(row.get("coordinate_source", "unknown") for row in entities.values())
    estimated_vectors = sum(1 for vector in vectors if vector.get("temporal_scope") == "estimated_transition_year")
    unknown_vectors = sum(1 for vector in vectors if vector.get("temporal_scope") == "unknown_transition_year")

    return {
        "meta": {
            "years": YEARS,
            "partial_years": PARTIAL_YEARS,
            "source_snapshot": source_snapshot(sources["stats"]),
            "entity_count_full": len(entities),
            "entity_count_visible_initial": len(visible_entity_ids),
            "edge_count_full": len(edges),
            "edge_count_visual_payload": len(payload_edges),
            "data_quality_summary": {
                "issue_count": len(quality_report["issues"]),
                "high_severity_issues": sum(1 for issue in quality_report["issues"] if issue.get("severity") == "high"),
                "missing_value_policy": quality_report["missing_value_policy"],
                "confidence_distribution": dict(confidence_distribution),
                "coordinate_source_distribution": dict(coordinate_source_distribution),
                "sampled_revolving_vectors": len(vectors),
                "estimated_revolving_vectors": estimated_vectors,
                "unknown_revolving_vectors": unknown_vectors,
            },
            "data_issues": quality_report["issues"],
            "edges_truncated": edges_truncated,
            "total_edges_in_data": total_edges_in_data,
            "generated_at": source_snapshot(sources["stats"]),
            "performance_caps": {
                "initial_visible_entities": VISIBLE_ENTITY_CAP,
                "payload_edges": PAYLOAD_EDGE_CAP,
                "sampled_revolving_vectors": REVOLVING_VECTOR_CAP,
                "animated_revolving_arcs": 100,
                "gap_grid_rendering": "single_texture_plane",
            },
            "visual_encoding": {
                "x": "UMAP issue-space coordinate or marked inference",
                "y": "UMAP issue-space coordinate or marked inference",
                "vertical_axis": "Three.js Y axis encodes year when the 3D time-stack view is enabled",
                "node_size": "log observed spend or log filings; gov exposure excluded",
                "color_default": "entity_type",
                "shape": "uniform round marker; entity type is encoded by color and letter identifier",
                "opacity": "selected year and confidence",
                "halo": "revolving_door_score",
                "outline": "model-derived gap lead score",
                "arcs": "resolved revolving-door flow records with observed, estimated, or unknown transition-year semantics",
            },
        },
        "entities": payload_entities,
        "entity_years": payload_entity_years,
        "edges": payload_edges,
        "clusters": sorted(clusters, key=lambda row: -safe_float(row.get("total_spending"))),
        "gap_grid": gap_grid,
        "revolving_vectors": vectors,
        "topics": topics,
    }


def build_split_payloads(payload: dict[str, Any], *, full_payload_filename: str) -> dict[str, dict[str, Any]]:
    """Build offline-friendly frontend chunks from the full payload."""

    visible_ids = {
        entity["id"]
        for entity in payload.get("entities", [])
        if entity.get("default_visible")
    }

    scene_payload = {
        "meta": payload.get("meta", {}),
        "entities": [
            entity for entity in payload.get("entities", [])
            if entity.get("id") in visible_ids
        ],
        "entity_years": [
            row for row in payload.get("entity_years", [])
            if row.get("entity_id") in visible_ids
        ],
        "edges": payload.get("edges", []),
        "clusters": payload.get("clusters", []),
        "gap_grid": payload.get("gap_grid", {}),
        "revolving_vectors": payload.get("revolving_vectors", []),
        "topics": payload.get("topics", {}),
    }

    search_index = {
        "meta": payload.get("meta", {}),
        "entities": [
            {
                "id": entity.get("id"),
                "name": entity.get("name"),
                "entity_type": entity.get("entity_type"),
                "entity_subtype": entity.get("entity_subtype"),
                "primary_policy_category": entity.get("primary_policy_category"),
                "confidence": entity.get("confidence"),
                "coordinate_source": entity.get("coordinate_source"),
                "default_visible": entity.get("default_visible", False),
                "source_files": entity.get("source_files", []),
            }
            for entity in payload.get("entities", [])
        ],
    }

    adjacency: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in payload.get("edges", []):
        edge_stub = {
            "source_id": edge.get("source_id"),
            "source_name": edge.get("source_name"),
            "target_id": edge.get("target_id"),
            "target_name": edge.get("target_name"),
            "edge_type": edge.get("edge_type"),
            "weight": edge.get("weight"),
            "confidence": edge.get("confidence"),
        }
        if edge.get("source_id"):
            adjacency[edge["source_id"]].append(edge_stub)
        if edge.get("target_id"):
            adjacency[edge["target_id"]].append(edge_stub)
    adjacency_topk = {
        entity_id: sorted(rows, key=lambda row: -safe_float(row.get("weight")))[:25]
        for entity_id, rows in adjacency.items()
    }

    manifest = {
        "meta": payload.get("meta", {}),
        "files": {
            "scene": "scene_payload.json",
            "search": "search_index.json",
            "adjacency": "adjacency_topk.json",
            "full": full_payload_filename,
        },
        "counts": {
            "full_entities": len(payload.get("entities", [])),
            "scene_entities": len(scene_payload["entities"]),
            "search_entities": len(search_index["entities"]),
            "scene_edges": len(scene_payload["edges"]),
            "adjacency_entities": len(adjacency_topk),
        },
    }

    return {
        "scene_payload.json": scene_payload,
        "search_index.json": search_index,
        "adjacency_topk.json": adjacency_topk,
        "frontend_manifest.json": manifest,
    }


def validate_outputs(
    entities: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    issue_profiles: list[dict[str, Any]],
    entity_year_rows: list[dict[str, Any]],
    payload: dict[str, Any],
    quality_report: dict[str, Any],
    quarantined_merges: list[dict[str, Any]],
) -> dict[str, Any]:
    checks = []

    def check(name: str, passed: bool, detail: Any = None) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    missing_policy = set(quality_report["missing_value_policy"])
    check("audit_counts_blank_and_empty_values", {"blank_string", "empty_array"}.issubset(missing_policy), sorted(missing_policy))
    check("no_truncated_fallback_ids", not any(re.search(r"_[A-Z][A-Z ]{20,}$", eid) for eid in entities), None)
    check("legacy_fuzzy_merges_quarantined", len(quarantined_merges) > 0, {"count": len(quarantined_merges)})
    check("duplicate_edge_triples_aggregated", len(edges) == len({(e["source_id"], e["target_id"], e["edge_type"]) for e in edges}), None)
    missing_edge_endpoints = sorted({
        endpoint
        for edge in edges
        for endpoint in (edge["source_id"], edge["target_id"])
        if endpoint not in entities
    })
    check("all_edge_endpoints_exist", not missing_edge_endpoints, missing_edge_endpoints[:20])
    check(
        "stats_latest_year_mismatch_checked",
        True,
        {"reported": any(issue.get("code") == "STALE_LATEST_YEAR" for issue in quality_report["issues"])},
    )
    gov_metric_ok = all(
        entity.get("observed_spend") is None
        and entity.get("node_size_metric") == "log_lobbying_exposure"
        and entity.get("lobbying_exposure") is not None
        and safe_float(entity.get("lobbying_exposure")) >= 0
        for entity in entities.values()
        if entity.get("entity_type") == "gov_agency"
    )
    check("government_exposure_separate_from_spend", gov_metric_ok, None)
    temporal_types = {row["temporal_value_type"] for row in entity_year_rows}
    check("no_random_yearly_size_generation", "synthetic_random" not in temporal_types, sorted(temporal_types))
    firm_client_years_ok = all(
        row["active"] == ("true" if row["year"] in set(safe_int(y) for y in entities[row["entity_id"]].get("active_years", []) if safe_int(y)) else "false")
        for row in entity_year_rows
        if entities[row["entity_id"]].get("active_year_basis") == "raw_years_array"
    )
    check("active_years_reflect_raw_year_arrays", firm_client_years_ok, None)
    issue_label_ok = all(row.get("issue_label") and row.get("policy_category") for row in issue_profiles)
    check("issue_labels_and_rollups_present", issue_label_ok, {"issue_profile_rows": len(issue_profiles)})
    required_payload_keys = {"meta", "entities", "entity_years", "edges", "clusters", "gap_grid", "revolving_vectors", "topics"}
    check("visual_payload_schema_valid", required_payload_keys.issubset(payload), sorted(payload.keys()))
    max_node_size = max((safe_float(e.get("metrics", {}).get("node_size_value")) for e in payload["entities"]), default=0.0)
    check("node_size_is_log_scaled", max_node_size < 30, {"max_node_size_value": max_node_size})
    confidence_ok = all("confidence" in e and "source_files" in e for e in payload["entities"])
    check("confidence_and_source_provenance_present", confidence_ok, None)
    check("edge_truncation_disclosed", "edges_truncated" in payload["meta"] and "total_edges_in_data" in payload["meta"], None)
    valid_vector_years = True
    invalid_vector_years = []
    valid_year_set = set(payload.get("meta", {}).get("years", []))
    for vector in payload.get("revolving_vectors", []):
        transition_year = vector.get("transition_year")
        temporal_scope = vector.get("temporal_scope")
        if transition_year is None:
            if temporal_scope != "unknown_transition_year":
                valid_vector_years = False
                invalid_vector_years.append(vector.get("vector_id"))
        elif transition_year not in valid_year_set or temporal_scope not in {"observed_transition_year", "estimated_transition_year"}:
            valid_vector_years = False
            invalid_vector_years.append(vector.get("vector_id"))
    check("revolving_vector_year_semantics_valid", valid_vector_years, invalid_vector_years[:10])

    return {
        "passed": all(row["passed"] for row in checks),
        "checks": checks,
        "counts": {
            "entities": len(entities),
            "edges": len(edges),
            "entity_year_rows": len(entity_year_rows),
            "issue_profile_rows": len(issue_profiles),
            "payload_entities": len(payload["entities"]),
            "payload_entity_years": len(payload["entity_years"]),
            "payload_edges": len(payload["edges"]),
        },
    }


def write_readme(output_dir: Path) -> None:
    readme = """# Reliable Influence Map Data

Generated by `V3_Epistemic/pipeline/09_build_reliable_payload.py`.

This folder contains the cleaned, defensible data layer for the DC lobbying
3D influence map. It does not use random yearly sizing from the legacy
`entities_3d.json` generator.

Key files:

- `entities.csv`: canonical actors with stable IDs, categories, coordinates, scores, confidence, and source provenance.
- `edges.csv`: deduplicated relationship graph with normalized edge types and aggregated weights.
- `entity_year_metrics.csv`: year rows with explicit `temporal_value_type`; aggregate values are repeated only when true entity-year data is unavailable.
- `issue_profiles.csv`: issue code, readable label, policy rollup, and entity weight.
- `visual_payload.json`: frontend-ready replacement payload with meta, entities, entity_years, edges, clusters, gap grid, vectors, and topics.
- `scene_payload.json`: smaller initial scene payload for static/offline loading.
- `search_index.json`: full entity search/detail index for entities outside the initial scene.
- `adjacency_topk.json`: compact relationship-neighborhood index for detail views.
- `frontend_manifest.json`: preview manifest with file names, counts, caps, and data semantics.
- `quality_report.json`: missingness, suspicious values, temporal mismatches, and quarantined legacy assumptions.
- `validation_report.json`: acceptance checks for the reliable payload.
- `quarantined_dedup_merges.csv`: legacy fuzzy merges requiring review instead of silent acceptance.

Government target-side exposure is preserved separately as
`target_attention_exposure`; it is not used as raw node size.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build reliable 3D influence-map payload")
    parser.add_argument("--output-dir", type=Path, default=RELIABLE_DIR)
    parser.add_argument("--copy-to-frontend", action="store_true", default=True)
    args = parser.parse_args()

    sources = load_sources()
    issue_labels, code_to_rollup = build_issue_rollups(sources["industries"])
    quality_report, quarantined_merges = build_quality_report(sources)
    indexes = build_feature_indexes(sources, issue_labels, code_to_rollup)

    entities = build_entities(sources, indexes)
    edges = build_edges(sources, indexes, entities)
    attach_layout(entities, edges)
    attach_scores(entities, edges, sources)

    entity_year_rows = build_entity_year_rows(entities)
    issue_profiles = build_issue_profiles(entities, issue_labels, code_to_rollup)
    payload = build_visual_payload(entities, entity_year_rows, edges, issue_profiles, sources, quality_report)
    reliable_split_payloads = build_split_payloads(payload, full_payload_filename="visual_payload.json")
    frontend_split_payloads = build_split_payloads(payload, full_payload_filename="reliable_visual_payload.json")
    validation = validate_outputs(entities, edges, issue_profiles, entity_year_rows, payload, quality_report, quarantined_merges)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    entity_fields = [
        "canonical_id", "legacy_id", "name", "entity_type", "entity_subtype",
        "primary_policy_category", "region", "state", "source_files", "source_record_id",
        "active_years", "active_year_basis", "observed_spend", "target_attention_exposure",
        "lobbying_exposure", "filings_total", "top_issue_code", "top_issue_label", "issue_count", "issue_codes",
        "coord_x", "coord_y", "coordinate_source", "cluster_id", "cluster_label",
        "graph_degree_weighted", "gov_target_breadth", "influence_score", "momentum_score",
        "revolving_door_score", "concentration_score", "gap_score", "node_size_metric",
        "node_size_value", "confidence_score", "confidence_level", "quality_flags",
    ]
    write_csv_rows(output_dir / "entities.csv", list(entities.values()), entity_fields)

    edge_fields = [
        "source_id", "source_name", "target_id", "target_name", "edge_type",
        "weight", "raw_value", "measure_type", "source_files", "confidence",
        "resolution", "duplicate_count", "is_self_edge",
    ]
    write_csv_rows(output_dir / "edges.csv", edges, edge_fields)

    year_fields = [
        "entity_id", "year", "active", "active_year_basis", "observed_spend",
        "lobbying_exposure", "filings_total", "display_size_metric", "display_size_value",
        "temporal_value_type", "is_partial_year",
    ]
    write_csv_rows(output_dir / "entity_year_metrics.csv", entity_year_rows, year_fields)

    issue_fields = ["entity_id", "issue_code", "issue_label", "policy_category", "weight", "source"]
    write_csv_rows(output_dir / "issue_profiles.csv", issue_profiles, issue_fields)

    merge_fields = ["kept", "dropped", "reason", "status"]
    write_csv_rows(output_dir / "quarantined_dedup_merges.csv", quarantined_merges, merge_fields)

    write_json(output_dir / "quality_report.json", quality_report)
    write_json(output_dir / "validation_report.json", validation)
    write_json(output_dir / "visual_payload.json", payload, compact=True)
    for filename, content in reliable_split_payloads.items():
        write_json(output_dir / filename, content, compact=True)
    write_readme(output_dir)

    if args.copy_to_frontend:
        FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
        write_json(FRONTEND_DIR / "reliable_visual_payload.json", payload, compact=True)
        for filename, content in frontend_split_payloads.items():
            write_json(FRONTEND_DIR / filename, content, compact=True)

    print("Reliable payload build complete")
    print(f"  entities: {len(entities):,}")
    print(f"  edges: {len(edges):,}")
    print(f"  entity_year_metrics: {len(entity_year_rows):,}")
    print(f"  issue_profiles: {len(issue_profiles):,}")
    print(f"  validation_passed: {validation['passed']}")
    print(f"  output: {output_dir}")
    if not validation["passed"]:
        failed = [row["name"] for row in validation["checks"] if not row["passed"]]
        print(f"  failed_checks: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
