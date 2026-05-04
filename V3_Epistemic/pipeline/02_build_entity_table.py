import csv
import json
import re
from rapidfuzz import fuzz
from common import ensure_dirs, load_json, PROCESSED_DIR, slug, require_raw_inputs

ensure_dirs()
require_raw_inputs()

SUFFIXES = {' llc', ' inc', ' ltd', ' llp', ' plc', ' corp', ' corporation', ' co', ' company'}


def norm(name: str) -> str:
    n = re.sub(r'[^A-Za-z0-9 ]+', ' ', (name or '').upper())
    n = re.sub(r'\s+', ' ', n).strip()
    for s in SUFFIXES:
        if n.endswith(s.upper()):
            n = n[: -len(s)].strip()
    return n

rows = []
for r in (load_json('top_firms') or []):
    rows.append({'name': r.get('name', ''), 'entity_type': 'firm', 'industry': 'Law & Lobbying', 'total_spending': float(r.get('totalIncome', 0) or 0), 'year_first': 2018, 'year_last': 2025, 'filings_total': int(r.get('filings', 0) or 0), 'state': ''})
for r in (load_json('top_clients') or []):
    rows.append({'name': r.get('name', ''), 'entity_type': 'client', 'industry': 'Other / Multi-sector', 'total_spending': float(r.get('totalSpending', 0) or 0), 'year_first': 2018, 'year_last': 2025, 'filings_total': int(r.get('filings', 0) or 0), 'state': r.get('state', '') or ''})
for r in (load_json('gov_entities') or []):
    rows.append({'name': r.get('name', ''), 'entity_type': 'gov_agency', 'industry': 'Government & Nonprofit', 'total_spending': float(r.get('spending', 0) or 0), 'year_first': 2018, 'year_last': 2025, 'filings_total': int(r.get('filings', 0) or 0), 'state': 'DC'})

clean = []
log = []
for r in rows:
    if not r['name']:
        continue
    key = norm(r['name'])
    merged = None
    for c in clean:
        score = fuzz.ratio(key, c['norm']) / 100
        if score >= 0.88:
            merged = c
            break
    if merged:
        merged['total_spending'] += r['total_spending']
        merged['filings_total'] += r['filings_total']
        merged['year_first'] = min(merged['year_first'], r['year_first'])
        merged['year_last'] = max(merged['year_last'], r['year_last'])
        log.append({'from': r['name'], 'to': merged['name'], 'score': score})
    else:
        clean.append({**r, 'norm': key})

for c in clean:
    c['entity_id'] = f"{c['entity_type']}_{slug(c['name'])}"
    c.pop('norm', None)

fields = ['entity_id', 'name', 'entity_type', 'industry', 'total_spending', 'year_first', 'year_last', 'filings_total', 'state']
with open(PROCESSED_DIR / 'entities.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(clean)

(PROCESSED_DIR / 'dedup_log.json').write_text(json.dumps(log, indent=2))
print(f'Saved entities.csv with {len(clean)} entities')
