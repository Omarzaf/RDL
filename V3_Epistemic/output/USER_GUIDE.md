# User Guide: DC Lobbying Evidence Map

## What This Visual Shows

The DC Lobbying Evidence Map is an interactive view of Washington lobbying relationships from 2018-2025. It connects lobbying firms, clients, lobbyists, government entities, policy issues, spending/exposure signals, confidence levels, and model-derived gap leads.

Use it as an exploration tool, not as a final legal or financial claim. The strongest use case is finding patterns, clusters, relationships, and areas that deserve deeper source review.

## How To Open It

Use the local server URL:

```text
http://127.0.0.1:8765/V3_Epistemic/output/reliable_influence_map.html
```

Do not open the file directly with `file://...`. The visual loads a separate JSON payload, and browser security blocks that fetch from a raw file path.

If you see `Failed to fetch`, reopen the map through the localhost URL above.

## First Screen

The top bar shows:

- `Entities`: how many actors are currently visible.
- `Visible Edges`: how many relationships are visible after filters.
- `Time View`: whether you are seeing all years or one year.
- `Quality Issues`: known data caveats surfaced by the pipeline.
- `Partial Year`: years treated as incomplete, currently 2025.

The main canvas is the evidence map. Nodes are actors. Lines are relationships. Copper/orange signals indicate model-derived gap or revolving-door layers.

## Node Types

All nodes now use the same round marker. Actor type is shown through color and letter identifiers:

| Identifier | Meaning |
| --- | --- |
| `F` | Lobbying firm |
| `C` | Client |
| `L` | Lobbyist |
| `G` | Government entity |
| `R` | Reference node |

Reference nodes are not lobbying actors. They are comparison anchors, such as federal-contract context.

## View Modes

### 3D Mode

Use `3D` when you want the full temporal structure.

- Horizontal position: policy/issue-space relationship.
- Vertical stacking: years from 2018 to 2025.
- Use the year rail to isolate one year.
- Use all-years mode to see the full time stack.

Controls:

- Drag: rotate the map.
- Shift-drag or right-drag: pan.
- Scroll: zoom.
- Double-click: reset the view.

### 2D Mode

Use `2D` when you want a clearer map-like view.

- The network is flattened into policy/issue space.
- Nodes are easier to compare spatially.
- Relationships are easier to follow.
- Time filters still work, but the visual is no longer vertically stacked.

Controls:

- Drag: pan.
- Scroll: zoom.
- Double-click: reset the view.

## Search

Use the search box to find a firm, client, lobbyist, agency, subtype, or policy category.

Examples:

```text
MEHLMAN
CHAMBER
HEALTHCARE
DEFENSE
TREASURY
```

Search updates the visible nodes in real time.

## Color Lenses

The dropdown changes what node colors mean.

| Lens | What It Means |
| --- | --- |
| `Entity type` | Colors identify firms, clients, lobbyists, government entities, and reference nodes. |
| `Confidence` | Colors show how complete/reliable the record is. |
| `Gap score` | Colors show model-derived gap lead intensity. |
| `Policy category` | Colors group entities by policy/issue rollup. |

For public explanation, start with `Entity type`. Use `Gap score` only after explaining that it is model-derived.

## Filters

Open `Controls` or switch to `Analyst` mode to access filters.

Available filters:

- Minimum evidence-weighted prominence.
- Entity type checkboxes.
- All years vs single year.
- Year slider.
- Layer toggles.

Use filters to reduce clutter before discussing a specific actor or policy area.

## Layers

| Layer | Meaning |
| --- | --- |
| `Model-derived gap plane` | Copper/amber heat layer showing model-derived gap leads. |
| `Top relationships` | Relationship lines between visible actors. |
| `Aggregate revolving-door arcs` | Career-transition flow layer. |
| `Type identifiers` | Letter markers on nodes. |
| `Anchor labels` | Labels for selected/high-signal entities. |

Turn off relationships or arcs when the scene feels too dense.

## Clicking A Node

Click any node to open the entity drawer.

The drawer shows:

- Entity name.
- Type, subtype, and policy category.
- Evidence-weighted prominence score.
- Confidence score.
- Gap score.
- Revolving-door score.
- Source files.
- Quality flags.
- A plain-language explanation of what the visual claim means.

Government entities are labeled differently: their size uses lobbying exposure directed at the agency, not government spending.

## Data Notes

The bottom-right `Data Notes` panel contains the most important public caveats:

- Temporal data is often aggregate repeated across years.
- 2025 is partial.
- 2026 is not included.
- Revolving-door counts represent transitions, not unique people.
- Government nodes use lobbying exposure, not agency spending.
- The frontend may show a capped subset for performance.

Keep this panel visible during a public demo if the audience includes researchers, journalists, or policy reviewers.

## Recommended Demo Flow

1. Open the map in `Briefing` mode.
2. Start in `2D` mode to explain the overall network.
3. Explain the identifiers: `F`, `C`, `L`, `G`, `R`.
4. Switch to `3D` mode to show the year stack.
5. Click `2025` and mention that it is partial.
6. Search for a known firm or client.
7. Click a node and walk through the entity drawer.
8. Switch to `Gap score` lens and explain that gaps are model-derived leads.
9. Open `Analyst` mode only if the audience wants filters and layers.

## What Not To Claim

Do not say:

- A gap score is direct evidence of wrongdoing or a proven causal finding.
- Government exposure is government spending.
- 2025 is complete.
- Revolving-door event counts are unique lobbyist counts.
- All year-to-year node size movement is observed annual spending.

Safer language:

- "This is a model-derived lead."
- "This indicates lobbying exposure directed at the agency."
- "This entity has lower confidence because the source evidence is incomplete."
- "This view is designed to guide source review, not replace it."

## Troubleshooting

### `Failed to fetch`

You opened the file directly. Use:

```text
http://127.0.0.1:8765/V3_Epistemic/output/reliable_influence_map.html
```

### The Map Looks Too Dense

Try:

- Switch to `2D`.
- Turn off `Aggregate revolving-door arcs`.
- Turn off `Top relationships`.
- Use search.
- Increase minimum influence.
- Filter to one entity type.

### Nodes Are Hard To Interpret

Use:

- `Entity type` color lens.
- `Type identifiers` layer.
- Click a node for the detail drawer.
- Turn on `Anchor labels` only when needed.

### The Page Does Not Load

Confirm the local server is running from the repository root:

```bash
python3 -m http.server 8765
```

Then open:

```text
http://127.0.0.1:8765/V3_Epistemic/output/reliable_influence_map.html
```
