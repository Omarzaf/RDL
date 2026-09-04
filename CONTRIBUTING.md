# Contributing

This repository is prepared for public review, but the active product contract is
narrow: `V3_Epistemic` is the current map and `_archive/` is historical
reference.

## Local Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
```

## Required Checks

For documentation, tests, or public-surface changes:

```bash
.venv/bin/python scripts/public_preflight.py
.venv/bin/python -m pytest
```

For pipeline or generated-data refresh work, after the standard checks:

```bash
.venv/bin/python -m V3_Epistemic.pipeline.cli run --raw-dir "Raw Data" --out-dir V3_Epistemic/data --strict
```

## Contribution Rules

- Do not edit files under `Raw Data/` in place.
- Do not add secrets, private documents, office files, PDFs, or local app state.
- Keep public language exploratory and evidence-weighted.
- Keep generated artifacts reproducible from documented commands.
- Keep `requirements.txt`, `requirements-dev.txt`, and `constraints.txt` in sync
  when dependency versions change.
- Update docs and tests when changing pipeline contracts or frontend payloads.
