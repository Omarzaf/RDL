# Data Provenance

`Raw Data/` is the evidence boundary. The pipeline reads JSON exports for firms,
clients, lobbyists, government entities, filing activity, network analysis,
contracts comparisons, industry/category mappings, text analysis, and
revolving-door records.

Processed layout-stage files use `entity_id`. Reliable publication files use
`canonical_id`. Frontend payloads expose reliable entities as `id`, sourced from
`canonical_id`. The main publication outputs are:

- `data/processed/entities.csv`
- `data/processed/edges.csv`
- `data/processed/issue_matrix_aggregate.csv`
- `data/processed/umap_coords.csv`
- `data/processed/clusters.csv`
- `data/processed/embedding_manifest.json`
- `data/processed/graph_metrics.json`
- `data/processed/gap_leads.json`
- `data/processed/revolving_vectors.json`
- `data/reliable/entities.csv`
- `data/reliable/edges.csv`
- `data/reliable/entity_year_metrics.csv`
- `data/reliable/issue_profiles.csv`
- `data/reliable/quality_report.json`
- `data/reliable/validation_report.json`
- `data/reliable/visual_payload.json`

The frontend receives chunked copies in `data/frontend/`: `scene_payload.json`,
`search_index.json`, `adjacency_topk.json`, and `frontend_manifest.json`.

Every public payload should expose years, partial years, performance caps, data
issues, confidence, coordinate source, source files, and observed, derived, or
modeled semantics.
