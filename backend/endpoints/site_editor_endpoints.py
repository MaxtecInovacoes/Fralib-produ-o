"""
PR13: Editor visual WYSIWYG de sites gerados (sem LLM).

Recebe HTML editado pelo cliente via iframe contentEditable e persiste no disco
(/var/www/fralib/sites/...) + tabela leads.html_gerado. Faz backup, valida tenant,
sanitiza contra injecao de script externo, limita tamanho.
"""
import os
import re
import hashlib
import sys
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
sys.path.append('/root/fralib/backend')
sys.path.append('/root/fralib/backend/core')
from database import get_db
from auth import get_current_user
from sse_endpoints import adicionar_log

router = APIRouter(prefix='/api/sites', tags=['site-editor'])
logger = logging.getLogger('uvicorn')

SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,80}$')
MAX_HTML_BYTES = 500 * 1024  # 500KB


def _resolver_html_path(tenant_id, lead_nome: str, url_site: str):
    """Descobre o path do index.html no disco, tentando layout novo (tenant/slug) e legado (slug)."""
    if url_site:
        slug_url = url_site.rstrip('/').split('/sites/')[-1].rstrip('/')
        if '/' in slug_url:
            slug_url = slug_url.split('/')[-1]
    else:
        slug_url = ''
    slug_nome = re.sub(r'[^a-z0-9]+', '-', (lead_nome or '').lower()).strip('-')[:50]

    candidatos = []
    for slug in [slug_url, slug_nome]:
        if not slug or not SLUG_RE.match(slug):
            continue
        candidatos.append((f'/var/www/fralib/sites/{tenant_id}/{slug}/index.html', slug))
        candidatos.append((f'/var/www/fralib/sites/{slug}/index.html', slug))

    for path, slug in candidatos:
        if os.path.exists(path):
            return path, slug
    return None, None


def _sanitizar_html(html_novo: str, html_antigo: str) -> str:
    """
    Rejeita scripts/iframes novos. Permite manter os que ja existiam no HTML original.
    Bloqueia javascript: em hrefs novos.
    """
    if '<iframe' in html_novo.lower() and '<iframe' not in html_antigo.lower():
        raise HTTPException(400, 'HTML contem <iframe> nao permitido')
    if '<object' in html_novo.lower() or '<embed' in html_novo.lower():
        raise HTTPException(400, 'HTML contem <object>/<embed> nao permitido')

    scripts_novos = re.findall(r'<script\b[^>]*\bsrc\s*=\s*["\'][^"\']+["\'][^>]*>', html_novo, re.IGNORECASE)
    scripts_antigos = set(
        re.findall(r'<script\b[^>]*\bsrc\s*=\s*["\'][^"\']+["\'][^>]*>', html_antigo, re.IGNORECASE)
    )
    for s in scripts_novos:
        if s not in scripts_antigos:
            raise HTTPException(400, 'HTML contem <script src=...> externo nao autorizado')

    if re.search(r'\bhref\s*=\s*["\']\s*javascript:', html_novo, re.IGNORECASE):
        if not re.search(r'\bhref\s*=\s*["\']\s*javascript:', html_antigo, re.IGNORECASE):
            raise HTTPException(400, 'href javascript: nao permitido')
    return html_novo


def _carregar_lead(db: Session, lead_id: str, tenant_id):
    row = db.execute(
        text('SELECT nome, url_site, html_gerado FROM leads WHERE id=:id AND user_id=:uid'),
        {'id': lead_id, 'uid': tenant_id}
    ).fetchone()
    if not row:
        raise HTTPException(404, 'Lead nao encontrado')
    return dict(row._mapping)


@router.get('/{lead_id}/html')
async def obter_html(lead_id: str, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    tenant_id = usuario.get('tenant_id', usuario['id'])
    lead = _carregar_lead(db, lead_id, tenant_id)
    html_path, slug = _resolver_html_path(tenant_id, lead.get('nome') or '', lead.get('url_site') or '')
    if html_path and os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return {'html': f.read(), 'fonte': 'disco', 'slug': slug, 'url_site': lead.get('url_site') or ''}
    html_db = lead.get('html_gerado') or ''
    if not html_db:
        raise HTTPException(404, 'Site ainda nao foi gerado')
    return {'html': html_db, 'fonte': 'db', 'slug': slug, 'url_site': lead.get('url_site') or ''}


class SalvarHtmlRequest(BaseModel):
    html: str


@router.post('/{lead_id}/salvar-html')
async def salvar_html(lead_id: str, req: SalvarHtmlRequest, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    tenant_id = usuario.get('tenant_id', usuario['id'])
    lead = _carregar_lead(db, lead_id, tenant_id)

    html_novo = req.html or ''
    if not html_novo.strip():
        raise HTTPException(400, 'HTML vazio')
    if len(html_novo.encode('utf-8')) > MAX_HTML_BYTES:
        raise HTTPException(413, f'HTML excede {MAX_HTML_BYTES // 1024}KB')
    if '<body' not in html_novo.lower() or '</body>' not in html_novo.lower():
        raise HTTPException(400, 'HTML invalido: sem tag body')

    html_path, slug = _resolver_html_path(tenant_id, lead.get('nome') or '', lead.get('url_site') or '')
    if not html_path:
        raise HTTPException(404, 'Arquivo HTML do site nao encontrado no disco')

    with open(html_path, 'r', encoding='utf-8') as f:
        html_antigo = f.read()

    html_sanitizado = _sanitizar_html(html_novo, html_antigo)

    backup_path = html_path + '.bak'
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(html_antigo)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_sanitizado)
    except OSError as e:
        raise HTTPException(500, f'Erro ao escrever arquivo: {e}')

    try:
        db.execute(
            text('UPDATE leads SET html_gerado=:h WHERE id=:id AND user_id=:uid'),
            {'h': html_sanitizado, 'id': lead_id, 'uid': tenant_id}
        )
        db.commit()
    except Exception as e:
        logger.warning(f'[SiteEditor] DB sync falhou: {e}')

    adicionar_log(f'[Editor WYSIWYG] Site do lead {lead.get("nome")} salvo ({len(html_sanitizado)} chars)', 'success')
    return {
        'ok': True,
        'tamanho': len(html_sanitizado),
        'slug': slug,
        'url_site': lead.get('url_site') or '',
        'backup': os.path.basename(backup_path),
    }
