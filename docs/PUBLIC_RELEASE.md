# Public Release Checklist

Use this checklist before making the repository public or deploying a public
demo.

## Required Commands

```bash
.venv/bin/python scripts/public_preflight.py
.venv/bin/python -m pytest
.venv/bin/python -m V3_Epistemic.pipeline.cli run --raw-dir "Raw Data" --out-dir V3_Epistemic/data --strict
```

## Do Not Publish

- `.codex/`
- `.claude/settings.local.json`
- `.venv/` or any nested virtual environment
- `node_modules/`
- personal or private documents, including W2/tax/credential files
- PDF, DOCX, or RTF research/source documents unless the owner has verified
  redistribution rights
- `_archive/` dependency folders or legacy generated payloads

## Public Demo Scope

Publish the active static map and its active payload chunks:

- `V3_Epistemic/output/reliable_influence_map.html`
- `V3_Epistemic/output/vendor/three.min.js`
- `V3_Epistemic/data/frontend/scene_payload.json`
- `V3_Epistemic/data/frontend/search_index.json`
- `V3_Epistemic/data/frontend/adjacency_topk.json`
- `V3_Epistemic/data/frontend/frontend_manifest.json`

Keep `V3_Epistemic/data/reliable/` with the release when auditability matters.
Do not present `_archive/`, `V3_Epistemic/processed/`, or legacy preview HTML as
the active product.

## Public Caveats

- The map is exploratory and correlational.
- Government target-side exposure is not government spending.
- Model-derived gap leads are not evidence of absence, causality, or intent.
- Revolving-door records are career-transition records/events unless
  deduplication proves unique people.
- 2025 is partial unless refreshed source exports and validation say otherwise.
