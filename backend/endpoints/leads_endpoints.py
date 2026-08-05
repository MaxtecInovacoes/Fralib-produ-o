from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import sys
sys.path.append('/root/fralib/backend')
sys.path.append('/root/fralib/backend/core')
from database import get_db
from auth import get_current_user
from sse_endpoints import adicionar_log
from whatsapp_listener import is_tenant_connected

router = APIRouter(prefix='/api/leads', tags=['leads'])


@router.get('/sites')
async def get_sites(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id_s = usuario.get("tenant_id", usuario["id"])
        result = db.execute(text("""
            SELECT id, nome, cidade, segmento, url_site, valor_venda, status, criado_em, score
            FROM leads 
            WHERE url_site IS NOT NULL AND url_site != ''
            AND user_id = :uid
            ORDER BY criado_em DESC
        """), {"uid": tenant_id_s}).fetchall()
        
        sites = []
        for r in result:
            d = dict(r._mapping)
            url = d.get('url_site') or ''
            slug = url.rstrip('/').split('/sites/')[-1].rstrip('/') if '/sites/' in url else ''
            thumb = f'/sites/{slug}/assets/foto_1.webp' if slug else ''
            sites.append({
                "id": d['id'],
                "nome": d['nome'] or '—',
                "cidade": d['cidade'] or '—',
                "segmento": d['segmento'] or '—',
                "url_site": url,
                "thumb": thumb,
                "valor_venda": float(d['valor_venda'] or 0),
                "status": d['status'] or '—',
                "criado_em": str(d['criado_em'] or ''),
                "score": d['score'] or 0,
            })
        
        return {"sites": sites, "total": len(sites)}
    except Exception as e:
        print(f"[Sites] Erro: {e}")
        return {"sites": [], "total": 0}

@router.get('/{lead_id}/conversa')
async def get_conversa(lead_id: str, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        result = db.execute(text("""
            SELECT i.id, i.mensagem, i.direcao, i.criado_em
            FROM interacoes i
            JOIN leads l ON l.id = i.lead_id
            WHERE i.lead_id = :lead_id AND l.user_id = :uid
            ORDER BY i.id ASC
        """), {"lead_id": lead_id, "uid": tenant_id}).fetchall()
        return {"mensagens": [dict(r._mapping) for r in result]}
    except Exception as e:
        return {"mensagens": []}

@router.patch('/{lead_id}')
async def atualizar_lead(lead_id: str, request_data: dict, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        campos = {}
        campos_permitidos = ['whatsapp', 'telefone_whatsapp', 'telefone', 'nome', 'segmento', 'cidade', 'observacoes', 'valor_venda', 'status']
        for k in campos_permitidos:
            if k in request_data:
                campos[k] = request_data[k]
        # Alias: whatsapp → telefone_whatsapp
        if 'whatsapp' in request_data:
            campos['telefone_whatsapp'] = request_data['whatsapp']

        if not campos:
            return {"ok": True}

        tenant_id = usuario.get("tenant_id", usuario["id"])
        sets = ", ".join([f"{k}=:{k}" for k in campos.keys()])
        campos['lead_id'] = lead_id
        campos['uid'] = tenant_id
        db.execute(text(f"UPDATE leads SET {sets}, atualizado_em=NOW()::text WHERE id=:lead_id AND user_id=:uid"), campos)
        db.commit()
        return {"ok": True}
    except Exception as e:
        print(f"[Leads] Erro ao atualizar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/{lead_id}/reprocessar')
async def reprocessar_lead(lead_id: str, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        lead = db.execute(text("SELECT * FROM leads WHERE id=:id AND user_id=:uid"), {"id": lead_id, "uid": tenant_id}).fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead nao encontrado")
        db.execute(text("UPDATE leads SET status='pendente', atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"), {"id": lead_id, "uid": tenant_id})
        db.commit()
        return {"ok": True, "mensagem": "Lead marcado para reprocessamento"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel
import os

class EditarSiteRequest(BaseModel):
    prompt: str

@router.post('/{lead_id}/editar-site')
async def editar_site(lead_id: str, req: EditarSiteRequest, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    from sqlalchemy import text as _text
    plano = db.execute(_text('SELECT plano FROM users WHERE id=:id'), {'id': usuario['id']}).scalar()
    if plano not in ('pro', 'beta', 'admin'):
        raise HTTPException(403, 'Edicao de site disponivel apenas no plano Pro. Faca upgrade em /planos')
    from services.credits_manager import consume_tokens
    consume_tokens(db, int(usuario['id']), 1, 'Edicao de site')
    sys.path.append('/root/fralib/backend/agents')
    from llm_direct import call_claude
    import re as _re2

    adicionar_log(f'[Edicao Site] Iniciando: {req.prompt[:60]}', 'info')
    tenant_id = usuario.get('tenant_id', usuario['id'])
    lead = db.execute(text('SELECT * FROM leads WHERE id=:id AND user_id=:uid'), {'id': lead_id, 'uid': tenant_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail='Lead nao encontrado')

    lead_dict = dict(lead._mapping)
    url_site = lead_dict.get('url_site') or lead_dict.get('site_url') or ''
    if not url_site:
        raise HTTPException(status_code=400, detail='Lead nao tem site gerado')

    slug = url_site.rstrip('/').split('/')[-1]
    # Defesa em profundidade: bloquear path traversal mesmo que url_site venha corrompido do banco
    import re as _re_path
    if not _re_path.match(r'^[a-z0-9][a-z0-9-]{0,80}$', slug):
        raise HTTPException(status_code=400, detail='Slug do site invalido')
    html_path = f'/var/www/fralib/sites/{tenant_id}/{slug}/index.html'

    if not os.path.exists(html_path):
        # Fallback: tentar path antigo (sites sem tenant_id)
        html_path_legacy = '/var/www/fralib/sites/' + slug + '/index.html'
        if os.path.exists(html_path_legacy):
            html_path = html_path_legacy
        else:
            raise HTTPException(status_code=404, detail='Arquivo HTML nao encontrado')

    with open(html_path, 'r', encoding='utf-8') as f:
        html_atual = f.read()

    try:
        body_match = _re2.search(r'<body[^>]*>(.*?)</body>', html_atual, _re2.DOTALL | _re2.IGNORECASE)
        if not body_match:
            raise HTTPException(status_code=400, detail='HTML invalido: sem tag body')

        body_inner = body_match.group(1)

        # Guardar styles e scripts do body para reinserir depois
        styles_body = _re2.findall(r'<style[^>]*>.*?</style>', body_inner, _re2.DOTALL)
        scripts_body = _re2.findall(r'<script[^>]*>.*?</script>', body_inner, _re2.DOTALL)

        # Body limpo sem style/script para reduzir tokens
        body_limpo = _re2.sub(r'<style[^>]*>.*?</style>', '', body_inner, flags=_re2.DOTALL)
        body_limpo = _re2.sub(r'<script[^>]*>.*?</script>', '', body_limpo, flags=_re2.DOTALL)
        body_limpo = _re2.sub(r'\n{3,}', '\n\n', body_limpo).strip()
        if len(body_limpo) > 28000:
            body_limpo = body_limpo[:28000]

        bt = chr(96) * 3
        system_edit = (
            'Voce e um editor de sites HTML. '
            'Recebera o conteudo do BODY (sem style/script) e uma instrucao. '
            'Retorne APENAS o conteudo do body modificado, sem tags html/head/body/style/script, '
            'sem markdown, sem ' + bt + ', sem explicacoes. '
            'Aplique SOMENTE a modificacao pedida. Preserve TODAS as classes, IDs e atributos.'
        )
        user_edit = 'INSTRUCAO: ' + req.prompt + '\n\nBODY HTML:\n' + body_limpo

        adicionar_log(f'[Edicao Site] Enviando {len(body_limpo)} chars ao LLM...', 'info')
        body_novo = call_claude(system_edit, user_edit, model='sonnet', max_tokens=16000, temperature=0.2)

        if not body_novo or len(body_novo) < 50:
            adicionar_log('[Edicao Site] LLM retornou resposta invalida', 'error')
            raise HTTPException(status_code=500, detail='LLM retornou resposta invalida')

        adicionar_log(f'[Edicao Site] LLM respondeu ({len(body_novo)} chars), remontando...', 'success')

        # Limpar markdown
        stripped = body_novo.strip()
        if stripped.startswith(bt):
            parts = stripped.split(bt)
            if len(parts) >= 2:
                body_novo = parts[1]
                if body_novo.startswith('html'):
                    body_novo = body_novo[4:]

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
        backup_path = html_path.replace('index.html', 'index.html.bak')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(html_atual)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_novo)

        adicionar_log('[Edicao Site] Site atualizado com sucesso!', 'success')
        return {'ok': True, 'mensagem': 'Site atualizado com sucesso!', 'url': url_site}

    except HTTPException:
        raise
    except Exception as e:
        adicionar_log(f'[Edicao Site] Erro: {str(e)[:80]}', 'error')
        raise HTTPException(status_code=500, detail='Erro ao editar site: ' + str(e))

@router.post('/{lead_id}/upload-foto')
async def upload_foto(
    lead_id: str,
    foto: UploadFile = File(...),
    tipo: str = Form(default='foto'),
    numero: int = Form(default=1),
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    import os
    tenant_id = usuario.get("tenant_id", usuario["id"])
    lead = db.execute(text("SELECT * FROM leads WHERE id=:id AND user_id=:uid"), {"id": lead_id, "uid": tenant_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nao encontrado")

    lead_dict = dict(lead._mapping)
    url_site = lead_dict.get('url_site') or lead_dict.get('site_url') or ''
    if not url_site:
        raise HTTPException(status_code=400, detail="Lead nao tem site gerado")

    slug = url_site.rstrip('/').split('/sites/')[-1].rstrip('/')
    if not slug or slug == url_site.rstrip('/'):
        slug = url_site.rstrip('/').split('/')[-1]

    # Validação anti-traversal
    import re as _re_upload
    slug_parts = slug.split('/')
    for part in slug_parts:
        if not _re_upload.match(r'^[a-zA-Z0-9_\-]+$', part):
            raise HTTPException(status_code=400, detail="Slug invalido")

    assets_dir = f'/var/www/fralib/sites/{tenant_id}/{slug_parts[-1]}/assets'
    os.makedirs(assets_dir, exist_ok=True)

    if tipo == 'logo':
        filename = 'logo.webp'
    else:
        filename = 'foto_' + str(numero) + '.webp'

    filepath = assets_dir + '/' + filename
    contents = await foto.read()

    # Limite de 10MB por upload
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Arquivo muito grande (max 10MB)")

    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(contents))
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        if img.width > 1920:
            ratio = 1920 / img.width
            img = img.resize((1920, int(img.height * ratio)), Image.LANCZOS)
        output = io.BytesIO()
        img.save(output, format='WEBP', quality=85)
        with open(filepath, 'wb') as f:
            f.write(output.getvalue())
    except ImportError:
        with open(filepath, 'wb') as f:
            f.write(contents)
    except Exception as e:
        ext = foto.filename.split('.')[-1].lower() if foto.filename else 'jpg'
        filepath = filepath.replace('.webp', '.' + ext)
        filename = filename.replace('.webp', '.' + ext)
        with open(filepath, 'wb') as f:
            f.write(contents)

    foto_url = '/sites/' + slug + '/assets/' + filename
    return {"ok": True, "url": foto_url, "filename": filename, "mensagem": "Foto salva em " + foto_url}

from pydantic import BaseModel as _BaseModel2
from typing import Optional as _Optional2
from fastapi import BackgroundTasks

class LeadManualRequest(_BaseModel2):
    nome: str
    telefone: str
    whatsapp: _Optional2[str] = None
    nicho: str
    cidade: str
    briefing: _Optional2[str] = None
    score: _Optional2[int] = 80

@router.post('/manual')
async def criar_lead_manual(req: LeadManualRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    from datetime import datetime
    import uuid as _uuid
    lead_id = str(_uuid.uuid4())
    agora = datetime.now().isoformat()
    db.execute(text("""
        INSERT INTO leads (id, nome, cidade, segmento, telefone, whatsapp, telefone_whatsapp, score, status, criado_em, atualizado_em, processado, tentativas, observacoes, user_id)
        VALUES (:id, :nome, :cidade, :segmento, :telefone, :whatsapp, :whatsapp, :score, 'pendente', :criado_em, :criado_em, false, 0, :briefing, :user_id)
        ON CONFLICT DO NOTHING
    """), {
        "id": lead_id, "nome": req.nome, "cidade": req.cidade,
        "segmento": req.nicho, "telefone": req.telefone,
        "whatsapp": req.whatsapp or req.telefone,
        "score": req.score or 80, "criado_em": agora,
        "briefing": req.briefing or "", "user_id": usuario.get("id")
    })
    db.commit()
    if req.briefing:
        background_tasks.add_task(_gerar_site_manual, lead_id, req, usuario.get("id"))
    return {"ok": True, "lead_id": lead_id, "mensagem": "Lead criado!" + (" Site sendo gerado..." if req.briefing else " Sem briefing — site não gerado.")}

async def _gerar_site_manual(lead_id: str, req: LeadManualRequest, user_id):
    import sys as _sys, os as _os
    _sys.path.append('/root/fralib/backend/agents')
    _sys.path.append('/root/fralib/backend/core')
    from database import engine
    from sqlalchemy import text as _text
    try:
        from agents.liam import gerar_html_componentizado, montar_template_python
        from agents.arquiteto_mestre import gerar_arquiteto_mestre_prd
        _use_agent = os.getenv("ARQUITETO_AGENT_LOOP", "0") == "1"
        if _use_agent:
            from agents.arquiteto_agent_loop import gerar_arquiteto_mestre_prd_agent
        
        # Montar dados mínimos para o Arquiteto Mestre
        dados_hunter = {
            "nome": req.nome,
            "telefone": req.telefone or "",
            "endereco": "",
            "rating": 4.5,
            "reviews": [],
            "fotos": [],
            "logo_url": ""
        }
        # Cores base por nicho (o Arquiteto Mestre vai harmonizar via LLM)
        _nicho = (req.nicho or '').lower()
        _cores_nicho = {
            'academia': {'primaria': '#1a1a2e', 'acento': '#e63946'},
            'barbearia': {'primaria': '#1c1c1c', 'acento': '#c9a84c'},
            'restaurante': {'primaria': '#1b1b1b', 'acento': '#e07b39'},
            'clinica': {'primaria': '#0f3460', 'acento': '#16213e'},
            'salao': {'primaria': '#2d1b33', 'acento': '#e91e8c'},
            'pet': {'primaria': '#1a3a2a', 'acento': '#4caf50'},
            'advocacia': {'primaria': '#1a1a2e', 'acento': '#c9a84c'},
            'odontologia': {'primaria': '#0d2137', 'acento': '#00b4d8'},
        }
        alex_colors = next(
            (v for k, v in _cores_nicho.items() if k in _nicho),
            {'primaria': '#111827', 'acento': '#6366f1'}
        )
        
        _prd_fn = gerar_arquiteto_mestre_prd_agent if _use_agent else gerar_arquiteto_mestre_prd
        prd = _prd_fn(
            dados_hunter=dados_hunter,
            cidade=req.cidade,
            segmento=req.nicho,
            jina_insights=req.briefing or "Negócio local de qualidade",
            caio_tier="STANDARD",
            caio_score=req.score or 80,
            caio_motivo="Lead manual",
            briefing_theo=req.briefing or ""
        )
        html_main = gerar_html_componentizado(prd)
        html_final = montar_template_python(html_main, prd)
        if html_final:
            import re as _re_slug
            # Sanitizar: so a-z, 0-9 e hifen. Evita command/path injection no web_dir.
            _slug_raw = _re_slug.sub(r'[^a-z0-9]+', '-', (req.nome or '').lower()).strip('-')[:40]
            slug = (_slug_raw or 'lead') + '-manual'
            web_dir = f'/var/www/fralib/sites/{user_id}/{slug}'
            _os.makedirs(web_dir, exist_ok=True)
            with open(f'{web_dir}/index.html', 'w', encoding='utf-8') as f:
                f.write(html_final)
            site_url = f'https://seunegociofralib.site/sites/{user_id}/{slug}/'
            from datetime import datetime as _dt
            from sqlalchemy import create_engine as _ce
            import os as _os2
            _eng = _ce(_os2.environ.get('DATABASE_URL', ''), pool_pre_ping=True)
            with _eng.connect() as conn:
                conn.execute(_text("UPDATE leads SET url_site=:url, site_url=:url, status='concluido', processado=true, atualizado_em=:ts WHERE id=:id AND user_id=:uid"),
                    {"url": site_url, "ts": _dt.now().isoformat(), "id": lead_id, "uid": user_id})
                conn.commit()
            print(f"[LeadManual] Site salvo: {site_url}")
    except Exception as e:
        print(f"[LeadManual] Erro ao gerar site: {e}")
        import traceback; traceback.print_exc()
        from datetime import datetime as _dt
        from sqlalchemy import create_engine as _ce
        import os as _os2
        _eng = _ce(_os2.environ.get('DATABASE_URL', ''), pool_pre_ping=True)
        with _eng.connect() as conn:
            conn.execute(_text("UPDATE leads SET status='erro', atualizado_em=:ts WHERE id=:id AND user_id=:uid"),
                {"ts": _dt.now().isoformat(), "id": lead_id, "uid": user_id})
            conn.commit()

@router.get('/mensagens-novas')
async def get_mensagens_novas(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        result = db.execute(text("""
            SELECT DISTINCT i.lead_nome, COUNT(*) as total
            FROM interacoes i
            JOIN leads l ON l.id = i.lead_id
            WHERE i.direcao = 'entrada'
            AND i.criado_em > (NOW() - INTERVAL '24 hours')::text
            AND l.user_id = :uid
            GROUP BY i.lead_nome
        """), {"uid": tenant_id}).fetchall()
        return {"leads_com_resposta": [{"nome": r.lead_nome, "total": r.total} for r in result]}
    except Exception as e:
        return {"leads_com_resposta": []}


@router.get('/{lead_id}/chat')
async def get_lead_chat(lead_id: str, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Retorna histórico de conversas de um lead (para modal de chat no CRM)."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    # Verificar que lead pertence ao tenant
    lead = db.execute(text("SELECT id, nome, sdr_stage FROM leads WHERE id=:id AND user_id=:uid"), {"id": lead_id, "uid": tenant_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nao encontrado")
    msgs = db.execute(text("""
        SELECT mensagem, direcao, criado_em
        FROM interacoes
        WHERE lead_id = :lid
        ORDER BY id ASC
        LIMIT 100
    """), {"lid": lead_id}).fetchall()
    return {
        "lead_nome": lead.nome,
        "sdr_stage": lead.sdr_stage,
        "mensagens": [
            {"texto": m.mensagem, "direcao": m.direcao, "ts": m.criado_em}
            for m in msgs
        ]
    }


@router.get('/capturados')
async def get_leads_capturados(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get('tenant_id', usuario['id'])
        cap_sql = "SELECT id, nome, cidade, segmento, rating, score, tier, status FROM leads WHERE user_id=:user_id AND status=:st ORDER BY criado_em DESC"
        result = db.execute(text(cap_sql), {'user_id': tenant_id, 'st': 'capturado'}).fetchall()
        leads = []
        import json
        for r in result:
            d = dict(r._mapping)
            dc = d.get('dados_completos')
            if dc and isinstance(dc, str):
                try: d['dados_completos'] = json.loads(dc)
                except: d['dados_completos'] = {}
            elif not dc:
                d['dados_completos'] = {}
            leads.append(d)
        return {'leads': leads, 'total': len(leads)}
    except Exception as e:
        print(f'[Leads] Erro capturados: {e}')
        return {'leads': [], 'total': 0}


@router.delete('/fila')
async def limpar_fila_capturados(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get('tenant_id', usuario['id'])
        result = db.execute(text(del_sql), {'user_id': tenant_id, 'st': 'capturado'})
        db.commit()
        deletados = result.rowcount
        return {'ok': True, 'deletados': deletados, 'mensagem': str(deletados) + ' lead(s) removido(s) da fila'}
    except Exception as e:
        print(f'[Leads] Erro limpar fila: {e}')
        import traceback; traceback.print_exc()
        raise


@router.post('/processar-fila')
async def processar_proximo_fila(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    from fastapi import BackgroundTasks
    try:
        tenant_id = usuario.get('tenant_id', usuario['id'])
        fila = db.execute(text(fila_sql), {'user_id': tenant_id, 'st': 'capturado'}).fetchone()
        if not fila:
            return {'ok': False, 'mensagem': 'Nenhum lead na fila'}
        return {'ok': True, 'mensagem': 'Processando lead: ' + fila.nome, 'lead_id': fila.id}
    except Exception as e:
        print(f'[Leads] Erro processar fila: {e}')
        raise


@router.get('/desqualificados')
async def get_leads_desqualificados(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get('tenant_id', usuario['id'])
        result = db.execute(text(desq_sql), {'user_id': tenant_id}).fetchall()
        leads = []
        import json
        for r in result:
            d = dict(r._mapping)
            dc = d.get('dados_completos')
            if dc and isinstance(dc, str):
                try: d['dados_completos'] = json.loads(dc)
                except: d['dados_completos'] = {}
            elif not dc:
                d['dados_completos'] = {}
            leads.append(d)
        return {'leads': leads, 'total': len(leads)}
    except Exception as e:
        print(f'[Leads] Erro desqualificados: {e}')
        return {'leads': [], 'total': 0}


# ═══════════════════════════════════════════════════════════════════
# SPRINT 2 — Novos endpoints
# ═══════════════════════════════════════════════════════════════════

# 2.1 — Leads incompletos/rejeitados para revisão manual
@router.get('/incompletos')
async def get_leads_incompletos(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get('tenant_id', usuario['id'])
        result = db.execute(text("""
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
        """), {"uid": tenant_id}).fetchall()
        leads = [dict(r._mapping) for r in result]
        return {"leads": leads, "total": len(leads)}
    except Exception as e:
        print(f"[Leads] Erro incompletos: {e}")
        return {"leads": [], "total": 0}


# 2.1 — Aprovar lead manualmente para o pipeline
@router.patch('/{lead_id}/aprovar-pipeline')
async def aprovar_lead_pipeline(lead_id: str, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        lead = db.execute(text("SELECT id FROM leads WHERE id=:id AND user_id=:uid"), {"id": lead_id, "uid": tenant_id}).fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")
        db.execute(text("""
            UPDATE leads SET status='qualificado', score=50
            WHERE id=:id AND user_id=:uid
        """), {"id": lead_id, "uid": tenant_id})
        db.commit()
        return {"ok": True, "mensagem": "Lead aprovado manualmente para o pipeline"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Leads] Erro aprovar-pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 2.2 — Descartar lead manualmente
@router.patch('/{lead_id}/descartar')
async def descartar_lead(lead_id: str, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        lead = db.execute(text("SELECT id FROM leads WHERE id=:id AND user_id=:uid"), {"id": lead_id, "uid": tenant_id}).fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")
        db.execute(text("""
            UPDATE leads SET status='descartado', atualizado_em=NOW()::text
            WHERE id=:id AND user_id=:uid
        """), {"id": lead_id, "uid": tenant_id})
        db.commit()
        return {"ok": True, "mensagem": "Lead descartado"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 2.1 / 2.4 — Atualizar campos individuais do lead
from pydantic import BaseModel as _BM3
from typing import Optional as _Opt3

class CamposLeadRequest(_BM3):
    nome: _Opt3[str] = None
    telefone: _Opt3[str] = None
    segmento: _Opt3[str] = None
    cidade: _Opt3[str] = None
    observacao: _Opt3[str] = None
    sdr_stage: _Opt3[str] = None
    status: _Opt3[str] = None

@router.patch('/{lead_id}/campos')
async def atualizar_campos_lead(lead_id: str, req: CamposLeadRequest, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        lead = db.execute(text("SELECT id FROM leads WHERE id=:id AND user_id=:uid"), {"id": lead_id, "uid": tenant_id}).fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")
        campos = {}
        if req.nome is not None:
            campos['nome'] = req.nome
        if req.telefone is not None:
            campos['telefone'] = req.telefone
            campos['whatsapp'] = req.telefone
            campos['telefone_whatsapp'] = req.telefone
        if req.segmento is not None:
            campos['segmento'] = req.segmento
        if req.cidade is not None:
            campos['cidade'] = req.cidade
        if req.observacao is not None:
            campos['observacoes'] = req.observacao
        if req.sdr_stage is not None:
            campos['sdr_stage'] = req.sdr_stage
        if req.status is not None:
            campos['status'] = req.status
        if not campos:
            return {"ok": True, "mensagem": "Nenhum campo para atualizar"}
        tenant_id = usuario.get("tenant_id", usuario["id"])
        sets = ", ".join([f"{k}=:{k}" for k in campos.keys()])
        campos['lead_id'] = lead_id
        campos['uid'] = tenant_id
        db.execute(text(f"UPDATE leads SET {sets} WHERE id=:lead_id AND user_id=:uid"), campos)
        db.commit()
        return {"ok": True, "mensagem": "Campos atualizados com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Leads] Erro atualizar campos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 2.2 — Fila de leads qualificados aguardando pipeline
@router.get('/fila-qualificados')
async def get_fila_qualificados(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Fila de atendimento: apenas leads que completaram pipeline (site pronto, aguardando SDR enviar msg)"""
    try:
        tenant_id = usuario.get('tenant_id', usuario['id'])
        result = db.execute(text("""
            SELECT id, nome, cidade, segmento, score, tier, status, criado_em
            FROM leads
            WHERE user_id = :uid
              AND status = 'concluido'
              AND (sdr_stage IN ('hook', 'pendente_wpp') OR sdr_stage IS NULL)
            ORDER BY criado_em ASC
            LIMIT 100
        """), {"uid": tenant_id}).fetchall()
        leads = []
        for i, r in enumerate(result):
            d = dict(r._mapping)
            d['posicao'] = i + 1
            leads.append(d)
        return {"leads": leads, "total": len(leads)}
    except Exception as e:
        print(f"[Leads] Erro fila-qualificados: {e}")
        return {"leads": [], "total": 0}


@router.get('/descartados')
async def get_descartados(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get('tenant_id', usuario['id'])
        result = db.execute(text("""
            SELECT id, nome, cidade, segmento, telefone, telefone_whatsapp, score, status, criado_em, atualizado_em
            FROM leads
            WHERE user_id = :uid AND status = 'descartado'
            ORDER BY atualizado_em DESC
            LIMIT 100
        """), {"uid": tenant_id}).fetchall()
        leads = [dict(r._mapping) for r in result]
        return {"leads": leads, "total": len(leads)}
    except Exception as e:
        print(f"[Leads] Erro descartados: {e}")
        return {"leads": [], "total": 0}


# 2.3 — Deletar lead
@router.delete('/{lead_id}')
async def deletar_lead(lead_id: str, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get('tenant_id', usuario['id'])
        lead = db.execute(text("SELECT id FROM leads WHERE id=:id AND user_id=:uid"), {"id": lead_id, "uid": tenant_id}).fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")
        # Deletar interações relacionadas primeiro
        db.execute(text("DELETE FROM interacoes WHERE lead_id IN (SELECT id FROM leads WHERE id=:id AND user_id=:uid)"), {"id": lead_id, "uid": tenant_id})
        db.execute(text("DELETE FROM leads WHERE id=:id AND user_id=:uid"), {"id": lead_id, "uid": tenant_id})
        db.commit()
        return {"ok": True, "mensagem": "Lead deletado com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Leads] Erro deletar lead: {e}")


# ===== 3.1 — Feedback loop / Brain =====

class FeedbackRequest(BaseModel):
    resultado: str  # 'convertido' ou 'perdido'
    observacao: str = ""

@router.post('/{lead_id}/feedback')
async def registrar_feedback(
    lead_id: str,
    req: FeedbackRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user)
):
    """
    Registra feedback de conversão/perda de um lead.
    Salva na tabela sdr_learning para o franz aprender com o histórico.
    Se resultado='convertido', atualiza lead.status='convertido'.
    """
    if req.resultado not in ('convertido', 'perdido'):
        raise HTTPException(status_code=400, detail="resultado deve ser 'convertido' ou 'perdido'")

    try:
        tenant_id = usuario.get('tenant_id', usuario['id'])

        # Buscar dados do lead
        lead = db.execute(text(
            "SELECT id, segmento, tier, telefone FROM leads WHERE id=:id AND user_id=:uid"
        ), {"id": lead_id, "uid": tenant_id}).fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")

        lead_dict = dict(lead._mapping)
        segmento = lead_dict.get('segmento') or ''
        tier = lead_dict.get('tier') or 'STANDARD'
        telefone = lead_dict.get('telefone') or ''

        # Buscar última mensagem enviada pelo franz (direcao='saida')
        # Defesa em profundidade: JOIN com leads valida ownership por user_id
        ultima_msg = db.execute(text("""
            SELECT i.mensagem FROM interacoes i
            JOIN leads l ON l.id = i.lead_id
            WHERE i.lead_id = :lead_id AND i.direcao = 'saida' AND l.user_id = :uid
            ORDER BY i.id DESC
            LIMIT 1
        """), {"lead_id": lead_id, "uid": tenant_id}).fetchone()
        mensagem_usada = ultima_msg[0] if ultima_msg else ""

        # Salvar na sdr_learning
        db.execute(text("""
            INSERT INTO sdr_learning
                (lead_id, nicho, segmento, tier, mensagem_usada, resultado, observacao, user_id, criado_em)
            VALUES
                (:lead_id, :nicho, :segmento, :tier, :mensagem_usada, :resultado, :observacao, :user_id, NOW()::text)
        """), {
            "lead_id": lead_id,
            "nicho": segmento,
            "segmento": segmento,
            "tier": tier,
            "mensagem_usada": mensagem_usada,
            "resultado": req.resultado,
            "observacao": req.observacao,
            "user_id": tenant_id,
        })

        # Se convertido, atualizar status do lead
        if req.resultado == 'convertido':
            db.execute(text(
                "UPDATE leads SET status='convertido', atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"
            ), {"id": lead_id, "uid": tenant_id})

        db.commit()

        adicionar_log(
            f"[Feedback] Lead {lead_id} marcado como '{req.resultado}' no segmento '{segmento}'",
            'success' if req.resultado == 'convertido' else 'info'
        )

        return {
            "ok": True,
            "mensagem": f"Feedback '{req.resultado}' registrado com sucesso",
            "lead_id": lead_id,
            "segmento": segmento,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Leads] Erro ao registrar feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/{lead_id}/enviar-mensagem')
async def enviar_mensagem_lead(lead_id: str, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Envia mensagem franz para lead com site pronto (sdr_stage=pendente_wpp)."""
    import os, httpx, re as _re
    tenant_id = usuario.get("user_id") or usuario.get("sub")

    # Buscar lead
    row = db.execute(text(
        "SELECT nome, telefone, whatsapp, segmento, cidade, site_url, rating, sdr_stage FROM leads WHERE id=:id AND user_id=:uid"
    ), {"id": lead_id, "uid": tenant_id}).fetchone()
    if not row:
        raise HTTPException(404, "Lead não encontrado")

    nome, telefone, whatsapp, segmento, cidade, site_url, rating, sdr_stage = row

    if not site_url:
        raise HTTPException(400, "Lead não tem site gerado. Rode o pipeline primeiro.")

    # Verificar WPP conectado
    meowhats_url = os.getenv("MEOWHATS_URL", "http://localhost:3001")
    meowhats_key = os.getenv("MEOWHATS_KEY", "")
    wpp_tenant = f"fralib_user_{tenant_id}"
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r_wpp = await c.get(f"{meowhats_url}/api/sessions", headers={"X-API-Key": meowhats_key})
            wpp_ok = False
            if r_wpp.status_code == 200:
                for s in r_wpp.json():
                    if s.get("id") == wpp_tenant and s.get("status") == "connected":
                        wpp_ok = True
                        break
            if not wpp_ok:
                raise HTTPException(400, "WhatsApp não está conectado. Conecte primeiro no painel.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "Erro ao verificar status do WhatsApp")

    # Gerar mensagem com franz
    from agents.franz import iniciar_contato, FranzInput
    franz_input = FranzInput(
        nome=nome, cidade=cidade or "", segmento=segmento or "",
        telefone=telefone or "", whatsapp=whatsapp or "",
        rating=rating or 0.0, site_url=site_url,
        score_caio=80, tier="STANDARD"
    )
    franz_output = iniciar_contato(franz_input, user_id=tenant_id)

    # Enviar via meowhats
    tel = (whatsapp or telefone or "").strip()
    tel = _re.sub(r'\D', '', tel)
    if not tel.startswith('55'):
        tel = '55' + tel
    jid = f"{tel}@s.whatsapp.net"

    if not is_tenant_connected(wpp_tenant):
        raise HTTPException(409, "WhatsApp do usuário não está conectado. Pareie o QR code antes de enviar mensagens.")

    async with httpx.AsyncClient(timeout=10) as c:
        r_send = await c.post(
            f"{meowhats_url}/api/sessions/{wpp_tenant}/send",
            headers={"X-API-Key": meowhats_key},
            json={"jid": jid, "type": "text", "text": franz_output.reply}
        )
        if r_send.status_code != 200:
            raise HTTPException(500, f"Falha no envio: {r_send.text[:100]}")

    # Se franz bloqueou (fora do horário), não enviar
    if not franz_output.reply or not franz_output.reply.strip():
        return {"ok": False, "mensagem": f"Fora do horário de atendimento — lead permanece na fila"}

    # Atualizar sdr_stage
    db.execute(text(
        "UPDATE leads SET sdr_stage=:stage, atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"
    ), {"id": lead_id, "stage": franz_output.next_stage or "hook", "uid": tenant_id})
    db.commit()

    adicionar_log(f"📱 Mensagem enviada para {nome} ({tel})", "success", tenant_id)
    return {"ok": True, "mensagem": f"Mensagem enviada para {nome}"}
