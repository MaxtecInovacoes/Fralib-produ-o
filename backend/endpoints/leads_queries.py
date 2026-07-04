from fastapi import APIRouter, Depends, HTTPException
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY
import os, sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "core"))
from backend.core.database import get_db
from backend.core.auth import get_current_user

router = APIRouter(prefix="/api/leads", tags=["leads"])


# ═══════════════════════════════════════════════════════════════════
# SQL QUERIES
# ═══════════════════════════════════════════════════════════════════

del_sql = """
DELETE FROM leads WHERE user_id = :user_id AND status = :st
"""

fila_sql = """
SELECT id, nome, cidade, segmento, telefone, whatsapp, score, status, tier, dados_completos
FROM leads
WHERE user_id = :user_id AND status = :st
ORDER BY criado_em ASC
LIMIT 1
"""

desq_sql = """
SELECT id, nome, cidade, segmento, telefone, whatsapp, score, status, tier, dados_completos
FROM leads
WHERE user_id = :user_id
  AND (status = 'desqualificado' OR status = 'rejeitado')
ORDER BY criado_em DESC
LIMIT 200
"""


# ═══════════════════════════════════════════════════════════════════
# QUERY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════


@router.get("/{lead_id}/conversa")
async def get_conversa(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        result = db.execute(
            text("""
            SELECT i.id, i.mensagem, i.direcao, i.criado_em
            FROM interacoes i
            JOIN leads l ON l.id = i.lead_id
            WHERE i.lead_id = :lead_id AND l.user_id = :uid
            ORDER BY i.id ASC
        """),
            {"lead_id": lead_id, "uid": tenant_id},
        ).fetchall()
        return {"mensagens": [dict(r._mapping) for r in result]}
    except Exception:
        return {"mensagens": []}


@router.get("/mensagens-novas")
async def get_mensagens_novas(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        result = db.execute(
            text("""
            SELECT DISTINCT i.lead_nome, COUNT(*) as total
            FROM interacoes i
            JOIN leads l ON l.id = i.lead_id
            WHERE i.direcao = 'entrada'
            AND i.criado_em > (NOW() - INTERVAL '24 hours')::text
            AND l.user_id = :uid
            GROUP BY i.lead_nome
        """),
            {"uid": tenant_id},
        ).fetchall()
        return {
            "leads_com_resposta": [
                {"nome": r.lead_nome, "total": r.total} for r in result
            ]
        }
    except Exception:
        return {"leads_com_resposta": []}


@router.get("/{lead_id}/chat")
async def get_lead_chat(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    """Retorna histórico de conversas de um lead (para modal de chat no CRM)."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    # Verificar que lead pertence ao tenant
    lead = db.execute(
        text("SELECT id, nome, sdr_stage FROM leads WHERE id=:id AND user_id=:uid"),
        {"id": lead_id, "uid": tenant_id},
    ).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nao encontrado")
    msgs = db.execute(
        text("""
        SELECT mensagem, direcao, criado_em
        FROM interacoes
        WHERE lead_id = :lid
        ORDER BY id ASC
        LIMIT 100
    """),
        {"lid": lead_id},
    ).fetchall()
    return {
        "lead_nome": lead.nome,
        "sdr_stage": lead.sdr_stage,
        "mensagens": [
            {"texto": m.mensagem, "direcao": m.direcao, "ts": m.criado_em} for m in msgs
        ],
    }


@router.get("/capturados")
async def get_leads_capturados(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        cap_sql = "SELECT id, nome, cidade, segmento, rating, score, tier, status FROM leads WHERE user_id=:user_id AND status=:st ORDER BY criado_em DESC"
        result = db.execute(
            text(cap_sql), {"user_id": tenant_id, "st": "capturado"}
        ).fetchall()
        leads = []
        import json

        for r in result:
            d = dict(r._mapping)
            dc = d.get("dados_completos")
            if dc and isinstance(dc, str):
                try:
                    d["dados_completos"] = json.loads(dc)
                except json.JSONDecodeError:
                    d["dados_completos"] = {}
            elif not dc:
                d["dados_completos"] = {}
            leads.append(d)
        return {"leads": leads, "total": len(leads)}
    except Exception as e:
        print(f"[Leads] Erro capturados: {e}")
        return {"leads": [], "total": 0}


@router.delete("/fila")
async def limpar_fila_capturados(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        result = db.execute(text(del_sql), {"user_id": tenant_id, "st": "capturado"})
        db.commit()
        deletados = result.rowcount
        return {
            "ok": True,
            "deletados": deletados,
            "mensagem": str(deletados) + " lead(s) removido(s) da fila",
        }
    except Exception as e:
        print(f"[Leads] Erro limpar fila: {e}")
        import traceback

        traceback.print_exc()
        raise


@router.post("/processar-fila")
async def processar_proximo_fila(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):

    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        fila = db.execute(
            text(fila_sql), {"user_id": tenant_id, "st": "capturado"}
        ).fetchone()
        if not fila:
            return {"ok": False, "mensagem": "Nenhum lead na fila"}
        return {
            "ok": True,
            "mensagem": "Processando lead: " + fila.nome,
            "lead_id": fila.id,
        }
    except Exception as e:
        print(f"[Leads] Erro processar fila: {e}")
        raise


@router.get("/desqualificados")
async def get_leads_desqualificados(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        result = db.execute(text(desq_sql), {"user_id": tenant_id}).fetchall()
        leads = []
        import json

        for r in result:
            d = dict(r._mapping)
            dc = d.get("dados_completos")
            if dc and isinstance(dc, str):
                try:
                    d["dados_completos"] = json.loads(dc)
                except json.JSONDecodeError:
                    d["dados_completos"] = {}
            elif not dc:
                d["dados_completos"] = {}
            leads.append(d)
        return {"leads": leads, "total": len(leads)}
    except Exception as e:
        print(f"[Leads] Erro desqualificados: {e}")
        return {"leads": [], "total": 0}


@router.get("/incompletos")
async def get_leads_incompletos(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    """Leads incompletos/rejeitados para revisão manual."""
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        result = db.execute(
            text("""
            SELECT id, nome, cidade, segmento, telefone, whatsapp, score, status, criado_em, observacoes
            FROM leads
            WHERE user_id = :uid
              AND (
                score < 20
                OR status = 'rejeitado'
                OR (nome IS NULL OR nome = '')
                OR (telefone IS NULL OR telefone = '')
              )
            ORDER BY criado_em DESC
            LIMIT 200
        """),
            {"uid": tenant_id},
        ).fetchall()
        leads = [dict(r._mapping) for r in result]
        return {"leads": leads, "total": len(leads)}
    except Exception as e:
        print(f"[Leads] Erro incompletos: {e}")
        return {"leads": [], "total": 0}


@router.get("/fila-qualificados")
async def get_fila_qualificados(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    """Fila de atendimento: apenas leads que completaram pipeline (site pronto, aguardando SDR enviar msg)."""
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        result = db.execute(
            text("""
            SELECT id, nome, cidade, segmento, score, tier, status, criado_em
            FROM leads
            WHERE user_id = :uid
              AND status = 'concluido'
              AND (sdr_stage IN ('hook', 'pendente_wpp') OR sdr_stage IS NULL)
            ORDER BY criado_em ASC
            LIMIT 100
        """),
            {"uid": tenant_id},
        ).fetchall()
        leads = []
        for i, r in enumerate(result):
            d = dict(r._mapping)
            d["posicao"] = i + 1
            leads.append(d)
        return {"leads": leads, "total": len(leads)}
    except Exception as e:
        print(f"[Leads] Erro fila-qualificados: {e}")
        return {"leads": [], "total": 0}


@router.get("/descartados")
async def get_descartados(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        result = db.execute(
            text("""
            SELECT id, nome, cidade, segmento, telefone, telefone_whatsapp, score, status, criado_em, atualizado_em
            FROM leads
            WHERE user_id = :uid AND status = 'descartado'
            ORDER BY atualizado_em DESC
            LIMIT 100
        """),
            {"uid": tenant_id},
        ).fetchall()
        leads = [dict(r._mapping) for r in result]
        return {"leads": leads, "total": len(leads)}
    except Exception as e:
        print(f"[Leads] Erro descartados: {e}")
        return {"leads": [], "total": 0}


@router.get("/pendentes-whatsapp")
async def get_leads_pendentes_whatsapp(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    """Retorna leads que precisam de WhatsApp conectado para receber mensagens.

    - Leads que responderam mas o WhatsApp do usuario nao esta conectado
    - Mostra tempo de espera para criar urgencia
    """
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])

        # Buscar leads que:
        # 1. Tiveram resposta do WhatsApp (interacoes de entrada)
        # 2. Mas ainda nao foram convertidos em cliente
        # 3. Ordenados por tempo de espera (mais antigos primeiro)
        result = db.execute(
            text("""
            SELECT
                l.id,
                l.nome,
                l.cidade,
                l.segmento,
                l.telefone,
                l.telefone_whatsapp,
                l.site_url,
                l.score,
                l.status,
                l.criado_em,
                COALESCE(ultima_interacao.criado_em, l.criado_em) as ultima_interacao_em,
                EXTRACT(EPOCH FROM (NOW() - COALESCE(ultima_interacao.criado_em, l.criado_em))) / 3600 as horas_espera
            FROM leads l
            LEFT JOIN (
                SELECT lead_id, MAX(criado_em) as criado_em
                FROM interacoes
                WHERE direcao = 'entrada'
                GROUP BY lead_id
            ) ultima_interacao ON ultima_interacao.lead_id = l.id
            WHERE l.user_id = :uid
              AND l.telefone_whatsapp IS NOT NULL
              AND l.telefone_whatsapp != ''
              AND l.status NOT IN ('won', 'convertido', 'lost', 'perdido')
              AND (
                  -- Teve interacao de entrada (lead respondeu)
                  ultima_interacao.criado_em IS NOT NULL
                  OR
                  -- Ou foi criado nos ultimos 7 dias e ainda nao foi contatado
                  (l.criado_em > NOW() - INTERVAL '7 days' AND l.status IN ('novo', 'capturado'))
              )
            ORDER BY horas_espera DESC
            LIMIT 20
            """),
            {"uid": tenant_id},
        ).fetchall()

        leads = []
        for r in result:
            d = dict(r._mapping)
            # Calcular tempo legivel
            horas = d.get("horas_espera") or 0
            if horas < 1:
                tempo = "agora"
            elif horas < 24:
                tempo = f"{int(horas)}h"
            elif horas < 168:  # 7 dias
                dias = int(horas / 24)
                tempo = f"{dias}d"
            else:
                semanas = int(horas / 168)
                tempo = f"{semanas}s"
            d["tempo_espera"] = tempo
            leads.append(d)

        return {"leads": leads, "count": len(leads)}
    except Exception as e:
        print(f"[Leads] Erro pendentes-whatsapp: {e}")
        import traceback
        traceback.print_exc()
        return {"leads": [], "count": 0}
