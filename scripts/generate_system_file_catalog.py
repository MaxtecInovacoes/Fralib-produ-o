"""Generate a tracked-file catalog for FraLib documentation."""

from __future__ import annotations

import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "TRACKED_FILE_CATALOG.md"


AREAS = (
    ("backend/endpoints/", "Backend endpoints"),
    ("backend/agents/", "Backend agents"),
    ("backend/services/", "Backend services"),
    ("backend/core/", "Backend core"),
    ("backend/utils/", "Backend utils"),
    ("backend/migrations/", "Backend migrations"),
    ("frontend/", "Frontend"),
    ("scripts/", "Operational scripts"),
    ("tests/unit/", "Unit tests"),
    ("tests/integration/", "Integration tests"),
    ("tests/", "Other tests"),
    ("docs/", "Documentation"),
    ("openspec/", "OpenSpec"),
    ("alembic/", "Alembic"),
    (".codex/", "Codex workspace config"),
    (".agents/", "Agent skills/config"),
)


def _git_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def _area_for(path: str) -> str:
    for prefix, name in AREAS:
        if path.startswith(prefix):
            return name
    if "/" not in path:
        return "Repository root"
    return "Other tracked files"


def _purpose_for(path: str) -> str:
    name = Path(path).name
    suffix = Path(path).suffix.lower()
    if path == "AGENTS.md":
        return "Operational rules for agents and deploy."
    if path == "pipeline.py":
        return "Official operational CLI."
    if path == "worker.py":
        return "PM2 worker daemon for long-running jobs."
    if path == "server.py":
        return "API/server entrypoint."
    if name.startswith("test_") or "/test_" in path:
        return "Automated contract or regression test."
    if path.startswith("backend/endpoints/"):
        return "HTTP/API route module."
    if path.startswith("backend/agents/"):
        return "Agent, Builder, prompt, SEO, design or validation module."
    if path.startswith("backend/services/"):
        return "Service layer used by endpoints, workers or agents."
    if path.startswith("backend/core/"):
        return "Core database, auth, queue or shared infrastructure."
    if path.startswith("frontend/"):
        return "Frontend source, static asset or build partial."
    if path.startswith("scripts/"):
        return "Operational script for validation, recovery, deploy or audit."
    if path.startswith("docs/"):
        return "Documentation source."
    if path.startswith("openspec/"):
        return "Spec-driven change artifact."
    if suffix in {".md", ".txt"}:
        return "Text documentation or contract."
    if suffix in {".py"}:
        return "Python module."
    if suffix in {".js", ".mjs", ".ts", ".tsx"}:
        return "JavaScript/TypeScript source."
    if suffix in {".html", ".css"}:
        return "Web/static source."
    if suffix in {".json"}:
        return "Structured configuration or data."
    if suffix in {".yml", ".yaml", ".ini", ".toml"}:
        return "Configuration."
    return "Tracked repository file."


def _render(files: list[str]) -> str:
    groups: dict[str, list[str]] = defaultdict(list)
    for path in files:
        groups[_area_for(path)].append(path)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Tracked File Catalog",
        "",
        f"Generated at: `{stamp}`.",
        "",
        "This catalog is generated from `git ls-files`. It intentionally excludes",
        "untracked local caches, coverage output, logs, checkpoints and temporary",
        "pytest folders. Regenerate it with:",
        "",
        "```bash",
        "python scripts/generate_system_file_catalog.py",
        "```",
        "",
        "## Areas",
        "",
    ]
    for area in sorted(groups):
        area_files = sorted(groups[area])
        lines.append(f"### {area}")
        lines.append("")
        lines.append("| File | Purpose |")
        lines.append("| --- | --- |")
        for path in area_files:
            lines.append(f"| `{path}` | {_purpose_for(path)} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    files = _git_files()
    OUT.write_text(_render(files), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} with {len(files)} tracked files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
