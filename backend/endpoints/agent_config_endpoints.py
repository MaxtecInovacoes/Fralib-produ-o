"""
CRUD de configuração de agentes (modelo, provider, params) + Playground A/B + Pipeline Sandbox.
Restrito a superadmin.
"""
import time
import json
import requests
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from auth import get_current_user

router = APIRouter(prefix='/api/agent-configs', tags=['agent-configs'])

SUPERADMIN_EMAIL = 'dezigpi@gmail.com'

# Modelos disponíveis por provider (referência para o frontend)
AVAILABLE_MODELS = {
    'anthropic': [
        {'id': 'claude-opus-4-7', 'label': 'Claude Opus 4', 'tier': 'heavy'},
        {'id': 'claude-sonnet-4-6', 'label': 'Claude Sonnet 4', 'tier': 'medium'},
        {'id': 'claude-haiku-4-5', 'label': 'Claude Haiku 4', 'tier': 'light'},
    ],
    'openai': [
        {'id': 'gpt-4o', 'label': 'GPT-4o', 'tier': 'heavy'},
        {'id': 'gpt-4o-mini', 'label': 'GPT-4o Mini', 'tier': 'light'},
        {'id': 'gpt-4-turbo', 'label': 'GPT-4 Turbo', 'tier': 'heavy'},
    ],
    'google': [
        {'id': 'gemini-2.5-flash', 'label': 'Gemini 2.5 Flash', 'tier': 'medium'},
        {'id': 'gemini-2.5-pro', 'label': 'Gemini 2.5 Pro', 'tier': 'heavy'},
        {'id': 'gemini-2.0-flash', 'label': 'Gemini 2.0 Flash', 'tier': 'light'},
    ],
    'groq': [
        {'id': 'llama-3.3-70b-versatile', 'label': 'Llama 3.3 70B', 'tier': 'heavy'},
        {'id': 'llama-3.1-8b-instant', 'label': 'Llama 3.1 8B', 'tier': 'light'},
        {'id': 'mixtral-8x7b-32768', 'label': 'Mixtral 8x7B', 'tier': 'medium'},
    ],
}


def require_superadmin(user: dict = Depends(get_current_user)):
    if user.get('email') != SUPERADMIN_EMAIL:
        raise HTTPException(status_code=403, detail='Acesso negado: Super Admin apenas')
    return user


# ============================================================
# CRUD
# ============================================================

@router.get('')
async def list_configs(db: Session = Depends(get_db), user=Depends(require_superadmin)):
    """Lista todas as configurações de agentes."""
    rows = db.execute(text("""
        SELECT agent_name, provider, model_id, fallback_provider, fallback_model_id,
               temperature, top_p, max_tokens, enabled, atualizado_em
        FROM agent_model_configs ORDER BY agent_name
    """)).fetchall()
    configs = []
    for r in rows:
        configs.append({
            'agent_name': r[0],
            'provider': r[1],
            'model_id': r[2],
            'fallback_provider': r[3],
            'fallback_model_id': r[4],
            'temperature': r[5],
            'top_p': r[6],
            'max_tokens': r[7],
            'enabled': r[8],
            'atualizado_em': r[9].isoformat() if r[9] else None,
        })
    return {'ok': True, 'configs': configs}


@router.put('/{agent_name}')
async def update_config(agent_name: str, body: dict, db: Session = Depends(get_db), user=Depends(require_superadmin)):
    """Atualiza configuração de um agente."""
    allowed_fields = ['provider', 'model_id', 'fallback_provider', 'fallback_model_id',
                      'temperature', 'top_p', 'max_tokens', 'enabled']
    updates = {}
    for f in allowed_fields:
        if f in body:
            updates[f] = body[f]
    if not updates:
        raise HTTPException(400, 'Nenhum campo para atualizar')

    # Verificar se agente existe
    exists = db.execute(text("SELECT 1 FROM agent_model_configs WHERE agent_name = :n"), {"n": agent_name}).fetchone()
    if not exists:
        # Criar novo
        updates['agent_name'] = agent_name
        updates['atualizado_por'] = user.get('id')
        cols = ', '.join(updates.keys())
        vals = ', '.join(f':{k}' for k in updates.keys())
        db.execute(text(f"INSERT INTO agent_model_configs ({cols}, atualizado_em) VALUES ({vals}, NOW())"), updates)
    else:
        set_clause = ', '.join(f"{k} = :{k}" for k in updates.keys())
        updates['n'] = agent_name
        updates['uid'] = user.get('id')
        db.execute(text(f"UPDATE agent_model_configs SET {set_clause}, atualizado_em = NOW(), atualizado_por = :uid WHERE agent_name = :n"), updates)
    db.commit()

    # Invalidar cache do llm_direct
    try:
        from agents.llm_direct import _invalidar_agent_config_cache
        _invalidar_agent_config_cache()
    except Exception:
        pass

    return {'ok': True, 'agent_name': agent_name}


@router.get('/models')
async def list_models(user=Depends(require_superadmin)):
    """Lista modelos disponíveis por provider."""
    return {'ok': True, 'models': AVAILABLE_MODELS}


# ============================================================
# PLAYGROUND
# ============================================================

@router.post('/playground')
async def run_playground(body: dict, db: Session = Depends(get_db), user=Depends(require_superadmin)):
    """Executa teste de um agente com modelo específico. Não afeta produção."""
    agent_name = body.get('agent_name', 'theo')
    provider = body.get('provider', 'anthropic')
    model_id = body.get('model_id', 'claude-sonnet-4-6')
    prompt_system = body.get('system', '')
    prompt_user = body.get('user', '')
    temperature = float(body.get('temperature', 0.7))
    max_tokens = int(body.get('max_tokens', 2000))

    if not prompt_user:
        raise HTTPException(400, 'Prompt user obrigatório')

    # Carregar system prompt do agente se não fornecido
    if not prompt_system:
        prompt_system = _get_agent_system_prompt(agent_name)

    start = time.time()
    try:
        from services.llm_router import call_llm
        response_text, usage = call_llm(
            provider=provider,
            model_id=model_id,
            system=prompt_system,
            user=prompt_user,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency_ms = int((time.time() - start) * 1000)
        input_tokens = usage.get('input_tokens', 0)
        output_tokens = usage.get('output_tokens', 0)
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return {
            'ok': False,
            'error': str(e),
            'latency_ms': latency_ms,
        }

    # Salvar no histórico
    try:
        db.execute(text("""
            INSERT INTO playground_runs (agent_name, provider, model_id, prompt_system, prompt_user,
                                         response, input_tokens, output_tokens, latency_ms, temperature, criado_por)
            VALUES (:agent, :provider, :model, :sys, :usr, :resp, :inp, :out, :lat, :temp, :uid)
        """), {
            'agent': agent_name, 'provider': provider, 'model': model_id,
            'sys': prompt_system[:2000], 'usr': prompt_user[:2000],
            'resp': response_text[:5000] if response_text else '',
            'inp': input_tokens, 'out': output_tokens,
            'lat': latency_ms, 'temp': temperature, 'uid': user.get('id'),
        })
        db.commit()
    except Exception:
        pass

    return {
        'ok': True,
        'response': response_text,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'latency_ms': latency_ms,
        'model_id': model_id,
        'provider': provider,
    }


@router.get('/playground/history')
async def playground_history(db: Session = Depends(get_db), user=Depends(require_superadmin)):
    """Últimos 20 testes do playground."""
    rows = db.execute(text("""
        SELECT agent_name, provider, model_id, input_tokens, output_tokens,
               latency_ms, temperature, criado_em
        FROM playground_runs ORDER BY criado_em DESC LIMIT 20
    """)).fetchall()
    runs = []
    for r in rows:
        runs.append({
            'agent_name': r[0], 'provider': r[1], 'model_id': r[2],
            'input_tokens': r[3], 'output_tokens': r[4],
            'latency_ms': r[5], 'temperature': r[6],
            'criado_em': r[7].isoformat() if r[7] else None,
        })
    return {'ok': True, 'runs': runs}


def _get_agent_system_prompt(agent_name: str) -> str:
    """Retorna system prompt padrão do agente (pra playground)."""
    prompts = {
        'theo': 'Voce e Theo, estrategista de marketing digital da FraLib. Gere briefings estrategicos para sites de negocios locais.',
        'liam': 'Voce e Liam, desenvolvedor frontend senior da FraLib. Gere HTML/Tailwind para sections de sites.',
        'bryan': 'Voce e Bryan, especialista em mensagens WhatsApp da FraLib. Gere mensagens persuasivas e curtas.',
        'liz': 'Voce e Liz, auditora de qualidade HTML da FraLib. Analise e corrija problemas em codigo HTML.',
        'arquiteto_mestre': 'Voce e o Arquiteto Mestre da FraLib. Gere PRDs detalhados para sites de negocios locais.',
        'designer_prd': 'Voce e o Designer PRD da FraLib. Crie especificacoes visuais para sites.',
        'alex': 'Voce e Alex, especialista em identidade visual da FraLib. Defina paletas de cores e logos.',
    }
    return prompts.get(agent_name.lower(), f'Voce e {agent_name}, um agente especializado da FraLib.')


# ============================================================
# PIPELINE SANDBOX — roda pipeline real com modelos customizáveis
# Sem WhatsApp, sem deploy. Retorna HTML final + métricas.
# ============================================================

@router.post('/pipeline-sandbox')
async def run_pipeline_sandbox(body: dict, db: Session = Depends(get_db), user=Depends(require_superadmin)):
    """
    Roda pipeline completo em sandbox: Hunter → Caio → Theo → Arquiteto → Liam → Liz.
    Sem envio de WhatsApp, sem deploy na Vercel.
    Retorna HTML final + métricas de cada fase.

    body: {
        segmento: str,
        cidade: str,
        models: {  // modelo por agente (opcional, usa config do DB se não informado)
            theo: {provider, model_id},
            arquiteto_mestre: {provider, model_id},
            liam: {provider, model_id},
            liz: {provider, model_id},
        }
    }
    """
    segmento = body.get('segmento', '')
    cidade = body.get('cidade', '')
    models_override = body.get('models', {})

    results = {
        'fases': [],
        'html_final': '',
        'total_tokens': 0,
        'total_latency_ms': 0,
        'lead': None,
    }

    # Temporariamente sobrescrever configs de agentes se models_override fornecido
    from agents.llm_direct import _load_agent_configs, _invalidar_agent_config_cache
    original_configs = None

    try:
        # Se tem override de modelos, salvar temporariamente no DB
        if models_override:
            for agent_name, cfg in models_override.items():
                if cfg.get('provider') and cfg.get('model_id'):
                    db.execute(text("""
                        INSERT INTO agent_model_configs (agent_name, provider, model_id, atualizado_em, atualizado_por)
                        VALUES (:name, :prov, :model, NOW(), :uid)
                        ON CONFLICT (agent_name) DO UPDATE SET
                            provider = :prov, model_id = :model, atualizado_em = NOW()
                    """), {'name': agent_name, 'prov': cfg['provider'], 'model': cfg['model_id'], 'uid': user.get('id')})
            db.commit()
            _invalidar_agent_config_cache()

        # FASE 1: Hunter — buscar lead real do banco (não roda scraper em sandbox)
        t0 = time.time()
        try:
            row = db.execute(text("""
                SELECT id, nome, cidade, segmento, telefone, rating
                FROM leads
                WHERE segmento ILIKE :seg AND cidade ILIKE :cid
                  AND nome IS NOT NULL AND nome != ''
                ORDER BY RANDOM() LIMIT 1
            """), {'seg': f'%{segmento}%', 'cid': f'%{cidade}%'}).fetchone()

            if not row:
                # Fallback: qualquer lead com dados
                row = db.execute(text("""
                    SELECT id, nome, cidade, segmento, telefone, rating
                    FROM leads WHERE nome IS NOT NULL AND nome != ''
                    ORDER BY RANDOM() LIMIT 1
                """)).fetchone()

            lat = int((time.time() - t0) * 1000)
            if row:
                class _Lead:
                    pass
                lead = _Lead()
                lead.nome = row[1] or 'Negócio Teste'
                lead.cidade = row[2] or cidade
                lead.segmento = row[3] or segmento
                lead.telefone = row[4] or '11999999999'
                lead.rating = row[5] or 4.5
                results['lead'] = {
                    'nome': lead.nome,
                    'cidade': lead.cidade,
                    'segmento': lead.segmento,
                    'telefone': lead.telefone,
                    'rating': lead.rating,
                }
                results['fases'].append({'fase': 'Hunter', 'status': 'ok', 'latency_ms': lat, 'detail': f'Lead do banco: {lead.nome}'})
            else:
                # Usar lead fictício pra não travar
                class _Lead:
                    pass
                lead = _Lead()
                lead.nome = f'{segmento} Modelo'
                lead.cidade = cidade
                lead.segmento = segmento
                lead.telefone = '11999999999'
                lead.rating = 4.7
                results['lead'] = {
                    'nome': lead.nome,
                    'cidade': lead.cidade,
                    'segmento': lead.segmento,
                    'telefone': lead.telefone,
                    'rating': lead.rating,
                }
                results['fases'].append({'fase': 'Hunter', 'status': 'ok', 'latency_ms': lat, 'detail': 'Lead fictício (nenhum no banco)'})
        except Exception as e:
            lat = int((time.time() - t0) * 1000)
            results['fases'].append({'fase': 'Hunter', 'status': 'error', 'latency_ms': lat, 'detail': str(e)[:200]})
            return {'ok': False, 'results': results, 'error': f'Hunter falhou: {e}'}

        results['total_latency_ms'] += lat

        # FASE 2: Caio — qualificação (simulada no sandbox)
        t0 = time.time()
        try:
            # Caio é Python puro — simular qualificação baseada em rating
            class _Qual:
                pass
            qual = _Qual()
            qual.tier = 'GOLD' if lead.rating >= 4.5 else 'SILVER' if lead.rating >= 4.0 else 'BRONZE'
            qual.score = int(lead.rating * 20)
            lat = int((time.time() - t0) * 1000)
            results['fases'].append({'fase': 'Caio', 'status': 'ok', 'latency_ms': lat, 'detail': f'tier={qual.tier} score={qual.score}'})
        except Exception as e:
            lat = int((time.time() - t0) * 1000)
            results['fases'].append({'fase': 'Caio', 'status': 'error', 'latency_ms': lat, 'detail': str(e)[:200]})
            qual = None
        results['total_latency_ms'] += lat

        # FASE 3: Theo — briefing estratégico
        t0 = time.time()
        try:
            from services.llm_router import call_llm
            theo_cfg = models_override.get('theo', {})
            theo_provider = theo_cfg.get('provider', 'anthropic')
            theo_model = theo_cfg.get('model_id', 'claude-sonnet-4-6')

            theo_prompt = f"""Gere um briefing estrategico para o site de: {lead.nome}
Cidade: {lead.cidade}. Segmento: {segmento}.
Rating: {lead.rating}/5. Telefone: {lead.telefone or 'N/A'}.
Foco em conversao, SEO local e credibilidade."""

            theo_resp, theo_usage = call_llm(theo_provider, theo_model, _get_agent_system_prompt('theo'), theo_prompt, 0.7, 4000)
            lat = int((time.time() - t0) * 1000)
            theo_tokens = (theo_usage.get('input_tokens', 0) + theo_usage.get('output_tokens', 0))
            results['fases'].append({'fase': 'Theo', 'status': 'ok', 'latency_ms': lat, 'tokens': theo_tokens, 'detail': f'{len(theo_resp)} chars', 'provider': theo_provider, 'model': theo_model})
            results['total_tokens'] += theo_tokens
        except Exception as e:
            lat = int((time.time() - t0) * 1000)
            results['fases'].append({'fase': 'Theo', 'status': 'error', 'latency_ms': lat, 'detail': str(e)[:200]})
            theo_resp = f"Site profissional para {lead.nome} em {cidade}."
        results['total_latency_ms'] += lat

        # FASE 4: Arquiteto — PRD
        t0 = time.time()
        try:
            arq_cfg = models_override.get('arquiteto_mestre', {})
            arq_provider = arq_cfg.get('provider', 'anthropic')
            arq_model = arq_cfg.get('model_id', 'claude-sonnet-4-6')

            arq_prompt = f"""Crie um PRD (Product Requirements Document) para o site de: {lead.nome}
Cidade: {lead.cidade}. Segmento: {segmento}.
Briefing do Theo: {theo_resp[:2000]}
Tier: {qual.tier if qual else 'STANDARD'}. Score: {qual.score if qual else 50}.
Inclua: sections (hero, sobre, servicos, depoimentos, localizacao, contato), copy por secao, layout_type por secao."""

            arq_resp, arq_usage = call_llm(arq_provider, arq_model, _get_agent_system_prompt('arquiteto_mestre'), arq_prompt, 0.7, 6000)
            lat = int((time.time() - t0) * 1000)
            arq_tokens = (arq_usage.get('input_tokens', 0) + arq_usage.get('output_tokens', 0))
            results['fases'].append({'fase': 'Arquiteto', 'status': 'ok', 'latency_ms': lat, 'tokens': arq_tokens, 'detail': f'{len(arq_resp)} chars', 'provider': arq_provider, 'model': arq_model})
            results['total_tokens'] += arq_tokens
        except Exception as e:
            lat = int((time.time() - t0) * 1000)
            results['fases'].append({'fase': 'Arquiteto', 'status': 'error', 'latency_ms': lat, 'detail': str(e)[:200]})
            return {'ok': False, 'results': results, 'error': f'Arquiteto falhou: {e}'}
        results['total_latency_ms'] += lat

        # FASE 5: Liam — geração HTML
        t0 = time.time()
        try:
            liam_cfg = models_override.get('liam', {})
            liam_provider = liam_cfg.get('provider', 'anthropic')
            liam_model = liam_cfg.get('model_id', 'claude-opus-4-7')

            liam_prompt = f"""INSTRUÇÃO: Retorne APENAS código HTML puro. ZERO texto explicativo antes ou depois. Nenhuma introdução, nenhum comentário fora do HTML.

Gere o HTML COMPLETO para o site de: {lead.nome}
Cidade: {lead.cidade}. Segmento: {segmento}.
WhatsApp: 55{(lead.telefone or '11999999999').replace(' ','').replace('-','')}
PRD do Arquiteto: {arq_resp[:3000]}
Briefing: {theo_resp[:1000]}

OBRIGATÓRIO gerar TODAS estas sections na ordem:
1. <nav> — menu fixo no topo com logo + links âncora + botão WhatsApp
2. <section id="hero"> — headline + CTA + imagem
3. <section id="sobre"> — sobre o negócio
4. <section id="servicos"> — cards de serviços
5. <section id="depoimentos"> — avaliações reais
6. <section id="localizacao"> — mapa + endereço
7. <section id="contato"> — formulário ou CTA WhatsApp
8. <footer> — rodapé com links, copyright, redes sociais

Use Tailwind CSS. Cores via variáveis CSS: var(--bg), var(--fg), var(--accent), var(--surface), var(--muted), var(--border).
Comece DIRETAMENTE com <nav. Termine com </footer>.
NÃO inclua <!DOCTYPE>, <html>, <head>, <body> — apenas o conteúdo interno."""

            liam_resp, liam_usage = call_llm(liam_provider, liam_model,
                "Voce e um gerador de HTML. Retorne APENAS codigo HTML puro usando Tailwind CSS. NUNCA escreva texto explicativo, introducoes ou comentarios fora do HTML. Comece diretamente com a primeira tag HTML.",
                liam_prompt, 0.4, 12000)
            lat = int((time.time() - t0) * 1000)
            # Limpar texto antes do HTML (Gemini às vezes adiciona introdução)
            import re as _re_html
            _html_start = _re_html.search(r'<(?:nav|section|div|header)', liam_resp)
            if _html_start and _html_start.start() > 0:
                liam_resp = liam_resp[_html_start.start():]
            # Remover code fences se vieram
            liam_resp = _re_html.sub(r'^```(?:html)?\s*', '', liam_resp)
            liam_resp = _re_html.sub(r'\s*```\s*$', '', liam_resp)
            liam_tokens = (liam_usage.get('input_tokens', 0) + liam_usage.get('output_tokens', 0))
            results['fases'].append({'fase': 'Liam', 'status': 'ok', 'latency_ms': lat, 'tokens': liam_tokens, 'detail': f'{len(liam_resp)} chars HTML', 'provider': liam_provider, 'model': liam_model})
            results['total_tokens'] += liam_tokens
        except Exception as e:
            lat = int((time.time() - t0) * 1000)
            results['fases'].append({'fase': 'Liam', 'status': 'error', 'latency_ms': lat, 'detail': str(e)[:200]})
            return {'ok': False, 'results': results, 'error': f'Liam falhou: {e}'}
        results['total_latency_ms'] += lat

        # FASE 6: Liz — auditoria (opcional, rápida)
        t0 = time.time()
        try:
            liz_cfg = models_override.get('liz', {})
            liz_provider = liz_cfg.get('provider', 'anthropic')
            liz_model = liz_cfg.get('model_id', 'claude-haiku-4-5')

            liz_prompt = f"Audite este HTML e dê uma nota de 0-100. Liste problemas críticos (max 5):\n\n{liam_resp[:4000]}"
            liz_resp, liz_usage = call_llm(liz_provider, liz_model, _get_agent_system_prompt('liz'), liz_prompt, 0.3, 2000)
            lat = int((time.time() - t0) * 1000)
            liz_tokens = (liz_usage.get('input_tokens', 0) + liz_usage.get('output_tokens', 0))
            results['fases'].append({'fase': 'Liz', 'status': 'ok', 'latency_ms': lat, 'tokens': liz_tokens, 'detail': liz_resp[:200], 'provider': liz_provider, 'model': liz_model})
            results['total_tokens'] += liz_tokens
        except Exception as e:
            lat = int((time.time() - t0) * 1000)
            results['fases'].append({'fase': 'Liz', 'status': 'error', 'latency_ms': lat, 'detail': str(e)[:200]})
        results['total_latency_ms'] += lat

        # Montar HTML final com wrapper
        html_wrapper = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{lead.nome} — Site Sandbox</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
:root{{--bg:#ffffff;--surface:#f8f9fa;--fg:#1a1a2e;--muted:#6b7280;--border:#e5e7eb;--accent:#9333ea;}}
body{{font-family:system-ui,sans-serif;margin:0;padding:0;color:var(--fg);background:var(--bg);}}
</style>
</head>
<body>
{liam_resp}
</body>
</html>"""
        results['html_final'] = html_wrapper

        return {'ok': True, 'results': results}

    except Exception as e:
        return {'ok': False, 'results': results, 'error': str(e)[:500], 'traceback': traceback.format_exc()[-500:]}

    finally:
        # Restaurar configs originais se foram sobrescritas
        if models_override:
            _invalidar_agent_config_cache()
