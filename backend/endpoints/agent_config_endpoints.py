"""
CRUD de configuração de agentes (modelo, provider, params) + Playground A/B.
Restrito a superadmin.
"""
import time
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.core.database import get_db
from backend.core.access_control import require_superadmin
from backend.core.proxy_models import (
    ALLOWED_PROXY_MODELS,
    PROXY_MODEL_OPTIONS,
    PROXY_PROVIDER,
    proxy_model_list_text,
)

router = APIRouter(prefix='/api/agent-configs', tags=['agent-configs'])

BUILDER_RENDERER_AGENT = 'builder_renderer'
BUILDER_AIBEE_PROVIDER = PROXY_PROVIDER
BUILDER_NON_AIBEE_OVERRIDE_TOKEN = 'ALLOW_NON_AIBEE_BUILDER_PROVIDER'


# Modelos disponíveis por provider (referência para o frontend).
# Em producao, "anthropic" é o endpoint Anthropic-compatible do LiteLLM.
AVAILABLE_MODELS = {
    PROXY_PROVIDER: PROXY_MODEL_OPTIONS,
}
ALLOWED_AGENT_PROVIDERS = set(AVAILABLE_MODELS)
ALLOWED_AGENT_MODELS = ALLOWED_PROXY_MODELS


def _guard_agent_proxy_policy(updates: dict):
    provider = (updates.get('provider') or '').strip().lower()
    model_id = (updates.get('model_id') or '').strip()
    fallback_provider = (updates.get('fallback_provider') or '').strip()
    fallback_model_id = (updates.get('fallback_model_id') or '').strip()
    if provider and provider not in ALLOWED_AGENT_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail='Provider desativado. Use anthropic via LiteLLM FraLib.',
        )
    if model_id and model_id not in ALLOWED_AGENT_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f'Modelo desativado. Use um alias do proxy: {proxy_model_list_text()}.',
        )
    if fallback_provider or fallback_model_id:
        raise HTTPException(
            status_code=400,
            detail='Fallback externo desativado. A pipeline usa apenas o proxy LiteLLM FraLib.',
        )

def _guard_builder_provider_policy(agent_name: str, body: dict, updates: dict):
    if (agent_name or '').lower() != BUILDER_RENDERER_AGENT:
        return
    provider = (updates.get('provider') or '').strip().lower()
    fallback_provider = (updates.get('fallback_provider') or '').strip().lower()
    model_id = (updates.get('model_id') or '').strip()
    non_aibee_provider = provider and provider != BUILDER_AIBEE_PROVIDER
    non_aibee_fallback = fallback_provider and fallback_provider != BUILDER_AIBEE_PROVIDER
    openrouter_style_model = '/' in model_id
    if not (non_aibee_provider or non_aibee_fallback or openrouter_style_model):
        return
    raise HTTPException(
        status_code=400,
        detail=(
            'builder_renderer esta travado no provider anthropic via LiteLLM FraLib. '
            'OpenRouter, providers externos e modelos com "/" estao desativados na pipeline.'
        ),
    )


def _audit_agent_config_update(db: Session, user: dict, agent_name: str, updates: dict):
    try:
        db.execute(text("""
            INSERT INTO audit_log (actor_id, action, target_type, target_id, metadata)
            VALUES (:actor, 'agent_config_update', 'agent_model_config', :target_id, CAST(:meta AS JSONB))
        """), {
            'actor': user.get('id'),
            'target_id': agent_name,
            'meta': json.dumps(updates, default=str),
        })
        db.commit()
    except Exception as e:
        print(f'[audit] falha agent_config_update: {e}')
        try:
            db.rollback()
        except Exception:
            pass


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
    _guard_agent_proxy_policy(updates)
    _guard_builder_provider_policy(agent_name, body, updates)

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
    _audit_agent_config_update(db, user, agent_name, updates)

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
    agent_name = body.get('agent_name', 'agente_nicho')
    provider = body.get('provider', 'anthropic')
    model_id = body.get('model_id', 'claude-sonnet-4-6')
    prompt_system = body.get('system', '')
    prompt_user = body.get('user', '')
    temperature = float(body.get('temperature', 0.7))
    max_tokens = int(body.get('max_tokens', 2000))

    if not prompt_user:
        raise HTTPException(400, 'Prompt user obrigatório')
    _guard_agent_proxy_policy({'provider': provider, 'model_id': model_id})

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
        'bryan': 'Voce e Franz, especialista em mensagens WhatsApp da FraLib. Gere mensagens persuasivas e curtas.',
        'arquiteto_mestre': 'Voce e o Arquiteto Mestre da FraLib. Gere PRDs detalhados para sites de negocios locais.',
        'agente_nicho': 'Voce e o Agente de Nicho da FraLib. Gere analise objetiva do segmento local.',
        'agente_variacao': 'Voce e o Agente de Variacao da FraLib. Defina estrutura visual e layout.',
        'curadoria': 'Voce e o agente de curadoria multimidia da FraLib. Selecione imagens e assets coerentes com o segmento.',
        'validador': 'Voce e o Validador da FraLib. Audite HTML contra o PRD e a consistencia do site.',
    }
    return prompts.get(agent_name.lower(), f'Voce e {agent_name}, um agente especializado da FraLib.')


# ============================================================
# PIPELINE SANDBOX LEGADO
# ============================================================

@router.post('/pipeline-sandbox')
async def run_pipeline_sandbox(body: dict, db: Session = Depends(get_db), user=Depends(require_superadmin)):
    """Endpoint legado desativado; use o smoke oficial versionado."""
    raise HTTPException(
        status_code=410,
        detail={
            'error': 'pipeline_sandbox_legacy_disabled',
            'message': 'Use o smoke oficial: python pipeline.py smoke --dry-run',
        },
    )
