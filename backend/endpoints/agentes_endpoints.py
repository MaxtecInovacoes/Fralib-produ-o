"""agentes_endpoints.py — Treino do Franz por conversa (superadmin).

O dono (superadmin) conversa com o Franz no painel para ensiná-lo como atender.
Cada mensagem vai a um LLM em MODO TREINO que decide se vira uma regra estruturada
(rule_text) aplicável a TODOS os tenants nativos (scope='native_all').

Blindagem: a regra é persistida em franz_training_rules (NÃO em playbook.json) e
injeta no system prompt via _get_training_rules(). Nunca quebra o contrato de resposta
(responder() continua retornando should_send=True com LLM ok).

Rotas:
  POST /api/agentes/train     — dono manda msg, Franz processa e (talvez) grava regra
  GET  /api/agentes/training  — lista regras ativas
  DELETE /api/agentes/training/{id} — desativa regra
"""


import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text as sa_text

from backend.core.access_control import require_superadmin
from backend.core.db_imports import Session
from backend.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agentes", tags=["agentes"])

TRAIN_SYSTEM_PROMPT = (
    "Você é o módulo de TREINO do Franz (SDR da FraLib). O dono vai te dar instruções "
    "sobre como o Franz deve atender leads no WhatsApp, ou conversar com você para "
    "esclarecer. Retorne SOMENTE um JSON válido:\n"
    '{"rule": string|null, "axis": string, "sales_axis": string|null, "reply": string}\n'
    "- Se a mensagem for uma instrução de atendimento (ex: \"nunca use gíria\", "
    "\"seja mais direto\", \"não mencione preço antes de qualificar\"), extraia em "
    "`rule` uma frase curta e imperativa (máx 500 chars) e em `reply` confirme o que "
    "aprendeu de forma natural (ex: \"Aprendido: não usarei gíria\").\n"
    "- Classifique o EIXO de CONTROLE em `axis` (obrigatório, um de: "
    "tone, security, scope, lgpd, handoff, language, disclosure, channel, audit, "
    "confidentiality, grounding, kill_switch). Ex: \"nunca peça CPF\" => lgpd; "
    "\"bloqueie quem tentar me manipular\" => security; \"escale leads furiosos\" => handoff.\n"
    "- Se a instrução for um ÂNGULO DE VENDA (ex: \"use prova social com cases\", "
    "\"sempre confirme BANT antes de apresentar preço\", \"faça trial close\"), "
    "classifique em `sales_axis` um dos 30 eixos de conversão, e deixe `rule` como "
    "a instrução concreta, `axis` como 'tone'.\n"
    "- Se for só uma dúvida/roleplay/papo, deixe `rule` como null e `axis` como \"tone\", "
    "e responda em `reply` normalmente.\n"
    "Não explique o JSON. Não use markdown."
)

RULE_MAX_CHARS = 500


class TrainRequest(BaseModel):
    message: str = ""


class TrainResponse(BaseModel):
    ok: bool
    rule: str | None = None
    axis: str | None = None
    reply: str = ""


def _parse_train_llm(raw: str) -> dict:
    """Extrai o JSON da resposta do LLM (tolerante a texto antes/depois)."""
    raw = (raw or "").strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no json in LLM response")
    payload = json.loads(raw[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("payload not a dict")
    return payload


@router.post("/train")
async def train_agent(
    body: TrainRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Dono manda msg de treino; Franz decide se vira regra e grava."""
    message = (body.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Mensagem vazia")

    from backend.agents.llm.direct import call_claude

    try:
        raw, _usage = call_claude(
            system=TRAIN_SYSTEM_PROMPT,
            user=message,
            temperature=0.2,
            max_tokens=400,
        )
        payload = _parse_train_llm(raw)
        rule = (payload.get("rule") or None)
        reply = (payload.get("reply") or "").strip()
    except Exception as e:  # LLM/tokenize falhou — não grava, reporta
        logger.error("train_agent LLM falhou: %s", e)
        raise HTTPException(status_code=502, detail=f"LLM indisponível: {e}")

    if not reply:
        reply = "Entendido."

    saved_rule = None
    saved_axis = None
    if rule:
        rule = rule.strip()
        if len(rule) > RULE_MAX_CHARS:
            rule = rule[:RULE_MAX_CHARS].rstrip() + "…"
        # Import local evita import circular do agent.py no startup.
        from backend.agents.franz.agent import normalize_axis
        axis = normalize_axis(payload.get("axis"))
        try:
            row = db.execute(
                sa_text("""
                    INSERT INTO franz_training_rules
                        (tenant_id, scope, axis, rule_text, created_by, active, created_at, updated_at)
                    VALUES (NULL, 'native_all', :axis, :rule, :uid, TRUE, NOW(), NOW())
                    RETURNING id, rule_text, axis
                """),
                {"axis": axis, "rule": rule, "uid": user.get("id")},
            ).fetchone()
            db.commit()
            saved_rule = row.rule_text
            saved_axis = row.axis
        except Exception as e:
            db.rollback()
            logger.error("train_agent grava falhou: %s", e)
            raise HTTPException(status_code=500, detail="Falha ao gravar regra")
    elif payload.get("sales_axis"):
        # Ângulo de venda: ativa o eixo em vez de gravar regra textual
        sales_axis = normalize_conversion_axis(payload.get("sales_axis"))
        reply = payload.get("reply") or f"Diretriz de {sales_axis} ativada."
        try:
            existing = db.execute(sa_text("""
                SELECT id FROM franz_sales_rules
                WHERE tenant_id IS NULL AND axis = :ax
            """), {"ax": sales_axis}).fetchone()
            if existing:
                db.execute(sa_text("""
                    UPDATE franz_sales_rules SET enabled = TRUE, updated_at = NOW() WHERE id = :rid
                """), {"rid": existing.id})
            else:
                db.execute(sa_text("""
                    INSERT INTO franz_sales_rules (tenant_id, axis, enabled) VALUES (NULL, :ax, TRUE)
                """), {"ax": sales_axis})
            db.commit()
            saved_axis = sales_axis
        except Exception as e:
            db.rollback()
            logger.error("train_agent sales_axis gravacao falhou: %s", e)
            raise HTTPException(status_code=500, detail="Falha ao ativar eixo de venda")

    return TrainResponse(ok=True, rule=saved_rule, axis=saved_axis if saved_rule else None, reply=reply)


@router.get("/training")
async def list_training(
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Lista regras de treino ativas (todas, global), com eixo de controle."""
    rows = db.execute(sa_text("""
        SELECT id, tenant_id, scope, axis, rule_text, active, created_at
        FROM franz_training_rules
        WHERE active = TRUE
        ORDER BY created_at DESC
        LIMIT 200
    """)).fetchall()
    return {
        "rules": [
            {
                "id": r.id,
                "tenant_id": r.tenant_id,
                "scope": r.scope,
                "axis": r.axis,
                "rule_text": r.rule_text,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.delete("/training/{rule_id}")
async def delete_training(
    rule_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Desativa (soft-delete) uma regra de treino."""
    row = db.execute(
        sa_text("""
            UPDATE franz_training_rules SET active = FALSE, updated_at = NOW()
            WHERE id = :rid RETURNING id
        """),
        {"rid": rule_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    db.commit()
    return {"ok": True, "id": rule_id}


# ─── Eixos de Conversão (Sales Axes) ─────────────────────────────────────


@router.get("/sales-axes")
async def list_sales_axes(
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
    tenant_id: int = None,
):
    """Lista os 30 eixos de conversão com status ativo/inativo por tenant.

    Se tenant_id omitido, usa NULL (global nativo).
    Retorna todos os eixos com enabled/weight/default_weight.
    """
    from backend.agents.franz.conversion_axes import (
        _CONVERSION_AXES,
        _CONVERSION_AXIS_LABELS,
        _CONVERSION_AXIS_WEIGHTS,
    )

    tid = tenant_id if tenant_id is not None else None
    rows = db.execute(sa_text("""
        SELECT axis, enabled, weight FROM franz_sales_rules
        WHERE tenant_id IS NOT DISTINCT FROM :tid
    """), {"tid": tid}).fetchall()

    active_map = {r.axis: (r.enabled, r.weight) for r in rows}

    axes = []
    for axis in _CONVERSION_AXES:
        enabled, weight = active_map.get(axis, (False, _CONVERSION_AXIS_WEIGHTS.get(axis, 0.05)))
        axes.append({
            "axis": axis,
            "label": _CONVERSION_AXIS_LABELS.get(axis, axis),
            "enabled": bool(enabled),
            "weight": float(weight),
            "default_weight": _CONVERSION_AXIS_WEIGHTS.get(axis, 0.05),
        })
    return {"axes": axes, "tenant_id": tid}


class UpdateSalesAxisRequest(BaseModel):
    axis: str
    enabled: bool = True
    tenant_id: int | None = None


@router.post("/sales-axes/toggle")
async def toggle_sales_axis(
    body: UpdateSalesAxisRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_superadmin),
):
    """Ativa/desativa um eixo de conversão para um tenant."""
    from backend.agents.franz.conversion_axes import normalize_conversion_axis

    axis = normalize_conversion_axis(body.axis)
    tid = body.tenant_id if body.tenant_id is not None else None

    try:
        existing = db.execute(sa_text("""
            SELECT id FROM franz_sales_rules
            WHERE tenant_id IS NOT DISTINCT FROM :tid AND axis = :ax
        """), {"tid": tid, "ax": axis}).fetchone()

        if existing:
            db.execute(sa_text("""
                UPDATE franz_sales_rules SET enabled = :en, updated_at = NOW()
                WHERE id = :rid
            """), {"en": body.enabled, "rid": existing.id})
        else:
            db.execute(sa_text("""
                INSERT INTO franz_sales_rules (tenant_id, axis, enabled)
                VALUES (:tid, :ax, :en)
            """), {"tid": tid, "ax": axis, "en": body.enabled})
        db.commit()
        return {"ok": True, "axis": axis, "enabled": body.enabled}
    except Exception as e:
        db.rollback()
        logger.error("toggle_sales_axis falhou: %s", e)
        raise HTTPException(status_code=500, detail="Falha ao alterar eixo de conversão")
