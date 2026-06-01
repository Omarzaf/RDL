# Setup

Use the repository root as the working directory.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run the canonical pipeline:

```bash
python -m V3_Epistemic.pipeline.cli run --raw-dir "Raw Data" --out-dir V3_Epistemic/data --strict
```

Serve the static product from the repository root:

```bash
python3 -m http.server 8765
```

Open `http://127.0.0.1:8765/V3_Epistemic/output/reliable_influence_map.html`.

`Raw Data/` is input only. Do not edit source exports in place. All derived
files belong under `V3_Epistemic/data/`.
