import csv, json
from common import PROCESSED_DIR
coords=[]
with open(PROCESSED_DIR/'umap_coords.csv') as f: coords=list(csv.DictReader(f))
xs=[float(r['x']) for r in coords] or [0.0]; ys=[float(r['y']) for r in coords] or [0.0]
xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys)
grid=[]
for i in range(20):
    for j in range(20):
        x=xmin+(xmax-xmin)*(i/19 if 19 else 0); y=ymin+(ymax-ymin)*(j/19 if 19 else 0)
        gap=abs(x*y)/(1+abs(x)+abs(y)); grid.append({'x':x,'y':y,'gap_score':gap})
top=sorted(grid,key=lambda z:z['gap_score'], reverse=True)[:10]
(PROCESSED_DIR/'gap_grid.json').write_text(json.dumps({'grid':grid},indent=2))
(PROCESSED_DIR/'top_gaps.json').write_text(json.dumps(top,indent=2))
print('Saved gap analysis')
