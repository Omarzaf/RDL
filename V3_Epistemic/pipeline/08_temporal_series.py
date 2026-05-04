import csv, json
from common import PROCESSED_DIR, FRONTEND_DIR, ensure_dirs
ensure_dirs()
def load_csv(p):
    with open(p) as f: return list(csv.DictReader(f)) if p.exists() else []
entities=load_csv(PROCESSED_DIR/'entities.csv'); coords={r['entity_id']:r for r in load_csv(PROCESSED_DIR/'umap_coords.csv')}; clusters={r['entity_id']:r for r in load_csv(PROCESSED_DIR/'clusters.csv')}
out=[]
for e in entities:
    for y in range(2018,2026):
        c=coords.get(e['entity_id'],{}); cl=clusters.get(e['entity_id'],{})
        out.append({'entity_id':e['entity_id'],'name':e['name'],'entity_type':e['entity_type'],'industry':e['industry'],'cluster_id':int(cl.get('cluster_id',0)),'cluster_label':cl.get('cluster_label','General'),'x':float(c.get('x',0)),'y':float(c.get('y',0)),'z':y,'size':float(e.get('total_spending',0)),'filings':int(float(e.get('filings_total',0))),'active':True,'gap_score':0.0,'revolving_door_count':0})
(FRONTEND_DIR/'entities_3d.json').write_text(json.dumps(out,indent=2))
(FRONTEND_DIR/'clusters.json').write_text(json.dumps(list(clusters.values()),indent=2))
for nm in ['gap_grid.json','revolving_vectors.json']:
    p=PROCESSED_DIR/nm
    (FRONTEND_DIR/nm).write_text(p.read_text() if p.exists() else '[]')
(FRONTEND_DIR/'trends.json').write_text(json.dumps([{'year':y} for y in range(2018,2026)],indent=2))
print('Saved frontend bundle data')
