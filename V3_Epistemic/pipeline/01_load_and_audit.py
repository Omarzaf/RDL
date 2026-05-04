import json
from common import INPUT_FILES, ensure_dirs, load_json, PROCESSED_DIR, require_raw_inputs


def recs(x):
    return x if isinstance(x, list) else ([x] if isinstance(x, dict) else [])


ensure_dirs()
require_raw_inputs()
report = {"files": {}, "missing_fields": []}
for key in INPUT_FILES:
    data = load_json(key)
    rows = recs(data)
    fields = sorted({k for r in rows if isinstance(r, dict) for k in r.keys()})
    null = {f: 0 for f in fields}
    years = set()
    for r in rows:
        if not isinstance(r, dict):
            continue
        for f in fields:
            if r.get(f) is None:
                null[f] += 1
        for k, v in r.items():
            if 'year' in k.lower() and isinstance(v, int):
                years.add(v)
    report['files'][key] = {
        'records': len(rows),
        'fields': fields,
        'null_rates': {f: (null[f] / max(1, len(rows))) for f in fields},
        'year_coverage': sorted(years)
    }

required = {'top_firms': ['name', 'totalIncome'], 'top_clients': ['name', 'totalSpending'], 'gov_entities': ['name']}
for k, req in required.items():
    has = set(report['files'].get(k, {}).get('fields', []))
    for f in req:
        if f not in has:
            report['missing_fields'].append({'file': k, 'field': f})

out = PROCESSED_DIR / 'audit_report.json'
out.write_text(json.dumps(report, indent=2))
print(f'Saved {out}')
