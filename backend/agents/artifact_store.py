"""Persistent artifacts for pipeline visual custody.

Each pipeline step can write the payload it received/produced here without
affecting the production deploy path.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value or "").strip("-").lower()
    return cleaned[:80] or "lead"


def artifact_dir(run_id: str | int | None, lead_id: str | None, lead_name: str = "") -> Path:
    base = Path(os.environ.get("FRALIB_ARTIFACTS_DIR", "/app/artifacts"))
    run = _slug(str(run_id or "manual"))
    lead = _slug(f"{lead_name}-{lead_id or 'sem-lead'}")
    path = base / run / lead
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_sidecar(path: Path, metadata: dict[str, Any] | None) -> None:
    sidecar = {
        "artifact": path.name,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "metadata": metadata or {},
    }
    path.with_suffix(path.suffix + ".meta.json").write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def write_json_artifact(
    *,
    run_id: str | int | None,
    lead_id: str | None,
    lead_name: str = "",
    filename: str,
    payload: Any,
    metadata: dict[str, Any] | None = None,
) -> str:
    path = artifact_dir(run_id, lead_id, lead_name) / filename
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    _write_sidecar(path, metadata)
    return str(path)


def write_html_artifact(
    *,
    run_id: str | int | None,
    lead_id: str | None,
    lead_name: str = "",
    filename: str,
    html: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    path = artifact_dir(run_id, lead_id, lead_name) / filename
    path.write_text(html or "", encoding="utf-8")
    _write_sidecar(path, metadata)
    return str(path)
