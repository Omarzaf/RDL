"""
02_build_entity_table.py  —  v2
Builds a unified master entity table + edge list for the DC lobbying network.

Node types:  firm | client | gov_agency | lobbyist
Edge types:  firm_represents | gov_lobbied_by | lobbyist_at_firm | lobbyist_serves_client

New in v2
---------
* Lobbyist nodes from revolving-door.json
* Edges: lobbyist → firm, lobbyist → client
* Issue feature vectors  (binary, from top-clients.json issues[])
* Gov targeting features  (GOV_HOUSE, GOV_SENATE, GOV_HHS … 15 binary columns)
* Log-normalised numerics: log_spend, log_filings
* entities.csv extended with all of the above
* validation_report.json broken out by node type

Outputs (all in --output-dir):
  entities.csv            canonical deduped entity table with features
  entity_nodes.csv        legacy alias for older reference scripts only
  edges.csv               all relationship edges
  embedding_matrix.csv    weighted numeric features keyed by entity_id
  validation_report.json  counts, coverage stats
  frontend_bundle.json    compact JSON for the 3-D viewer
"""

import argparse
import json
import csv
import math
import re
import sys
import hashlib
from pathlib import Path
from config import RAW_DATA_DIR, PROCESSED_DIR
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ModuleNotFoundError:
    import difflib
    RAPIDFUZZ_AVAILABLE = False

    class fuzz:
        @staticmethod
        def token_sort_ratio(a, b):
            a_tokens = " ".join(sorted(str(a).split()))
            b_tokens = " ".join(sorted(str(b).split()))
            return difflib.SequenceMatcher(None, a_tokens, b_tokens).ratio() * 100

# ---------------------------------------------------------------------------
# Argument parsing + path resolution
# ---------------------------------------------------------------------------
_SCRIPT_DIR  = Path(__file__).resolve().parent
_DEFAULT_RAW = RAW_DATA_DIR
_DEFAULT_OUT = PROCESSED_DIR

parser = argparse.ArgumentParser(description="Build entity table v2")
parser.add_argument("--input-dir",  type=Path, default=_DEFAULT_RAW)
parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUT)
parser.add_argument("--minimal",    action="store_true", default=False,
                    help="Suppress verbose per-section output")
args   = parser.parse_args()
RAW    = args.input_dir.resolve()
OUT    = args.output_dir.resolve()
QUIET  = args.minimal

if not RAW.is_dir():
    print(f"ERROR: Raw data directory not found.\n  Searched at: {RAW}", file=sys.stderr)
    sys.exit(1)
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load(fname, required=True):
    p = RAW / fname
    if not p.exists():
        if required:
            print(f"ERROR: missing required file: {p}", file=sys.stderr)
            sys.exit(1)
        return None
    with open(p) as f:
        return json.load(f)

def log1p(x):
    """Safe log(1 + x) — returns 0 for non-numeric or negative."""
    try:
        v = float(x)
        return round(math.log1p(max(v, 0)), 6)
    except (TypeError, ValueError):
        return 0.0

def _top_issue_str(top_issues):
    """Normalise topIssues entries — may be str or {"code":…, "count":…} dicts."""
    if not top_issues:
        return ""
    first = top_issues[0]
    return first.get("code", "") if isinstance(first, dict) else str(first)

def resolve_id(name_to_id, name, fallback_prefix="ext"):
    return name_to_id.get(name.strip().upper(),
                          f"{fallback_prefix}_{stable_hash(fallback_prefix + ':' + name_key(name))}")

def stable_hash(value: str, length: int = 14) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:length]

def name_key(name: str) -> str:
    """Stable exact-ish key for cross-file entity names."""
    return " ".join(str(name or "").replace("&AMP;", "&").strip().upper().split())

def loose_name_key(name: str) -> str:
    """Punctuation-insensitive key used only when it is unambiguous."""
    return re.sub(r"[^A-Z0-9]+", "", name_key(name))

def l2_normalize(vec: dict) -> dict:
    """Return an L2-normalized sparse vector with deterministic key order."""
    clean = {}
    for k, v in (vec or {}).items():
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv > 0:
            clean[str(k)] = fv
    norm = math.sqrt(sum(v * v for v in clean.values()))
    if not norm:
        return {}
    return {k: round(clean[k] / norm, 6) for k in sorted(clean)}

def add_vec(total: dict, vec: dict, weight: float = 1.0) -> None:
    """In-place sparse vector addition."""
    for k, v in (vec or {}).items():
        try:
            total[k] = total.get(k, 0.0) + float(v) * weight
        except (TypeError, ValueError):
            continue

def vec_dot(a: dict, b: dict) -> float:
    """Sparse vector dot product."""
    if len(a) > len(b):
        a, b = b, a
    return sum(float(v) * float(b.get(k, 0.0)) for k, v in a.items())

def top_vec_key(vec: dict) -> str:
    """Return the strongest feature key, or empty string for an empty vec."""
    return max(vec, key=vec.get) if vec else ""

DEDUP_STOP_TOKENS = {
    "THE", "AND", "FOR", "WITH", "FROM", "INC", "LLC", "LTD", "PLC", "LP",
    "LLP", "CORP", "CORPORATION", "COMPANY", "CO", "GROUP", "SERVICES",
    "ASSOCIATION", "ASSN", "NATIONAL", "AMERICAN", "UNITED", "USA", "U",
    "S", "US", "OF", "DE", "DBA", "FKA", "FORMERLY", "REPORTED",
}

def dedup_tokens(name: str) -> set:
    """Tokens used to preselect fuzzy-dedup candidates in fallback mode."""
    tokens = re.findall(r"[A-Z0-9]+", name_key(name))
    useful = {t for t in tokens if len(t) > 2 and t not in DEDUP_STOP_TOKENS}
    return useful or set(tokens[:2])

# ---------------------------------------------------------------------------
# Load raw sources
# ---------------------------------------------------------------------------
firms     = load("top-firms.json")
clients   = load("top-clients.json")
gov       = load("gov-entities.json")
lobbyists = load("revolving-door.json")          # ← node source for lobbyists
_          = load("top-lobbyists.json")           # loaded but not used for nodes

firm_conc_raw = load("firm-concentration.json")
firm_conc     = (firm_conc_raw.get("firms", [])
                 if isinstance(firm_conc_raw, dict)
                 else firm_conc_raw)
firm_issue_map = {f["firm"]: f.get("topIssue", "") for f in firm_conc}

if not QUIET:
    print(f"Loaded  firms={len(firms)}  clients={len(clients)}  "
          f"gov={len(gov)}  lobbyists={len(lobbyists)}")

# ---------------------------------------------------------------------------
# Build global ISSUE VOCABULARY  (all 3-letter codes seen across clients
# plus government topIssue profiles)
# ---------------------------------------------------------------------------
issue_vocab: list[str] = sorted({
    code
    for c in clients
    for code in c.get("issues", [])
    if isinstance(code, str)
} | {
    item.get("code", "")
    for g in gov
    for item in g.get("topIssues", [])
    if isinstance(item, dict) and isinstance(item.get("code"), str)
} | {
    str(item)
    for g in gov
    for item in g.get("topIssues", [])
    if isinstance(item, str)
} | {
    f.get("topIssue", "")
    for f in firm_conc
    if isinstance(f.get("topIssue", ""), str)
})
issue_vocab = [code for code in issue_vocab if code]
if not QUIET:
    print(f"Issue vocab: {len(issue_vocab)} codes  "
          f"({', '.join(issue_vocab[:8])}…)")

def make_issue_vec(issue_list: list) -> dict:
    """Return a sparse issue vector from string codes or topIssue dicts."""
    weights = {}
    for item in issue_list or []:
        if isinstance(item, dict):
            code = item.get("code")
            if isinstance(code, str) and code in issue_vocab:
                weights[code] = weights.get(code, 0.0) + float(item.get("count", 1) or 1)
        elif isinstance(item, str) and item in issue_vocab:
            weights[item] = weights.get(item, 0.0) + 1.0
    return weights

# ---------------------------------------------------------------------------
# Build GOV TARGETING index
#   gov-entities.json.topClients tells us which clients lobby each gov body.
#   gov-entities.json.topIssues expands coverage through issue overlap.
# ---------------------------------------------------------------------------
GOV_FEATURE_MAP = {
    "HOUSE OF REPRESENTATIVES":                          "GOV_HOUSE",
    "SENATE":                                            "GOV_SENATE",
    "White House Office":                                "GOV_WHITEHOUSE",
    "Health & Human Services, Dept of (HHS)":           "GOV_HHS",
    "Treasury, Dept of":                                 "GOV_TREASURY",
    "Transportation, Dept of (DOT)":                    "GOV_DOT",
    "Commerce, Dept of (DOC)":                          "GOV_DOC",
    "Environmental Protection Agency (EPA)":            "GOV_EPA",
    "Agriculture, Dept of (USDA)":                      "GOV_USDA",
    "Energy, Dept of":                                   "GOV_ENERGY",
    "Defense, Dept of (DOD)":                           "GOV_DOD",
    "Centers For Medicare and Medicaid Services (CMS)": "GOV_CMS",
    "Executive Office of the President (EOP)":          "GOV_EOP",
    "Homeland Security, Dept of (DHS)":                 "GOV_DHS",
    "Justice, Dept of (DOJ)":                           "GOV_DOJ",
    "Labor, Dept of":                                    "GOV_LABOR",
    "State, Dept of":                                    "GOV_STATE",
}
GOV_COLS = sorted(set(GOV_FEATURE_MAP.values()))   # deterministic column order
GOV_DIRECT_WEIGHT = 1.0
GOV_ISSUE_OVERLAP_WEIGHT = 0.75
GOV_ISSUE_OVERLAP_TOP_N = 5
GOV_ISSUE_OVERLAP_MIN_SCORE = 0.05

# Direct signal: gov-entities topClients explicitly names this client.
client_gov_targets: dict[str, set] = {}
for g in gov:
    col = GOV_FEATURE_MAP.get(g["name"])
    if not col:
        continue
    for tc in g.get("topClients", []):
        key = name_key(tc.get("name", ""))
        client_gov_targets.setdefault(key, set()).add(col)

# Issue-overlap signal: compare each client issue profile with each gov body
# topIssues profile. This raises coverage without fabricating relationships.
gov_issue_profiles: dict[str, dict] = {}
for g in gov:
    col = GOV_FEATURE_MAP.get(g["name"])
    if not col:
        continue
    gov_issue_profiles[col] = l2_normalize(make_issue_vec(g.get("topIssues", [])))

def infer_client_gov_vec(client_name: str, client_issue_vec: dict) -> dict:
    """Return raw GOV scores from direct topClient and issue-overlap signals."""
    scores = {}
    for col in client_gov_targets.get(name_key(client_name), set()):
        scores[col] = max(scores.get(col, 0.0), GOV_DIRECT_WEIGHT)

    client_issue_norm = l2_normalize(client_issue_vec)
    overlap_scores = []
    for col, gov_issue_vec in gov_issue_profiles.items():
        score = vec_dot(client_issue_norm, gov_issue_vec)
        if score >= GOV_ISSUE_OVERLAP_MIN_SCORE:
            overlap_scores.append((score, col))

    for score, col in sorted(overlap_scores, reverse=True)[:GOV_ISSUE_OVERLAP_TOP_N]:
        scores[col] = max(scores.get(col, 0.0), score * GOV_ISSUE_OVERLAP_WEIGHT)
    return scores

# ---------------------------------------------------------------------------
# Shared "empty" vectors  (for non-client entity types)
# ---------------------------------------------------------------------------
_EMPTY_ISSUE = {}
_EMPTY_GOV   = {}

def _gov_row(vec: dict) -> dict:
    """Expand gov_vec dict to per-column normalized values for CSV rows."""
    return {col: vec.get(col, 0.0) for col in GOV_COLS}

# ---------------------------------------------------------------------------
# Client feature index used for propagation into firms and lobbyists
# ---------------------------------------------------------------------------
client_feature_by_key: dict[str, dict] = {}
client_feature_by_loose_key: dict[str, dict] = {}
ambiguous_loose_client_keys: set[str] = set()

for c in clients:
    issue_raw = make_issue_vec(c.get("issues", []))
    gov_raw = infer_client_gov_vec(c.get("name", ""), issue_raw)
    feature = {
        "issue_vec": l2_normalize(issue_raw),
        "gov_vec": l2_normalize(gov_raw),
    }
    key = name_key(c.get("name", ""))
    loose_key = loose_name_key(c.get("name", ""))
    client_feature_by_key[key] = feature

    if loose_key in client_feature_by_loose_key and client_feature_by_loose_key[loose_key] != feature:
        ambiguous_loose_client_keys.add(loose_key)
        client_feature_by_loose_key.pop(loose_key, None)
    elif loose_key not in ambiguous_loose_client_keys:
        client_feature_by_loose_key[loose_key] = feature

def get_client_feature(client_name: str):
    """Find a client's feature vector by exact key, then unambiguous loose key."""
    key = name_key(client_name)
    if key in client_feature_by_key:
        return client_feature_by_key[key]
    return client_feature_by_loose_key.get(loose_name_key(client_name))

def aggregate_client_features(client_names: list, feature_name: str) -> tuple[dict, int]:
    """Aggregate normalized client vectors, then normalize the combined vector."""
    total = {}
    matched = 0
    for cname in client_names or []:
        feature = get_client_feature(cname)
        if not feature:
            continue
        vec = feature.get(feature_name, {})
        if vec:
            add_vec(total, vec)
            matched += 1
    return l2_normalize(total), matched

# ---------------------------------------------------------------------------
# Build entity list
# ---------------------------------------------------------------------------
entities: list[dict] = []

def _base(entity_id, name, etype, industry, spend, filings, state,
          top_issue, clients_count, source,
          firm="", gov_positions=0,
          issue_vec=None, gov_vec=None,
          firm_issue_vec=None, firm_gov_vec=None,
          lobbyist_issue_vec=None, lobbyist_gov_vec=None,
          feature_clients_matched=0):
    """Return a fully-populated entity row dict."""
    iv = l2_normalize(issue_vec or _EMPTY_ISSUE)
    gv = l2_normalize(gov_vec   or _EMPTY_GOV)
    fiv = l2_normalize(firm_issue_vec or _EMPTY_ISSUE)
    fgv = l2_normalize(firm_gov_vec or _EMPTY_GOV)
    liv = l2_normalize(lobbyist_issue_vec or _EMPTY_ISSUE)
    lgv = l2_normalize(lobbyist_gov_vec or _EMPTY_GOV)
    row = {
        # --- core identity ---
        "entity_id":          entity_id,
        "name":               name,
        "entity_type":        etype,
        "industry":           industry,
        "total_spending":     spend,
        "filings_total":      filings,
        "state":              state,
        "top_issue":          top_issue,
        "clients_count":      clients_count,
        "source":             source,
        # --- lobbyist-specific ---
        "firm":               firm,
        "gov_positions_count": gov_positions,
        # --- log-normalised numerics ---
        "log_spend":          log1p(spend),
        "log_filings":        log1p(filings),
        # --- issue features ---
        "issue_count":        len(iv),
        "issue_codes":        "|".join(iv.keys()),
        "issue_vec":          json.dumps(iv, separators=(",", ":")),
        "feature_clients_matched": feature_clients_matched,
        "firm_issue_vec":     json.dumps(fiv, separators=(",", ":")),
        "firm_gov_vec":       json.dumps(fgv, separators=(",", ":")),
        "lobbyist_issue_vec": json.dumps(liv, separators=(",", ":")),
        "lobbyist_gov_vec":   json.dumps(lgv, separators=(",", ":")),
        # --- gov targeting features (normalized columns + compact vec) ---
        **_gov_row(gv),
        "gov_vec":            json.dumps(gv, separators=(",", ":")),
    }
    return row

# --- FIRMS ---
for f in firms:
    firm_issue_vec, firm_issue_matches = aggregate_client_features(
        f.get("clients", []), "issue_vec"
    )
    firm_gov_vec, firm_gov_matches = aggregate_client_features(
        f.get("clients", []), "gov_vec"
    )
    fallback_issue_vec = make_issue_vec([firm_issue_map.get(f["name"], "")])
    if not firm_issue_vec:
        firm_issue_vec = fallback_issue_vec
    entities.append(_base(
        entity_id     = f"firm_{f['id']}",
        name          = f["name"],
        etype         = "firm",
        industry      = "Law & Lobbying",
        spend         = f.get("totalIncome", 0),
        filings       = f.get("filings", 0),
        state         = "",
        top_issue     = firm_issue_map.get(f["name"], "") or top_vec_key(firm_issue_vec),
        clients_count = len(f.get("clients", [])),
        source        = "top-firms",
        issue_vec     = firm_issue_vec,
        gov_vec       = firm_gov_vec,
        firm_issue_vec = firm_issue_vec,
        firm_gov_vec  = firm_gov_vec,
        feature_clients_matched = max(firm_issue_matches, firm_gov_matches),
    ))

# --- CLIENTS ---
for i, c in enumerate(clients):
    feature = client_feature_by_key.get(name_key(c["name"]), {})
    iv      = feature.get("issue_vec", {})
    gv      = feature.get("gov_vec", {})
    entities.append(_base(
        entity_id     = f"client_{i:05d}",
        name          = c["name"],
        etype         = "client",
        industry      = "",
        spend         = c.get("totalSpending", 0),
        filings       = c.get("filings", 0),
        state         = c.get("state", ""),
        top_issue     = _top_issue_str(c.get("issues", [])),
        clients_count = 0,
        source        = "top-clients",
        issue_vec     = iv,
        gov_vec       = gv,
    ))

# --- GOV AGENCIES ---
for i, g in enumerate(gov):
    top_issues = g.get("topIssues", [])
    iv = make_issue_vec(top_issues)
    gov_col = GOV_FEATURE_MAP.get(g["name"])
    gv = {gov_col: 1.0} if gov_col else {}
    entities.append(_base(
        entity_id     = f"gov_{i:04d}",
        name          = g["name"],
        etype         = "gov_agency",
        industry      = "Government",
        spend         = g.get("spending", 0),
        filings       = g.get("filings", 0),
        state         = "DC",
        top_issue     = _top_issue_str(top_issues),
        clients_count = 0,
        source        = "gov-entities",
        issue_vec     = iv,
        gov_vec       = gv,
    ))

# --- LOBBYISTS  (from revolving-door.json) ---
for lb in lobbyists:
    firm_str      = " | ".join(lb.get("firms", []))
    n_positions   = len(lb.get("positions", []))
    lb_clients    = lb.get("clients", [])
    lb_issue_vec, lb_issue_matches = aggregate_client_features(lb_clients, "issue_vec")
    lb_gov_vec, lb_gov_matches = aggregate_client_features(lb_clients, "gov_vec")
    entities.append(_base(
        entity_id     = f"lobbyist_{lb['id']}",
        name          = lb["name"],
        etype         = "lobbyist",
        industry      = "Lobbying",
        spend         = 0,
        filings       = lb.get("filings", 0),
        state         = "",
        top_issue     = top_vec_key(lb_issue_vec),
        clients_count = len(lb_clients),
        source        = "revolving-door",
        firm          = firm_str,
        gov_positions = n_positions,
        issue_vec     = lb_issue_vec,
        gov_vec       = lb_gov_vec,
        lobbyist_issue_vec = lb_issue_vec,
        lobbyist_gov_vec = lb_gov_vec,
        feature_clients_matched = max(lb_issue_matches, lb_gov_matches),
    ))

print(f"Raw entity count: {len(entities)}  "
      f"(firms={len(firms)}, clients={len(clients)}, "
      f"gov={len(gov)}, lobbyists={len(lobbyists)})")

# ---------------------------------------------------------------------------
# Dedup (fuzzy name match)
# Lobbyists are people-names; they won't collide with org names in practice.
# Threshold 88 chosen to balance precision/recall on manual spot-check of 50 pairs.
# Conservative public-build policy: scores 85-91 are quarantined, not merged.
# ---------------------------------------------------------------------------
merged_log: list[dict] = []
quarantine_log: list[dict] = []
deduped:    list[dict] = []
seen_names: dict       = {}
seen_token_index: dict[str, set] = {}
AUTO_ACCEPT_THRESHOLD = 92
QUARANTINE_LOWER_BOUND = 85

for ent in entities:
    name    = ent["name"].strip().upper()
    matched = False
    if RAPIDFUZZ_AVAILABLE:
        candidates = seen_names.items()
    else:
        candidate_idxs = set()
        for tok in dedup_tokens(name):
            candidate_idxs.update(seen_token_index.get(tok, set()))
        candidates = ((deduped[idx]["name"].strip().upper(), idx) for idx in candidate_idxs)

    for seen_name, seen_idx in candidates:
        match_score = float(fuzz.token_sort_ratio(name, seen_name))
        if QUARANTINE_LOWER_BOUND <= match_score < AUTO_ACCEPT_THRESHOLD:
            quarantine_log.append({
                "entity_a_id": deduped[seen_idx]["entity_id"],
                "entity_b_id": ent["entity_id"],
                "entity_a_name": deduped[seen_idx]["name"],
                "entity_b_name": ent["name"],
                "match_score": round(match_score, 2),
                "merge_accepted": False,
            })
            continue
        if match_score >= AUTO_ACCEPT_THRESHOLD:
            # Keep the record with higher spending
            if ent["total_spending"] > deduped[seen_idx]["total_spending"]:
                merged_log.append({
                    "entity_a_id": ent["entity_id"],
                    "entity_b_id": deduped[seen_idx]["entity_id"],
                    "entity_a_name": ent["name"],
                    "entity_b_name": deduped[seen_idx]["name"],
                    "match_score": round(match_score, 2),
                    "merge_accepted": True,
                    "kept": ent["name"],
                    "dropped": deduped[seen_idx]["name"],
                })
                deduped[seen_idx] = ent
            else:
                merged_log.append({
                    "entity_a_id": deduped[seen_idx]["entity_id"],
                    "entity_b_id": ent["entity_id"],
                    "entity_a_name": deduped[seen_idx]["name"],
                    "entity_b_name": ent["name"],
                    "match_score": round(match_score, 2),
                    "merge_accepted": True,
                    "kept": deduped[seen_idx]["name"],
                    "dropped": ent["name"],
                })
            matched = True
            break
    if not matched:
        seen_names[name] = len(deduped)
        deduped.append(ent)
        if not RAPIDFUZZ_AVAILABLE:
            new_idx = len(deduped) - 1
            for tok in dedup_tokens(name):
                seen_token_index.setdefault(tok, set()).add(new_idx)

print(f"After dedup: {len(deduped)} entities  ({len(merged_log)} merges)")

# ---------------------------------------------------------------------------
# Name → entity_id index  (for edge resolution)
# ---------------------------------------------------------------------------
name_to_id: dict[str, str] = {e["name"].upper(): e["entity_id"] for e in deduped}

def res(name: str, fallback: str = "ext") -> str:
    normalized = name.strip().upper()
    return name_to_id.get(normalized, f"{fallback}_{stable_hash(fallback + ':' + normalized)}")

# ---------------------------------------------------------------------------
# Build edges
# ---------------------------------------------------------------------------
edges: list[dict] = []

def add_edge(src_id, src_name, dst_id, dst_name, etype, weight=1):
    edges.append({
        "source_id":   src_id,
        "source_name": src_name,
        "target_id":   dst_id,
        "target_name": dst_name,
        "edge_type":   etype,
        "weight":      weight,
    })

# 1. Firm → Client  (firm represents client)
for f in firms:
    firm_id = f"firm_{f['id']}"
    for cname in f.get("clients", []):
        add_edge(firm_id, f["name"], res(cname, "client"), cname, "firm_represents")

# 2. Gov → Client  (gov entity lobbied by client — weighted by spending)
for i, g in enumerate(gov):
    gov_id = f"gov_{i:04d}"
    for tc in g.get("topClients", []):
        cname = tc.get("name", "")
        if cname:
            add_edge(gov_id, g["name"], res(cname, "client"), cname,
                     "gov_lobbied_by", tc.get("spending", 1))

# 3. Lobbyist → Firm  (lobbyist works at firm)
for lb in lobbyists:
    lb_id = f"lobbyist_{lb['id']}"
    for fname in lb.get("firms", []):
        add_edge(lb_id, lb["name"], res(fname, "firm"), fname, "lobbyist_at_firm")

# 4. Lobbyist → Client  (lobbyist serves client)
for lb in lobbyists:
    lb_id = f"lobbyist_{lb['id']}"
    for cname in lb.get("clients", []):
        add_edge(lb_id, lb["name"], res(cname, "client"), cname, "lobbyist_serves_client")

# Edge-type summary
etype_counts = {}
for e in edges:
    etype_counts[e["edge_type"]] = etype_counts.get(e["edge_type"], 0) + 1

print(f"Edges built: {len(edges)}")
for et, n in sorted(etype_counts.items()):
    print(f"  {et:<30}: {n:,}")

# ---------------------------------------------------------------------------
# Entity type distribution
# ---------------------------------------------------------------------------
type_dist: dict[str, int] = {}
for e in deduped:
    t = e["entity_type"]
    type_dist[t] = type_dist.get(t, 0) + 1

# ---------------------------------------------------------------------------
# Feature coverage stats
# ---------------------------------------------------------------------------
def has_nonzero_json_vec(row: dict, field: str) -> bool:
    try:
        vec = json.loads(row.get(field, "{}") or "{}")
    except json.JSONDecodeError:
        return False
    return any(float(v) > 0 for v in vec.values())

n_with_issues = sum(1 for e in deduped if has_nonzero_json_vec(e, "issue_vec"))
n_with_gov    = sum(1 for e in deduped if has_nonzero_json_vec(e, "gov_vec"))
n_lobbyists   = type_dist.get("lobbyist", 0)
issue_coverage_pct = round((n_with_issues / len(deduped)) * 100, 2) if deduped else 0
gov_coverage_pct = round((n_with_gov / len(deduped)) * 100, 2) if deduped else 0

# ---------------------------------------------------------------------------
# Write outputs
# ---------------------------------------------------------------------------

# 1. entities.csv / entity_nodes.csv  —  extended schema
node_fields = (
    # identity
    ["entity_id", "name", "entity_type", "industry",
     "total_spending", "filings_total", "state",
     "top_issue", "clients_count", "source",
     # lobbyist-specific
     "firm", "gov_positions_count",
     # log-normalised numerics
     "log_spend", "log_filings",
     # issue features
     "issue_count", "issue_codes", "issue_vec",
     "feature_clients_matched",
     "firm_issue_vec", "firm_gov_vec",
     "lobbyist_issue_vec", "lobbyist_gov_vec"]
    + GOV_COLS            # normalized GOV_* columns
    + ["gov_vec"]         # compact JSON gov vector
)

with open(OUT / "entity_nodes.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=node_fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(deduped)

# Canonical processed entity table consumed by every downstream stage.
# `entity_nodes.csv` is kept as a legacy alias for older scripts/docs.
with open(OUT / "entities.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=node_fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(deduped)

# 2. edges.csv
edge_fields = ["source_id", "source_name", "target_id", "target_name",
               "edge_type", "weight"]
with open(OUT / "edges.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=edge_fields)
    w.writeheader()
    w.writerows(edges)

merge_audit_fields = [
    "entity_a_id", "entity_b_id", "entity_a_name", "entity_b_name",
    "match_score", "merge_accepted",
]
with open(OUT / "dedup_merge_log.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=merge_audit_fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(merged_log)

with open(OUT / "dedup_merge_quarantine.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=merge_audit_fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(quarantine_log)

with open(OUT / "dedup_log.json", "w", encoding="utf-8") as f:
    json.dump(merged_log, f, indent=2)

# 3. embedding_matrix.csv
EMBED_GOV_WEIGHT = 3.0
EMBED_ISSUE_WEIGHT = 1.0
EMBED_NUMERIC_WEIGHT = 0.25

embedding_fields = (
    ["entity_id"]
    + [f"gov_{col}" for col in GOV_COLS]
    + [f"issue_{code}" for code in issue_vocab]
    + ["num_log_spend", "num_log_filings"]
)

max_log_spend = max((float(e.get("log_spend", 0) or 0) for e in deduped), default=0.0)
max_log_filings = max((float(e.get("log_filings", 0) or 0) for e in deduped), default=0.0)

embedding_rows = []
for e in deduped:
    issue_vec = json.loads(e.get("issue_vec", "{}") or "{}")
    gov_vec = json.loads(e.get("gov_vec", "{}") or "{}")
    row = {"entity_id": e["entity_id"]}
    for col in GOV_COLS:
        row[f"gov_{col}"] = round(float(gov_vec.get(col, 0.0)) * EMBED_GOV_WEIGHT, 6)
    for code in issue_vocab:
        row[f"issue_{code}"] = round(float(issue_vec.get(code, 0.0)) * EMBED_ISSUE_WEIGHT, 6)
    row["num_log_spend"] = round(
        (float(e.get("log_spend", 0) or 0) / max_log_spend) * EMBED_NUMERIC_WEIGHT,
        6,
    ) if max_log_spend else 0.0
    row["num_log_filings"] = round(
        (float(e.get("log_filings", 0) or 0) / max_log_filings) * EMBED_NUMERIC_WEIGHT,
        6,
    ) if max_log_filings else 0.0
    embedding_rows.append(row)

with open(OUT / "embedding_matrix.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=embedding_fields)
    w.writeheader()
    w.writerows(embedding_rows)

# 4. validation_report.json
validation = {
    "node_count":          len(deduped),
    "edge_count":          len(edges),
    "entity_type_dist":    type_dist,       # lobbyist / firm / client / gov_agency
    "edge_type_dist":      etype_counts,
    "dedup_merges":        len(merged_log),
    "dedup_quarantine_candidates": len(quarantine_log),
    "feature_coverage": {
        "nodes_with_issue_vec": n_with_issues,
        "nodes_with_gov_vec":   n_with_gov,
        "pct_nodes_with_issue_vec": issue_coverage_pct,
        "pct_nodes_with_gov_vec": gov_coverage_pct,
        "issue_vocab_size":     len(issue_vocab),
        "gov_feature_cols":     len(GOV_COLS),
    },
    "embedding_matrix": {
        "rows": len(embedding_rows),
        "features": len(embedding_fields) - 1,
        "weights": {
            "gov": EMBED_GOV_WEIGHT,
            "issue": EMBED_ISSUE_WEIGHT,
            "numeric": EMBED_NUMERIC_WEIGHT,
        },
    },
    "source_counts": {
        "firms":     len(firms),
        "clients":   len(clients),
        "gov":       len(gov),
        "lobbyists": len(lobbyists),
    },
    "output_dir": str(OUT),
}
with open(OUT / "validation_report.json", "w") as f:
    json.dump(validation, f, indent=2)

# 5. frontend_bundle.json  (compact — nodes + edge sample + meta)
bundle = {
    "meta": {
        "node_count":   len(deduped),
        "edge_count":   len(edges),
        "entity_types": type_dist,
        "issue_vocab":  issue_vocab,
        "gov_cols":     GOV_COLS,
        "embedding_matrix": "embedding_matrix.csv",
        "embedding_weights": validation["embedding_matrix"]["weights"],
    },
    "nodes": [
        {
            "id":        e["entity_id"],
            "label":     e["name"],
            "type":      e["entity_type"],
            "spend":     e["total_spending"],
            "issue":     e["top_issue"],
            "state":     e["state"],
            "firm":      e.get("firm", ""),
            "log_spend": e["log_spend"],
            "log_filings": e["log_filings"],
            "issue_vec": json.loads(e["issue_vec"]) if e.get("issue_vec") else {},
            "gov_vec":   json.loads(e["gov_vec"])   if e.get("gov_vec")   else {},
            "firm_issue_vec": json.loads(e["firm_issue_vec"]) if e.get("firm_issue_vec") else {},
            "firm_gov_vec": json.loads(e["firm_gov_vec"]) if e.get("firm_gov_vec") else {},
            "lobbyist_issue_vec": json.loads(e["lobbyist_issue_vec"]) if e.get("lobbyist_issue_vec") else {},
            "lobbyist_gov_vec": json.loads(e["lobbyist_gov_vec"]) if e.get("lobbyist_gov_vec") else {},
        }
        for e in deduped
    ],
    "edges": [
        {
            "src":    e["source_id"],
            "dst":    e["target_id"],
            "type":   e["edge_type"],
            "weight": e["weight"],
        }
        for e in edges[:100_000]   # cap at 100k for bundle size
    ],
}
with open(OUT / "frontend_bundle.json", "w") as f:
    json.dump(bundle, f, separators=(",", ":"))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n✓  entity_nodes.csv       {len(deduped):>7,} nodes  "
      f"({len(node_fields)} columns)")
print(f"✓  entities.csv           {len(deduped):>7,} nodes  "
      f"({len(node_fields)} columns)")
print(f"✓  edges.csv              {len(edges):>7,} edges")
print(f"✓  embedding_matrix.csv   {len(embedding_rows):>7,} rows   "
      f"({len(embedding_fields) - 1} features)")
print(f"✓  validation_report.json")
print(f"✓  frontend_bundle.json")

print(f"\nValidation:")
print(f"  Total nodes          : {len(deduped):,}")
print(f"  Total edges          : {len(edges):,}")

print(f"\nNode count by type:")
for label, key in [
    ("lobbyist", "lobbyist"),
    ("client", "client"),
    ("firm", "firm"),
    ("gov", "gov_agency"),
]:
    print(f"  {label:<15}: {type_dist.get(key, 0):,}")

print(f"\nFeature coverage:")
print(f"  Issue vocab           : {len(issue_vocab)} codes")
print(f"  Nodes with issue_vec  : {n_with_issues:,} ({issue_coverage_pct:.2f}%)")
print(f"  Nodes with gov_vec    : {n_with_gov:,} ({gov_coverage_pct:.2f}%)")
print(f"  GOV_* columns         : {len(GOV_COLS)}")

print(f"\nAll outputs → {OUT}")
