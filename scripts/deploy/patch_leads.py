"""Patch: adiciona endpoints faltantes ao leads_endpoints.py existente."""

filepath = "/opt/fralib/backend/endpoints/leads_endpoints.py"

with open(filepath, "r") as f:
    content = f.read()

# Adicionar endpoints: escalados, assumir, conversas-ativas
missing = '''

# ─── Adicionado por Hermes (2026-08-06) ─────────────────────────────────────

@router.get("/escalados")
async def get_escalados(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Lista leads que precisam de followup humano."""
    uid = usuario.get("tenant_id", usuario["id"])
    try:
        rows = db.execute(text("""
            SELECT id, nome, telefone, whatsapp, cidade, segmento,
                   atualizado_em, status, sdr_stage,
                   COALESCE(observacoes, '') as followup_reason
            FROM leads
            WHERE user_id = :uid
              AND (
                sdr_stage IN ('escalated', 'human_followup', 'blocked', 'needs_human')
                OR status IN ('erro', 'failed', 'escalated')
                OR observacoes ILIKE '%%escalado%%'
                OR observacoes ILIKE '%%followup%%'
              )
            ORDER BY atualizado_em DESC NULLS LAST
            LIMIT 50
        """), {"uid": uid}).fetchall()
        escalados = []
        for r in rows:
            d = dict(r._mapping)
            if d.get("atualizado_em"):
                d["atualizado_em"] = str(d["atualizado_em"])
            escalados.append(d)
        return {"escalados": escalados, "total": len(escalados)}
    except Exception:
        return {"escalados": [], "total": 0}


@router.post("/{lead_id}/assumir")
async def assumir_lead(lead_id: str, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Marca lead como assumido pelo humano."""
    uid = usuario.get("tenant_id", usuario["id"])
    try:
        result = db.execute(text("""
            UPDATE leads SET sdr_stage = 'human_takeover', status = 'pendente',
            atualizado_em = NOW() WHERE id = :id AND user_id = :uid RETURNING id
        """), {"id": lead_id, "uid": uid}).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Lead nao encontrado")
        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversas-ativas")
async def get_conversas_ativas(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Lista leads com conversa WhatsApp ativa."""
    uid = usuario.get("tenant_id", usuario["id"])
    try:
        rows = db.execute(text("""
            SELECT l.id, l.nome, l.cidade, l.segmento, l.telefone, l.whatsapp,
                   l.sdr_stage, l.status, l.atualizado_em,
                   COUNT(i.id) as total_msgs,
                   MAX(i.criado_em) as ultima_msg
            FROM leads l
            LEFT JOIN interacoes i ON i.lead_id = l.id
            WHERE l.user_id = :uid AND l.status NOT IN ('descartado', 'perdido')
            GROUP BY l.id
            HAVING COUNT(i.id) > 0
            ORDER BY ultima_msg DESC NULLS LAST
            LIMIT 30
        """), {"uid": uid}).fetchall()
        leads = []
        for r in rows:
            d = dict(r._mapping)
            if d.get("atualizado_em"):
                d["atualizado_em"] = str(d["atualizado_em"])
            leads.append(d)
        return {"leads": leads, "total": len(leads)}
    except Exception:
        return {"leads": [], "total": 0}

'''

# Adicionar no final do arquivo (antes de eventuais imports de rodapé)
if "# Adicionado por Hermes" not in content:
    content = content.rstrip() + "\n" + missing

with open(filepath, "w") as f:
    f.write(content)
print("Patch OK: endpoints escalados/assumir/conversas-ativas adicionados a leads_endpoints.py")
