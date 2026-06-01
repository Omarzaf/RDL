# DC Evidence Map Roadmap

**Project codename:** V3 Epistemic  
**Status:** Historical planning note. The active implementation is the static
`V3_Epistemic/output/reliable_influence_map.html` map backed by the canonical
pipeline in `V3_Epistemic/pipeline/`.  
**Goal:** A publicly hosted, interactive relationship map of DC lobbying data,
showing issue/profile similarity, observed relationships, confidence,
source provenance, and model-derived gap leads across time.  
**Audience:** General public, researchers, policymakers, LinkedIn/portfolio.  
**Hosting:** Static file host.  
**Stack:** Python pipeline -> JSON/CSV outputs -> static HTML + Three.js.

---

## The Concept

The main visualization is an interactive evidence map where:

- **X and Y axes** = issue/profile embedding coordinates computed from
  observed issue patterns and related profile features.
- **Z axis** = year when the 3D time-stack view is enabled.
- **Node size** = log observed spend or filing volume, with government target
  exposure kept separate from spending.
- **Node color** = selected lens such as entity type or policy category.
- **Clusters** = derived feature-space communities with labels and confidence.
- **Gap leads** = model-derived areas where spending/exposure density is high
  relative to observed actor density.
- **Revolving door** = resolved career-transition records between government
  roles and lobbying-side entities, with unknown years preserved as unknown.

Supporting views:
- **Relationship filters** — issue/profile, entity type, confidence, and year.
- **Gap Analysis Panel** — ranked model-derived gap leads with explanation.

---

## What Does "Gap Lead" Mean Here?

A gap lead is a model-derived region of the issue/profile embedding where:

1. **High spending or exposure density** is observed in the available data.
2. **Lower actor density** is observed under the current entity universe.

This is an exploratory lead for review. It is not evidence of absence,
wrongdoing, causality, or intent.

---

## Active Folder Structure

```
Think Tank/
├── CONTEXT.md              ← AI agent index (already exists)
├── ROADMAP.md              ← this file
├── Raw Data/               ← source data (JSON exports + ICPSR datasets)
├── Theoratical Data/       ← academic PDFs
├── _archive/               ← old V1 and V2 repos (reference only)
└── V3_Epistemic/           ← active project
    ├── pipeline/           ← canonical Python pipeline
    ├── data/
    │   ├── processed/      ← layout-stage CSV/JSON files
    │   ├── reliable/       ← release/audit outputs
    │   └── frontend/       ← active scene/search JSON chunks
    └── output/             ← static HTML map and output docs
```

---

## Phase 0 — Clean Foundation
**Status:** ✅ Done  
**What happened:**
- Created `CONTEXT.md` as AI agent index.
- Archived V1 (React dashboard) and V2 (Python pipeline) into `_archive/`.
- Identified all data assets and their schemas.

---

## Phase 1 — Data Audit & Preparation
**Estimated sessions:** 1–2  
**You do:** Nothing. Agent runs all scripts.

### What happens
An agent reads every JSON file in `Raw Data/` and builds a clean, unified dataset. Specifically:

1. **Master entity table** — every firm, client, lobbyist, and government entity gets a unique ID, name, type, industry, and year-range of activity. Estimated: ~15,000 unique entities across all years.

2. **Issue matrix** — for every entity, for every year, we extract which issue codes they lobbied on (there are 79 issue codes in the LDA system: healthcare, defense, energy, finance, etc.). This becomes a matrix of shape `[entities × 79 issue codes]` per year.

3. **Spending table** — total lobbying income/spend per entity per year.

4. **Revolving door table** — every person who appears in both a government position and a lobbying firm position, with the year of transition.

### Inputs
- `Raw Data/top-firms.json` (2,000 firms)
- `Raw Data/top-clients.json` (5,000 clients)
- `Raw Data/top-lobbyists.json` (5,000 lobbyists)
- `Raw Data/revolving-door.json` (5,000 revolving door records)
- `Raw Data/gov-entities.json` (240 government agencies)
- `Raw Data/industries.json` (10 industry groups with yearly spending)
- `Raw Data/text-analysis.json` (79 issue areas + trending words)

### Outputs
- `V3_Epistemic/data/processed/entities.csv`
- `V3_Epistemic/data/processed/issue_matrix.csv`
- `V3_Epistemic/data/processed/spending_by_year.csv`
- `V3_Epistemic/data/processed/revolving_door.csv`

---

## Phase 2 — Statistical Modeling
**Estimated sessions:** 2–3  
**You do:** Review outputs at each step. Agent runs all code.

This is the analytical core of the project. Plain-language explanation of each method:

### Step 1 — Issue Vectorization
**What it is:** Convert each entity's lobbying history into a number vector.  
**Why:** You can't put words into a geometry. You need numbers.  
**How:** For each entity, count how often they lobbied on each of the 79 issue codes. Normalize by total filings. Result: each entity becomes a point in 79-dimensional space.  
**Tool:** `scikit-learn` TF-IDF or simple normalized counts.

### Step 2 — UMAP Dimensionality Reduction
**What it is:** Collapse issue/profile vectors down to 2 dimensions (X, Y).  
**Why:** You can't visualize every feature dimension directly. UMAP preserves neighborhood structure, so entities with similar issue/profile evidence tend to appear near each other.  
**How:** Run UMAP on the full dataset (all years pooled) to get stable, consistent X and Y coordinates. This ensures 2018 and 2025 use the same coordinate system.  
**Tool:** `umap-learn` Python library.  
**Output:** Every entity has an X and Y coordinate. These are fixed. Their Z coordinate is the year.

### Step 3 — Community Detection
**What it is:** Automatically group entities into clusters based on their X/Y proximity and their network connections.  
**Why:** These are not political compass labels. They are derived communities of entities with similar issue/profile or relationship evidence.  
**How:** Build a k-nearest-neighbor graph of entities (connect each entity to its 10 closest neighbors in X/Y space). Run the Louvain algorithm to find communities. Label each community after inspecting which issue areas dominate it.  
**Tool:** `python-louvain` or `networkx`.  
**Output:** Every entity has a cluster ID. We label clusters post-hoc (e.g., "Defense-Industrial Complex," "Healthcare Corridor," "Financial Regulatory Cluster," etc.)

### Step 4 — Gap Analysis
**What it is:** Find regions of the issue/profile embedding with high spending or exposure density relative to observed actor density.  
**Why:** These are model-derived leads for review.  
**How:** Estimate the density of spending across the 2D plane using Kernel Density Estimation (KDE). Estimate the density of entities separately. Compute: `gap = spending_density - entity_density`. High gap = lots of money, few actors.  
**Tool:** `scipy.stats.gaussian_kde`.  
**Output:** A 2D heatmap of gap scores overlaid on the plane.

### Step 5 — Revolving Door Movement Vectors
**What it is:** For each resolved career-transition record, calculate the vector between the government-side and lobbying-side endpoint in the 2D embedding.  
**Why:** This gives an exploratory view of career-transition flow records without treating them as causal proof.  
**How:** Look up the X/Y coordinates of the entity the person came from and the entity they went to. Compute a vector (direction + magnitude). Aggregate these vectors by year to show "currents" of influence.  
**Output:** A list of movement vectors per year, colored by direction.

### Step 6 — Temporal Series Export
**What it is:** Package all of the above as a year-by-year time series.  
**Why:** The 3D visualization needs each entity's state (size, cluster, gap score) for each year from 2018 to 2025.  
**How:** For each entity, for each year, record: X, Y, Z (year), size (spending), cluster, active (boolean), gap_score, revolving_door_count.

### Outputs
- `V3_Epistemic/data/processed/umap_coords.csv` — X, Y per entity
- `V3_Epistemic/data/processed/clusters.csv` — cluster ID + label per entity
- `V3_Epistemic/data/processed/gap_heatmap.json` — 2D gap density grid
- `V3_Epistemic/data/processed/revolving_vectors.json` — movement vectors per year
- `V3_Epistemic/data/frontend/entities_3d.json` — final frontend payload

---

## Phase 3 — 3D Frontend
**Estimated sessions:** 3–4  
**You do:** Review screenshots, give design feedback. Agent builds.

### Tech stack
- **React + Vite** (same as V1, already familiar)
- **React Three Fiber** (declarative Three.js — the best way to build 3D in React without being a Three.js expert)
- **@react-three/drei** (helper components: orbit controls, labels, environment)
- **@react-spring/three** (smooth 3D animations)
- **D3** (for supporting 2D panels: gap analysis, echo chamber)

### The 3D Scene

**Nodes:** Markers at (X, Y, Z) where Z = year in the time-stack view. Size is log-scaled observed spend, exposure, or filings depending on entity type. Color is a selected lens.

**Temporal trails:** Each node leaves a thin line connecting its position across years — like a particle trail through 3D space. You can see entities that are stable (vertical trails) vs. drifting (diagonal trails).

**Cluster hulls:** Semi-transparent convex volumes wrapping each community, colored by cluster. They morph across time.

**Gap lead zones:** A disclosed model-derived overlay marking regions of high gap score.

**Revolving door streams:** Animated particle arcs at specific Z-levels (years), connecting the node the person left and the node they joined. The arc color shows direction: orange = gov→lobby, blue = lobby→gov.

**Camera and controls:** Full orbital rotation. Click a node to isolate it and see its full trajectory and connections. Zoom in on a year-slice. Filter by industry, cluster, or gap score.

### Supporting panels (2D, alongside the 3D view)

- **Gap Analysis Panel:** Ranked list of the top 10 epistemic gaps with the issue areas they cover, the spending flowing through them, and the absence of organized actors.
- **Echo Chamber Detector:** A chord diagram showing closed lobbying loops — issue areas dominated by the same firms year after year.
- **Entity Detail Drawer:** Click any node → see name, industry, yearly spending, issue fingerprint, revolving door events, cluster membership.

---

## Phase 4 — Hosting on Vercel
**Estimated sessions:** 0.5  
**You do:** Create a free Vercel account, connect your GitHub repo. Agent does the config.

Steps:
1. Push V3_Epistemic/frontend to a GitHub repo.
2. Connect repo to Vercel.
3. Set build command: `npm run build` / output dir: `dist`.
4. Vercel auto-deploys on every push. You get a public URL immediately.

Optional: custom domain (free with a `.vercel.app` subdomain, or ~$10/year for a real domain).

---

## Phase 5 — Polish & Publication
**Estimated sessions:** 1–2

- Write a short explainer/methodology note for the website footer.
- Take a video walkthrough for LinkedIn.
- Write a Substack post explaining the epistemic gap thesis.
- Submit to policy data visualization communities (PolicyViz, Data Journalism Network, etc.).

---

## The Statistical Bottleneck — Solved

The reason this has been stuck is that the statistical methods sounded intimidating without knowing what they're for. Here's the plain-language version:

| Question | Method | Plain English |
|---|---|---|
| Where does each entity sit in the issue/profile embedding? | UMAP | "Squeeze many profile features into 2 by preserving who is similar to whom" |
| What are the derived communities? | Louvain community detection | "Find groups with similar feature or relationship evidence" |
| Where are the gap leads? | Kernel Density Estimation | "Compare spending/exposure density to actor density" |
| What does the revolving door do to the plane? | Vector field calculation | "For each person who moved, draw an arrow from where they came from to where they went" |
| How does this all change over time? | Temporal panel analysis | "Run everything above for each year and stack the results on the Z-axis" |

None of this requires you to write a single line of code. Each step is a Python script that an agent writes and runs. You review the output at each step and confirm before moving on.

---

## Session-by-Session Order

| Session | Goal | Deliverable |
|---|---|---|
| **Next session** | Build V3 folder, scaffold pipeline scripts, run Phase 1 data audit | `entities.csv`, `issue_matrix.csv` |
| **Session 2** | Run UMAP + community detection | `umap_coords.csv`, `clusters.csv` + cluster labels |
| **Session 3** | Run gap analysis + revolving door vectors | `gap_heatmap.json`, `revolving_vectors.json` |
| **Session 4** | Export final frontend JSON, scaffold React + Three.js app | Working 3D scene with nodes |
| **Session 5** | Add cluster hulls, gap voids, revolving door streams | Full 3D visualization |
| **Session 6** | Add supporting panels + interactivity | Complete app |
| **Session 7** | Deploy to Vercel | Public URL |
| **Session 8** | Polish, explainer text, LinkedIn video | Launch-ready |

---

## One Important Note

The current JSON files in `Raw Data/` appear to be pre-processed exports (not raw LDA API pulls). They're rich and usable, but they represent a specific snapshot and processing layer. Before the statistical pipeline runs, the agent will inspect each file for completeness and flag any gaps. If the issue code data in the files is insufficient for vectorization, we'll need to either enrich from the ICPSR Stata datasets or pull specific fields from the LDA API (which is free and public, no key required for basic access).

---

*Last updated: May 2026. Built with Claude Cowork.*
