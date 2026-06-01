# Security

The active product is a static HTML/JSON map. There is no application server,
database, authentication layer, or privileged write path in the deployed
surface.

## Supported Surface

- `V3_Epistemic/output/reliable_influence_map.html`
- `V3_Epistemic/output/vendor/three.min.js`
- `V3_Epistemic/data/frontend/scene_payload.json`
- `V3_Epistemic/data/frontend/search_index.json`
- `V3_Epistemic/data/frontend/adjacency_topk.json`
- `V3_Epistemic/data/frontend/frontend_manifest.json`

## Rules For Contributors

- Do not commit secrets, API tokens, private keys, or local credentials.
- Do not load remote scripts into the active map without review.
- Keep generated payload paths relative and explicit.
- Run strict pipeline validation before release.
- Treat `_archive/`, old prompt files, and legacy preview HTML as reference-only.

## Reporting Issues

Report security concerns privately to the repository owner before public
disclosure. Include the affected file, reproduction steps, expected impact, and
whether any public deployment is affected.
