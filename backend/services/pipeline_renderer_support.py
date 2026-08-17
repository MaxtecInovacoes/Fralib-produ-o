"""Renderer/publication support helpers for the pipeline orchestrator."""


import os
import re
import uuid
from datetime import datetime

from sqlalchemy import text


_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_renderer_or_publication_error(error: object) -> bool:
    """Errors after an approved lead must retry the same lead, not hunt a new one."""
    text_error = str(error or "").lower()
    type_error = type(error).__name__.lower()
    tokens = (
        "acprpcerror",
        "htmlqualitygate",
        "visual_contract",
        "quality gate",
        "builder_renderer",
        "render_site_with_builder",
        "manifest existente",
        "idempotency_key",
        "socket connection was closed",
        "renderer",
        "html",
        "deploy",
        "nginx",
        "filesystem",
    )
    return any(token in text_error or token in type_error for token in tokens)


def builder_job_id_for_state(
    state, config: dict | None = None, repair_hash: str = ""
) -> str:
    """Keep builder manifests stable by default and isolated for forced reruns."""
    config = config or {}
    base = str(getattr(state, "pipeline_id", "") or uuid.uuid4().hex[:12]).strip()
    base = re.sub(r"[^a-zA-Z0-9._-]+", "-", base).strip("-_.") or uuid.uuid4().hex[:12]
    suffix_parts: list[str] = []
    if (
        config.get("_forcar_renovacao")
        or config.get("_cold_run")
        or config.get("_lead_id_existente")
    ):
        run_marker = str(
            getattr(state, "run_id", "") or config.get("_run_id") or uuid.uuid4().hex[:12]
        )
        run_marker = re.sub(r"[^a-zA-Z0-9._-]+", "-", run_marker).strip("-_.")[:12]
        if run_marker:
            suffix_parts.append(f"run-{run_marker}")
    if repair_hash:
        suffix_parts.append(f"repair-{repair_hash}")
    suffix = "-".join(suffix_parts)
    max_len = 96
    if suffix:
        base = base[: max(1, max_len - len(suffix) - 1)].strip("-_.")
        return f"{base}-{suffix}"[:max_len]
    return base[:max_len].strip("-_.") or uuid.uuid4().hex[:12]


def persist_failed_renderer_html(
    state, error: object, renderer_agent: str = "builder_renderer"
) -> None:
    """Keep rejected HTML for audit before the gate aborts publication."""
    html = getattr(state, "html_final", "") or ""
    if len(html) < 500:
        return
    pipeline_id = getattr(state, "pipeline_id", "") or uuid.uuid4().hex[:12]
    lead_id = getattr(state, "lead_id", "") or ""
    tenant_id = getattr(state, "tenant_id", None)
    safe_id = re.sub(r"[^a-zA-Z0-9_.-]+", "-", pipeline_id)[:120]
    try:
        audit_dir = os.path.join(_BASE, "..", "logs", "failed_html")
        os.makedirs(audit_dir, exist_ok=True)
        path = os.path.join(audit_dir, f"{safe_id}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        meta_path = os.path.join(audit_dir, f"{safe_id}.json")
        import json as _json_failed

        with open(meta_path, "w", encoding="utf-8") as f:
            _json_failed.dump(
                {
                    "pipeline_id": pipeline_id,
                    "lead_id": lead_id,
                    "lead_nome": getattr(state, "lead_nome", ""),
                    "renderer": renderer_agent,
                    "error": str(error)[:1000],
                    "created_at": datetime.now().isoformat(),
                    "html_path": path,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception:
        pass
    if lead_id and tenant_id:
        try:
            try:
                from database import engine
            except Exception:  # pragma: no cover - package import variant
                from backend.core.database import engine

            with engine.connect() as conn:
                conn.execute(
                    text(
                        """
                        UPDATE leads
                        SET html_gerado=:html,
                            erro_pipeline=:erro,
                            atualizado_em=:ts
                        WHERE id=:id AND user_id=:uid AND status NOT IN ('concluido','descartado')
                        """
                    ),
                    {
                        "html": html,
                        "erro": str(error)[:1000],
                        "ts": datetime.now().isoformat(),
                        "id": lead_id,
                        "uid": tenant_id,
                    },
                )
                conn.commit()
        except Exception:
            pass
