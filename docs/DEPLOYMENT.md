# Deployment

Deployment is static-file based. Regenerate the data first:

```bash
python -m V3_Epistemic.pipeline.cli run --raw-dir "Raw Data" --out-dir V3_Epistemic/data --strict
```

Deploy these paths together:

- `V3_Epistemic/output/reliable_influence_map.html`
- `V3_Epistemic/output/vendor/three.min.js`
- `V3_Epistemic/data/frontend/scene_payload.json`
- `V3_Epistemic/data/frontend/search_index.json`
- `V3_Epistemic/data/frontend/adjacency_topk.json`
- `V3_Epistemic/data/frontend/frontend_manifest.json`

Keep `V3_Epistemic/data/reliable/` with the release when auditability matters.
It contains full CSVs, the full payload, quality reports, and validation reports.

Do not deploy legacy/reference artifacts such as `_archive/`,
`V3_Epistemic/processed/`, `V3_Epistemic/output/dc_epistemic_map_mvp.html`, or
`V3_Epistemic/output/lobbying_influence_preview.html` as the active product.

The static map works from the repository root path and from the `V3_Epistemic/`
subroot because payload URLs are relative to the HTML file.
