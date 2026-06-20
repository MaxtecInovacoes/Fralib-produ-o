# llm_client.py — LLM SDK client and HTTP utilities
"""
Low-level client module for FraLib LLM client.
Handles SDK client creation, LiteLLM OpenAI chat, error handling, and tool_use extraction.
"""
from __future__ import annotations

import json
import os
import time as _time
import uuid as _uuid

import anthropic
import httpx

from backend.agents import llm_config
from backend.agents.llm_context import (
    _llm_context_value,
    _get_byok_key,
    _resolve_anthropic,
    get_current_user_id,
)


# ─────────────────────────────────────────────────────────────────
# SDK CLIENT FACTORY
# ─────────────────────────────────────────────────────────────────
def _create_client(api_key: str, base_url: str) -> anthropic.Anthropic:
    """Create an Anthropic SDK client.

    Args:
        api_key: API key to use
        base_url: Base URL for the API

    Returns:
        Configured Anthropic client
    """
    read_timeout = float(os.getenv("FRALIB_LLM_READ_TIMEOUT", "420"))
    if base_url and base_url.endswith("/v1"):
        base_url = base_url[:-3]
    return anthropic.Anthropic(
        api_key=api_key,
        base_url=base_url,
        max_retries=0,
        timeout=httpx.Timeout(connect=10.0, read=read_timeout, write=60.0, pool=10.0),
    )


# ─────────────────────────────────────────────────────────────────
# LITELLM OPENAI CHAT
# ─────────────────────────────────────────────────────────────────
def _is_litellm_openai_chat_base(base_url: str | None) -> bool:
    """Check if base URL is a LiteLLM OpenAI chat endpoint.

    Args:
        base_url: URL to check

    Returns:
        True if this is a LiteLLM OpenAI chat endpoint
    """
    if os.getenv("FRALIB_LITELLM_OPENAI_CHAT", "1").strip().lower() in {"0", "false", "no"}:
        return False
    base = (base_url or "").lower()
    return any(
        marker in base
        for marker in (
            "127.0.0.1:4000",
            "localhost:4000",
            "llm.seunegociofralib.site",
            "ia.namehost.com.br",
        )
    )


def _litellm_chat_url(base_url: str) -> str:
    """Build the chat completions URL from a base URL.

    Args:
        base_url: Base URL

    Returns:
        Full chat completions URL
    """
    base = (base_url or "").rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _call_litellm_openai_chat(
    *,
    api_key: str,
    base_url: str,
    model_id: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
) -> tuple[str, dict]:
    """Call LiteLLM via OpenAI-compatible chat completions API.

    Args:
        api_key: API key
        base_url: Base URL
        model_id: Model identifier
        system: System prompt
        user: User message
        temperature: Temperature setting
        max_tokens: Maximum tokens

    Returns:
        Tuple of (response_text, usage_dict)
    """
    read_timeout = float(os.getenv("FRALIB_LLM_READ_TIMEOUT", "420"))
    payload = {
        "model": model_id,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system or ""},
            {"role": "user", "content": user or ""},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(
        timeout=httpx.Timeout(connect=10.0, read=read_timeout, write=60.0, pool=10.0)
    ) as client:
        response = client.post(_litellm_chat_url(base_url), headers=headers, json=payload)
        response.raise_for_status()
    data = response.json()
    message = (data.get("choices") or [{}])[0].get("message") or {}
    text_out = message.get("content") or ""
    usage = data.get("usage") or {}
    return text_out, {
        "input_tokens": usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0,
        "output_tokens": usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0,
    }


# ─────────────────────────────────────────────────────────────────
# ERROR HANDLING & ALERTING
# ─────────────────────────────────────────────────────────────────
def _llm_error_status(error) -> int | None:
    """Extract HTTP status code from an error.

    Args:
        error: Exception object

    Returns:
        HTTP status code or None
    """
    status = getattr(error, "status_code", None)
    response = getattr(error, "response", None)
    if status is None and response is not None:
        status = getattr(response, "status_code", None)
    try:
        return int(status) if status is not None else None
    except Exception:
        return None


def _llm_error_text(error) -> str:
    """Extract human-readable error text from an exception.

    Args:
        error: Exception object

    Returns:
        Error message string
    """
    response = getattr(error, "response", None)
    text = getattr(response, "text", None) if response is not None else None
    if not text and response is not None:
        try:
            text = json.dumps(response.json(), ensure_ascii=False)
        except Exception:
            pass
    if not text:
        text = str(error)
    return " ".join(str(text).split())[:320]


def _llm_alert_type(status: int | None) -> str:
    """Determine alert type from HTTP status code.

    Args:
        status: HTTP status code

    Returns:
        Alert type string
    """
    if status in (401, 403):
        return "key_invalid"
    if status == 429:
        return "rate_limit"
    if status and status >= 500:
        return "all_keys_failed"
    return "test_failed"


def _alert_llm_provider_failure(
    provider: str,
    model_id: str,
    error,
    *,
    key_id: int | None = None,
    source: str = "call_claude",
    mark_env_fallback: bool = False,
) -> None:
    """Expose LLM provider failures in provider_alerts without leaking secrets.

    Args:
        provider: Provider name
        model_id: Model identifier
        error: Exception object
        key_id: Key ID for tracking
        source: Source of the failure
        mark_env_fallback: Whether key came from env fallback
    """
    try:
        import ia_manager as _ia
    except Exception:
        return

    status = _llm_error_status(error)
    alert_type = _llm_alert_type(status)
    cooldown = 600 if status in (401, 403) else 60 if status == 429 else 300
    if key_id is not None or mark_env_fallback:
        try:
            _ia.mark_failure(
                key_id,
                f"{status or type(error).__name__} provider failure",
                cooldown,
            )
        except Exception:
            pass

    status_label = f"HTTP {status}" if status else type(error).__name__
    message = (
        f"{source}: provider {provider}/{model_id} falhou com {status_label}. "
        f"{_llm_error_text(error)}"
    )
    if provider == "anthropic" and key_id is None:
        message += " Chave ativa veio do ambiente LiteLLM FraLib em ANTHROPIC_API_KEY."
    try:
        _ia.raise_alert(
            alert_type,
            key_id,
            message,
            lead_id=None,
            user_id=get_current_user_id(),
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────
# TOOL USE EXTRACTION — proxy aibee.cloud workaround
# ─────────────────────────────────────────────────────────────────
def _extract_text_from_tool_use(
    response,
    client,
    model_id: str,
    max_tokens: int,
    temperature: float,
    system,
    user,
    extra_headers: dict,
) -> str:
    """Proxy aibee.cloud workaround: extrai texto de tool_use blocks fantasma.

    Args:
        response: API response object
        client: Anthropic client
        model_id: Model identifier
        max_tokens: Max tokens setting
        temperature: Temperature setting
        system: System prompt
        user: User message
        extra_headers: Extra headers for request

    Returns:
        Extracted text

    Raises:
        RuntimeError: If no text found after retries
    """
    for block in response.content:
        if block.type == "tool_use":
            inp = block.input
            if isinstance(inp, dict):
                for key in [
                    "text",
                    "content",
                    "response",
                    "message",
                    "output",
                    "html",
                    "code",
                ]:
                    if key in inp and isinstance(inp[key], str) and len(inp[key]) > 50:
                        print(f"[LLM] Recuperado de tool_use.input.{key}")
                        return inp[key]
            elif isinstance(inp, str) and len(inp) > 50:
                return inp

    if llm_config.fallbacks_disabled():
        raise RuntimeError("[LLM] tool_use sem texto e fallback desativado em produção")

    # Retry sem cache — forçar nova geração
    for retry in range(1, 4):
        _time.sleep(2 * retry)
        _fallback_model = llm_config.PROXY_BUILDER_MODEL
        print(f"[LLM] Retry {retry}/3 - Fallback proxy builder model (tool_use workaround)")
        _cache_bust = f"\n\n[{_uuid.uuid4().hex[:8]}]"
        system_clean = system + _cache_bust if isinstance(system, str) else system

        try:
            resp2 = client.messages.create(
                model=_fallback_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=[{"type": "text", "text": system_clean}]
                if isinstance(system_clean, str)
                else system_clean,
                messages=[{"role": "user", "content": user}],
            )
            for block in resp2.content:
                if block.type == "text" and block.text.strip():
                    return block.text
            for block in resp2.content:
                if block.type == "tool_use":
                    inp = block.input
                    if isinstance(inp, dict):
                        for key in [
                            "text",
                            "content",
                            "response",
                            "message",
                            "output",
                            "html",
                            "code",
                        ]:
                            if (
                                key in inp
                                and isinstance(inp[key], str)
                                and len(inp[key]) > 50
                            ):
                                print(
                                    f"[LLM] Retry {retry}: recuperado de tool_use.input.{key}"
                                )
                                return inp[key]
                    elif isinstance(inp, str) and len(inp) > 50:
                        return inp
        except Exception as e:
            print(f"[LLM] Retry {retry} falhou: {e}")

    print(f"[LLM] ERRO: nenhum bloco text encontrado apos 3 retries")
    raise RuntimeError("[LLM] Proxy retornou tool_use sem texto apos 3 retries")
