# Privacy

The active map is a static, local-first data visualization. It does not require
user accounts, cookies, analytics beacons, or form submissions.

## Data Shown

The visualization uses project JSON exports in `Raw Data/` and generated
artifacts under `V3_Epistemic/data/`. Person-level records are limited to the
public-record-derived revolving-door/lobbying fields already present in the
source exports.

## Data Handling Rules

- Do not add private credentials, private contact lists, or non-public personal
  data to `Raw Data/` or generated payloads.
- Do not infer misconduct, intent, or causality from public-record relationships.
- Treat revolving-door counts as career-transition records or events unless a
  deduplication report proves unique people.
- Keep low-confidence, inferred, and modeled fields labeled in the payload and
  UI.

## Deployment Notes

If the map is hosted publicly, serve only the active static files listed in
`docs/DEPLOYMENT.md`. Re-check source licensing and public-data terms before
redistributing raw or full generated datasets.
