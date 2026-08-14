"""
PR13: Editor visual WYSIWYG de sites gerados (sem LLM).

Recebe HTML editado pelo cliente via iframe contentEditable e persiste no disco
(/var/www/fralib/sites/...) + tabela leads.html_gerado. Faz backup, valida tenant,
sanitiza contra injecao de script externo, limita tamanho.
"""
import os
import re
import hashlib
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from backend.core.database import get_db
from backend.endpoints.auth_endpoints import get_current_user
from backend.endpoints.sse_endpoints import adicionar_log

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


class EditarIARequest(BaseModel):
    prompt: str


@router.post('/{lead_id}/editar-ia')
async def editar_com_ia(lead_id: str, req: EditarIARequest, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Endpoint dedicado do Studio: edita site via LLM, consome 1 crédito."""
    tenant_id = usuario.get('tenant_id', usuario['id'])
    lead = _carregar_lead(db, lead_id, tenant_id)

    if not req.prompt or not req.prompt.strip():
        raise HTTPException(400, 'Instrução vazia')

    # Consumir 1 crédito
    from backend.services.credits_manager import consume_tokens
    consume_tokens(db, int(usuario['id']), 1, 'Studio IA: ' + req.prompt[:40])

    # Resolver path do HTML
    html_path, slug = _resolver_html_path(tenant_id, lead.get('nome') or '', lead.get('url_site') or '')
    if not html_path:
        raise HTTPException(404, 'Arquivo HTML do site não encontrado')

    with open(html_path, 'r', encoding='utf-8') as f:
        html_atual = f.read()

    # Extrair body
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html_atual, re.DOTALL | re.IGNORECASE)
    if not body_match:
        raise HTTPException(400, 'HTML inválido: sem tag body')

    body_inner = body_match.group(1)

    # Separar styles/scripts pra não enviar ao LLM
    styles_body = re.findall(r'<style[^>]*>.*?</style>', body_inner, re.DOTALL)
    scripts_body = re.findall(r'<script[^>]*>.*?</script>', body_inner, re.DOTALL)
    body_limpo = re.sub(r'<style[^>]*>.*?</style>', '', body_inner, flags=re.DOTALL)
    body_limpo = re.sub(r'<script[^>]*>.*?</script>', '', body_limpo, flags=re.DOTALL)
    body_limpo = re.sub(r'\n{3,}', '\n\n', body_limpo).strip()
    if len(body_limpo) > 30000:
        body_limpo = body_limpo[:30000]

    # Chamar LLM
    from llm_direct import call_claude

    system_prompt = (
        'Voce e um editor de sites HTML profissional. '
        'Recebera o conteudo do BODY de um site e uma instrucao de edicao. '
        'Retorne SOMENTE o HTML do body modificado. '
        'NAO inclua DOCTYPE, html, head, body tags. NAO use markdown ou ```.'
        'NAO inclua style ou script tags. '
        'Aplique APENAS a modificacao pedida. Preserve TODAS as classes, IDs, estrutura e atributos existentes. '
        'Se a instrucao pedir algo impossivel, faca o mais proximo possivel.'
    )
    user_prompt = f'INSTRUCAO: {req.prompt}\n\nBODY HTML ATUAL:\n{body_limpo}'

    try:
        # System prompt expandido (>1024 chars ativa prompt caching, evita tool_use do proxy)
        system_full = (
            'Voce e um editor de sites HTML profissional e experiente. '
            'Sua tarefa e receber o conteudo do BODY de um site e uma instrucao de edicao do usuario, '
            'e retornar o HTML modificado conforme solicitado.\n\n'
            'REGRAS OBRIGATORIAS:\n'
            '1. Retorne SOMENTE o HTML do body modificado\n'
            '2. NAO inclua DOCTYPE, html, head, body, style ou script tags\n'
            '3. NAO use markdown, crases (```), ou explicacoes\n'
            '4. Aplique APENAS a modificacao pedida pelo usuario\n'
            '5. Preserve TODAS as classes CSS, IDs, data-attributes e estrutura existente\n'
            '6. Preserve todos os links, imagens e URLs existentes\n'
            '7. Mantenha a mesma indentacao e formatacao do HTML original\n'
            '8. Se a instrucao pedir algo impossivel, faca o mais proximo possivel\n'
            '9. NAO remova secoes que nao foram mencionadas na instrucao\n'
            '10. NAO adicione comentarios HTML explicativos\n\n'
            'IMPORTANTE: Sua resposta deve comecar diretamente com uma tag HTML (ex: <section, <div, <header, etc). '
            'Nunca comece com texto explicativo, markdown ou qualquer coisa que nao seja HTML puro.\n\n'
            'Voce e preciso, eficiente e segue instrucoes ao pe da letra. '
            'O HTML que voce retornar sera inserido diretamente no site do cliente, '
            'entao deve ser valido, limpo e funcional.'
        )
        body_novo = call_claude(system_full, user_prompt, model='sonnet', max_tokens=16000, temperature=0.2)
        logger.info(f'[Studio IA] LLM retornou: type={type(body_novo).__name__}, len={len(str(body_novo)) if body_novo else 0}')
    except Exception as e:
        logger.error(f'[Studio IA] Erro LLM: {e}')
        raise HTTPException(500, f'Erro ao chamar LLM: {str(e)[:100]}')

    # Validar resposta — call_claude retorna string ou None
    if body_novo is None:
        raise HTTPException(500, 'LLM não retornou resposta (possível timeout ou rate limit)')
    if not isinstance(body_novo, str):
        # Tentar extrair texto se veio como dict/objeto
        if hasattr(body_novo, 'text'):
            body_novo = body_novo.text
        elif isinstance(body_novo, dict):
            body_novo = body_novo.get('text', str(body_novo))
        else:
            body_novo = str(body_novo)

    # Limpar markdown se LLM envolveu em ```
    body_novo = body_novo.strip()
    if body_novo.startswith('```'):
        lines = body_novo.split('\n')
        # Remover primeira e última linha (```)
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        body_novo = '\n'.join(lines)

    # Se retornou muito curto, provavelmente erro
    if len(body_novo) < 20:
        raise HTTPException(500, f'LLM retornou resposta muito curta ({len(body_novo)} chars)')

    # Remontar body com styles e scripts originais
    body_final = body_novo.strip()
    if styles_body:
        body_final = '\n'.join(styles_body) + '\n' + body_final
    if scripts_body:
        body_final = body_final + '\n' + '\n'.join(scripts_body)

    # Remontar HTML completo
    body_tag = html_atual[body_match.start():body_match.start(1)]
    html_novo = html_atual[:body_match.start()] + body_tag + '\n' + body_final + '\n</body>' + html_atual[body_match.end():]

    # Backup e salvar
    backup_path = html_path + '.bak'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(html_atual)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_novo)

    # Sync DB
    try:
        db.execute(text('UPDATE leads SET html_gerado=:h WHERE id=:id AND user_id=:uid'),
                   {'h': html_novo, 'id': lead_id, 'uid': tenant_id})
        db.commit()
    except Exception:
        pass

    adicionar_log(f'[Studio IA] Edição aplicada: {req.prompt[:50]}', 'success', user_id=tenant_id)
    return {'ok': True, 'mensagem': 'Edição aplicada com sucesso!'}
