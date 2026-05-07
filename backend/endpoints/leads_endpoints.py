from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import sys
sys.path.append('/root/fralib/backend')
sys.path.append('/root/fralib/backend/core')
from database import get_db
from auth import get_current_user
from endpoints.sse_endpoints import adicionar_log

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
        result = db.execute(text(
            "SELECT id, mensagem, direcao, criado_em FROM interacoes WHERE lead_id = :lead_id ORDER BY id ASC"
        ), {"lead_id": lead_id}).fetchall()
        return {"mensagens": [dict(r._mapping) for r in result]}
    except Exception as e:
        return {"mensagens": []}

@router.patch('/{lead_id}')
async def atualizar_lead(lead_id: str, request_data: dict, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        campos = {}
        if 'whatsapp' in request_data:
            campos['whatsapp'] = request_data['whatsapp']
            campos['telefone_whatsapp'] = request_data['whatsapp']
        if 'observacoes' in request_data:
            campos['observacoes'] = request_data['observacoes']
        if 'valor_venda' in request_data:
            campos['valor_venda'] = request_data['valor_venda']
        if 'status' in request_data:
            campos['status'] = request_data['status']

        if not campos:
            return {"ok": True}

        sets = ", ".join([f"{k}=:{k}" for k in campos.keys()])
        campos['lead_id'] = lead_id
        db.execute(text(f"UPDATE leads SET {sets} WHERE id=:lead_id"), campos)
        db.commit()
        return {"ok": True}
    except Exception as e:
        print(f"[Leads] Erro ao atualizar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/{lead_id}/reprocessar')
async def reprocessar_lead(lead_id: str, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        lead = db.execute(text("SELECT * FROM leads WHERE id=:id"), {"id": lead_id}).fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead nao encontrado")
        db.execute(text("UPDATE leads SET status='pendente', atualizado_em=NOW()::text WHERE id=:id"), {"id": lead_id})
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
    lead = db.execute(text('SELECT * FROM leads WHERE id=:id'), {'id': lead_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail='Lead nao encontrado')

    lead_dict = dict(lead._mapping)
    url_site = lead_dict.get('url_site') or lead_dict.get('site_url') or ''
    if not url_site:
        raise HTTPException(status_code=400, detail='Lead nao tem site gerado')

    slug = url_site.rstrip('/').split('/')[-1]
    html_path = '/var/www/fralib/sites/' + slug + '/index.html'

    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail='Arquivo HTML nao encontrado: ' + html_path)

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
    lead = db.execute(text("SELECT * FROM leads WHERE id=:id"), {"id": lead_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nao encontrado")

    lead_dict = dict(lead._mapping)
    url_site = lead_dict.get('url_site') or lead_dict.get('site_url') or ''
    if not url_site:
        raise HTTPException(status_code=400, detail="Lead nao tem site gerado")

    slug = url_site.rstrip('/').split('/sites/')[-1].rstrip('/')
    if not slug or slug == url_site.rstrip('/'):
        slug = url_site.rstrip('/').split('/')[-1]

    assets_dir = '/var/www/fralib/sites/' + slug + '/assets'
    os.makedirs(assets_dir, exist_ok=True)

    if tipo == 'logo':
        filename = 'logo.webp'
    else:
        filename = 'foto_' + str(numero) + '.webp'

    filepath = assets_dir + '/' + filename
    contents = await foto.read()

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
        
        prd = gerar_arquiteto_mestre_prd(
            dados_hunter=dados_hunter,
            cidade=req.cidade,
            segmento=req.nicho,
            jina_insights=req.briefing or "Negócio local de qualidade",
            alex_colors=alex_colors,
            caio_tier="STANDARD",
            caio_score=req.score or 80,
            caio_motivo="Lead manual",
            briefing_theo=req.briefing or ""
        )
        html_main = gerar_html_componentizado(prd)
        html_final = montar_template_python(html_main, prd)
        if html_final:
            slug = req.nome.lower().replace(' ', '-')[:40] + '-manual'
            web_dir = f'/var/www/fralib/sites/{slug}'
            _os.makedirs(web_dir, exist_ok=True)
            with open(f'{web_dir}/index.html', 'w', encoding='utf-8') as f:
                f.write(html_final)
            site_url = f'https://seunegociofralib.site/sites/{slug}/'
            from datetime import datetime as _dt
            from sqlalchemy import create_engine as _ce
            import os as _os2
            _eng = _ce(_os2.environ.get('DATABASE_URL', ''), pool_pre_ping=True)
            with _eng.connect() as conn:
                conn.execute(_text("UPDATE leads SET url_site=:url, site_url=:url, status='concluido', processado=true, atualizado_em=:ts WHERE id=:id"),
                    {"url": site_url, "ts": _dt.now().isoformat(), "id": lead_id})
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
            conn.execute(_text("UPDATE leads SET status='erro', atualizado_em=:ts WHERE id=:id"),
                {"ts": _dt.now().isoformat(), "id": lead_id})
            conn.commit()

@router.get('/mensagens-novas')
async def get_mensagens_novas(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        result = db.execute(text("""
            SELECT DISTINCT lead_nome, COUNT(*) as total
            FROM interacoes
            WHERE direcao = 'entrada'
            AND criado_em > (NOW() - INTERVAL '24 hours')::text
            GROUP BY lead_nome
        """)).fetchall()
        return {"leads_com_resposta": [{"nome": r.lead_nome, "total": r.total} for r in result]}
    except Exception as e:
        return {"leads_com_resposta": []}



@router.get('/capturados')
async def get_leads_capturados(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id = usuario.get('tenant_id', usuario['id'])
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
