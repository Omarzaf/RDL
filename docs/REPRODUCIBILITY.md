# Reproducibility

Install the pinned dependency set with:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
```

The canonical command is:

```bash
.venv/bin/python -m V3_Epistemic.pipeline.cli run --raw-dir "Raw Data" --out-dir V3_Epistemic/data --strict
```

The CLI writes `V3_Epistemic/data/run_manifest.json` with input file checksums,
the command, Python version, stage list, output directories, and validation
status. Generated artifacts should be committed only when the manifest reflects
the current raw inputs and strict validation passes.

`requirements.txt` names the direct runtime dependencies and applies
`constraints.txt`. `requirements-dev.txt` adds the test runner used by CI and
the documented verification flow.

The layout stage uses a deterministic seed and records the embedding method in
`data/processed/embedding_manifest.json`. If UMAP is unavailable, the pipeline
falls back to a deterministic dimensionality-reduction method and records
`coordinate_source`.

Release validation uses the public preflight script and lightweight contract
tests. Full raw-data regeneration remains a manual or scheduled strict check
because it can be slower than unit-level validation.
