"""Rotas de monitoramento do pipeline: cooldown-status, analytics/overview, stats."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional

from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.get("/cooldown-status")
async def cooldown_status(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Status completo de cooldown, creditos e fila para dashboard."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    from services.credits_manager import validar_permissao_pipeline, get_user_tokens, LIMITES_DIARIOS, COOLDOWNS

    perm = validar_permissao_pipeline(db, tenant_id)
    info = get_user_tokens(db, tenant_id)
    plano = info.get("plano", "trial")
    cooldown_secs = COOLDOWNS.get(plano, 3600)
    limite = LIMITES_DIARIOS.get(plano, 1)

    pode_rodar = perm["allowed"]

    # Cooldown info
    cooldown_info = {"ativo": False, "total_seg": cooldown_secs, "restante_seg": 0, "percentual_completo": 100}
    if not pode_rodar and perm.get("reason") == "cooldown":
        cooldown_info = {
            "ativo": True,
            "total_seg": cooldown_secs,
            "restante_seg": perm.get("cooldown_restante_seg", 0),
            "proximo_em": perm.get("proximo_em"),
            "percentual_completo": round((1 - perm.get("cooldown_restante_seg", 0) / max(cooldown_secs, 1)) * 100, 1),
        }

    # Creditos info
    creditos_info = {
        "limite_diario": limite,
        "usados_hoje": info.get("sites_hoje", 0),
        "restantes_hoje": info.get("creditos_restantes_hoje", limite),
        "reset_at": None,
    }
    if not pode_rodar and perm.get("reason") == "creditos_esgotados":
        from services.credits_manager import _proximo_reset_iso
        creditos_info["reset_at"] = _proximo_reset_iso()

    # Fila de leads
    fila_row = db.execute(text("""
        SELECT COUNT(*) as total,
               (SELECT nome FROM leads WHERE user_id=:uid AND status='capturado' ORDER BY score DESC LIMIT 1),
               (SELECT cidade FROM leads WHERE user_id=:uid AND status='capturado' ORDER BY score DESC LIMIT 1)
        FROM leads WHERE user_id=:uid AND status='capturado'
    """), {"uid": tenant_id}).fetchone()
    fila = {
        "leads_aguardando": fila_row[0] if fila_row else 0,
        "proximo_lead_nome": fila_row[1] if fila_row else None,
        "proximo_lead_cidade": fila_row[2] if fila_row else None,
        "auto_run_ativo": (fila_row[0] or 0) > 0,
    }

    # Uso
    uso = {"sites_hoje": info.get("sites_hoje", 0), "sites_total": info.get("sites_used", 0)}

    return {
        "pode_rodar": pode_rodar,
        "raiz_bloqueio": perm.get("reason"),
        "cooldown": cooldown_info,
        "creditos": creditos_info,
        "fila": fila,
        "uso": uso,
    }


@router.get("/analytics/overview")
async def get_analytics(periodo: str = "mes", db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Overview de analytics do tenant."""
    agora = datetime.now()
    if periodo == "hoje":
        inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "semana":
        inicio = agora - timedelta(days=7)
    elif periodo == "mes":
        inicio = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "ano":
        inicio = agora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        inicio = None

    tenant_id = usuario.get("tenant_id", usuario["id"])
    if inicio:
        where = "WHERE user_id = :uid AND criado_em >= :inicio"
        params = {"uid": tenant_id, "inicio": inicio.isoformat()}
    else:
        where = "WHERE user_id = :uid"
        params = {"uid": tenant_id}

    total_leads = db.execute(text(f"SELECT COUNT(*) FROM leads {where}"), params).scalar() or 0
    total_sites = db.execute(text(f"SELECT COUNT(*) FROM leads {where} AND url_site IS NOT NULL AND url_site != ''"), params).scalar() or 0
    total_vendidos = db.execute(text(f"SELECT COUNT(*) FROM leads {where} AND valor_venda > 0"), params).scalar() or 0
    receita = db.execute(text(f"SELECT COALESCE(SUM(valor_venda),0) FROM leads {where} AND valor_venda > 0"), params).scalar() or 0

    conversao_site = round((total_sites / total_leads * 100), 1) if total_leads > 0 else 0
    conversao_venda = round((total_vendidos / total_sites * 100), 1) if total_sites > 0 else 0

    leads_por_dia_rows = db.execute(text(
        "SELECT DATE(criado_em::timestamp) as dia, COUNT(*) as total "
        "FROM leads "
        "WHERE user_id = :uid AND criado_em IS NOT NULL AND criado_em != '' "
        "GROUP BY dia ORDER BY dia DESC LIMIT 30"
    ), {"uid": tenant_id}).fetchall()

    top_cidades_rows = db.execute(text(f"SELECT cidade, COUNT(*) as total FROM leads {where} GROUP BY cidade ORDER BY total DESC LIMIT 8"), params).fetchall()
    top_nichos_rows = db.execute(text(f"SELECT segmento, COUNT(*) as total FROM leads {where} GROUP BY segmento ORDER BY total DESC LIMIT 8"), params).fetchall()
    total_ciclos = db.execute(text("SELECT COUNT(*) FROM ciclos WHERE user_id = :uid"), {"uid": tenant_id}).scalar() or 0

    return {
        "periodo": periodo,
        "total_leads": total_leads,
        "total_sites": total_sites,
        "total_vendidos": total_vendidos,
        "receita": float(receita),
        "conversao": conversao_site,
        "conversao_venda": conversao_venda,
        "total_ciclos": total_ciclos,
        "leads_qualificados": total_sites,
        "taxa_conversao": conversao_site,
        "por_dia": [{"dia": str(r.dia), "total": r.total} for r in leads_por_dia_rows],
        "por_cidade": [{"nome": r.cidade or "-", "total": r.total} for r in top_cidades_rows],
        "por_nicho": [{"nome": r.segmento or "-", "total": r.total} for r in top_nichos_rows],
    }


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Stats operacionais do tenant."""
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        total_com_site = db.execute(text(
            "SELECT COUNT(*) FROM leads WHERE user_id=:uid AND url_site IS NOT NULL AND url_site != ''"
        ), {"uid": tenant_id}).scalar() or 0
        total_respondeu = db.execute(text(
            "SELECT COUNT(DISTINCT i.lead_nome) FROM interacoes i "
            "JOIN leads l ON l.nome=i.lead_nome WHERE l.user_id=:uid AND i.direcao='entrada'"
        ), {"uid": tenant_id}).scalar() or 0
        taxa_resposta = round(total_respondeu / total_com_site * 100, 1) if total_com_site > 0 else 0

        nicho_top = db.execute(text("""
            SELECT segmento,
                   COUNT(CASE WHEN url_site IS NOT NULL AND url_site != '' THEN 1 END) * 100.0 / COUNT(*) as conv
            FROM leads
            WHERE user_id = :uid AND segmento IS NOT NULL AND segmento != ''
            GROUP BY segmento
            HAVING COUNT(*) >= 3
            ORDER BY conv DESC
            LIMIT 1
        """), {"uid": tenant_id}).fetchone()

        cidade_top = db.execute(text("""
            SELECT cidade, COUNT(*) as total
            FROM leads
            WHERE user_id = :uid AND cidade IS NOT NULL AND cidade != ''
            GROUP BY cidade
            ORDER BY total DESC
            LIMIT 1
        """), {"uid": tenant_id}).fetchone()

        ticket_medio = db.execute(text(
            "SELECT COALESCE(AVG(valor_venda), 0) FROM leads WHERE user_id=:uid AND valor_venda > 0"
        ), {"uid": tenant_id}).scalar() or 0
        total_msgs = db.execute(text(
            "SELECT COUNT(*) FROM interacoes i JOIN leads l ON l.nome=i.lead_nome WHERE l.user_id=:uid AND i.direcao='saida'"
        ), {"uid": tenant_id}).scalar() or 0

        return {
            "taxa_resposta": taxa_resposta,
            "nicho_top": nicho_top.segmento if nicho_top else "—",
            "nicho_top_conv": round(nicho_top.conv, 1) if nicho_top else 0,
            "cidade_top": cidade_top.cidade if cidade_top else "—",
            "cidade_top_total": cidade_top.total if cidade_top else 0,
            "ticket_medio": float(ticket_medio),
            "total_msgs_bryan": total_msgs,
        }
    except Exception as e:
        print(f"[Stats] Erro: {e}")
        return {
            "taxa_resposta": 0, "nicho_top": "—", "nicho_top_conv": 0,
            "cidade_top": "—", "cidade_top_total": 0, "ticket_medio": 0, "total_msgs_bryan": 0
        }
