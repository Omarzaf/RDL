# Legacy Processed Outputs

This directory is reference-only. The active pipeline writes current generated
data under `V3_Epistemic/data/processed/`, `V3_Epistemic/data/reliable/`, and
`V3_Epistemic/data/frontend/`.

Do not use files in this directory for release claims, frontend payloads, or
validation. Regenerate current artifacts with:

```bash
.venv/bin/python -m V3_Epistemic.pipeline.cli run --raw-dir "Raw Data" --out-dir V3_Epistemic/data --strict
```
