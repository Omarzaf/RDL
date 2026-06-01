# Public Release Certificate

Date: 2026-06-01

Repository: `Omarzaf/RDL`

## Certified Release Surface

This public package is prepared around the active V3 static map:

- `V3_Epistemic/output/reliable_influence_map.html`
- `V3_Epistemic/output/vendor/three.min.js`
- `V3_Epistemic/data/frontend/scene_payload.json`
- `V3_Epistemic/data/frontend/search_index.json`
- `V3_Epistemic/data/frontend/adjacency_topk.json`
- `V3_Epistemic/data/frontend/frontend_manifest.json`

The repository also includes pipeline code, release/audit data under
`V3_Epistemic/data/reliable/`, processed validation artifacts, source JSON
exports under `Raw Data/`, tests, and public documentation.

## Checks Run

```bash
.venv/bin/python scripts/public_preflight.py
.venv/bin/python -m pytest
.venv/bin/python -m V3_Epistemic.pipeline.cli run --raw-dir "Raw Data" --out-dir V3_Epistemic/data --strict
```

Latest known outcomes:

- public preflight passed
- tests passed: `7 passed`
- strict pipeline validation passed
- frontend manifest paths resolve
- active map loads from a local HTTP server

## Public-Use Caveats

- The map is exploratory and correlational.
- Government target-side exposure is not government spending.
- Model-derived gap leads are not evidence of absence, causality, intent, or
  wrongdoing.
- Revolving-door records are career-transition records/events unless
  deduplication proves unique people.
- 2025 is partial unless refreshed source exports and validation reports say
  otherwise.
- The full searchable graph includes inferred placements; the initial scene is
  capped for browser performance.

## Withheld From Public Package

The public preflight excludes local app state, virtual environments,
dependency folders, internal prompt notes, private/copyright-sensitive office
documents, PDFs, archives, and demo capture videos.
