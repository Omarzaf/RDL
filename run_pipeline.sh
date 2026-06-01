#!/usr/bin/env sh
set -eu

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python runtime not found at $PYTHON_BIN"
  echo "Create it with: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

"$PYTHON_BIN" -m V3_Epistemic.pipeline.cli run --raw-dir "${RAW_DIR:-Raw Data}" --out-dir "${OUT_DIR:-V3_Epistemic/data}" --strict
