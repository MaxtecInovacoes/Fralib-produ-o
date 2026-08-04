import os
import sys
sys.path.append("/root/fralib/backend")
import re as _re
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel as _BaseModel
from database import get_db
from auth import get_current_user
from sse_endpoints import adicionar_log

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])
logger = logging.getLogger("uvicorn")


# === LEGACY STUBS — agentes removidos ===

class _LizRemovida(Exception):
    pass

def _liz_stub(*args, **kwargs):
    raise _LizRemovida("agents.liz foi removido. Use QA v2 (quality_gate_v2) para validacao de HTML.")

# Substituem imports de agents.liz
editar_secao = _liz_stub
listar_secoes = _liz_stub


class EditarSecaoRequest(_BaseModel):
    lead_id: str
    secao: str
    instrucao: str


@router.post("/editar-secao")
async def editar_secao_endpoint(
    req: EditarSecaoRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    result = db.execute(
        text("SELECT site_url, nome FROM leads WHERE id = :lead_id AND user_id = :uid"),
        {"lead_id": req.lead_id, "uid": tenant_id}
    ).fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Lead nao encontrado")
    site_url = result[0]
    lead_nome = result[1]
    if not site_url:
        raise HTTPException(status_code=404, detail="Site ainda nao foi gerado para este lead")
    slug = _re.sub(r"[^a-z0-9]+", "-", lead_nome.lower()).strip("-")[:50]
    html_path = f"/var/www/fralib/sites/{tenant_id}/{slug}/index.html"
    # fallback para path legado
    if not os.path.exists(html_path):
        html_path = f"/var/www/fralib/sites/{slug}/index.html"
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail=f"Arquivo HTML nao encontrado: {html_path}")
    with open(html_path, "r", encoding="utf-8") as f:
        html_atual = f.read()
    secoes_disponiveis = listar_secoes(html_atual)
    if req.secao not in secoes_disponiveis and req.secao != "geral":
        raise HTTPException(status_code=400, detail=f"Secao nao encontrada. Disponiveis: {secoes_disponiveis}")
    adicionar_log(f"[Edicao] Editando secao {req.secao} do lead {lead_nome}", "info")
    html_editado = editar_secao(html_atual, req.secao, req.instrucao)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_editado)
    adicionar_log(f"[Edicao] Secao {req.secao} editada com sucesso", "success")
    logger.info(f"[Pipeline] Edicao: secao={req.secao} lead={req.lead_id}")
    return {"sucesso": True, "secao": req.secao, "lead_id": req.lead_id, "html_path": html_path, "tamanho_html": len(html_editado), "mensagem": f"Secao {req.secao} editada com sucesso"}


@router.get("/listar-secoes/{lead_id}")
async def listar_secoes_endpoint(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    # agents.liz removido (legado). listar_secoes e editar_secao sao stubs que levantam _LizRemovida.
    tenant_id = usuario.get("tenant_id", usuario["id"])
    result = db.execute(
        text("SELECT site_url, nome FROM leads WHERE id = :lead_id AND user_id = :uid"),
        {"lead_id": lead_id, "uid": tenant_id}
    ).fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Lead nao encontrado")
    lead_nome = result[1]
    slug = _re.sub(r"[^a-z0-9]+", "-", lead_nome.lower()).strip("-")[:50]
    html_path = f"/var/www/fralib/sites/{tenant_id}/{slug}/index.html"
    if not os.path.exists(html_path):
        html_path = f"/var/www/fralib/sites/{slug}/index.html"
    if not os.path.exists(html_path):
        return {"secoes": [], "mensagem": "Site ainda nao gerado"}
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    secoes = listar_secoes(html)
    return {"lead_id": lead_id, "lead_nome": lead_nome, "secoes": secoes, "total": len(secoes)}
