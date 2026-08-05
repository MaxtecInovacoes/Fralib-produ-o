import os
import sys
import json
import time as _time
import threading as _threading
from collections import defaultdict as _defaultdict
from dotenv import load_dotenv
import anthropic
import httpx

_services_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services"))
if _services_dir not in sys.path:
    sys.path.insert(0, _services_dir)


class RateLimitError(Exception):
    """Exceção quando API atinge rate limit após todas as tentativas."""
    def __init__(self, reset_seconds: int = 0):
        self.reset_seconds = reset_seconds
        if reset_seconds > 60:
            tempo = f"{reset_seconds // 60}min {reset_seconds % 60}s"
        else:
            tempo = f"{reset_seconds}s"
        super().__init__(f"Limite de uso atingido. Sera resetado em: {tempo}")


# ══════════════════════════════════════════════════════════════════
# AGENT CONFIG CACHE — lookup dinâmico do DB com fallback hardcoded
# ══════════════════════════════════════════════════════════════════
_AGENT_CONFIG_CACHE: dict = {}
_AGENT_CONFIG_CACHE_TS: float = 0.0
_AGENT_CONFIG_CACHE_TTL: float = 60.0


def _invalidar_agent_config_cache():
    """Chamado quando superadmin altera config de agente."""
    global _AGENT_CONFIG_CACHE, _AGENT_CONFIG_CACHE_TS
    _AGENT_CONFIG_CACHE = {}
    _AGENT_CONFIG_CACHE_TS = 0.0
    print("[LLM] Agent config cache invalidado")


def _load_agent_configs():
    """Carrega configs do DB. Retorna dict {agent_name: {provider, model_id, temperature, max_tokens, ...}}."""
    global _AGENT_CONFIG_CACHE, _AGENT_CONFIG_CACHE_TS
    now = _time.time()
    if _AGENT_CONFIG_CACHE and (now - _AGENT_CONFIG_CACHE_TS) < _AGENT_CONFIG_CACHE_TTL:
        return _AGENT_CONFIG_CACHE
    try:
        from core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT agent_name, provider, model_id, fallback_provider, fallback_model_id,
                       temperature, top_p, max_tokens, enabled
                FROM agent_model_configs WHERE enabled = TRUE
            """)).fetchall()
        configs = {}
        for r in rows:
            configs[r[0]] = {
                'provider': r[1],
                'model_id': r[2],
                'fallback_provider': r[3],
                'fallback_model_id': r[4],
                'temperature': r[5],
                'top_p': r[6],
                'max_tokens': r[7],
            }
        _AGENT_CONFIG_CACHE = configs
        _AGENT_CONFIG_CACHE_TS = now
        return configs
    except Exception as e:
        print(f"[LLM] agent_model_configs load falhou (usando hardcoded): {e}")
        return {}


# ══════════════════════════════════════════════════════════════════
# CALL SPACING — mínimo 1.2s entre calls por processo
# ══════════════════════════════════════════════════════════════════
_LAST_CALL_TIME = 0.0
_CALL_SPACING_LOCK = _threading.Lock()
CALL_SPACING_SECONDS = float(os.environ.get("LLM_CALL_SPACING", "1.2"))


def _enforce_call_spacing():
    global _LAST_CALL_TIME
    with _CALL_SPACING_LOCK:
        now = _time.time()
        elapsed = now - _LAST_CALL_TIME
        if elapsed < CALL_SPACING_SECONDS:
            _time.sleep(CALL_SPACING_SECONDS - elapsed)
        _LAST_CALL_TIME = _time.time()


# ══════════════════════════════════════════════════════════════════
# TENANT RATE LIMIT — sliding window per tenant
# ══════════════════════════════════════════════════════════════════
_TENANT_CALLS_LOCK = _threading.Lock()
_TENANT_CALLS: dict = _defaultdict(list)
TENANT_MAX_CALLS_PER_MIN = int(os.environ.get("TENANT_MAX_CALLS_PER_MIN", "40"))
TENANT_THROTTLE_WAIT = 10


def _tenant_rate_check(user_id) -> tuple:
    if not user_id:
        return (True, 0, 0)
    now = _time.time()
    window = 60.0
    with _TENANT_CALLS_LOCK:
        _TENANT_CALLS[user_id] = [t for t in _TENANT_CALLS[user_id] if now - t < window]
        count = len(_TENANT_CALLS[user_id])
        if count >= TENANT_MAX_CALLS_PER_MIN:
            oldest = _TENANT_CALLS[user_id][0]
            wait = int(window - (now - oldest)) + 1
            return (False, wait, count)
        _TENANT_CALLS[user_id].append(now)
        return (True, 0, count + 1)


def _tenant_rate_alert(user_id, wait_seconds, calls_count):
    print(f"[RATE-LIMIT] Tenant {user_id} throttled: {calls_count} calls/min (max={TENANT_MAX_CALLS_PER_MIN}). Aguardando {wait_seconds}s")
    try:
        import ia_manager as _ia
        _ia.raise_alert(
            'rate_limit', None,
            f'Tenant throttled: {calls_count} chamadas/min excede limite de {TENANT_MAX_CALLS_PER_MIN}. Pipeline aguardou {wait_seconds}s.',
            lead_id=None, user_id=user_id
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
# ENV LOADING
# ══════════════════════════════════════════════════════════════════
import pathlib as _pathlib
_env_paths = [
    '/root/fralib/.env',
    str(_pathlib.Path(__file__).parent.parent.parent / '.env'),
    str(_pathlib.Path(__file__).parent.parent / '.env'),
]
for _env_path in _env_paths:
    if _pathlib.Path(_env_path).exists():
        load_dotenv(_env_path, override=True)
        break
else:
    load_dotenv()

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ANTHROPIC_BASE_URL = os.getenv('ANTHROPIC_BASE_URL', 'https://api.aibee.cloud')


# ══════════════════════════════════════════════════════════════════
# USER CONTEXT + BYOK
# ══════════════════════════════════════════════════════════════════
_current_user_id = None


def set_current_user_id(uid):
    global _current_user_id
    _current_user_id = uid


_byok_cache = {}


def _get_byok_key():
    uid = _current_user_id
    if not uid:
        return None
    if uid in _byok_cache:
        return _byok_cache[uid]
    try:
        from core.database import engine
        from sqlalchemy import text
        from utils.secrets_crypto import decriptar
        with engine.connect() as conn:
            row = conn.execute(text('SELECT plano, anthropic_key_encrypted FROM users WHERE id=:id'), {'id': uid}).fetchone()
        if row and (row[0] or '').lower() == 'pro' and row[1]:
            key = decriptar(row[1])
            _byok_cache[uid] = key or None
            return _byok_cache[uid]
        _byok_cache[uid] = None
    except Exception as e:
        print(f'[llm_direct] BYOK lookup falhou para user {uid}: {e}')
    return None


def _resolve_anthropic():
    """Retorna (api_key, base_url, key_id_or_None)."""
    byok = _get_byok_key()
    if byok:
        return (byok, ANTHROPIC_BASE_URL, None)
    try:
        import ia_manager
        picked = ia_manager.pick_key('anthropic')
        if picked:
            return picked
    except Exception as e:
        print(f'[llm_direct] ia_manager falhou, usando .env: {e}')
    return (ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, None)


def _get_active_api_key():
    return _resolve_anthropic()[0]


def invalidar_byok_cache(uid=None):
    global _byok_cache
    if uid is None:
        _byok_cache = {}
    else:
        _byok_cache.pop(uid, None)


# ══════════════════════════════════════════════════════════════════
# USAGE TRACKING
# ══════════════════════════════════════════════════════════════════
def _salvar_uso_llm(modelo, input_tokens, output_tokens, agente=None):
    try:
        from core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(
                text('INSERT INTO llm_usage (modelo, input_tokens, output_tokens, agente, user_id) VALUES (:m, :i, :o, :a, :u)'),
                {'m': modelo, 'i': input_tokens, 'o': output_tokens, 'a': agente, 'u': _current_user_id}
            )
            conn.commit()
    except Exception as e:
        print(f'[LLM Usage] Erro ao salvar: {e}')


# ══════════════════════════════════════════════════════════════════
# SDK CLIENT FACTORY
# ══════════════════════════════════════════════════════════════════
def _create_client(api_key: str, base_url: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key=api_key,
        base_url=base_url,
        max_retries=0,
        timeout=httpx.Timeout(connect=10.0, read=180.0, write=30.0, pool=10.0),
    )


# ══════════════════════════════════════════════════════════════════
# CALL CLAUDE — SDK-based with manual retry for key rotation
# ══════════════════════════════════════════════════════════════════
_AGENT_MODEL_MAP = {
    'liz': 'haiku',
    'theo': 'sonnet',
    'alex': 'sonnet',
    'liam': 'opus',
    'arquiteto_mestre': 'sonnet',
    'designer_prd': 'sonnet',
}

MODEL_MAP = {
    'opus': 'claude-opus-4-7',
    'sonnet': 'claude-sonnet-4-6',
    'haiku': 'claude-haiku-4-5',
}

# Cascade: ordem de fallback quando modelo primário retorna 529/503/502.
# Lido de env vars; fallback hardcoded se env não definida.
_CASCADE_ENV = {
    'light': os.getenv('FRALIB_PROXY_LIGHT_MODEL', 'claude-haiku-4-5'),
    'default': os.getenv('FRALIB_PROXY_DEFAULT_MODEL', 'claude-sonnet-4-6'),
    'builder': os.getenv('FRALIB_PROXY_BUILDER_MODEL', 'claude-opus-4-8'),
}

# Modelos de alta resistência para cascade (mais caros = mais quota).
_TOPK_MODELS = ['claude-opus-5', 'claude-opus-4-8', 'claude-opus-4-7']

# ── helpers cascade ──
def _cascade_chain(primary_model_id: str, tier: str = 'default') -> list:
    """Retorna lista [primary, fallback1, fallback2, ...] sem duplicatas."""
    pool = set()
    pool.add(primary_model_id)
    pool.update(_TOPK_MODELS)
    pool.add(_CASCADE_ENV.get('light', 'claude-haiku-4-5'))
    pool.add(_CASCADE_ENV.get('default', 'claude-sonnet-4-6'))
    pool.add(_CASCADE_ENV.get('builder', 'claude-opus-4-8'))
    # Remove primary do começo, coloca no começo
    chain = [primary_model_id]
    for m in _TOPK_MODELS:
        if m not in chain and m != primary_model_id:
            chain.append(m)
    # Adiciona modelos do env que ainda não estão
    for key in ('builder', 'default', 'light'):
        m = _CASCADE_ENV.get(key)
        if m and m not in chain:
            chain.append(m)
    return chain


def call_claude(system, user, model='opus', max_tokens=4000, temperature=0.7, agent_name=None, base_url=None):
    """Chama Claude API via SDK com RAG, Skills, Memory, Agent Router, BYOK, e key rotation."""

    # ── RAG + Skills injection ──
    rag_block = ""
    if agent_name:
        try:
            from agent_rag import buscar_contexto_rag, format_rag_prompt, mark_rag_used
            from skill_loader import get_skills_agente, carregar_skills

            rag_context = buscar_contexto_rag(user, agent_name.lower())
            if rag_context:
                rag_block = f"CONTEXTO RAG (conhecimento da base):\n{rag_context}\n\n---\n\n"
                mark_rag_used(agent_name)
                print(f"[LLM Direct] RAG ativado para {agent_name} ({len(rag_block)} chars)")

            skills = get_skills_agente(agent_name.lower())
            if skills:
                guidelines = carregar_skills(skills)
                if guidelines:
                    system = f"{system}\n\n{'='*60}\n# SKILLS ATIVADAS\n{'='*60}\n{guidelines}"
                    print(f"[LLM Direct] Skills ativadas para {agent_name}: {', '.join(skills)}")
        except Exception as e:
            print(f"[LLM Direct] Erro RAG/Skills para {agent_name}: {e}")

    # ── Memory injection (PRD #11) ──
    if agent_name:
        try:
            from agent_memory import get_memory, gerar_prompt_com_memoria
            _mem_core, _mem_warm, _mem_nicho = get_memory()
            if _mem_core and _mem_warm and _mem_nicho:
                system = gerar_prompt_com_memoria(system, agent_name.lower(), _mem_nicho, _mem_core, _mem_warm)
        except Exception:
            pass

    # ── Model routing ──
    _db_config = None
    if agent_name:
        _all_configs = _load_agent_configs()
        _db_config = _all_configs.get(agent_name.lower())

    if _db_config:
        model_id = _db_config['model_id']
        if _db_config.get('temperature') is not None:
            temperature = _db_config['temperature']
        if _db_config.get('max_tokens') is not None:
            max_tokens = _db_config['max_tokens']
        print(f"[LLM Router] {agent_name} -> {_db_config['provider']}/{model_id} (DB config)")
    else:
        _routed = False
        if agent_name:
            try:
                from agent_router import get_router
                _active_router = get_router()
                if _active_router:
                    _routed_model = _active_router.get_model(agent_name.lower())
                    if _routed_model:
                        model = _routed_model
                        _routed = True
            except Exception:
                pass

        if not _routed and agent_name and model == 'opus':
            _auto = _AGENT_MODEL_MAP.get(agent_name.lower())
            if _auto:
                model = _auto
                print(f"[LLM Router] {agent_name} -> {model} (hardcoded fallback)")

        model_id = MODEL_MAP.get(model, MODEL_MAP['opus'])

    # ── Resolve key/base_url ──
    if base_url:
        _api_key = _get_byok_key() or ANTHROPIC_API_KEY
        _key_id = None
        _base = base_url
    else:
        _api_key, _base, _key_id = _resolve_anthropic()

    # ── Prompt caching: system payload ──
    extra_headers = {}
    cache_ativo = False
    if system and len(system) >= 1024:
        system_payload = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        cache_ativo = True
    else:
        system_payload = [{"type": "text", "text": system}] if system else []

    # ── Messages: RAG block cacheado separadamente ──
    if rag_block and len(rag_block) >= 1024:
        messages_content = [
            {"type": "text", "text": rag_block, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": user},
        ]
        cache_ativo = True
    elif rag_block:
        messages_content = rag_block + user
    else:
        messages_content = user

    if cache_ativo:
        extra_headers["anthropic-beta"] = "prompt-caching-2024-07-31"

    # ── Tenant rate limit ──
    if _key_id is not None and _current_user_id:
        allowed, wait, count = _tenant_rate_check(_current_user_id)
        if not allowed:
            _tenant_rate_alert(_current_user_id, wait, count)
            _time.sleep(min(wait, TENANT_THROTTLE_WAIT))
            allowed2, wait2, _ = _tenant_rate_check(_current_user_id)
            if not allowed2:
                _time.sleep(wait2)

    # ── ia_manager ref ──
    try:
        import ia_manager as _ia
    except Exception:
        _ia = None

    # ── Pre-flight: Circuit Breaker + Budget checks ──
    if _ia and not base_url:  # Skip checks for BYOK users
        try:
            # Fase 1: Circuit breaker global — se todas as keys em cooldown, não tentar
            _cooled, _cd_remaining = _ia.is_globally_cooled_down()
            if _cooled and _cd_remaining > 60:
                print(f"[LLM] Circuit breaker OPEN — cooldown {_cd_remaining}s restantes")
                raise RateLimitError(_cd_remaining)

            # Fase 2: Budget diário global
            _budget_ok, _budget_remaining = _ia.check_daily_budget()
            if not _budget_ok:
                print(f"[LLM] Budget diário ESGOTADO — 0 tokens restantes")
                raise Exception("Budget diário de tokens esgotado. Aguarde reset (24h rolling window).")

            # Fase 3: Budget por tenant
            if _current_user_id:
                _plano = 'starter'  # default
                try:
                    from core.database import engine as _budget_engine
                    from sqlalchemy import text as _budget_text
                    with _budget_engine.connect() as _bconn:
                        _prow = _bconn.execute(_budget_text("SELECT plano FROM users WHERE id = :uid"), {"uid": _current_user_id}).fetchone()
                        if _prow:
                            _plano = (_prow[0] or 'starter').lower()
                except Exception:
                    pass
                _tenant_ok, _tenant_remaining = _ia.check_tenant_budget(_current_user_id, _plano)
                if not _tenant_ok:
                    print(f"[LLM] Tenant {_current_user_id} budget ESGOTADO (plano={_plano})")
                    raise Exception(f"Limite diário de tokens atingido para seu plano ({_plano}). Upgrade para mais capacidade.")

            # Fase 5: Coordenação cross-process — backpressure suave
            _rate_ok, _rate_count = _ia.check_global_call_rate()
            if not _rate_ok:
                import time as _time_bp
                _time_bp.sleep(2)  # Backpressure: espera 2s se acima do limite global
        except RateLimitError:
            raise  # Re-raise para o worker tratar
        except Exception as _preflight_err:
            if "Budget" in str(_preflight_err) or "Limite" in str(_preflight_err):
                raise  # Budget errors devem propagar
            print(f"[LLM] Pre-flight check erro (ignorando): {_preflight_err}")

    # ── Token Bucket: throttle preventivo ──
    if not base_url:  # Skip para BYOK
        try:
            from services.token_bucket import throttle as _tb_throttle
            _input_est = (len(system or '') + len(user or '')) // 4
            _total_est = _input_est + max_tokens
            _tb_throttle(_total_est)
        except Exception:
            pass  # Não bloquear se bucket falhar

    # ── SDK retry loop com model cascade ──
    MAX_ATTEMPTS = 5
    response = None
    _cascade = _cascade_chain(model_id)
    _current_model = model_id
    _cascade_idx = 0
    print(f"[LLM] model={model_id} cascade={_cascade} cache={'on' if cache_ativo else 'off'} agent={agent_name or '-'}")

    for _attempt in range(1, MAX_ATTEMPTS + 1):
        _enforce_call_spacing()
        client = _create_client(_api_key, _base)
        try:
            response = client.messages.create(
                model=_current_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_payload,
                messages=[{"role": "user", "content": messages_content}],
                extra_headers=extra_headers if extra_headers else None,
            )

            # ── Success: log usage ──
            usage = response.usage
            input_tokens = usage.input_tokens
            output_tokens = usage.output_tokens
            cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
            cache_created = getattr(usage, 'cache_creation_input_tokens', 0) or 0
            if cache_read or cache_created:
                print(f"[LLM] stop={response.stop_reason} in={input_tokens} out={output_tokens} cache_read={cache_read} cache_created={cache_created}")
            else:
                print(f"[LLM] stop={response.stop_reason} in={input_tokens} out={output_tokens}")

            _salvar_uso_llm(_current_model, input_tokens, output_tokens, agent_name)

            try:
                from token_tracker import get_tracker
                _tracker = get_tracker()
                if _tracker:
                    _tracker.registrar(agente=agent_name or "unknown", model=_current_model, usage={
                        'input_tokens': input_tokens, 'output_tokens': output_tokens,
                        'cache_read_input_tokens': cache_read, 'cache_creation_input_tokens': cache_created,
                    })
            except Exception:
                pass

            if _ia and _key_id:
                _ia.mark_success(_key_id)

            # ── Extract text from response ──
            for block in response.content:
                if block.type == "text":
                    return block.text

            # ── Proxy workaround: tool_use text extraction ──
            return _extract_text_from_tool_use(response, client, model_id, max_tokens, temperature, system, user, extra_headers)

        except anthropic.RateLimitError as e:
            cd = 60
            if _ia:
                try:
                    cd = _ia.parse_cooldown_from_response(429, dict(e.response.headers) if e.response else {})
                except Exception:
                    pass
            if _ia and _key_id:
                _ia.mark_failure(_key_id, '429 rate limit', cd)
                if _attempt == 1:
                    _ia.raise_alert('rate_limit', _key_id, f'429 em call_claude (cooldown {cd}s)', lead_id=None, user_id=_current_user_id)
            if _attempt >= MAX_ATTEMPTS:
                if _ia:
                    _ia.raise_alert('all_keys_failed', _key_id, f'Rate limit persistente apos {MAX_ATTEMPTS} tentativas', lead_id=None, user_id=_current_user_id)
                raise RateLimitError(reset_seconds=cd)
            if base_url is None:
                new_key = _resolve_anthropic()
                if new_key and new_key[2] != _key_id:
                    _api_key, _base, _key_id = new_key
                    wait = min(10 * _attempt, 20)
                    print(f'[LLM] 429 — trocou key, aguardando {wait}s (tentativa {_attempt}/{MAX_ATTEMPTS})')
                else:
                    wait = min(cd, 60)
                    print(f'[LLM] 429 — 1 key no pool, aguardando cooldown {wait}s (tentativa {_attempt}/{MAX_ATTEMPTS})')
            else:
                wait = min(cd, 60)
                print(f'[LLM] 429 — aguardando {wait}s (tentativa {_attempt}/{MAX_ATTEMPTS})')
            _time.sleep(wait)

        except anthropic.APIStatusError as e:
            if e.status_code in (529, 503, 502):
                if _ia and _key_id:
                    _ia.mark_failure(_key_id, f'{e.status_code} overloaded', 30)
                # Cascade: troca modelo ao invés de dormir
                if _cascade_idx + 1 < len(_cascade):
                    _cascade_idx += 1
                    _current_model = _cascade[_cascade_idx]
                    wait = min(5 * _cascade_idx, 15)
                    print(f'[LLM] {e.status_code} Cascade: {model_id} → {_current_model} (pos {_cascade_idx}/{len(_cascade)-1})')
                else:
                    wait = min(20 * _attempt, 60)
                    print(f'[LLM] {e.status_code} Cascade esgotada, aguardando {wait}s (tentativa {_attempt}/{MAX_ATTEMPTS})')
                _time.sleep(wait)
            elif e.status_code == 400:
                print(f'[LLM] 400 Bad Request (tentativa {_attempt}/{MAX_ATTEMPTS})')
                if _attempt < MAX_ATTEMPTS:
                    _time.sleep(5 * _attempt)
                else:
                    raise
            elif e.status_code in (401, 403):
                if _ia and _key_id:
                    _ia.mark_failure(_key_id, f'{e.status_code} auth', 600)
                    _ia.raise_alert('key_invalid', _key_id, f'{e.status_code} — key pode estar invalida', lead_id=None, user_id=_current_user_id)
                raise
            else:
                raise

    # Esgotou tentativas
    if _ia:
        _ia.raise_alert('all_keys_failed', _key_id, 'Todas as tentativas de call_claude falharam', lead_id=None, user_id=_current_user_id)
    raise RuntimeError(f"[LLM] Falhou apos {MAX_ATTEMPTS} tentativas")


def _extract_text_from_tool_use(response, client, model_id, max_tokens, temperature, system, user, extra_headers):
    """Proxy aibee.cloud workaround: extrai texto de tool_use blocks fantasma."""
    for block in response.content:
        if block.type == "tool_use":
            inp = block.input
            if isinstance(inp, dict):
                for key in ['text', 'content', 'response', 'message', 'output', 'html', 'code']:
                    if key in inp and isinstance(inp[key], str) and len(inp[key]) > 50:
                        print(f"[LLM] Recuperado de tool_use.input.{key}")
                        return inp[key]
            elif isinstance(inp, str) and len(inp) > 50:
                return inp

    # Retry sem cache — forçar nova geração
    import uuid as _uuid
    for retry in range(1, 4):
        _time.sleep(2 * retry)
        _fallback_model = 'claude-sonnet-4-6'
        print(f'[LLM] Retry {retry}/3 - Fallback Sonnet (tool_use workaround)')
        _cache_bust = f"\n\n[{_uuid.uuid4().hex[:8]}]"
        system_clean = system + _cache_bust if isinstance(system, str) else system

        try:
            resp2 = client.messages.create(
                model=_fallback_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=[{"type": "text", "text": system_clean}] if isinstance(system_clean, str) else system_clean,
                messages=[{"role": "user", "content": user}],
            )
            for block in resp2.content:
                if block.type == "text" and block.text.strip():
                    return block.text
            for block in resp2.content:
                if block.type == "tool_use":
                    inp = block.input
                    if isinstance(inp, dict):
                        for key in ['text', 'content', 'response', 'message', 'output', 'html', 'code']:
                            if key in inp and isinstance(inp[key], str) and len(inp[key]) > 50:
                                print(f"[LLM] Retry {retry}: recuperado de tool_use.input.{key}")
                                return inp[key]
                    elif isinstance(inp, str) and len(inp) > 50:
                        return inp
        except Exception as e:
            print(f"[LLM] Retry {retry} falhou: {e}")

    print(f"[LLM] ERRO: nenhum bloco text encontrado apos 3 retries")
    raise RuntimeError("[LLM] Proxy retornou tool_use sem texto apos 3 retries")


# ══════════════════════════════════════════════════════════════════
# CALL CLAUDE STRUCTURED — tool_use forçado para JSON
# ══════════════════════════════════════════════════════════════════
def call_claude_structured(system, user, tool_name, tool_description, input_schema, model='opus', max_tokens=8000, temperature=0.7):
    """Chama Claude com tool_use para forcar retorno de JSON estruturado."""
    model_map = {
        'opus': 'claude-opus-4-7',
        'sonnet': 'claude-sonnet-4-6',
        'haiku': 'claude-haiku-4-5',
    }
    model_id = model_map.get(model, model_map['opus'])

    _api_key, _base, _key_id = _resolve_anthropic()

    # Prompt caching no system
    extra_headers = {}
    if system and len(system) >= 1024:
        system_payload = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        extra_headers["anthropic-beta"] = "prompt-caching-2024-07-31"
    else:
        system_payload = [{"type": "text", "text": system}] if system else []

    try:
        import ia_manager as _ia
    except Exception:
        _ia = None

    for _attempt in range(1, 4):
        _enforce_call_spacing()
        client = _create_client(_api_key, _base)
        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_payload,
                messages=[{"role": "user", "content": user}],
                tools=[{
                    "name": tool_name,
                    "description": tool_description,
                    "input_schema": input_schema,
                }],
                tool_choice={"type": "tool", "name": tool_name},
                extra_headers=extra_headers if extra_headers else None,
            )

            # Log usage
            usage = response.usage
            input_tokens = usage.input_tokens
            output_tokens = usage.output_tokens
            cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
            cache_created = getattr(usage, 'cache_creation_input_tokens', 0) or 0
            if cache_read or cache_created:
                print(f"[LLM Structured] stop={response.stop_reason} in={input_tokens} out={output_tokens} cache_read={cache_read} cache_created={cache_created}")
            else:
                print(f"[LLM Structured] stop={response.stop_reason} in={input_tokens} out={output_tokens}")

            _salvar_uso_llm(model_id, input_tokens, output_tokens, f"structured_{tool_name}")

            if _ia and _key_id:
                _ia.mark_success(_key_id)

            # Extract tool_use input
            for block in response.content:
                if block.type == "tool_use" and block.name == tool_name:
                    return block.input

            # Fallback: any tool_use block
            for block in response.content:
                if block.type == "tool_use":
                    return block.input

            raise RuntimeError(f"[LLM Structured] Nenhum tool_use block na resposta (stop={response.stop_reason})")

        except anthropic.RateLimitError as e:
            cd = 60
            if _ia:
                try:
                    cd = _ia.parse_cooldown_from_response(429, dict(e.response.headers) if e.response else {})
                except Exception:
                    pass
            if _ia and _key_id:
                _ia.mark_failure(_key_id, '429 rate limit', cd)
                _ia.raise_alert('rate_limit', _key_id, f'429 em call_claude_structured (cooldown {cd}s)', lead_id=None, user_id=_current_user_id)
            if _attempt >= 3:
                raise RateLimitError(reset_seconds=cd)
            _api_key, _base, _key_id = _resolve_anthropic()
            wait = min(15 * _attempt, 30)
            print(f'[LLM Structured] 429 — trocando key, aguardando {wait}s (tentativa {_attempt}/3)')
            _time.sleep(wait)

        except anthropic.APIStatusError as e:
            if e.status_code in (401, 403) and _ia and _key_id:
                _ia.mark_failure(_key_id, f'{e.status_code} auth', 600)
                _ia.raise_alert('key_invalid', _key_id, f'{e.status_code} em call_claude_structured', lead_id=None, user_id=_current_user_id)
            raise

    raise RuntimeError("[LLM Structured] Falhou apos 3 tentativas")


# ══════════════════════════════════════════════════════════════════
# CALL CLAUDE JSON — structured output com parsing robusto
# ══════════════════════════════════════════════════════════════════
import re as _re


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` fences."""
    text = text.strip()
    if text.startswith("```"):
        text = _re.sub(r"^```\w*\n?", "", text)
        text = _re.sub(r"\n?```$", "", text)
    return text.strip()


def call_claude_json(
    system: str,
    user: str,
    model: str = "sonnet",
    max_tokens: int = 4096,
    temperature: float = 0.5,
    agent_name: str = None,
    output_model=None,
    retries: int = 2,
) -> dict:
    """Chama Claude e retorna JSON parseado. Retry automático em parse failure.

    Args:
        output_model: Pydantic BaseModel class (opcional). Se passado, valida e retorna instância.
        retries: Tentativas extras em caso de JSON inválido.

    Returns:
        dict (ou instância Pydantic se output_model passado)
    """
    json_instruction = "\n\nResponda EXCLUSIVAMENTE com JSON válido. Sem markdown, sem texto antes ou depois."
    full_system = system + json_instruction

    last_error = None
    for attempt in range(1, retries + 2):
        try:
            raw = call_claude(
                system=full_system,
                user=user,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                agent_name=agent_name,
            )
            clean = _strip_markdown_fences(raw)
            parsed = json.loads(clean)

            if output_model:
                return output_model.model_validate(parsed)
            return parsed

        except (json.JSONDecodeError, Exception) as e:
            last_error = e
            if attempt <= retries:
                print(f"[LLM JSON] Parse falhou (tentativa {attempt}/{retries+1}): {e}")
                _time.sleep(2 * attempt)
            else:
                break

    raise RuntimeError(f"[LLM JSON] JSON parse falhou apos {retries+1} tentativas: {last_error}")


# ══════════════════════════════════════════════════════════════════
# CALL CLAUDE STREAM — streaming com callback (Fase 4)
# ══════════════════════════════════════════════════════════════════
def call_claude_stream(
    system: str,
    user: str,
    model: str = "opus",
    max_tokens: int = 16384,
    temperature: float = 0.7,
    agent_name: str = None,
    on_chunk: callable = None,
) -> str:
    """Streaming com callback por chunk. Retorna texto completo ao final."""

    # ── Model routing (simplificado — sem RAG/Skills para streaming) ──
    _db_config = None
    if agent_name:
        _all_configs = _load_agent_configs()
        _db_config = _all_configs.get(agent_name.lower())

    if _db_config:
        model_id = _db_config['model_id']
        if _db_config.get('temperature') is not None:
            temperature = _db_config['temperature']
        if _db_config.get('max_tokens') is not None:
            max_tokens = _db_config['max_tokens']
    else:
        model_id = MODEL_MAP.get(model, MODEL_MAP['opus'])

    _api_key, _base, _key_id = _resolve_anthropic()

    # Prompt caching
    extra_headers = {}
    if system and len(system) >= 1024:
        system_payload = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        extra_headers["anthropic-beta"] = "prompt-caching-2024-07-31"
    else:
        system_payload = [{"type": "text", "text": system}] if system else []

    _enforce_call_spacing()
    client = _create_client(_api_key, _base)

    full_text = ""
    with client.messages.stream(
        model=model_id,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_payload,
        messages=[{"role": "user", "content": user}],
        extra_headers=extra_headers if extra_headers else None,
    ) as stream:
        for text in stream.text_stream:
            full_text += text
            if on_chunk:
                on_chunk(text)

    # Log usage do stream
    response = stream.get_final_message()
    usage = response.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
    cache_created = getattr(usage, 'cache_creation_input_tokens', 0) or 0
    if cache_read or cache_created:
        print(f"[LLM Stream] stop={response.stop_reason} in={input_tokens} out={output_tokens} cache_read={cache_read}")
    else:
        print(f"[LLM Stream] stop={response.stop_reason} in={input_tokens} out={output_tokens}")
    _salvar_uso_llm(model_id, input_tokens, output_tokens, agent_name)

    if _key_id:
        try:
            import ia_manager as _ia
            _ia.mark_success(_key_id)
        except Exception:
            pass

    return full_text


# ══════════════════════════════════════════════════════════════════
# CALL CLAUDE CACHED — explicit prompt caching (Fase 5)
# ══════════════════════════════════════════════════════════════════
def call_claude_cached(
    system: str,
    user: str,
    model: str = "sonnet",
    max_tokens: int = 4096,
    temperature: float = 0.7,
    agent_name: str = None,
    cache_user_prefix: str = None,
) -> str:
    """Chamada com prompt caching explícito. Cacheia system + opcionalmente prefixo do user.

    Args:
        cache_user_prefix: Se passado, este texto é cacheado como primeiro bloco do user message.
    """
    _api_key, _base, _key_id = _resolve_anthropic()

    model_id = MODEL_MAP.get(model, MODEL_MAP['opus'])

    system_payload = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

    if cache_user_prefix:
        messages_content = [
            {"type": "text", "text": cache_user_prefix, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": user},
        ]
    else:
        messages_content = user

    extra_headers = {"anthropic-beta": "prompt-caching-2024-07-31"}

    _enforce_call_spacing()
    client = _create_client(_api_key, _base)

    response = client.messages.create(
        model=model_id,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_payload,
        messages=[{"role": "user", "content": messages_content}],
        extra_headers=extra_headers,
    )

    usage = response.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
    cache_created = getattr(usage, 'cache_creation_input_tokens', 0) or 0
    print(f"[LLM Cached] in={input_tokens} out={output_tokens} cache_read={cache_read} cache_created={cache_created}")
    _salvar_uso_llm(model_id, input_tokens, output_tokens, agent_name)

    for block in response.content:
        if block.type == "text":
            return block.text

    raise RuntimeError("[LLM Cached] Nenhum bloco text na resposta")

