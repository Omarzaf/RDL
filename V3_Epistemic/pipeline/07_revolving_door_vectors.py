"""
07_revolving_door_vectors.py

Builds conservative revolving-door vectors. Source endpoints are restricted to
government entities resolved through controlled aliases/patterns; target
endpoints are restricted to exact or unambiguous firm/client entities. Unknown
transition years remain unknown instead of being forced into a representative
year.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from config import PROCESSED_DIR, RAW_DATA_DIR, YEARS


RAW = RAW_DATA_DIR
OUT = PROCESSED_DIR


GOV_PATTERNS = [
    ("HOUSE OF REPRESENTATIVES", ["HOUSE OF REPRESENTATIVES", "HOUSE REP", "HOUSE REPUBLICAN", "MEMBER OF CONGRESS"]),
    ("SENATE", ["SENATE", "SENATOR"]),
    ("White House Office", ["WHITE HOUSE"]),
    ("Executive Office of the President (EOP)", ["EXECUTIVE OFFICE OF THE PRESIDENT", " EOP"]),
    ("Commerce, Dept of (DOC)", ["DEPARTMENT OF COMMERCE", "COMMERCE", "SECRETARY OF COMMERCE"]),
    ("Treasury, Dept of", ["DEPARTMENT OF TREASURY", "TREASURY"]),
    ("Health & Human Services, Dept of (HHS)", ["HEALTH & HUMAN SERVICES", "HEALTH AND HUMAN SERVICES", " HHS"]),
    ("Defense, Dept of (DOD)", ["DEPARTMENT OF DEFENSE", "DEFENSE", " DOD", "PENTAGON"]),
    ("Transportation, Dept of (DOT)", ["DEPARTMENT OF TRANSPORTATION", "TRANSPORTATION", " DOT"]),
    ("Environmental Protection Agency (EPA)", ["ENVIRONMENTAL PROTECTION AGENCY", " EPA"]),
    ("Agriculture, Dept of (USDA)", ["DEPARTMENT OF AGRICULTURE", "AGRICULTURE", " USDA"]),
    ("Energy, Dept of", ["DEPARTMENT OF ENERGY", "ENERGY"]),
    ("Homeland Security, Dept of (DHS)", ["HOMELAND SECURITY", " DHS"]),
    ("Justice, Dept of (DOJ)", ["DEPARTMENT OF JUSTICE", "JUSTICE", " DOJ"]),
    ("Labor, Dept of", ["DEPARTMENT OF LABOR", "LABOR"]),
    ("State, Dept of", ["DEPARTMENT OF STATE", "STATE DEPARTMENT"]),
    ("Centers For Medicare and Medicaid Services (CMS)", ["CENTERS FOR MEDICARE", "MEDICAID SERVICES", " CMS"]),
]


def load_json(fname: str) -> Any:
    with (RAW / fname).open(encoding="utf-8") as f:
        return json.load(f)


def stable_hash(value: str, length: int = 14) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def norm(value: Any) -> str:
    text = str(value or "").replace("&AMP;", "&").upper()
    return re.sub(r"\s+", " ", text).strip()


def loose(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", norm(value))


def canonical_person_id(person: dict[str, Any]) -> str:
    signature = "|".join(
        [
            norm(person.get("name")),
            ";".join(sorted(norm(p) for p in person.get("positions", []) or [])[:5]),
            ";".join(sorted(norm(f) for f in person.get("firms", []) or [])[:5]),
        ]
    )
    return f"person_{stable_hash(signature)}"


def entity_lookup(coords: pd.DataFrame, entities: pd.DataFrame):
    merged = coords.merge(
        entities[["entity_id", "name", "entity_type"]],
        on=["entity_id", "name"],
        how="left",
    )
    by_exact: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_loose: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_id = {}
    for _, row in merged.iterrows():
        item = {
            "entity_id": str(row["entity_id"]),
            "name": str(row["name"]),
            "entity_type": str(row.get("entity_type", "")),
            "x": float(row["x"]),
            "y": float(row["y"]),
        }
        by_id[item["entity_id"]] = item
        by_exact[norm(item["name"])].append(item)
        key = loose(item["name"])
        if len(key) >= 3:
            by_loose[key].append(item)
    return by_exact, by_loose, by_id


def resolve_exact_entity(
    names: list[str],
    by_exact: dict[str, list[dict[str, Any]]],
    by_loose: dict[str, list[dict[str, Any]]],
    allowed_types: set[str],
) -> tuple[dict[str, Any] | None, str, float, list[str]]:
    flags = []
    for name in names:
        key = norm(name)
        if len(key) <= 1:
            flags.append("rejected_single_character_name")
            continue
        exact = [item for item in by_exact.get(key, []) if item["entity_type"] in allowed_types]
        if len(exact) == 1:
            return exact[0], "exact_name", 0.95, flags
        loose_key = loose(name)
        loose_matches = [item for item in by_loose.get(loose_key, []) if item["entity_type"] in allowed_types]
        if len(loose_key) >= 4 and len(loose_matches) == 1:
            return loose_matches[0], "exact_loose_name", 0.85, flags
        if len(exact) > 1 or len(loose_matches) > 1:
            flags.append("ambiguous_target_name")
    return None, "unresolved", 0.0, flags


def resolve_gov_entity(position_texts: list[str], gov_by_name: dict[str, dict[str, Any]]) -> tuple[dict[str, Any] | None, str, float, list[str]]:
    combined = " | ".join(norm(text) for text in position_texts)
    flags = []
    for gov_name, patterns in GOV_PATTERNS:
        if any(pattern in combined for pattern in patterns):
            item = gov_by_name.get(norm(gov_name))
            if item:
                return item, "controlled_gov_pattern", 0.82, flags
    for gov_key, item in gov_by_name.items():
        if len(gov_key) >= 5 and gov_key in combined:
            return item, "exact_gov_name_in_position", 0.88, flags
    flags.append("unresolved_government_endpoint")
    return None, "unresolved", 0.0, flags


def extract_transition_year(positions: list[Any]) -> tuple[int | None, bool]:
    for position in positions:
        text = json.dumps(position) if isinstance(position, dict) else str(position)
        match = re.search(r"(20\d{2}|19\d{2})", text)
        if match:
            year = int(match.group(1))
            if year in YEARS:
                return year, False
    return None, True


def main() -> None:
    revolving = load_json("revolving-door.json")
    coords = pd.read_csv(OUT / "umap_coords.csv")
    entities = pd.read_csv(OUT / "entities.csv")
    by_exact, by_loose, _ = entity_lookup(coords, entities)

    gov_entities = [
        item for items in by_exact.values() for item in items if item["entity_type"] == "gov_agency"
    ]
    gov_by_name = {norm(item["name"]): item for item in gov_entities}

    vectors = []
    unresolved = []
    yearly_currents = {yr: {"gov_to_lobby": [], "lobby_to_gov": []} for yr in YEARS}
    seen_vector_keys = set()

    for person in revolving:
        positions = person.get("positions", []) or []
        firms = [str(f) for f in person.get("firms", []) or []]
        clients = [str(c) for c in person.get("clients", []) or []]
        if not positions or not firms:
            continue

        person_id = canonical_person_id(person)
        source, source_resolution, source_conf, source_flags = resolve_gov_entity([str(p) for p in positions], gov_by_name)
        target, target_resolution, target_conf, target_flags = resolve_exact_entity(
            firms,
            by_exact,
            by_loose,
            {"firm", "client"},
        )
        if source is None or target is None:
            unresolved.append(
                {
                    "person_id": person_id,
                    "person": person.get("name", ""),
                    "source_resolution": source_resolution,
                    "target_resolution": target_resolution,
                    "quality_flags": source_flags + target_flags,
                }
            )
            continue

        key = (person_id, source["entity_id"], target["entity_id"])
        if key in seen_vector_keys:
            continue
        seen_vector_keys.add(key)

        dx = target["x"] - source["x"]
        dy = target["y"] - source["y"]
        magnitude = float(np.sqrt(dx**2 + dy**2))
        transition_year, estimated = extract_transition_year(positions)
        year_unknown = transition_year is None
        year_estimated = bool(estimated and not year_unknown)
        year_penalty = 0.2 if (year_unknown or year_estimated) else 0.0
        confidence = round(max(0.05, min(1.0, (source_conf + target_conf) / 2 - year_penalty)), 4)
        flags = source_flags + target_flags
        if year_unknown:
            flags.append("unknown_transition_year")
        elif year_estimated:
            flags.append("estimated_transition_year")

        vector = {
            "vector_id": f"vector_{stable_hash('|'.join(key))}",
            "person_id": person_id,
            "person": person.get("name", ""),
            "source_id": source["entity_id"],
            "target_id": target["entity_id"],
            "source_name": source["name"],
            "target_name": target["name"],
            "source_type": source["entity_type"],
            "target_type": target["entity_type"],
            "src_x": source["x"],
            "src_y": source["y"],
            "tgt_x": target["x"],
            "tgt_y": target["y"],
            "dx": round(dx, 4),
            "dy": round(dy, 4),
            "magnitude": round(magnitude, 4),
            "vector_weight": 1.0,
            "people_count": 1,
            "sample_people": [person.get("name", "")],
            "direction": "gov_to_lobby",
            "transition_year": transition_year,
            "transition_year_estimated": year_estimated,
            "temporal_scope": (
                "unknown_transition_year"
                if year_unknown
                else ("estimated_transition_year" if year_estimated else "observed_transition_year")
            ),
            "confidence": confidence,
            "confidence_components": {
                "source_resolution": source_resolution,
                "target_resolution": target_resolution,
                "source_confidence": source_conf,
                "target_confidence": target_conf,
                "year_observed": not year_unknown and not year_estimated,
            },
            "quality_flags": flags,
            "explanation": (
                "Career-transition record linking a parsed government role to a lobbying firm. "
                "This is an exploratory flow record, not proof of causal influence."
            ),
        }
        vectors.append(vector)
        if transition_year in yearly_currents:
            yearly_currents[transition_year]["gov_to_lobby"].append(
                {
                    "src_x": source["x"],
                    "src_y": source["y"],
                    "tgt_x": target["x"],
                    "tgt_y": target["y"],
                    "magnitude": round(magnitude, 4),
                    "transition_year_estimated": year_estimated,
                    "confidence": confidence,
                }
            )

    yearly_summary = {}
    for yr in YEARS:
        g2l = yearly_currents[yr]["gov_to_lobby"]
        if g2l:
            avg_dx = float(np.mean([v["tgt_x"] - v["src_x"] for v in g2l]))
            avg_dy = float(np.mean([v["tgt_y"] - v["src_y"] for v in g2l]))
            yearly_summary[yr] = {
                "year": yr,
                "gov_to_lobby_count": len(g2l),
                "avg_dx": round(avg_dx, 4),
                "avg_dy": round(avg_dy, 4),
                "magnitude": round(np.sqrt(avg_dx**2 + avg_dy**2), 4),
                "sample_vectors": g2l[:50],
            }
        else:
            yearly_summary[yr] = {
                "year": yr,
                "gov_to_lobby_count": 0,
                "avg_dx": 0,
                "avg_dy": 0,
                "magnitude": 0,
                "sample_vectors": [],
            }

    with (OUT / "revolving_vectors.json").open("w", encoding="utf-8") as f:
        json.dump(vectors[:2000], f, indent=2)
    with (OUT / "yearly_currents.json").open("w", encoding="utf-8") as f:
        json.dump(yearly_summary, f, indent=2)
    with (OUT / "revolving_resolution_report.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "raw_rows": len(revolving),
                "vectors": len(vectors),
                "unresolved": len(unresolved),
                "unknown_transition_years": sum(1 for v in vectors if v["transition_year"] is None),
                "unresolved_samples": unresolved[:100],
            },
            f,
            indent=2,
        )

    premium_path = RAW / "revolving-door-premium.json"
    if premium_path.exists():
        premium = load_json("revolving-door-premium.json")
        corrected = json.loads(json.dumps(premium))
        for row in corrected.get("topRevolvingDoorFirms", []):
            if "revolvingDoorLobbyists" in row:
                row["revolvingDoorEvents"] = row.pop("revolvingDoorLobbyists")
        with (OUT / "revolving-door-premium.corrected.json").open("w", encoding="utf-8") as f:
            json.dump(corrected, f, indent=2)

    print(f"Revolving door vectors extracted: {len(vectors)}")
    print(f"Unresolved records: {len(unresolved)}")
    print(f"Unknown transition years retained as null: {sum(1 for v in vectors if v['transition_year'] is None)}")
    print("Saved: revolving_vectors.json, yearly_currents.json, revolving_resolution_report.json")


if __name__ == "__main__":
    main()
