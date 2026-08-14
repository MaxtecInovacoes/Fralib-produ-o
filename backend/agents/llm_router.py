"""
LLM Router — Seleção de provider, rate limiting, circuit breaker e adaptadores diretos.

Canônico desde 2026-08-14. Fusão de:
- backend/agents/llm_router.py  (rate limiting, circuit breaker, router)
- backend/services/llm_router.py (adaptadores Anthropic/OpenAI/Groq)

Uso:
    # Router com rate limiting
    from agents.llm_router import get_router, call_llm, CircuitBreaker
    router = get_router()
    text, usage = router.call("anthropic", "claude-3-opus", system, user)

    # Direto, sem rate limiting (para endpoints próprios)
    from agents.llm_router import call_llm_direct
    text, usage = call_llm_direct("openai", "gpt-4o", system, user)
"""

from __future__ import annotations

import json
import os
import time as _time
import threading as _threading
from typing import Literal

# ══════════════════════════════════════════════════════════════════
# RATE LIMITING — Global sliding window + tenant throttle
# ══════════════════════════════════════════════════════════════════
_TENANT_CALLS_LOCK = _threading.Lock()
_TENANT_CALLS: dict = {}
TENANT_MAX_CALLS_PER_MIN = int(os.environ.get("TENANT_MAX_CALLS_PER_MIN", "40"))
TENANT_THROTTLE_WAIT = 10

_LAST_CALL_TIME = 0.0
_CALL_SPACING_LOCK = _threading.Lock()
CALL_SPACING_SECONDS = float(os.environ.get("LLM_CALL_SPACING", "1.2"))


def _enforce_call_spacing() -> None:
    """Garante espaçamento mínimo entre chamadas."""
    global _LAST_CALL_TIME
    with _CALL_SPACING_LOCK:
        now = _time.time()
        elapsed = now - _LAST_CALL_TIME
        if elapsed < CALL_SPACING_SECONDS:
            _time.sleep(CALL_SPACING_SECONDS - elapsed)
        _LAST_CALL_TIME = now


def _tenant_rate_check(user_id) -> tuple[bool, int, int]:
    """Verifica rate limit por tenant (janela 60s)."""
    if not user_id:
        return (True, 0, 0)
    now = _time.time()
    window = 60.0
    with _TENANT_CALLS_LOCK:
        if user_id not in _TENANT_CALLS:
            _TENANT_CALLS[user_id] = []
        _TENANT_CALLS[user_id] = [t for t in _TENANT_CALLS[user_id] if now - t < window]
        count = len(_TENANT_CALLS[user_id])
        if count >= TENANT_MAX_CALLS_PER_MIN:
            oldest = _TENANT_CALLS[user_id][0]
            wait = int(window - (now - oldest)) + 1
            return (False, wait, count)
        _TENANT_CALLS[user_id].append(now)
        return (True, 0, count + 1)


def _tenant_rate_throttle(user_id: str) -> None:
    """Bloqueia até respeitar rate limit."""
    if not user_id:
        return
    allowed, wait, count = _tenant_rate_check(user_id)
    if not allowed:
        print(f"[RATE-LIMIT] Tenant {user_id} throttled: {count} calls/min")
        _time.sleep(min(wait, TENANT_THROTTLE_WAIT))


def _tenant_rate_alert(user_id: str, wait_seconds: int, calls_count: int) -> None:
    """Reporta throttle (best-effort)."""
    print(
        f"[RATE-LIMIT] Tenant {user_id} throttled: {calls_count} calls/min "
        f"(max={TENANT_MAX_CALLS_PER_MIN}). Aguardando {wait_seconds}s"
    )
    try:
        import ia_manager as _ia  # noqa: F401
        _ia.raise_alert(
            "rate_limit", None,
            f"Tenant throttled: {calls_count} chamadas/min. Pipeline aguardou {wait_seconds}s.",
            lead_id=None, user_id=user_id,
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER
# ══════════════════════════════════════════════════════════════════
class CircuitBreaker:
    """Circuit breaker por provider."""

    def __init__(self, failure_threshold: int = 5, cooldown_seconds: int = 60) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failures: dict[str, int] = {}
        self._lock = _threading.Lock()
        self._last_failure_time: dict[str, float] = {}

    def record_failure(self, provider: str) -> None:
        with self._lock:
            self._failures[provider] = self._failures.get(provider, 0) + 1
            self._last_failure_time[provider] = _time.time()

    def record_success(self, provider: str) -> None:
        with self._lock:
            self._failures[provider] = 0

    def is_open(self, provider: str) -> bool:
        with self._lock:
            failures = self._failures.get(provider, 0)
            if failures < self.failure_threshold:
                return False
            last = self._last_failure_time.get(provider, 0.0)
            return (_time.time() - last) < self.cooldown_seconds

    def get_cooldown_remaining(self, provider: str) -> int:
        with self._lock:
            last = self._last_failure_time.get(provider, 0.0)
            return max(0, int(self.cooldown_seconds - (_time.time() - last)))


_circuit_breaker = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    return _circuit_breaker


# ══════════════════════════════════════════════════════════════════
# MODEL MAPS
# ══════════════════════════════════════════════════════════════════
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")

LITELLM_MODEL_MAP = {
    "opus": os.getenv("PROXY_BUILDER_MODEL", "claude-3-opus-20240229"),
    "sonnet": os.getenv("PROXY_DEFAULT_MODEL", "claude-3-sonnet-20240229"),
    "haiku": os.getenv("PROXY_LIGHT_MODEL", "claude-3-haiku-20240307"),
}

AIBEE_MODEL_MAP = {
    "opus": os.getenv("PROXY_BUILDER_MODEL", "claude-3-opus-20240229"),
    "sonnet": os.getenv("PROXY_DEFAULT_MODEL", "claude-3-sonnet-20240229"),
    "haiku": os.getenv("PROXY_LIGHT_MODEL", "claude-3-haiku-20240307"),
}


def get_model_map() -> dict[str, str]:
    """Retorna model map baseado na configuração."""
    return LITELLM_MODEL_MAP if LITELLM_API_KEY else AIBEE_MODEL_MAP


def resolve_model_id(alias: str) -> str:
    """Resolve alias (opus/sonnet/haiku) para ID real."""
    return get_model_map().get(alias, get_model_map()["opus"])


# ══════════════════════════════════════════════════════════════════
# TIPOS E EXCEÇÕES
# ══════════════════════════════════════════════════════════════════
ProviderType = Literal["anthropic", "openai", "groq", "litellm", ""]


class LLMRouterError(Exception):
    """Exceção base para erros do router."""


class AllProvidersFailedError(LLMRouterError):
    """Todos os providers tentados falharam."""


# ══════════════════════════════════════════════════════════════════
# ADAPTADORES (movidos de services/llm_router.py em 2026-08-14)
# ══════════════════════════════════════════════════════════════════
_BASE_URLS: dict[str, str] = {
    "anthropic": os.getenv("ANTHROPIC_BASE_URL", "https://api.aibee.cloud"),
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
}


def _get_key_for_provider(provider: str) -> tuple[str, str, str | None]:
    """Busca key via ia_manager (round-robin), cai para .env."""
    try:
        import services.ia_manager as _ia  # noqa: F401
        result = _ia.pick_key(provider)
        if result:
            key, base, key_id = result[0], result[1], result[2]
            base = _BASE_URLS.get(provider, base)
            return key, base, key_id
    except Exception as e:
        print(f"[llm_router] ia_manager falhou para {provider}: {e}")

    env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "groq": "GROQ_API_KEY",
    }
    key = os.getenv(env_map.get(provider, ""), "")
    base = _BASE_URLS.get(provider, "")
    return key, base, None


def _call_anthropic(
    model_id: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
) -> tuple[str, dict]:
    """Adaptador Anthropic (Messages API) com cascade de modelos."""
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    base_url = base_url or os.getenv("ANTHROPIC_BASE_URL", "https://api.aibee.cloud")
    if not api_key:
        raise Exception("Nenhuma API key Anthropic disponível")

    import requests

    _CASCADE_ORDER = [
        "claude-opus-5", "claude-opus-4-8", "claude-opus-4-7",
        "claude-sonnet-5", "claude-sonnet-4-6", "claude-sonnet-4-5",
        "claude-haiku-5", "claude-haiku-4-5",
    ]
    _cascade_idx = 0
    _cascade_model = model_id
    last_exc: Exception | None = None

    while _cascade_idx < len(_CASCADE_ORDER):
        _cascade_model = _CASCADE_ORDER[_cascade_idx]
        try:
            return _try_anthropic_call(_cascade_model, system, user, temperature, max_tokens, api_key, base_url)
        except Exception as e:
            last_exc = e
            status = getattr(getattr(e, "response", None), "status_code", 0)
            if status in (529, 522, 503, 502, 429):
                _cascade_idx += 1
                wait = min(5 * _cascade_idx, 15)
                print(f"[llm_router] {status} Cascade: tentando {_cascade_model} → próxima (idx {_cascade_idx})")
                _time.sleep(wait)
                continue
            if status in (401, 403):
                raise Exception(f"Auth error {status}") from None
            _cascade_idx += 1
            _time.sleep(2)
            continue

    raise Exception(f"Todos os modelos da cascata falharam. Último erro: {last_exc}") from last_exc


def _try_anthropic_call(
    model_id: str, system: str, user: str, temperature: float, max_tokens: int,
    api_key: str, base_url: str,
) -> tuple[str, dict]:
    """Chamada única ao Messages API."""
    import requests

    url = f"{base_url}/v1/messages"
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
    r = requests.post(url, headers=headers, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()

    text_out = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text_out = block["text"]
            break

    usage = data.get("usage", {})
    return text_out, {
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
    }


def _call_openai(
    model_id: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    *,
    provider: str = "openai",
    api_key: str | None = None,
    base_url: str | None = None,
) -> tuple[str, dict]:
    """Adaptador OpenAI-compatible (OpenAI, Groq, LiteLLM)."""
    api_key, base_url, _ = _get_key_for_provider(provider)
    if not api_key:
        raise Exception(f"Nenhuma API key {provider} disponível")

    import requests

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_id,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    r = requests.post(url, headers=headers, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()

    text_out = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})
    return text_out, {
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
    }


def _call_groq(model_id: str, system: str, user: str, temperature: float, max_tokens: int) -> tuple[str, dict]:
    """Groq é OpenAI-compatible."""
    return _call_openai(model_id, system, user, temperature, max_tokens, provider="groq")


# ══════════════════════════════════════════════════════════════════
# ROUTER COM FALLBACK
# ══════════════════════════════════════════════════════════════════
class LLMRouter:
    """Router com rate limiting + circuit breaker + fallback."""

    def __init__(self) -> None:
        self._last_error: Exception | None = None

    def call(
        self,
        provider: str,
        model_id: str,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        fallback_providers: list[str] | None = None,
        user_id: str | None = None,
        agent_name: str | None = None,
        **kwargs,
    ) -> tuple[str, dict]:
        _enforce_call_spacing()

        if user_id:
            allowed, wait, count = _tenant_rate_check(user_id)
            if not allowed:
                _tenant_rate_alert(user_id, wait, count)
                _time.sleep(min(wait, TENANT_THROTTLE_WAIT))

        providers_to_try = [provider]
        if fallback_providers:
            providers_to_try.extend(fallback_providers)
        seen: set[str] = set()
        providers_to_try = [p for p in providers_to_try if not (p in seen or seen.add(p))]

        last_error: Exception | None = None
        for try_provider in providers_to_try:
            if _circuit_breaker.is_open(try_provider):
                remaining = _circuit_breaker.get_cooldown_remaining(try_provider)
                print(f"[Router] Circuit breaker aberto para {try_provider}, aguardando {remaining}s")
                continue
            try:
                result = self._call_provider(try_provider, model_id, system, user, temperature, max_tokens, **kwargs)
                _circuit_breaker.record_success(try_provider)
                return result
            except Exception as e:
                last_error = e
                _circuit_breaker.record_failure(try_provider)
                print(f"[Router] Provider {try_provider} falhou: {str(e)[:100]}")
                error_text = str(e).lower()
                if "429" in error_text or "rate limit" in error_text.lower():
                    print("[Router] Rate limit, tentando próximo provider")
                    _time.sleep(5)
                elif any(marker in error_text for marker in ("522", "provider_error", "overloaded", "temporariamente")):
                    print("[Router] Falha transitória de provider, tentando próximo provider")
                    _time.sleep(3)
                continue

        raise AllProvidersFailedError(f"Todos os providers falharam. Último erro: {last_error}") from last_error

    def _call_provider(self, provider: str, model_id: str, system: str, user: str,
                       temperature: float, max_tokens: int, **kwargs) -> tuple[str, dict]:
        p = provider.lower()
        if p == "anthropic":
            return _call_anthropic(model_id, system, user, temperature, max_tokens)
        if p in ("openai", "litellm", "groq"):
            return _call_openai(model_id, system, user, temperature, max_tokens, provider=p)
        return _call_openai(model_id, system, user, temperature, max_tokens, provider=p, **kwargs)


_router_instance: LLMRouter | None = None


def get_router() -> LLMRouter:
    """Singleton do router."""
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance


def call_llm(
    provider: str,
    model_id: str,
    system: str,
    user: str,
    temperature: float = 0.7,
    max_tokens: int = 4000,
    fallback_providers: list[str] | None = None,
    user_id: str | None = None,
    agent_name: str | None = None,
    **kwargs,
) -> tuple[str, dict]:
    """Função de conveniência. Retorna (texto, usage_dict)."""
    return get_router().call(
        provider=provider,
        model_id=model_id,
        system=system,
        user=user,
        temperature=temperature,
        max_tokens=max_tokens,
        fallback_providers=fallback_providers,
        user_id=user_id,
        agent_name=agent_name,
        **kwargs,
    )


def call_llm_direct(
    provider: str,
    model_id: str,
    system: str,
    user: str,
    temperature: float = 0.7,
    max_tokens: int = 4000,
) -> tuple[str, dict]:
    """Chamada LLM direta (sem rate limiting). Para endpoints próprios."""
    p = provider.lower()
    if p == "anthropic":
        return _call_anthropic(model_id, system, user, temperature, max_tokens)
    if p in ("openai", "litellm", "groq"):
        return _call_openai(model_id, system, user, temperature, max_tokens, provider=p)
    return _call_openai(model_id, system, user, temperature, max_tokens, provider=p)
