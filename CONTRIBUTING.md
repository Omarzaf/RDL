# Contributing

This repository is prepared for public review, but the active product contract is
narrow: `V3_Epistemic` is the current map and `_archive/` is historical
reference.

## Local Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Required Checks

```bash
.venv/bin/python scripts/public_preflight.py
.venv/bin/python -m pytest
.venv/bin/python -m V3_Epistemic.pipeline.cli run --raw-dir "Raw Data" --out-dir V3_Epistemic/data --strict
```

## Contribution Rules

- Do not edit files under `Raw Data/` in place.
- Do not add secrets, private documents, office files, PDFs, or local app state.
- Keep public language exploratory and evidence-weighted.
- Keep generated artifacts reproducible from documented commands.
- Update docs and tests when changing pipeline contracts or frontend payloads.
