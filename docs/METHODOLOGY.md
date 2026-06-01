# Methodology

The rescue pipeline uses one canonical entity and edge universe. Stage 02 writes
`entities.csv` and `edges.csv`; later stages read those files instead of older
standalone entity tables.

Issue features are built from observed client issue codes, propagated firm and
lobbyist client profiles, government target vectors, low-weight industry/type
features, and numeric graph features. No-issue flags are preserved before
feature scaling.

The embedding stage creates deterministic two-dimensional issue-space
coordinates from the canonical feature matrix. The manifest records the seed,
method, input checksum, row count, and coordinate source.

Two community systems are produced:

- `issue_community_id`: based on feature/embedding similarity.
- `relationship_community_id`: based on the weighted relationship graph.

Graph metrics include PageRank, weighted strength, betweenness, brokerage score,
participation coefficient, edge-type summaries, top brokers, and adjacency
indexes where the available fields support them.

Gap outputs are model-derived gap leads. They compare density patterns in the
constructed issue space and do not establish cause or intent.

Revolving-door vectors use canonical person and endpoint resolution. Unknown
transition years remain null or aggregate. Every vector carries confidence and
quality fields.
