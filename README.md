# RDL Evidence Map

`V3_Epistemic` is the active product surface for this workspace. It ships a
static, offline-friendly DC lobbying evidence map backed by a canonical Python
pipeline. `_archive/`, old prompt files, and
`V3_Epistemic/output/dc_epistemic_map_mvp.html` are legacy reference material.

## Status

Public research/demo repository. The active public surface is the static V3 map
plus the Python pipeline and validation artifacts that explain how it was
generated. It is suitable for review and reproducibility checks, not as a live
service or automated monitoring product.

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

## Setup

Use Python 3.11+ for clean-checkout verification and CI parity.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
```

## Verification

For ordinary documentation, test, and public-surface changes:

```bash
.venv/bin/python -m pytest
.venv/bin/python scripts/public_preflight.py
```

Run the canonical strict pipeline only when raw-source exports are complete and
the change affects generated data or pipeline contracts:

```bash
.venv/bin/python -m V3_Epistemic.pipeline.cli run --raw-dir "Raw Data" --out-dir V3_Epistemic/data --strict
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

The tests check canonical stage wiring, generated payload schemas, nondegenerate
analytics, revolving-door endpoint hygiene, frontend payload loading, and public
language constraints. `scripts/public_preflight.py` checks the public release
surface, required docs, and tracked-file hygiene.

## Interpretation

The map separates observed, derived, and modeled fields. It should be read as a
relationship and evidence-weighted prominence tool, not as a causal claim.
Government nodes use lobbying exposure directed at an agency, not agency
spending. Gap values are model-derived gap leads. 2025 is partial unless the
raw source set is refreshed and validated as complete.

## Limitations

- The map is exploratory and correlational; it does not establish causality or
  wrongdoing.
- Large generated payloads under `V3_Epistemic/data/reliable/` and
  `V3_Epistemic/data/processed/` are reproducible artifacts, not the primary
  day-to-day release surface.
- Strict regeneration depends on owner-validated raw exports and is heavier
  than the standard PR checks.

## Support And Maintainer

Maintainer: Omar Zafar.

Use the repository issue templates for bugs, data/methodology corrections, and
public discussion. Use the private security path in `SECURITY.md` for
vulnerability reports.

## License And Data Terms

Code, prose, generated data, and upstream-source materials do not share a
single open license here. Follow the restricted custom terms in `LICENSE.md`
exactly, and verify upstream redistribution terms before reusing generated or
source-derived data.

See `docs/` for setup, reproducibility, provenance, methodology,
interpretation, privacy, security, deployment, and legacy artifact policy. The
repository license stance is documented in `LICENSE.md`.
