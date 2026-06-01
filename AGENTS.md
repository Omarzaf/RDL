# Agent Instructions

This repository's active product is the V3 standalone lobbying-network map in
`V3_Epistemic`. Treat `_archive/`, old prompt files, and
`V3_Epistemic/output/dc_epistemic_map_mvp.html` as historical reference unless a
task explicitly says otherwise.

## Project Purpose

Build a reproducible, evidence-weighted DC lobbying relationship map suitable
for public demo and research review. The product must make data provenance,
model limits, confidence, and generated-artifact freshness visible instead of
using visual polish to cover weak evidence.

## Repo Structure

- `Raw Data/`: read-only source evidence.
- `V3_Epistemic/pipeline/`: canonical Python stages and CLI.
- `V3_Epistemic/data/processed/`: layout-stage outputs keyed by `entity_id`.
- `V3_Epistemic/data/reliable/`: release/audit outputs keyed by `canonical_id`.
- `V3_Epistemic/data/frontend/`: active static-map chunks.
- `V3_Epistemic/output/`: active HTML, output docs, and vendored runtime files.
- `docs/`: setup, provenance, methodology, interpretation, deployment,
  privacy, and security notes.
- `tests/`: contract and regression tests for known failure modes.
- `_archive/`: historical references only.

## Run Commands

- Install dependencies:
  `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- Run the canonical pipeline:
  `.venv/bin/python -m V3_Epistemic.pipeline.cli run --raw-dir "Raw Data" --out-dir V3_Epistemic/data --strict`
- Run the legacy-compatible wrapper:
  `sh run_pipeline.sh`
- Serve the active map from the repository root:
  `python3 -m http.server 8765`
- Active map URL from the repository root:
  `http://127.0.0.1:8765/V3_Epistemic/output/reliable_influence_map.html`
- Frontend build command:
  no npm build is required for the active static map. Serve the repository root
  with the command above.
- Run tests:
  `.venv/bin/python -m pytest`
- Validation command:
  `.venv/bin/python -m V3_Epistemic.pipeline.cli run --raw-dir "Raw Data" --out-dir V3_Epistemic/data --strict`

## Data And Generated Artifacts

- `Raw Data/` is read-only evidence. Do not edit raw files in place.
- Generated data must be reproducible from documented commands.
- Canonical generated outputs live under `V3_Epistemic/data/`.
- The canonical entity key is `canonical_id` in reliable outputs and
  `entity_id` in processed layout-stage outputs.
- Every generated artifact that is intended for release must have a current
  manifest or validation report tying it to raw inputs, commands, and checksums.
- Do not let downstream stages silently consume stale files. Stage contracts
  must fail loudly when required inputs are missing or inconsistent.
- `V3_Epistemic/data/frontend/frontend_manifest.json` paths must exist relative
  to `V3_Epistemic/data/frontend/`.
- `V3_Epistemic/data/reliable/frontend_manifest.json` paths must exist relative
  to `V3_Epistemic/data/reliable/`.

## Analytical Standards

- Do not label placeholder math, random layout, or arbitrary geometry as real
  analysis.
- Do not hardcode analytical claims such as entity counts, years, cluster
  counts, or gap counts in the frontend.
- Do not present inferred relationships as reported facts.
- Use correlational/exploratory language unless a causal model and source
  evidence have been added.
- Preferred public terms:
  - "evidence-weighted prominence" instead of causal "influence"
  - "issue/profile embedding" instead of "ideological space"
  - "model-derived gap lead" instead of "void", "uncontested zone", or
    "hidden power"
  - "government target-side exposure" instead of "government spending"
  - "revolving-door events" or "career-transition records" instead of unique
    people unless deduplication proves uniqueness

## Frontend Contract

- The active frontend is `V3_Epistemic/output/reliable_influence_map.html`.
- It fetches the split initial scene and full search chunks from
  `V3_Epistemic/data/frontend/scene_payload.json` and
  `V3_Epistemic/data/frontend/search_index.json`.
- Frontend stats must be computed from loaded data.
- Empty, missing, or schema-invalid data must show an explicit error state.
- The visible scene may be capped for performance, but the cap must be disclosed
  in `payload.meta.performance_caps` and the UI.
- Coordinate source counts must be computed from loaded data and disclosed using
  the actual source keys (`legacy_umap`, `neighbor_inferred`,
  `deterministic_unplaced_ring`, or future explicit keys).

## Privacy, Security, And Licensing

- Do not add secrets, tokens, private contact data, or credentials to the repo.
- Treat person-level revolving-door records as public-record-derived analytical
  data; do not imply wrongdoing or unique-person counts unless deduplication
  proves it.
- Keep privacy and security docs current when the public surface, data handling,
  hosting, or contact process changes.
- Do not assume an open-source license. Follow `LICENSE.md` until the owner
  chooses a different license.

## Coding Style

- Prefer deterministic transforms, explicit schemas, and validation reports.
- Keep generated data reproducible from documented commands.
- Use stable IDs, stable sorting, deterministic random seeds, and checksum
  manifests for release artifacts.
- Keep legacy compatibility code clearly labeled so it cannot be mistaken for
  the active public contract.

## Reporting Findings

When auditing or reviewing, report:

- files inspected
- findings with severity: blocker, high, medium, low
- proposed fixes
- tests needed
- open questions
- demo/release risks

## Validation Expectations

Strict validation must fail on:

- missing required raw files
- empty canonical entities or frontend payloads
- stale manifests or mismatched stage row counts
- dangling edge endpoints
- all-zero issue matrices or gap grids without an explicit waiver/explanation
- revolving-door vectors with bogus endpoints such as one-character substring
  matches
- hardcoded frontend years/counts that disagree with payload metadata
- causal or overclaiming public language outside legacy/reference files
- invalid revolving-door transition years; unknown years must be `null` with
  `temporal_scope=unknown_transition_year`
- broken frontend manifest paths
- fake, constant, all-zero, or ring/spiral-style coordinates in strict release

## Done Definition

A task is not complete if:

- frontend generated data is empty
- issue matrix is all zeros
- issue/profile embedding is fake or strict validation accepts fallback without
  explicit approval
- clusters are fake or unlabeled without disclosure
- gap metrics are arbitrary or all zero without a waiver/explanation
- revolving-door vectors are stubbed or unknown years are converted to fake
  observed years
- header stats are hardcoded
- manifest paths are broken or generated artifact lineage is stale
- tests do not cover the old failure modes touched by the task
