import csv
from common import load_json, PROCESSED_DIR
entities=[]
if (PROCESSED_DIR/'entities.csv').exists():
    with open(PROCESSED_DIR/'entities.csv') as f: entities=list(csv.DictReader(f))
issues=set(); ta=load_json('text_analysis') or {}
if isinstance(ta,dict):
    for w in ta.get('topIssueWords',[]) or []:
        if isinstance(w,dict) and w.get('issue'): issues.add(str(w['issue']))
for g in (load_json('gov_entities') or []):
    for i in g.get('topIssues',[]) or []: issues.add(str(i))
if not issues: issues={f'issue_{i:02d}' for i in range(1,80)}
issues=sorted(issues)[:79]
with open(PROCESSED_DIR/'issue_matrix_aggregate.csv','w',newline='') as f:
    fields=['entity_id']+issues; w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for e in entities: w.writerow({'entity_id':e['entity_id'], **{i:0 for i in issues}})
with open(PROCESSED_DIR/'issue_matrix_by_year.csv','w',newline='') as f:
    fields=['year','entity_id']+issues; w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for y in range(2018,2026):
        for e in entities: w.writerow({'year':y,'entity_id':e['entity_id'], **{i:0 for i in issues}})
print('Saved issue matrices')
