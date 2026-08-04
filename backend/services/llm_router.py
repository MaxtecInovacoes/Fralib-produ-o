"""
llm_router — Router universal multi-provider.

Suporta: Anthropic, OpenAI, Google Gemini, Groq.
Cada provider tem seu adaptador. O call_claude existente continua funcionando
(chama este router internamente quando provider != anthropic).

Uso:
    from services.llm_router import call_llm
    text, usage = call_llm('openai', 'gpt-4o', system, user, 0.7, 4000)
"""
import os
import time
import requests

# Base URLs padrão por provider
_BASE_URLS = {
    'anthropic': os.getenv('ANTHROPIC_BASE_URL', 'https://api.aibee.cloud'),
    'openai': 'https://api.openai.com/v1',
    'google': 'https://generativelanguage.googleapis.com/v1beta',
    'groq': 'https://api.groq.com/openai/v1',
}


def _get_key_for_provider(provider: str):
    """Busca key do provider via ia_manager ou .env."""
    try:
        import sys
        sys.path.insert(0, '/root/fralib/backend/services')
        import ia_manager
        result = ia_manager.pick_key(provider)
        if result:
            key, base, key_id = result[0], result[1], result[2]
            # Sempre usar base_url canônico; DB pode ter URL inválida
            base = _BASE_URLS.get(provider, base)
            return key, base, key_id
    except Exception as e:
        print(f"[llm_router] ia_manager falhou para {provider}: {e}")

    # Fallback .env
    env_map = {
        'anthropic': 'ANTHROPIC_API_KEY',
        'openai': 'OPENAI_API_KEY',
        'google': 'GOOGLE_API_KEY',
        'groq': 'GROQ_API_KEY',
    }
    key = os.getenv(env_map.get(provider, ''), '')
    base = _BASE_URLS.get(provider, '')
    return key, base, None


def call_llm(provider: str, model_id: str, system: str, user: str,
             temperature: float = 0.7, max_tokens: int = 4000) -> tuple:
    """
    Router universal. Retorna (response_text, usage_dict).
    usage_dict: {'input_tokens': int, 'output_tokens': int}
    """
    provider = provider.lower()
    if provider == 'anthropic':
        return _call_anthropic(model_id, system, user, temperature, max_tokens)
    elif provider == 'openai':
        return _call_openai(model_id, system, user, temperature, max_tokens)
    elif provider == 'google':
        return _call_google(model_id, system, user, temperature, max_tokens)
    elif provider == 'groq':
        return _call_groq(model_id, system, user, temperature, max_tokens)
    else:
        # Custom OpenAI-compatible
        return _call_openai(model_id, system, user, temperature, max_tokens, provider=provider)


def _call_anthropic(model_id, system, user, temperature, max_tokens):
    """Adaptador Anthropic (Messages API)."""
    api_key, base_url, key_id = _get_key_for_provider('anthropic')
    if not api_key:
        raise Exception("Nenhuma API key Anthropic disponível")

    url = f"{base_url}/v1/messages"
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': model_id,
        'max_tokens': max_tokens,
        'temperature': temperature,
        'system': system,
        'messages': [{'role': 'user', 'content': user}],
    }

    _CASCADE_ORDER = [
        'claude-opus-5', 'claude-opus-4-8', 'claude-opus-4-7',
        'claude-sonnet-5', 'claude-sonnet-4-6', 'claude-sonnet-4-5',
        'claude-haiku-5', 'claude-haiku-4-5',
    ]
    _cascade_idx = 0
    _cascade_model = model_id
    last_exc = None

    while _cascade_idx < len(_CASCADE_ORDER):
        _cascade_model = _CASCADE_ORDER[_cascade_idx]
        try:
            text_out, usage = _try_anthropic_call(
                _cascade_model, system, user, temperature, max_tokens,
                api_key, base_url,
            )
            if _cascade_idx > 0:
                print(f'[llm_router] Cascade: {model_id} → {_cascade_model} (ok)')
            return text_out, usage
        except requests.exceptions.HTTPError as e:
            last_exc = e
            status = e.response.status_code if e.response else 0
            body = ''
            try:
                body = e.response.text[:200] if e.response else ''
            except Exception:
                pass
            if status in (529, 503, 502, 429):
                _cascade_idx += 1
                wait = min(5 * _cascade_idx, 15)
                print(f'[llm_router] {status} Cascade: tentando {_cascade_model} → próxima (idx {_cascade_idx})')
                time.sleep(wait)
                continue
            if status in (401, 403):
                raise Exception(f"Auth error {status}: {body}") from None
            raise
        except Exception as e:
            last_exc = e
            _cascade_idx += 1
            time.sleep(2)
            continue

    raise Exception(f"Todos os modelos da cascata falharam. Último erro: {last_exc}") from last_exc


def _try_anthropic_call(model_id, system, user, temperature, max_tokens, api_key, base_url):
    """Single Anthropic call. Raises on non-2xx."""
    url = f"{base_url}/v1/messages"
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': model_id,
        'max_tokens': max_tokens,
        'temperature': temperature,
        'system': system,
        'messages': [{'role': 'user', 'content': user}],
    }
    r = requests.post(url, headers=headers, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()

    text_out = ''
    for block in data.get('content', []):
        if block.get('type') == 'text':
            text_out = block['text']
            break

    usage = data.get('usage', {})
    return text_out, {
        'input_tokens': usage.get('input_tokens', 0),
        'output_tokens': usage.get('output_tokens', 0),
    }


def _call_openai(model_id, system, user, temperature, max_tokens, provider='openai'):
    """Adaptador OpenAI / OpenAI-compatible (Groq usa mesmo formato)."""
    api_key, base_url, key_id = _get_key_for_provider(provider)
    if not api_key:
        raise Exception(f"Nenhuma API key {provider} disponível")

    url = f"{base_url}/chat/completions"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': model_id,
        'max_tokens': max_tokens,
        'temperature': temperature,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
    }

    r = requests.post(url, headers=headers, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()

    text_out = data.get('choices', [{}])[0].get('message', {}).get('content', '')
    usage = data.get('usage', {})
    return text_out, {
        'input_tokens': usage.get('prompt_tokens', 0),
        'output_tokens': usage.get('completion_tokens', 0),
    }


def _call_google(model_id, system, user, temperature, max_tokens):
    """Adaptador Google Gemini (generateContent)."""
    api_key, _, key_id = _get_key_for_provider('google')
    if not api_key:
        raise Exception("Nenhuma API key Google disponível")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        'contents': [{'parts': [{'text': user}]}],
        'systemInstruction': {'parts': [{'text': system}]},
        'generationConfig': {
            'temperature': temperature,
            'maxOutputTokens': max_tokens,
        },
    }

    r = requests.post(url, headers=headers, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()

    text_out = ''
    try:
        text_out = data['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError):
        pass

    usage_meta = data.get('usageMetadata', {})
    return text_out, {
        'input_tokens': usage_meta.get('promptTokenCount', 0),
        'output_tokens': usage_meta.get('candidatesTokenCount', 0),
    }


def _call_groq(model_id, system, user, temperature, max_tokens):
    """Adaptador Groq (OpenAI-compatible)."""
    return _call_openai(model_id, system, user, temperature, max_tokens, provider='groq')
