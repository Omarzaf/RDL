# RDL Evidence Map

`V3_Epistemic` is the active product surface for this workspace. It ships a
static, offline-friendly DC lobbying evidence map backed by a canonical Python
pipeline. `_archive/`, old prompt files, and
`V3_Epistemic/output/dc_epistemic_map_mvp.html` are legacy reference material.

## Active Surface

- Pipeline: `V3_Epistemic/pipeline/`
- Canonical processed outputs: `V3_Epistemic/data/processed/`
- Reliable publication outputs: `V3_Epistemic/data/reliable/`
- Frontend chunks: `V3_Epistemic/data/frontend/`
- Static map: `V3_Epistemic/output/reliable_influence_map.html`
- Project rules: `AGENTS.md`

## Public Release Files

- License stance: `LICENSE.md`
- Citation metadata: `CITATION.cff`
- Contribution guide: `CONTRIBUTING.md`
- Code of conduct: `CODE_OF_CONDUCT.md`
- Security policy: `SECURITY.md`
- Support guide: `SUPPORT.md`
- Public release certificate: `PUBLIC_RELEASE_CERTIFICATE.md`

## Run

Install dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run the canonical pipeline:

```bash
python -m V3_Epistemic.pipeline.cli run --raw-dir "Raw Data" --out-dir V3_Epistemic/data --strict
```

`Raw Data/` is read-only evidence. Derived files are written under
`V3_Epistemic/data/processed`, `V3_Epistemic/data/reliable`, and
`V3_Epistemic/data/frontend`.

Serve the map from the repository root:

```bash
python3 -m http.server 8765
```

Open:

```text
http://127.0.0.1:8765/V3_Epistemic/output/reliable_influence_map.html
```

Serving from inside `V3_Epistemic/` also works:

```text
http://127.0.0.1:8765/output/reliable_influence_map.html
```

## Validate

```bash
pytest
```

The tests check canonical stage wiring, generated payload schemas, nondegenerate
analytics, revolving-door endpoint hygiene, frontend payload loading, and public
language constraints.

## Interpretation

The map separates observed, derived, and modeled fields. It should be read as a
relationship and evidence-weighted prominence tool, not as a causal claim.
Government nodes use lobbying exposure directed at an agency, not agency
spending. Gap values are model-derived gap leads. 2025 is partial unless the
raw source set is refreshed and validated as complete.

See `docs/` for setup, reproducibility, provenance, methodology,
interpretation, privacy, security, deployment, and legacy artifact policy. The
repository license stance is documented in `LICENSE.md`.
