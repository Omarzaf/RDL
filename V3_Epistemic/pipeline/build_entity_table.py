#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from collections import Counter

REQUIRED = [
    'top-clients.json','industries.json','revolving-door.json','gov-entities.json','trends.json',
    'lobbying-vs-contracts.json','text-analysis.json','filing-activity.json'
]


def load(input_dir: Path):
    data = {}
    missing = []
    for fn in REQUIRED:
        p = input_dir / fn
        if not p.exists():
            missing.append(fn)
            continue
        data[fn] = json.loads(p.read_text())
    if missing:
        raise FileNotFoundError('Missing required inputs: ' + ', '.join(missing))
    return data


def sid(tp, name):
    key = ''.join(ch.lower() if ch.isalnum() else '_' for ch in str(name)).strip('_')[:80]
    return f'{tp}::{key}'


def year_weights(trends):
    ys = [int(r['year']) for r in trends]
    inc = {int(r['year']): float(r.get('totalIncome', 0) or 0) for r in trends}
    fil = {int(r['year']): float(r.get('filings', 0) or 0) for r in trends}
    s1, s2 = sum(inc.values()) or 1.0, sum(fil.values()) or 1.0
    return ys, {y: inc[y] / s1 for y in ys}, {y: fil[y] / s2 for y in ys}


def alloc(total, years, w):
    denom = sum(w.get(y, 0) for y in years) or 0
    if denom <= 0:
        return {y: (total / len(years) if years else 0.0) for y in years}
    return {y: total * (w.get(y, 0) / denom) for y in years}


def build_minimal(data):
    years, income_w, filing_w = year_weights(data['trends.json'])
    clients = data['top-clients.json']
    govs = data['gov-entities.json']
    rd = data['revolving-door.json']

    entities = {}
    edges = []

    gov_by_name = {}
    for g in govs:
        gid = sid('gov_entity', g.get('name', 'Unknown Government'))
        gname = g.get('name', 'Unknown Government')
        gov_by_name[gname] = gid
        entities[gid] = dict(entity_id=gid, name=gname, type='gov_entity', active_years=years, spend=float(g.get('spending', 0) or 0), filings=float(g.get('filings', 0) or 0), issues={i.get('code'): float(i.get('count', 0) or 0) for i in g.get('topIssues', []) if i.get('code')}, gov_targets={}, contracts=0.0, roi=0.0, revolving_door_count=0.0)

    client_by_name = {}
    for c in clients:
        cname = c.get('name', 'Unknown Client')
        cid = sid('client', cname)
        yrs = sorted({int(y) for y in (c.get('years', []) or []) if y}) or years
        client_by_name[str(cname).upper()] = cid
        entities[cid] = dict(entity_id=cid, name=cname, type='client', active_years=yrs, spend=float(c.get('totalSpending', 0) or 0), filings=float(c.get('filings', 0) or 0), issues={k: 1.0 for k in c.get('issues', [])}, gov_targets={}, contracts=0.0, roi=0.0, revolving_door_count=0.0)

    for g in govs:
        gname = g.get('name', 'Unknown Government')
        gid = gov_by_name[gname]
        for tc in g.get('topClients', []) or []:
            cid = client_by_name.get(str(tc.get('name', '')).upper())
            if not cid:
                continue
            w = float(tc.get('spending', 0) or 1.0)
            entities[cid]['gov_targets'][gname] = entities[cid]['gov_targets'].get(gname, 0.0) + w
            edges.append(dict(source_entity_id=cid, target_entity_id=gid, relation='client_to_gov_entity', weight=w))

    firm_by_name = {}
    for row in rd:
        lname = row.get('name', 'Unknown Lobbyist')
        lid = sid('lobbyist', lname)
        if lid not in entities:
            entities[lid] = dict(entity_id=lid, name=lname, type='lobbyist', active_years=years, spend=0.0, filings=float(row.get('filings', 0) or 0), issues={}, gov_targets={}, contracts=0.0, roi=0.0, revolving_door_count=float(len(row.get('positions', []) or [])))
        for f in row.get('firms', []) or []:
            fid = firm_by_name.setdefault(f, sid('firm', f))
            if fid not in entities:
                entities[fid] = dict(entity_id=fid, name=f, type='firm', active_years=years, spend=0.0, filings=0.0, issues={}, gov_targets={}, contracts=0.0, roi=0.0, revolving_door_count=0.0)
            edges.append(dict(source_entity_id=lid, target_entity_id=fid, relation='lobbyist_to_firm', weight=1.0))
            for cn in row.get('clients', []) or []:
                cid = client_by_name.get(str(cn).upper())
                if cid:
                    edges.append(dict(source_entity_id=fid, target_entity_id=cid, relation='firm_to_client', weight=1.0))

    for m in (data['lobbying-vs-contracts.json'].get('matches') or []):
        cid = client_by_name.get(str(m.get('name', '')).upper())
        if cid:
            entities[cid]['contracts'] = float(m.get('federalContracts', 0) or 0)
            entities[cid]['roi'] = float(m.get('roi', 0) or 0)

    rows = []
    for e in entities.values():
        salloc = alloc(e['spend'], e['active_years'], income_w)
        falloc = alloc(e['filings'], e['active_years'], filing_w)
        for y in e['active_years']:
            rows.append(dict(entity_id=e['entity_id'], type=e['type'], year=int(y), spend=float(salloc.get(y, 0)), filings=float(falloc.get(y, 0)), issues=e['issues'], gov_targets=e['gov_targets'], contracts=e['contracts'], roi=e['roi'], revolving_door_count=e['revolving_door_count'], name=e['name']))

    dedup_edges = []
    seen = set()
    for e in edges:
        k = (e['source_entity_id'], e['target_entity_id'], e['relation'])
        if k in seen:
            continue
        seen.add(k)
        dedup_edges.append(e)
    return rows, dedup_edges


def validate(nodes, edges):
    ent = {n['entity_id'] for n in nodes}
    dup = len(nodes) - len({(n['entity_id'], n['year']) for n in nodes})
    miss_src = sum(1 for e in edges if e['source_entity_id'] not in ent)
    miss_tgt = sum(1 for e in edges if e['target_entity_id'] not in ent)
    return {
        'rows': len(nodes),
        'edges': len(edges),
        'duplicate_entity_year': dup,
        'missing_edge_sources': miss_src,
        'missing_edge_targets': miss_tgt,
    }


def write_outputs(nodes, edges, report, out: Path, minimal: bool):
    out.mkdir(parents=True, exist_ok=True)
    node_fields = ['entity_id','type','year','spend','filings','issues','gov_targets','contracts','roi','revolving_door_count','name']
    with (out / 'entity_nodes.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=node_fields)
        w.writeheader()
        for n in nodes:
            r = n.copy()
            r['issues'] = json.dumps(r['issues'], sort_keys=True)
            r['gov_targets'] = json.dumps(r['gov_targets'], sort_keys=True)
            w.writerow(r)

    edge_fields = ['source_entity_id','target_entity_id','relation','weight']
    with (out / 'edges.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=edge_fields)
        w.writeheader()
        for e in edges:
            w.writerow(e)

    (out / 'validation_report.json').write_text(json.dumps(report, indent=2))
    (out / 'frontend_bundle.json').write_text(json.dumps({'nodes': nodes, 'edges': edges, 'mode': 'minimal' if minimal else 'full', 'notes': 'Correlational graph for exploratory analysis only.'}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input-dir', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--skip-embeddings', action='store_true')
    ap.add_argument('--minimal', action='store_true', help='Run with pure standard library (no pandas/numpy/sklearn).')
    args = ap.parse_args()

    data = load(Path(args.input_dir))

    if args.minimal:
        nodes, edges = build_minimal(data)
    else:
        # full mode currently delegates to minimal unless optional stack is installed
        try:
            import pandas  # noqa: F401
            import numpy  # noqa: F401
            nodes, edges = build_minimal(data)
        except Exception:
            raise RuntimeError('Full mode requires pandas/numpy stack. Use --minimal in offline environments.')

    report = validate(nodes, edges)
    write_outputs(nodes, edges, report, Path(args.output_dir), args.minimal)

    type_dist = Counter(n['type'] for n in nodes)
    print(f"node_count={len(nodes)}")
    print(f"edge_count={len(edges)}")
    print(f"entity_type_distribution={dict(type_dist)}")
    print("embeddings_generated=False (minimal/offline mode)")


if __name__ == '__main__':
    main()
