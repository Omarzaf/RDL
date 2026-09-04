#!/usr/bin/env python3
"""Preflight checks before making this repository public."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAX_GITHUB_FILE_BYTES = 95 * 1024 * 1024

REQUIRED_FILES = [
    "README.md",
    "LICENSE.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "SUPPORT.md",
    "PUBLIC_RELEASE_CERTIFICATE.md",
    "CITATION.cff",
    "AGENTS.md",
    "constraints.txt",
    "requirements-dev.txt",
    ".codexignore",
    ".github/dependabot.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/strict-pipeline.yml",
    "docs/SECURITY.md",
    "docs/PRIVACY.md",
    "docs/DATA_PROVENANCE.md",
    "docs/METHODOLOGY.md",
    "docs/INTERPRETATION_GUIDE.md",
    "docs/REPRODUCIBILITY.md",
    "docs/DEPLOYMENT.md",
    "docs/PUBLIC_RELEASE.md",
    "V3_Epistemic/output/reliable_influence_map.html",
    "V3_Epistemic/output/vendor/three.min.js",
    "V3_Epistemic/data/frontend/scene_payload.json",
    "V3_Epistemic/data/frontend/search_index.json",
    "V3_Epistemic/data/frontend/adjacency_topk.json",
    "V3_Epistemic/data/frontend/frontend_manifest.json",
]

FORBIDDEN_PATH_PATTERNS = [
    re.compile(r"(^|/)\.env(\.|$)"),
    re.compile(r"(^|/)\.codex(/|$)"),
    re.compile(r"(^|/)\.claude(/|$)"),
    re.compile(r"(^|/)_archive(/|$)"),
    re.compile(r"(^|/)demo_artifacts(/|$)"),
    re.compile(r"(^|/)\.venv(/|$)"),
    re.compile(r"(^|/)node_modules(/|$)"),
    re.compile(r"(^|/)(CODEX_FIX_PROMPT|CONTEXT|V3_AGENT_PROMPT|V3_FRONTEND_MULTIAGENT_PROMPT|deep-research-report)\.md$"),
    re.compile(r"^V3_Epistemic/output/(dc_epistemic_map_mvp|lobbying_influence_preview)\.html$"),
    re.compile(r"^V3_Epistemic/data/frontend/(entities_3d|clusters|gap_grid|revolving_vectors|trends)\.json$"),
    re.compile(r"(^|/)W2\b", re.IGNORECASE),
    re.compile(r"(^|/)tax[-_ ]?return", re.IGNORECASE),
    re.compile(r"(^|/)credential", re.IGNORECASE),
    re.compile(r"(^|/)secret", re.IGNORECASE),
]

FORBIDDEN_EXTENSIONS = {
    ".docx",
    ".pdf",
    ".rtf",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}

PUBLIC_LANGUAGE_PATHS = [
    "README.md",
    "ROADMAP.md",
    "docs",
    "V3_Epistemic/output/reliable_influence_map.html",
    "V3_Epistemic/output/METHODOLOGY.md",
]

BANNED_PUBLIC_TERMS = ["corruption", "bribery", "covert", "uncontested"]


def git_files() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    names = [name for name in proc.stdout.decode("utf-8", errors="replace").split("\0") if name]
    return [ROOT / name for name in names]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def check_required_files(failures: list[str]) -> None:
    for name in REQUIRED_FILES:
        path = ROOT / name
        if not path.exists() or path.stat().st_size == 0:
            fail(f"Missing required public-release file: {name}", failures)


def check_manifest_paths(failures: list[str]) -> None:
    for name in [
        "V3_Epistemic/data/frontend/frontend_manifest.json",
        "V3_Epistemic/data/reliable/frontend_manifest.json",
    ]:
        path = ROOT / name
        if not path.exists():
            fail(f"Missing frontend manifest: {name}", failures)
            continue
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for filename in manifest.get("files", {}).values():
            if not (path.parent / filename).exists():
                fail(f"Manifest path does not exist: {name} -> {filename}", failures)


def check_publishable_files(paths: list[Path], failures: list[str]) -> None:
    for path in paths:
        name = rel(path)
        for pattern in FORBIDDEN_PATH_PATTERNS:
            if pattern.search(name):
                fail(f"Private/local path must not be published: {name}", failures)
        if path.suffix.lower() in FORBIDDEN_EXTENSIONS:
            fail(f"Binary/private document type must not be published: {name}", failures)
        if not path.exists() or path.is_dir():
            continue
        if path.stat().st_size > MAX_GITHUB_FILE_BYTES:
            fail(f"File is near/over GitHub's hard size limit: {name}", failures)


def check_public_language(failures: list[str]) -> None:
    files: list[Path] = []
    for item in PUBLIC_LANGUAGE_PATHS:
        path = ROOT / item
        if path.is_dir():
            files.extend(sorted(path.glob("*.md")))
        elif path.exists():
            files.append(path)
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for term in BANNED_PUBLIC_TERMS:
            if term in text:
                fail(f"Unsupported public-language term `{term}` in {rel(path)}", failures)


def main() -> int:
    failures: list[str] = []
    paths = git_files()
    check_required_files(failures)
    check_manifest_paths(failures)
    check_publishable_files(paths, failures)
    check_public_language(failures)

    if failures:
        print("Public preflight failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(f"Public preflight passed ({len(paths)} publishable tracked/unignored files checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
