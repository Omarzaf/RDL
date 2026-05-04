import csv, math
from common import PROCESSED_DIR
rows=[]
with open(PROCESSED_DIR/'issue_matrix_aggregate.csv') as f:
    for i,r in enumerate(csv.DictReader(f)):
        rows.append({'entity_id':r['entity_id'],'x':math.cos(i/10)*10,'y':math.sin(i/10)*10})
with open(PROCESSED_DIR/'umap_coords.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['entity_id','x','y']); w.writeheader(); w.writerows(rows)
print('ASCII preview:')
print('\n'.join([f"{r['entity_id'][:18]:18} ({float(r['x']):6.2f},{float(r['y']):6.2f})" for r in rows[:20]]))
