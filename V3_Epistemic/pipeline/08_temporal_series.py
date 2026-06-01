"""
08_temporal_series.py
Packages all processed data into frontend-ready JSON files.
Produces the single entities_3d.json payload that the React app consumes.
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path

from config import RAW_DATA_DIR, PROCESSED_DIR, FRONTEND_DIR, YEARS

RAW = RAW_DATA_DIR
OUT = PROCESSED_DIR
FE  = FRONTEND_DIR
FE.mkdir(parents=True, exist_ok=True)

def load_raw(fname):
    with open(RAW / fname) as f:
        return json.load(f)

coords    = pd.read_csv(OUT / "umap_coords.csv")
entities  = pd.read_csv(OUT / "entities.csv")
clusters  = pd.read_csv(OUT / "clusters.csv")
top_gaps  = json.load(open(OUT / "top_gaps.json"))
rev_vecs  = json.load(open(OUT / "revolving_vectors.json"))
yearly_c  = json.load(open(OUT / "yearly_currents.json"))
cluster_p = json.load(open(OUT / "cluster_profiles.json"))
trends_raw = load_raw("trends.json")
industries_raw = load_raw("industries.json")

# ── Merge everything ──────────────────────────────────────────────────────────
merged = coords.merge(entities.drop(columns=["name"]), on="entity_id")
merged = merged.merge(clusters[["entity_id","cluster_id","cluster_label"]], on="entity_id")

# Load per-year spending from industries (for scaling node sizes over time)
yearly_scale = {yr_row["year"]: yr_row["totalIncome"] for yr_row in trends_raw}
base_income = max(yearly_scale.values())

# ── Build entities_3d.json ───────────────────────────────────────────────────
print(f"Building 3D entity records for {len(merged)} entities × {len(YEARS)} years...")

records = []
for _, ent in merged.iterrows():
    spending = float(ent.get("total_spending", 0) or 0)
    filings  = int(ent.get("filings_total", 0) or 0)
    cluster_id = int(ent.get("cluster_id", 0))

    # Gap score: look up nearest gap region
    ex, ey = float(ent["x"]), float(ent["y"])
    gap_score = 0.0
    for gap in top_gaps:
        dist = ((gap["centroid_x"] - ex)**2 + (gap["centroid_y"] - ey)**2)**0.5
        if dist < 0.2:
            gap_score = gap["gap_score"] * max(0, 1 - dist/0.2)
            break

    # Revolving door count
    rd_count = 0
    for v in rev_vecs:
        if (abs(v["src_x"] - ex) < 0.1 and abs(v["src_y"] - ey) < 0.1) or \
           (abs(v["tgt_x"] - ex) < 0.1 and abs(v["tgt_y"] - ey) < 0.1):
            rd_count += 1

    for yr in YEARS:
        # Scale aggregate spending only by the macro market trend. This is not
        # entity-year observed spend, so mark it as aggregate repeated.
        yr_factor = yearly_scale.get(yr, base_income) / base_income
        yr_spending = spending * yr_factor

        records.append({
            "entity_id":    ent["entity_id"],
            "name":         ent["name"],
            "entity_type":  ent["entity_type"],
            "industry":     str(ent.get("industry", "")),
            "cluster_id":   cluster_id,
            "cluster_label": str(ent.get("cluster_label", "")),
            "x":            round(float(ent["x"]), 4),
            "y":            round(float(ent["y"]), 4),
            "z":            yr,
            "size":         round(float(yr_spending), 2),
            "filings":      filings,
            "active":       True,
            "gap_score":    round(float(gap_score), 4),
            "revolving_door_count": rd_count,
            "temporal_value_type": "aggregate_repeated",
        })

print(f"Total records: {len(records)}")

# Write in chunks to avoid memory issues
with open(FE / "entities_3d.json","w") as f:
    json.dump(records, f, separators=(",",":"))
print(f"Saved: entities_3d.json ({len(records)} records, "
      f"{Path(FE / 'entities_3d.json').stat().st_size / 1e6:.1f} MB)")

# ── clusters.json ─────────────────────────────────────────────────────────────
clusters_fe = []
for cid_str, prof in cluster_p.items():
    clusters_fe.append({
        "cluster_id":    int(cid_str),
        "label":         prof["label"],
        "member_count":  prof["member_count"],
        "total_spending": prof["total_spending"],
        "centroid_x":    prof["centroid_x"],
        "centroid_y":    prof["centroid_y"],
        "entity_types":  prof["entity_types"],
    })
clusters_fe.sort(key=lambda c: -c["total_spending"])
with open(FE / "clusters.json","w") as f:
    json.dump(clusters_fe, f, indent=2)
print(f"Saved: clusters.json ({len(clusters_fe)} clusters)")

# ── gap_grid.json (copy from processed) ──────────────────────────────────────
import shutil
shutil.copy(OUT / "gap_grid.json", FE / "gap_grid.json")
print(f"Saved: gap_grid.json")

# ── revolving_vectors.json (sample for frontend) ─────────────────────────────
with open(FE / "revolving_vectors.json","w") as f:
    json.dump(rev_vecs[:500], f, separators=(",",":"))
print(f"Saved: revolving_vectors.json (500 sample vectors)")

# ── trends.json ───────────────────────────────────────────────────────────────
trends_fe = {
    "yearly": trends_raw,
    "industries": [
        {"name": ind["name"], "totalSpending": ind["totalSpending"],
         "totalFilings": ind["totalFilings"]}
        for ind in industries_raw
    ],
    "top_gaps": top_gaps,
    "yearly_currents": [
        {"year": int(yr), **{k:v for k,v in data.items() if k != "sample_vectors"}}
        for yr, data in yearly_c.items()
    ],
}
with open(FE / "trends.json","w") as f:
    json.dump(trends_fe, f, indent=2)
print(f"Saved: trends.json")

# ── Final summary ─────────────────────────────────────────────────────────────
print("\n" + "="*55)
print("PHASE 1 COMPLETE — FINAL SUMMARY")
print("="*55)
print(f"  Entities:           {len(merged):,}")
print(f"  Years covered:      2018–2025 ({len(YEARS)} years)")
print(f"  Clusters found:     {len(clusters_fe)}")
print(f"  Epistemic gaps:     {len(top_gaps)}")
print(f"  Revolving door:     {len(rev_vecs):,} movement vectors")
print(f"  Total 3D records:   {len(records):,}")
print(f"\nFrontend data ready in: V3_Epistemic/data/frontend/")
print("  entities_3d.json, clusters.json, gap_grid.json,")
print("  revolving_vectors.json, trends.json")
