# Methodology: Reliable DC Evidence Map

## 1. Data Sources

This visualization uses JSON exports in `Raw Data/` from the lobbying disclosure data workflow assembled for this project. The public-facing source domain is the U.S. lobbying disclosure ecosystem; source snapshots are preserved as read-only JSON evidence and are not edited in place.

- Source evidence directory: `Raw Data/`
- Reliable generated outputs: `V3_Epistemic/data/reliable/`
- Frontend payload chunks: `V3_Epistemic/data/frontend/scene_payload.json` and `V3_Epistemic/data/frontend/search_index.json`
- Access snapshot: read from `payload.meta.source_snapshot` / `payload.meta.generated_at`
- License: verify the upstream lobbying disclosure API and any secondary source license before public redistribution.

## 2. Entity Types

| Entity type | Definition | Visual treatment |
| --- | --- | --- |
| `firm` | Lobbying firm or registrant actor represented in firm-level source files. | Round marker; size uses log observed firm income or filings. |
| `client` | Client organization represented in client-level source files. | Round marker; size uses log observed client spend or filings. |
| `lobbyist` | Person-level revolving-door/lobbyist actor. | Round marker; size uses filing volume where spend is unavailable. |
| `gov_agency` | Government target of lobbying attention. | Round marker; size uses lobbying exposure directed at the agency, not government spending. |
| `reference_node` | Non-actor comparison node, such as federal contracts. | Round marker; shown for comparison and excluded from actor spending claims. |

## 3. Metrics

### Evidence-Weighted Prominence Score

Internal field: `influence_score`.

`influence_score = 0.35 log_spend + 0.20 log_filings + 0.20 graph_centrality + 0.10 gov_target_breadth + 0.10 revolving_door_score + 0.05 issue_breadth`

Government agencies do not receive raw observed spend. Their target-side value is stored as `lobbying_exposure` and kept separate.

### Momentum Score

Momentum uses recent activity flags, new-entrant status, and industry/category growth where available. Entity-year spend is not treated as observed unless the source provides real entity-year fields. Aggregate repeated values are marked with `temporal_value_type`.

### Revolving-Door Score

Revolving-door scoring uses available transition/event evidence, firm/client breadth, and position-derived seniority signals. Counts labeled as revolving-door events represent career transition events, not unique people.

### Concentration Score

Concentration uses firm HHI, top-client share, issue specialization, and related sector concentration where available.

### Gap Score

`gap_score` is model-derived. It combines spatial density, spending/exposure signals, actor diversity, issue diversity, and confidence penalties. It is an analytical lead, not a directly observed fact.

## 4. Pipeline Steps

| Script | Purpose |
| --- | --- |
| `01_load_and_audit.py` | Load source JSON, audit missingness, detect placeholder fields, and write corrected processed metadata such as `stats.corrected.json`. |
| `02_build_entity_table.py` | Build canonical entities and deduplicated edges, with accepted merge logs and quarantine files for risky fuzzy matches. |
| `03_build_issue_matrix.py` | Build issue/profile features, readable issue labels, policy rollups, and scaled UMAP input features. |
| `04_umap_layout.py` | Generate stable issue/profile coordinates with zero-vector handling for no-issue entities. |
| `05_community_detection.py` | Build communities using a Gaussian-weighted k-nearest-neighbor graph. |
| `06_gap_analysis.py` | Build model-derived gap grid with zero-range guards and government exposure separated from spend. |
| `07_revolving_door_vectors.py` | Build aggregate revolving-door vectors and assign transition years only when evidence exists; unknown years remain null. |
| `08_temporal_series.py` | Build deterministic temporal rows without random yearly noise and mark aggregate repeated values. |
| `09_build_reliable_payload.py` | Build reliable CSVs, validation reports, quality reports, and frontend-ready JSON. |

## 5. Limitations

- Temporal data is often aggregate repeated across years, not directly observed entity-year spend.
- The initial frontend scene is capped for browser performance; the payload discloses when edges are truncated.
- 2025 is treated as partial unless source metadata proves it complete.
- 2026 filing activity may exist in raw monthly source files but is not included as a visual year.
- Many low/medium confidence records have incomplete issue, state, description, or placement evidence.
- Government target-side exposure is not government spending and must not be summed with firm/client observed spend.

## 6. How To Cite

Recommended citation:

> DC Evidence Network, Reliable Evidence Map, generated from lobbying disclosure JSON source snapshot listed in `payload.meta.source_snapshot`, `V3_Epistemic` pipeline scripts 01-09.

When publishing screenshots or extracts, include the data notes: aggregate repeated temporal values, partial 2025, model-derived gap scores, and revolving-door events not unique individuals.
