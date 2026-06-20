#!/usr/bin/env python3
"""Generate a fast local Builder preview without running the full pipeline."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from sqlalchemy import text


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND, BACKEND / "core", BACKEND / "services"):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    load_dotenv(BACKEND / ".env")
except Exception:
    pass

from database import SessionLocal  # noqa: E402
from services.builder_worker import render_site_with_builder  # noqa: E402
from services.pipeline_prd_builder import (  # noqa: E402
    build_prompt_agent_prd,
    build_skill_fast_prd,
    ensure_prd_contracts,
    ensure_prd_design_reference,
    ensure_prd_publication_identity,
)


def _slugify(value: str) -> str:
    text_value = unicodedata.normalize("NFKD", str(value or ""))
    text_value = "".join(ch for ch in text_value if not unicodedata.combining(ch))
    text_value = re.sub(r"[^a-zA-Z0-9]+", "-", text_value).strip("-").lower()
    return text_value or f"preview-{uuid.uuid4().hex[:8]}"


def _load_lead(tenant_id: int, lead_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        row = db.execute(
            text(
                """
                SELECT id, user_id, nome, segmento, cidade, telefone, whatsapp, endereco,
                       rating, total_avaliacoes, website, site, dados_completos
                FROM leads
                WHERE id=:lead_id AND user_id=:tenant_id
                """
            ),
            {"lead_id": lead_id, "tenant_id": tenant_id},
        ).fetchone()
    if not row:
        raise RuntimeError(f"lead {lead_id} nao encontrado para tenant {tenant_id}")
    lead = dict(row._mapping)
    dados = lead.get("dados_completos") or {}
    if isinstance(dados, str):
        try:
            dados = json.loads(dados)
        except Exception:
            dados = {}
    if not isinstance(dados, dict):
        dados = {}
    merged = dict(dados)
    merged.setdefault("id", str(lead.get("id") or ""))
    merged.setdefault("nome", lead.get("nome") or "")
    merged.setdefault("segmento", lead.get("segmento") or "")
    merged.setdefault("cidade", lead.get("cidade") or "")
    merged.setdefault("telefone", lead.get("telefone") or "")
    merged.setdefault("whatsapp", lead.get("whatsapp") or "")
    merged.setdefault("endereco", lead.get("endereco") or "")
    merged.setdefault("rating", lead.get("rating") or 0)
    merged.setdefault("total_avaliacoes", lead.get("total_avaliacoes") or 0)
    merged.setdefault("website", lead.get("website") or lead.get("site") or "")
    return merged


def _load_raw_json(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("arquivo JSON precisa conter um objeto")
    return data


def _state_from_raw(raw: dict[str, Any], tenant_id: int, *, flow: str, keyword_research: str = "") -> Any:
    nome = str(raw.get("nome") or raw.get("business_name") or raw.get("name") or "").strip()
    segmento = str(raw.get("segmento") or raw.get("segment") or raw.get("nicho") or "").strip()
    cidade = str(raw.get("cidade") or raw.get("city") or "").strip()
    lead_id = str(raw.get("id") or raw.get("lead_id") or uuid.uuid4())
    qual = SimpleNamespace(
        tier=str(raw.get("tier") or raw.get("caio_tier") or "STANDARD"),
        score=int(raw.get("score") or raw.get("caio_score") or 0),
        motivo=str(raw.get("motivo") or raw.get("caio_motivo") or "preview fast"),
    )
    lead_ns = SimpleNamespace(
        id=lead_id,
        nome=nome,
        segmento=segmento,
        cidade=cidade,
        telefone=str(raw.get("telefone") or raw.get("phone") or ""),
        whatsapp=str(raw.get("whatsapp") or ""),
        endereco=str(raw.get("endereco") or raw.get("address") or ""),
        rating=raw.get("rating") or 0,
        reviews_count=raw.get("reviews_count") or raw.get("total_avaliacoes") or 0,
    )
    state = SimpleNamespace(
        tenant_id=tenant_id,
        pipeline_id=f"preview-fast-{lead_id}",
        run_id=f"preview-{uuid.uuid4().hex[:12]}",
        lead_raw_data=raw,
        lead_obj=SimpleNamespace(id=lead_id, lead=lead_ns),
        lead_id=lead_id,
        lead_nome=nome,
        lead_slug=_slugify(nome),
        segmento=segmento,
        cidade=cidade,
        qualificacao_caio=qual,
        jina_insights=str(raw.get("jina_insights") or ""),
        jina_intel_dict=raw.get("jina_market_intelligence") or {},
        keyword_research=keyword_research or str(raw.get("keyword_research") or ""),
        briefing_theo=str(raw.get("briefing_theo") or ""),
        nicho_briefing=None,
        variacao_estrutural=None,
    )
    if flow == "prompt-agent":
        state.nicho_briefing = raw.get("nicho_briefing")
        state.variacao_estrutural = raw.get("variacao_estrutural")
    return state


def _build_prd(state: Any, tenant_id: int, flow: str) -> Any:
    if flow == "prompt-agent":
        prd = build_prompt_agent_prd(state, tenant_id)
    else:
        prd = build_skill_fast_prd(state)
    ensure_prd_design_reference(prd, state)
    ensure_prd_contracts(prd, state)
    ensure_prd_publication_identity(prd, state, tenant_id)
    return prd


def main() -> int:
    parser = argparse.ArgumentParser(description="FraLib Builder Preview Fast")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--lead-id")
    source.add_argument("--lead-json")
    parser.add_argument("--tenant-id", type=int, default=2)
    parser.add_argument("--flow", choices=["skill-fast", "prompt-agent"], default="skill-fast")
    parser.add_argument("--job-id", default="")
    parser.add_argument("--keyword-research", default="")
    parser.add_argument("--publication-url", default="")
    parser.add_argument("--dump-prd-json", default="")
    args = parser.parse_args()

    raw = _load_lead(args.tenant_id, args.lead_id) if args.lead_id else _load_raw_json(args.lead_json)
    state = _state_from_raw(raw, args.tenant_id, flow=args.flow, keyword_research=args.keyword_research)
    prd = _build_prd(state, args.tenant_id, args.flow)
    if args.dump_prd_json:
        dump_target = Path(args.dump_prd_json)
        dump_target.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(prd, "model_dump"):
            payload = prd.model_dump()
        elif hasattr(prd, "__dict__"):
            payload = dict(prd.__dict__)
        else:
            payload = prd
        dump_target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    os.environ["FRALIB_VITE_PREVIEW_FAST"] = "1"
    job_id = args.job_id or f"preview-{state.lead_slug}-{uuid.uuid4().hex[:8]}"
    result = render_site_with_builder(
        prd,
        tenant_id=args.tenant_id,
        job_id=job_id,
        target="landing-page",
        publication_url=args.publication_url or "",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "flow": args.flow,
                "tenant_id": args.tenant_id,
                "lead_id": state.lead_id,
                "lead_nome": state.lead_nome,
                "lead_slug": state.lead_slug,
                "engine": result.get("engine"),
                "model": result.get("model"),
                "index_path": result.get("index_path"),
                "output_dir": result.get("output_dir"),
                "manifest_path": result.get("manifest_path"),
                "attempts": result.get("attempts"),
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
