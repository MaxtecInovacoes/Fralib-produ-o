"""
llm_router — Router universal multi-provider.

Suporta: Anthropic, OpenAI, Google Gemini, Groq e OpenRouter.
Cada provider tem seu adaptador. O call_claude existente continua funcionando
(chama este router internamente quando provider != anthropic).

Uso:
    from services.llm_router import call_llm
    text, usage = call_llm('openai', 'gpt-4o', system, user, 0.7, 4000)
"""

import os
import time
import logging
import requests
from dotenv import load_dotenv
from requests.exceptions import RequestException, HTTPError

logger = logging.getLogger("llm_router")


for _env_candidate in (
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")),
):
    if os.path.exists(_env_candidate):
        load_dotenv(dotenv_path=_env_candidate, override=False)
        break


def _retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    retry_on_status: tuple = (429, 500, 502, 503, 504),
):
    """
    Executa função com retry e exponential backoff.

    Args:
        func: Função a executar
        max_retries: Número máximo de tentativas
        base_delay: Delay inicial em segundos
        max_delay: Delay máximo em segundos
        retry_on_status: Códigos HTTP que triggers retry
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except HTTPError as e:
            last_exception = e
            status_code = e.response.status_code if e.response else 0
            if status_code not in retry_on_status:
                raise # Não retry para erros 4xx (exceto 429)
            if attempt == max_retries:
                raise
        except RequestException as e:
            last_exception = e
            if attempt == max_retries:
                raise
        except Exception as e:
            last_exception = e
            raise

        # Exponential backoff
        delay = min(base_delay * (2 ** attempt), max_delay)
        # Adiciona jitter aleatório (0-25% do delay)
        import random
        delay = delay * (1 + random.random() * 0.25)

        print(f"[LLMRouter] Retry {attempt + 1}/{max_retries} após {delay:.1f}s")
        time.sleep(delay)

    raise last_exception

# Base URLs padrão por provider
_BASE_URLS = {
    "anthropic": os.getenv("ANTHROPIC_BASE_URL", "https://api.kpalabz.com/v1"),
    "openai": "https://api.openai.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta",
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com",
    "moonshot": "https://api.moonshot.cn/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}


def _canonical_anthropic_base_url(base_url: str | None) -> str:
    base = (base_url or "").rstrip("/")
    if "api.aibee.cloud" in base.lower():
        return os.getenv("FRALIB_ANTHROPIC_CANONICAL_BASE_URL", "https://api.kpalabz.com/v1").rstrip("/")
    return base


def _get_key_for_provider(provider: str):
    """Busca key do provider via ia_manager ou .env."""
    if provider == "anthropic" and os.getenv("FRALIB_BUILDER_FORCE_ENV_ANTHROPIC", "").strip().lower() in {"1", "true", "yes", "on"}:
        if os.getenv("LITELLM_API_KEY"):
            return (
                os.getenv("LITELLM_API_KEY", ""),
                os.getenv("LITELLM_BASE_URL", os.getenv("ANTHROPIC_BASE_URL", "https://api.kpalabz.com/v1")),
                None,
            )
        return (
            os.getenv("ANTHROPIC_API_KEY", ""),
            os.getenv("ANTHROPIC_BASE_URL", _BASE_URLS.get("anthropic", "")),
            None,
        )
    if provider == "anthropic" and os.getenv("LITELLM_API_KEY"):
        return (
            os.getenv("LITELLM_API_KEY", ""),
            os.getenv("LITELLM_BASE_URL", os.getenv("ANTHROPIC_BASE_URL", "https://api.kpalabz.com/v1")),
            None,
        )
    if provider == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
        return (
            os.getenv("ANTHROPIC_API_KEY", ""),
            os.getenv("ANTHROPIC_BASE_URL", _BASE_URLS.get("anthropic", "")),
            None,
        )

    try:
        import sys

        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import ia_manager

        result = ia_manager.pick_key(provider)
        if result:
            key, base, key_id = result[0], result[1], result[2]
            # Garantir base_url padrão se não veio do DB
            if not base:
                base = _BASE_URLS.get(provider, "")
            return key, base, key_id
    except Exception as e:
        print(f"[llm_router] ia_manager falhou para {provider}: {e}")

    # Fallback .env
    env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "moonshot": "MOONSHOT_API_KEY",
        "qwen": "QWEN_API_KEY",
    }
    key = os.getenv(env_map.get(provider, ""), "")
    base = _BASE_URLS.get(provider, "")
    return key, base, None


def call_llm(
    provider: str,
    model_id: str,
    system: str,
    user: str,
    temperature: float = 0.7,
    max_tokens: int = 4000,
) -> tuple:
    """
    Router universal. Retorna (response_text, usage_dict).
    usage_dict: {'input_tokens': int, 'output_tokens': int}
    """
    provider = provider.lower()
    if provider == "anthropic":
        return _call_anthropic(model_id, system, user, temperature, max_tokens)
    elif provider == "openai":
        return _call_openai(model_id, system, user, temperature, max_tokens)
    elif provider == "google":
        return _call_google(model_id, system, user, temperature, max_tokens)
    elif provider == "groq":
        return _call_groq(model_id, system, user, temperature, max_tokens)
    elif provider == "openrouter":
        return _call_openrouter(model_id, system, user, temperature, max_tokens)
    else:
        # Custom OpenAI-compatible
        return _call_openai(
            model_id, system, user, temperature, max_tokens, provider=provider
        )


def _join_url(base_url: str, suffix: str) -> str:
    """Join a base URL and suffix, deduplicating the ``/v1`` segment.

    Some providers (kpalabz, litellm proxies) already expose a ``/v1`` base
    URL while the OpenAI/Anthropic SDKs (and our hand-rolled adapters) append
    ``/v1/messages`` or ``/v1/chat/completions``. A naive ``f"{base}/{suffix}"``
    produces ``https://api.kpalabz.com/v1/v1/messages`` (404) instead of
    the correct ``https://api.kpalabz.com/v1/messages``.

    This helper strips a trailing ``/v1`` from ``base_url`` when ``suffix``
    begins with ``/v1``, then concatenates the two with a single ``/``.
    """
    base = (base_url or "").rstrip("/")
    if suffix.startswith("/v1/") and base.endswith("/v1"):
        base = base[: -len("/v1")]
    if not suffix.startswith("/"):
        suffix = "/" + suffix
    return base + suffix


def _call_anthropic(model_id, system, user, temperature, max_tokens):
    """Adaptador Anthropic (Messages API)."""
    api_key, base_url, key_id = _get_key_for_provider("anthropic")
    if not api_key:
        raise Exception("Nenhuma API key Anthropic disponível")
    base_url = _canonical_anthropic_base_url(base_url)

    url = _join_url(base_url, "/v1/messages")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_id,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    # FIX: Never include "tools" in payload — proxy returns tool_use ghost responses
    payload.pop("tools", None)

    r = _retry_with_backoff(
        lambda: requests.post(url, headers=headers, json=payload, timeout=300)
    )
    r.raise_for_status()
    data = r.json()

    text_out = _extract_proxy_text(data.get("content"))

    # Fallback: extract text from tool_use ghost blocks (proxy bug)
    if not text_out:
        for block in _normalize_proxy_blocks(data.get("content")):
            if block.get("type") == "tool_use":
                inp = block.get("input", {})
                if isinstance(inp, dict):
                    for key in ("text", "content", "response", "html", "output"):
                        if (
                            key in inp
                            and isinstance(inp[key], str)
                            and len(inp[key]) > 50
                        ):
                            text_out = inp[key]
                            break
                elif isinstance(inp, str) and len(inp) > 50:
                    text_out = inp
            if text_out:
                break

    usage = data.get("usage", {})
    return text_out, {
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
    }


def _normalize_proxy_blocks(content):
    if isinstance(content, list):
        return [block for block in content if isinstance(block, dict)]
    if isinstance(content, dict):
        received = content.get("received")
        if isinstance(received, dict):
            return _normalize_proxy_blocks(received.get("content") or received.get("blocks"))
        blocks = content.get("content") or content.get("blocks")
        return _normalize_proxy_blocks(blocks)
    return []


def _extract_proxy_text(content):
    if isinstance(content, str):
        return content
    parts = []
    for block in _normalize_proxy_blocks(content):
        if block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text)
        if block.get("type") == "message":
            nested = _extract_proxy_text(block.get("content"))
            if nested:
                parts.append(nested)
    if parts:
        return "".join(parts)
    if isinstance(content, dict):
        for key in ("text", "content", "response", "html", "output"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return ""


def _call_openai(model_id, system, user, temperature, max_tokens, provider="openai"):
    """Adaptador OpenAI / OpenAI-compatible (Groq usa mesmo formato)."""
    api_key, base_url, key_id = _get_key_for_provider(provider)
    if not api_key:
        raise Exception(f"Nenhuma API key {provider} disponível")

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers.update({
            "HTTP-Referer": os.getenv("FRALIB_PUBLIC_URL", "https://seunegociofralib.site"),
            "X-Title": os.getenv("FRALIB_APP_TITLE", "FraLib"),
        })
    payload = {
        "model": model_id,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }

    r = _retry_with_backoff(
        lambda: requests.post(url, headers=headers, json=payload, timeout=300)
    )
    r.raise_for_status()
    data = r.json()

    message = data.get("choices", [{}])[0].get("message", {}) or {}
    text_out = _extract_openai_message_content(message.get("content"))
    usage = data.get("usage", {})
    return text_out, {
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
    }


def _extract_openai_message_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text)
                continue
            nested = item.get("content")
            if isinstance(nested, str) and nested.strip():
                parts.append(nested)
        return "".join(parts).strip()
    if isinstance(content, dict):
        for key in ("text", "content", "response", "html", "output"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return ""


def _call_google(model_id, system, user, temperature, max_tokens):
    """Adaptador Google Gemini (generateContent)."""
    api_key, _, key_id = _get_key_for_provider("google")
    if not api_key:
        raise Exception("Nenhuma API key Google disponível")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": user}]}],
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }

    r = requests.post(url, headers=headers, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()

    text_out = ""
    try:
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        # FIX: Silent failure - não avisava ninguém sobre resposta malformada
        # Agora loga o erro para detectar problemas
        logger.warning(
            f"[LLMRouter] Gemini response formato inesperado. "
            f"Esperava data['candidates'][0]['content']['parts'][0]['text']. "
            f"Recebido keys: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}. "
            f"Erro: {e}"
        )
        # FIX: Retorna erro descritivo ao invés de string vazia
        # Caller pode detectar e fazer fallback
        text_out = "[LLMRouter ERROR: Gemini response formato inesperado - ver logs]"

    usage_meta = data.get("usageMetadata", {})
    return text_out, {
        "input_tokens": usage_meta.get("promptTokenCount", 0),
        "output_tokens": usage_meta.get("candidatesTokenCount", 0),
    }


def _call_groq(model_id, system, user, temperature, max_tokens):
    """Adaptador Groq (OpenAI-compatible)."""
    return _call_openai(
        model_id, system, user, temperature, max_tokens, provider="groq"
    )


def _call_openrouter(model_id, system, user, temperature, max_tokens):
    """Adaptador OpenRouter (OpenAI-compatible chat completions)."""
    return _call_openai(
        model_id, system, user, temperature, max_tokens, provider="openrouter"
    )
