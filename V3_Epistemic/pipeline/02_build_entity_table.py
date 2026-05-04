import csv, json, difflib
from common import ensure_dirs, load_json, PROCESSED_DIR, slug
ensure_dirs(); rows=[]
for r in (load_json('top_firms') or []): rows.append({'name':r.get('name'),'entity_type':'firm','industry':'Unknown','total_spending':r.get('totalIncome',0) or 0,'year_first':2018,'year_last':2025,'filings_total':r.get('filings',0) or 0,'state':''})
for r in (load_json('top_clients') or []): rows.append({'name':r.get('name'),'entity_type':'client','industry':'Unknown','total_spending':r.get('totalSpending',0) or 0,'year_first':2018,'year_last':2025,'filings_total':r.get('filings',0) or 0,'state':r.get('state','') or ''})
for r in (load_json('gov_entities') or []): rows.append({'name':r.get('name'),'entity_type':'gov_agency','industry':'Government','total_spending':r.get('spending',0) or 0,'year_first':2018,'year_last':2025,'filings_total':r.get('filings',0) or 0,'state':'DC'})
clean=[]; log=[]
for r in rows:
    if not r['name']: continue
    m=None
    for c in clean:
        if difflib.SequenceMatcher(None,r['name'].lower(),c['name'].lower()).ratio()>=0.88: m=c; break
    if m:
        m['total_spending']+=float(r['total_spending']); m['filings_total']+=int(r['filings_total']); log.append({'from':r['name'],'to':m['name']})
    else: clean.append(r)
for c in clean: c['entity_id']=f"{c['entity_type']}_{slug(c['name'])}"
fields=['entity_id','name','entity_type','industry','total_spending','year_first','year_last','filings_total','state']
with open(PROCESSED_DIR/'entities.csv','w',newline='') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(clean)
(PROCESSED_DIR/'dedup_log.json').write_text(json.dumps(log,indent=2)); print('Saved entities.csv')
