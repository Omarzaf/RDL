# Reliable DC Evidence Map - Visual Design Spec

## Purpose

The visual is a policy intelligence map for exploring DC lobbying relationship data. It presents firms, clients, lobbyists, government agencies, relationships, issue spaces, confidence, provenance, and model-derived gap leads in one interactive environment.

The design goal is to make the map feel analytical, credible, and presentation-ready while keeping the data semantics defensible. Observed facts, derived metrics, and model-derived signals must remain visually distinguishable.

## Visual Direction

Style: policy intelligence cockpit.

Tone:

- Serious and institutional.
- Clean enough for executive presentation.
- Detailed enough for analyst exploration.
- Evidence-first, not decorative.

Current atmosphere:

- Ash-white spatial background.
- Transparent off-white UI panels.
- Dark graphite 3D nodes.
- Cyan for selected, active, or navigational signals.
- Copper and amber for partial-year and model-derived gap signals.
- Dark mode is available through the top toolbar toggle.

## Layout

The page uses a full-screen 3D canvas with floating interface layers.

Primary regions:

- Compact top command bar: title, data quality stats, search, color lens, mode controls.
- Left controls drawer: detailed analyst controls, hidden by default in Briefing mode.
- Right insight drawer: selected entity details and provenance.
- Bottom year rail: clickable temporal navigation from 2018 to 2025.
- Lower-left visual contract legend: explains shapes, colors, confidence, and gap semantics.
- Center-bottom interaction hint: mouse controls for rotating, panning, zooming, and resetting the scene.

Default mode:

- Briefing mode.
- Controls drawer closed.
- Insight drawer closed until the user clicks a node or search result.
- Legend closed until requested.
- No entity selected automatically.
- Type identifiers off by default for first-paint performance.

Analyst mode:

- Controls drawer opens.
- More filters and layer controls become immediately accessible.

## Color System

Background:

- Ash white: `#f2f1ec`
- Secondary ash: `#e7e3db`
- Canvas gradient: warm off-white with subtle copper tint.

UI surface:

- Panel: `rgba(250, 248, 241, 0.84)`
- Strong panel: `rgba(255, 253, 247, 0.94)`
- Panel border: `rgba(83, 74, 62, 0.2)`
- Text: `#24221e`
- Muted text: `#62594d`

Accent colors:

- Cyan: `#007c9b`
- Copper: `#c77937`
- Amber: `#b9802d`
- Warning red: `#b94d40`

Entity colors:

- Firm: cyan-blue.
- Client: green.
- Lobbyist: amber.
- Government agency: red.
- Contract reference: violet.

Gap colors:

- Low gap: muted gray/brown.
- Medium gap: amber.
- High gap: copper/red.

## 3D Scene Encoding

Entity position:

- Horizontal position comes from issue-space coordinates.
- Vertical position represents year slices from 2018 to 2025.

Node shape:

- Firm: sphere.
- Client: cube.
- Lobbyist: cone.
- Government agency: diamond/octahedron.
- Contract reference: ring.

Node size:

- Uses log-scaled observed spend or filing volume.
- Government target-side exposure is not used as raw node size.

Node color:

- Controlled by the selected color lens:
  - Entity type.
  - Confidence.
  - Gap score.
  - Policy category.

Node opacity and tone:

- Lower-confidence entities are visually muted.
- Higher-confidence entities retain stronger color and contrast.

Edges:

- Relationship edges are capped and sorted by weight to reduce visual noise.
- Default Briefing mode shows fewer edges than Analyst mode.

Revolving-door arcs:

- Copper aggregate arcs.
- Treated as aggregate flow unless exact transition years are available.

Gap plane:

- Copper/amber texture plane.
- Represents model-derived gap leads, not directly observed facts.

Selection:

- Selected entity gets a cyan wireframe halo.
- Related edges are highlighted in cyan.
- Detail drawer updates with metrics and provenance.

## Interaction Model

Mouse controls:

- Drag: rotate the 3D map.
- Shift-drag: pan the map.
- Right-drag: pan the map.
- Scroll: zoom in and out.
- Double-click: reset view.
- Reset View button: reset view.
- Hover: show tooltip.
- Click node: select entity and update insight drawer.

Modes:

- Briefing: presentation-first, minimal controls, cleaner scene.
- Analyst: opens controls and exposes filtering and layer toggles.

Year controls:

- Bottom year rail has buttons for All, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025.
- 2025 is marked partial.
- Clicking a year switches to single-year view.
- Clicking All restores all-year stacked view.

## UI Components

Top command bar:

- Project title.
- Subtitle.
- Entity count.
- Visible edge count.
- Current time view.
- Data quality issue count.
- Partial-year marker.
- Search input.
- Color lens dropdown.
- Briefing/Analyst mode buttons.
- Controls, Insight, Legend toggles.
- Reset View button.

Controls drawer:

- Time controls.
- Year slider.
- Minimum influence slider.
- Entity type filters.
- Layer toggles:
  - Model-derived gap plane.
  - Top relationships.
  - Aggregate revolving-door arcs.
  - Anchor labels.

Insight drawer:

- Entity name.
- Entity type, subtype, policy category.
- Evidence-weighted prominence score.
- Confidence score.
- Gap score.
- Revolving-door score.
- Observed / Derived / Model-derived provenance row.
- Source files.
- Confidence flags.

Legend:

- Shape mapping.
- Current color lens.
- Copper glow meaning.
- Confidence muting meaning.
- 2025 partial-year marker.

## Data Semantics

The visual must preserve the reliable payload contract.

Observed:

- Spend.
- Filing volume.
- Source files.
- Entity and relationship records from source data.

Derived:

- Evidence-weighted prominence score.
- Confidence score.
- Issue/category rollups.
- Revolving-door aggregate score.

Model-derived:

- Gap score.
- Gap heat plane.

Rules:

- Do not present model-derived gaps as observed facts.
- Do not use government exposure as raw spending.
- Keep low-confidence data visually distinct.
- Keep 2025 labeled as partial unless source metadata proves completeness.

## Responsive Behavior

Desktop:

- Top command bar spans the viewport.
- Details drawer stays right.
- Controls drawer opens left in Analyst mode.
- Legend sits lower left, shifting right when controls are open.
- Year rail stays bottom center.

Narrow viewport:

- Top bar stacks.
- Stats may hide.
- Drawers use available width.
- Details drawer sits above the bottom rail.
- Year rail remains accessible.

## Implementation Notes

Primary file:

- `V3_Epistemic/output/reliable_influence_map.html`

Data source:

- `V3_Epistemic/data/frontend/scene_payload.json`
- `V3_Epistemic/data/frontend/search_index.json`

Important implementation constraints:

- Keep the payload schema unchanged.
- Keep interaction state local to the HTML.
- Do not regenerate the reliable payload for visual-only changes.
- Avoid random yearly sizing or simulated temporal values.

## QA Checklist

- Page loads at `http://127.0.0.1:8765/V3_Epistemic/output/reliable_influence_map.html` when served from the repository root.
- Scene renders on ash-white background.
- Drag rotates the map.
- Shift-drag or right-drag pans the map.
- Scroll zooms the map.
- Double-click and Reset View restore the default camera.
- Briefing and Analyst modes work.
- Color lenses update node colors and legend text.
- Search filters visible entities.
- Entity type filters work.
- Year rail switches between all-year and single-year views.
- 2025 remains visibly marked as partial.
- Selected node displays halo and updates insight drawer.
- Gap plane remains labeled as model-derived.
- Text remains readable on the ash-white design.
