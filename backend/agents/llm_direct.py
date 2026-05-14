import os
import requests
import json
from dotenv import load_dotenv


class RateLimitError(Exception):
    """Exceção quando API atinge rate limit após todas as tentativas."""
    def __init__(self, reset_seconds: int = 0):
        self.reset_seconds = reset_seconds
        if reset_seconds > 60:
            tempo = f"{reset_seconds // 60}min {reset_seconds % 60}s"
        else:
            tempo = f"{reset_seconds}s"
        super().__init__(f"Limite de uso atingido. Sera resetado em: {tempo}")

# Carregar .env — tenta multiplos caminhos para garantir que encontra
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
    load_dotenv()  # fallback

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ANTHROPIC_BASE_URL = os.getenv('ANTHROPIC_BASE_URL', 'https://api.aibee.cloud')

# Contexto de usuario ativo (setado pelo pipeline antes de rodar)
_current_user_id = None

def set_current_user_id(uid):
    global _current_user_id
    _current_user_id = uid


# PR8: BYOK - cliente Pro usa a propria Anthropic key.
# Cache em memoria por user_id pra evitar bater no banco a cada chamada LLM.
_byok_cache = {}

def _get_byok_key():
    """Retorna a key BYOK do user Pro atual, ou None se nao houver."""
    uid = _current_user_id
    if not uid:
        return None
    if uid in _byok_cache:
        return _byok_cache[uid]
    try:
        import psycopg2
        from utils.secrets_crypto import decriptar
        conn = psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://postgres:fralib2024@localhost:5433/fralib_db'))
        cur = conn.cursor()
        cur.execute('SELECT plano, anthropic_key_encrypted FROM users WHERE id=%s', (uid,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and (row[0] or '').lower() == 'pro' and row[1]:
            key = decriptar(row[1])
            _byok_cache[uid] = key or None
            return _byok_cache[uid]
        _byok_cache[uid] = None
    except Exception as e:
        print(f'[llm_direct] BYOK lookup falhou para user {uid}: {e}')
    return None


def _resolve_anthropic():
    """Retorna (api_key, base_url, key_id_or_None).

    Prioridade:
    1. BYOK do user Pro ativo (key dele propria, sem failover).
    2. Round-robin via ia_manager entre keys cadastradas no superadmin.
    3. Fallback pro .env (ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL).
    """
    byok = _get_byok_key()
    if byok:
        return (byok, ANTHROPIC_BASE_URL, None)
    try:
        import ia_manager
        picked = ia_manager.pick_key('anthropic')
        if picked:
            return picked  # (key, base_url, id) ja com fallback .env interno
    except Exception as e:
        print(f'[llm_direct] ia_manager falhou, usando .env: {e}')
    return (ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, None)


# Compat: codigo legado pode importar _get_active_api_key.
def _get_active_api_key():
    return _resolve_anthropic()[0]

def invalidar_byok_cache(uid=None):
    """Chamar quando o cliente troca a key (ou cancela). uid=None limpa tudo."""
    global _byok_cache
    if uid is None:
        _byok_cache = {}
    else:
        _byok_cache.pop(uid, None)

def _salvar_uso_llm(modelo, input_tokens, output_tokens, agente=None):
    try:
        import psycopg2
        conn = psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://postgres:fralib2024@localhost:5433/fralib_db'))
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO llm_usage (modelo, input_tokens, output_tokens, agente, user_id) VALUES (%s, %s, %s, %s, %s)',
            (modelo, input_tokens, output_tokens, agente, _current_user_id)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f'[LLM Usage] Erro ao salvar: {e}')

def call_claude(system, user, model='opus', max_tokens=4000, temperature=0.7, agent_name=None, base_url=None):
    """
    Chama Claude API com suporte automático a RAG e Skills
    
    Args:
        system: System prompt
        user: User prompt
        model: 'opus', 'sonnet' ou 'haiku'
        max_tokens: Limite de tokens
        temperature: Temperatura (0.0-1.0)
        agent_name: Nome do agente (ex: 'Caio', 'Liam') - ativa RAG + Skills automaticamente
    
    Returns:
        Resposta do Claude
    """
    
    # ✅ AUTOMÁTICO: Se agent_name foi passado, ativar RAG + Skills
    # PR12: capturar rag_context cru para cachear separadamente (em vez de
    # fundir com user e perder a oportunidade de cache).
    rag_block = ""
    if agent_name:
        try:
            # 1. Importar funções (lazy import para não quebrar se não existir)
            from agent_rag import buscar_contexto_rag, format_rag_prompt, mark_rag_used
            from skill_loader import get_skills_agente, carregar_skills

            # 2. Buscar e injetar RAG
            rag_context = buscar_contexto_rag(user, agent_name.lower())
            if rag_context:
                # PR12: guarda o bloco RAG isolado para cachear; nao funde com user.
                # Formato igual ao format_rag_prompt para manter compatibilidade semantica.
                rag_block = f"CONTEXTO RAG (conhecimento da base):\n{rag_context}\n\n---\n\n"
                mark_rag_used(agent_name)
                print(f"[LLM Direct] ✅ RAG ativado para {agent_name} ({len(rag_block)} chars)")
            
            # 3. Buscar e injetar Skills
            skills = get_skills_agente(agent_name.lower())
            if skills:
                guidelines = carregar_skills(skills)
                if guidelines:
                    system = f"{system}\n\n{'='*60}\n# SKILLS ATIVADAS\n{'='*60}\n{guidelines}"
                    print(f"[LLM Direct] ✅ Skills ativadas para {agent_name}: {', '.join(skills)}")
        
        except Exception as e:
            print(f"[LLM Direct] ⚠️ Erro ao ativar RAG/Skills para {agent_name}: {e}")
            # Continua sem RAG/Skills se der erro
    
    # 4. Roteamento automático de modelo por agente
    # Haiku: tarefas simples/rápidas (Bryan mensagens, validações, checks)
    # Sonnet: tarefas médias (qualificação, briefing, SEO, follow-up)
    # Opus: tarefas complexas (geração de site completo, PRD, design system)
    _AGENT_MODEL_MAP = {
        # Haiku — respostas rápidas, sem raciocínio profundo
        'bryan':   'haiku',   # mensagens WhatsApp
        'liz':     'haiku',   # edições pontuais de HTML
        # Sonnet — qualificação e análise média
        # caio: zero LLM — Python puro, não entra no mapa
        'theo':    'sonnet',  # briefing e análise
        'alex':    'sonnet',  # cores e logos
        # Opus — geração criativa pesada
        'liam':    'opus',  # geração completa de site
        'arquiteto_mestre': 'sonnet',
        'designer_prd':     'sonnet',
    }
    if agent_name and model == 'opus':
        # Só faz override se o chamador não especificou modelo explicitamente
        _auto = _AGENT_MODEL_MAP.get(agent_name.lower())
        if _auto:
            model = _auto
            print(f"[LLM Router] {agent_name} -> {model}")

    model_map = {
        'opus': 'claude-opus-4-7',
        'sonnet': 'claude-sonnet-4-6',
        'haiku': 'claude-haiku-4-5'
    }

    model_id = model_map.get(model, model_map['opus'])
    
    # 5. Resolver key/base_url (BYOK > ia_manager > .env)
    if base_url:
        # Caller forcou base_url explicitamente — usa key default do .env / BYOK
        _api_key = _get_byok_key() or ANTHROPIC_API_KEY
        _key_id = None
        _base = base_url
    else:
        _api_key, _base, _key_id = _resolve_anthropic()
    url = f'{_base}/v1/messages'

    headers = {
        'x-api-key': _api_key,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json'
    }
    
    # Prompt caching: se system prompt >= 1024 chars, cachear automaticamente.
    # Economiza 80-90% dos tokens de input em chamadas repetidas do mesmo agente.
    # Minimo exigido pela Anthropic: 1024 tokens (~4096 chars para ser seguro, usamos 1024).
    extra_headers = {}
    cache_ativo = False
    if system and len(system) >= 1024:
        system_payload = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        cache_ativo = True
    else:
        system_payload = system

    # PR12: bloco RAG cacheado separadamente quando vale a pena (>= 1024 chars).
    # Em chamadas repetidas do mesmo agente sobre leads diferentes, o RAG se
    # repete - cachear economiza ate 90% dos tokens desse bloco.
    if rag_block and len(rag_block) >= 1024:
        messages_content = [
            {"type": "text", "text": rag_block, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": user},
        ]
        cache_ativo = True
    elif rag_block:
        # RAG pequeno: junta no user message sem cache (caso raro)
        messages_content = rag_block + user
    else:
        messages_content = user

    if cache_ativo:
        extra_headers = {"anthropic-beta": "prompt-caching-2024-07-31"}

    payload = {
        'model': model_id,
        'max_tokens': max_tokens,
        'temperature': temperature,
        'system': system_payload,
        'messages': [{'role': 'user', 'content': messages_content}]
    }

    # Mesclar headers extras (ex: prompt caching beta)
    if extra_headers:
        headers = {**headers, **extra_headers}

    import time as _llm_time
    try:
        import ia_manager as _ia
    except Exception:
        _ia = None

    response = None
    for _llm_attempt in range(1, 4):
        response = requests.post(url, headers=headers, json=payload, timeout=600)
        if response.status_code == 429:
            cd = _ia.parse_cooldown_from_response(429, dict(response.headers)) if _ia else 60
            if _ia and _key_id:
                _ia.mark_failure(_key_id, '429 rate limit', cd)
                _ia.raise_alert('rate_limit', _key_id,
                                f'429 em call_claude (cooldown {cd}s)',
                                lead_id=None, user_id=_current_user_id)
            if _llm_attempt >= 3:
                if _ia and _key_id is None:
                    _ia.raise_alert('all_keys_failed', None,
                                    'Todas as keys Anthropic estouraram 429 apos 3 tentativas',
                                    lead_id=None, user_id=_current_user_id)
                raise RateLimitError(reset_seconds=cd)
            # Pega proxima key e tenta de novo
            if base_url is None:
                _api_key, _base, _key_id = _resolve_anthropic()
                url = f'{_base}/v1/messages'
                headers['x-api-key'] = _api_key
            wait = min(15 * _llm_attempt, 30)
            print(f'[LLM] 429 — trocando key e aguardando {wait}s (tentativa {_llm_attempt}/3)...')
            _llm_time.sleep(wait)
            continue
        if response.status_code in (529, 503, 502):
            if _ia and _key_id:
                _ia.mark_failure(_key_id, f'{response.status_code} overloaded', 30)
            if base_url is None:
                _api_key, _base, _key_id = _resolve_anthropic()
                url = f'{_base}/v1/messages'
                headers['x-api-key'] = _api_key
            wait = 20 * _llm_attempt
            print(f'[LLM] {response.status_code} Proxy Overloaded - aguardando {wait}s (tentativa {_llm_attempt}/3)...')
            _llm_time.sleep(wait)
            continue
        if response.status_code == 400:
            print(f'[LLM] 400 Bad Request - payload pode ser grande demais, tentativa {_llm_attempt}/3')
            if _llm_attempt < 3:
                _llm_time.sleep(5 * _llm_attempt)
                continue
        if response.status_code >= 400:
            # 4xx que nao seja 429 = problema da request, nao da key. Nao penaliza.
            if _ia and _key_id and response.status_code in (401, 403):
                _ia.mark_failure(_key_id, f'{response.status_code} auth', 600)
                _ia.raise_alert('key_invalid', _key_id,
                                f'{response.status_code} retornado — key pode estar invalida',
                                lead_id=None, user_id=_current_user_id)
        response.raise_for_status()
        if _ia and _key_id:
            _ia.mark_success(_key_id)
        break
    else:
        # Esgotou as 3 tentativas sem break
        if _ia:
            _ia.raise_alert('all_keys_failed', _key_id,
                            'Todas as tentativas de call_claude falharam',
                            lead_id=None, user_id=_current_user_id)
        if response is not None:
            response.raise_for_status()

    data = response.json()
    stop_reason = data.get('stop_reason', '?')
    usage = data.get('usage', {})
    input_tokens = usage.get('input_tokens', 0)
    output_tokens = usage.get('output_tokens', 0)
    cache_read = usage.get('cache_read_input_tokens', 0)
    cache_created = usage.get('cache_creation_input_tokens', 0)
    if cache_read or cache_created:
        print(f"[LLM] stop_reason={stop_reason} input={input_tokens} output={output_tokens} cache_read={cache_read} cache_created={cache_created}")
    else:
        print(f"[LLM] stop_reason={stop_reason} input={input_tokens} output={output_tokens}")
    _salvar_uso_llm(model_id, input_tokens, output_tokens, agent_name)

    # O proxy aibee.cloud sempre adiciona bloco tool_use extra no final
    # Extrair texto IMEDIATAMENTE se houver bloco text (ignorar tool_use)
    for block in data.get('content', []):
        if block.get('type') == 'text':
            return block['text']

    # Sem bloco text — retry sem cache e sem tools (proxy pode estar cacheando tool_use)
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        retry_count += 1
        import time; time.sleep(2 * retry_count)
        print('[LLM] Retry ' + str(retry_count) + '/3 - sem bloco text, retentando')
        # Remover tools, tool_choice E cache_control para forcar nova geracao
        payload_retry = {k: v for k, v in payload.items() if k != 'tools' and k != 'tool_choice'}
        # Remover cache_control do system prompt
        if isinstance(payload_retry.get('system'), list):
            payload_retry['system'] = payload_retry['system'][0]['text'] if payload_retry['system'] else ''
        # Headers sem prompt-caching
        headers_retry = {k: v for k, v in headers.items() if 'beta' not in k.lower()}
        response2 = requests.post(url, headers=headers_retry, json=payload_retry, timeout=600)
        response2.raise_for_status()
        data = response2.json()
        stop_reason = data.get('stop_reason', '?')
        usage = data.get('usage', {})
        output_tokens = usage.get('output_tokens', 0)
        print('[LLM] Retry ' + str(retry_count) + ': stop=' + stop_reason + ' out=' + str(output_tokens))
        for block in data.get('content', []):
            if block.get('type') == 'text':
                return block['text']

    # Ultimo fallback: procurar qualquer bloco com chave 'text'
    for block in data.get('content', []):
        if 'text' in block:
            return block['text']

    # Ultimo fallback: tentar extrair texto do input do no_tool_available
    for block in data.get('content', []):
        if block.get('name') == 'no_tool_available':
            inp = block.get('input', {})
            if isinstance(inp, dict):
                # Tentar campos comuns onde o proxy pode ter colocado o texto
                for key in ['text', 'content', 'response', 'message', 'output']:
                    if key in inp and inp[key]:
                        print(f"[LLM] Recuperado de no_tool_available.input.{key}")
                        return str(inp[key])
            elif isinstance(inp, str) and inp:
                print("[LLM] Recuperado de no_tool_available.input (string)")
                return inp
    print(f"[LLM] ERRO: nenhum bloco text encontrado. content={data.get('content', [])}")
    return ""  


def call_claude_structured(system, user, tool_name, tool_description, input_schema, model='opus', max_tokens=8000, temperature=0.7):
    """
    Chama Claude com tool_use para forcar retorno de JSON estruturado exato.
    O Claude e obrigado a preencher o schema definido - sem texto livre.

    Args:
        system: System prompt
        user: User prompt
        tool_name: Nome da tool (ex: 'gerar_prd')
        tool_description: Descricao da tool
        input_schema: JSON Schema dict com os campos obrigatorios
        model: 'opus', 'sonnet' ou 'haiku'
        max_tokens: Limite de tokens
        temperature: Temperatura

    Returns:
        Dict com os campos retornados pelo Claude
    """
    model_map = {
        'opus': 'claude-opus-4-7',
        'sonnet': 'claude-sonnet-4-6',
        'haiku': 'claude-haiku-4-5'
    }
    model_id = model_map.get(model, model_map['opus'])

    _api_key, _base, _key_id = _resolve_anthropic()
    url = f'{_base}/v1/messages'
    headers = {
        'x-api-key': _api_key,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json'
    }

    # Prompt caching no system prompt (igual ao call_claude)
    if system and len(system) >= 1024:
        system_payload = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        headers["anthropic-beta"] = "prompt-caching-2024-07-31"
    else:
        system_payload = system

    payload = {
        'model': model_id,
        'max_tokens': max_tokens,
        'temperature': temperature,
        'system': system_payload,
        'tools': [{
            'name': tool_name,
            'description': tool_description,
            'input_schema': input_schema
        }],
        'tool_choice': {'type': 'tool', 'name': tool_name},
        'messages': [{'role': 'user', 'content': user}]
    }

    import time as _time_struct
    try:
        import ia_manager as _ia
    except Exception:
        _ia = None

    for _attempt in range(1, 4):
        response = requests.post(url, headers=headers, json=payload, timeout=600)
        if response.status_code == 429:
            cd = _ia.parse_cooldown_from_response(429, dict(response.headers)) if _ia else 60
            if _ia and _key_id:
                _ia.mark_failure(_key_id, '429 rate limit', cd)
                _ia.raise_alert('rate_limit', _key_id,
                                f'429 em call_claude_structured (cooldown {cd}s)',
                                lead_id=None, user_id=_current_user_id)
            if _attempt >= 3:
                raise RateLimitError(reset_seconds=cd)
            _api_key, _base, _key_id = _resolve_anthropic()
            url = f'{_base}/v1/messages'
            headers['x-api-key'] = _api_key
            wait = min(15 * _attempt, 30)
            print(f'[LLM Structured] 429 — trocando key e aguardando {wait}s (tentativa {_attempt}/3)...')
            _time_struct.sleep(wait)
            continue
        if response.status_code >= 400 and response.status_code in (401, 403):
            if _ia and _key_id:
                _ia.mark_failure(_key_id, f'{response.status_code} auth', 600)
                _ia.raise_alert('key_invalid', _key_id,
                                f'{response.status_code} em call_claude_structured',
                                lead_id=None, user_id=_current_user_id)
        response.raise_for_status()
        if _ia and _key_id:
            _ia.mark_success(_key_id)
        data = response.json()
        # Verificar se proxy retornou no_tool_available (falso tool_use)
        content_blocks = data.get('content', [])
        has_fake = any(b.get('name') == 'no_tool_available' for b in content_blocks)
        for block in content_blocks:
            if block.get('type') == 'tool_use' and block.get('name') == tool_name:
                return block['input']
        if has_fake and _attempt < 3:
            print(f'[LLM Structured] Proxy retornou no_tool_available, tentativa {_attempt}/3...')
            _time_struct.sleep(3 * _attempt)
            continue
        break
    raise ValueError(f'Claude nao retornou tool_use para {tool_name} apos 3 tentativas')
