import csv
from common import PROCESSED_DIR
coords=[]
with open(PROCESSED_DIR/'umap_coords.csv') as f: coords=list(csv.DictReader(f))
out=[]
for r in coords:
    x=float(r['x']); cid=0 if x<0 else 1; label='Public Sector Orbit' if cid==0 else 'Commercial Influence Orbit'
    out.append({'entity_id':r['entity_id'],'cluster_id':cid,'cluster_label':label})
with open(PROCESSED_DIR/'clusters.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['entity_id','cluster_id','cluster_label']); w.writeheader(); w.writerows(out)
print('Cluster labels generated')
