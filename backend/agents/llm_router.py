"""
LLM Router - Seleção de provider e lógica de fallback.

Este módulo fornece rate limiting centralizado e circuit breaker,
delegando as chamadas reais para o router de services ou providers individuais.

Uso:
    from agents.llm_router import get_router, call_llm, CircuitBreaker

    # Via router
    router = get_router()
    text, usage = router.call("anthropic", "claude-3-opus", system, user)

    # Via função direta
    from agents.llm_router import call_llm
    text, usage = call_llm("openai", "gpt-4o", system, user)

    # Com circuit breaker
    cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=60)
"""

import os
import time as _time
import threading as _threading
from typing import Optional, Literal

# ══════════════════════════════════════════════════════════════════
# RATE LIMITING - Global sliding window
# ══════════════════════════════════════════════════════════════════
_TENANT_CALLS_LOCK = _threading.Lock()
_TENANT_CALLS: dict = {}
TENANT_MAX_CALLS_PER_MIN = int(os.environ.get("TENANT_MAX_CALLS_PER_MIN", "40"))
TENANT_THROTTLE_WAIT = 10

# Call spacing
_LAST_CALL_TIME = 0.0
_CALL_SPACING_LOCK = _threading.Lock()
CALL_SPACING_SECONDS = float(os.environ.get("LLM_CALL_SPACING", "1.2"))


def _enforce_call_spacing():
    """Garante espaçamento mínimo entre chamadas."""
    global _LAST_CALL_TIME
    with _CALL_SPACING_LOCK:
        now = _time.time()
        elapsed = now - _LAST_CALL_TIME
        if elapsed < CALL_SPACING_SECONDS:
            _time.sleep(CALL_SPACING_SECONDS - elapsed)
        _LAST_CALL_TIME = _time.time()


def _tenant_rate_check(user_id) -> tuple:
    """Verifica rate limit por tenant.

    Returns:
        tuple: (allowed: bool, wait_seconds: int, current_count: int)
    """
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


def _tenant_rate_throttle(user_id: str):
    """Aplica throttle se necessário."""
    if not user_id:
        return
    allowed, wait, count = _tenant_rate_check(user_id)
    if not allowed:
        print(f"[RATE-LIMIT] Tenant {user_id} throttled: {count} calls/min")
        _time.sleep(min(wait, TENANT_THROTTLE_WAIT))


def _tenant_rate_alert(user_id: str, wait_seconds: int, calls_count: int):
    """Reporta throttle ao ia_manager."""
    print(
        f"[RATE-LIMIT] Tenant {user_id} throttled: {calls_count} calls/min (max={TENANT_MAX_CALLS_PER_MIN}). Aguardando {wait_seconds}s"
    )
    try:
        import ia_manager as _ia
        _ia.raise_alert(
            "rate_limit",
            None,
            f"Tenant throttled: {calls_count} chamadas/min excede limite de {TENANT_MAX_CALLS_PER_MIN}. Pipeline aguardou {wait_seconds}s.",
            lead_id=None,
            user_id=user_id,
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER
# ══════════════════════════════════════════════════════════════════
class CircuitBreaker:
    """Circuit breaker para evitar chamadas quando providers estão falhando."""

    def __init__(self, failure_threshold: int = 5, cooldown_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failures = {}
        self._lock = _threading.Lock()
        self._last_failure_time = {}

    def record_failure(self, provider: str):
        """Registra falha de um provider."""
        with self._lock:
            self._failures[provider] = self._failures.get(provider, 0) + 1
            self._last_failure_time[provider] = _time.time()

    def record_success(self, provider: str):
        """Registra sucesso - reseta contador."""
        with self._lock:
            self._failures[provider] = 0

    def is_open(self, provider: str) -> bool:
        """Verifica se circuit breaker está aberto para o provider."""
        with self._lock:
            failures = self._failures.get(provider, 0)
            if failures < self.failure_threshold:
                return False

            last_failure = self._last_failure_time.get(provider, 0)
            elapsed = _time.time() - last_failure

            return elapsed < self.cooldown_seconds

    def get_cooldown_remaining(self, provider: str) -> int:
        """Retorna segundos restantes de cooldown."""
        with self._lock:
            last_failure = self._last_failure_time.get(provider, 0)
            elapsed = _time.time() - last_failure
            remaining = self.cooldown_seconds - elapsed
            return max(0, int(remaining))


# Instância global do circuit breaker
_circuit_breaker = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    """Retorna instância global do circuit breaker."""
    return _circuit_breaker


# ══════════════════════════════════════════════════════════════════
# MODEL MAPS
# ══════════════════════════════════════════════════════════════════
LITELLM_API_KEY = os.getenv('LITELLM_API_KEY')

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


def get_model_map() -> dict:
    """Retorna model map baseado na configuração."""
    return LITELLM_MODEL_MAP if LITELLM_API_KEY else AIBEE_MODEL_MAP


def resolve_model_id(alias: str) -> str:
    """Resolve alias de modelo para ID real.

    Args:
        alias: Alias do modelo (opus, sonnet, haiku, etc)

    Returns:
        str: ID do modelo
    """
    model_map = get_model_map()
    return model_map.get(alias, model_map["opus"])


# ══════════════════════════════════════════════════════════════════
# TIPOS E EXCEÇÕES
# ══════════════════════════════════════════════════════════════════
ProviderType = Literal["anthropic", "openai", "google", "groq", "openrouter", "litellm"]


class LLMRouterError(Exception):
    """Exceção base para erros do router."""
    pass


class AllProvidersFailedError(LLMRouterError):
    """Todas as tentativas de providers falharam."""
    pass


# ══════════════════════════════════════════════════════════════════
# ROUTER COM FALLBACK
# ══════════════════════════════════════════════════════════════════
class LLMRouter:
    """Router com rate limiting e circuit breaker.

    Delega chamadas para services.llm_router que tem adaptadores
    para todos os providers suportados.
    """

    def __init__(self):
        self._services_router = None

    @property
    def services_router(self):
        """Lazy-load do router de services."""
        if self._services_router is None:
            try:
                from services.llm_router import call_llm as _call_llm
                self._services_router = _call_llm
            except ImportError:
                from backend.services.llm_router import call_llm as _call_llm
                self._services_router = _call_llm
        return self._services_router

    def call(
        self,
        provider: ProviderType,
        model_id: str,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        fallback_providers: list[ProviderType] = None,
        user_id: str = None,
        agent_name: str = None,
        **kwargs
    ) -> tuple[str, dict]:
        """Chama LLM com provider especificado e fallback automático.

        Args:
            provider: Provider primário
            model_id: ID do modelo
            system: Prompt de sistema
            user: Mensagem do usuário
            temperature: Temperatura
            max_tokens: Máximo de tokens
            fallback_providers: Lista de providers para fallback
            user_id: ID do tenant para rate limiting
            agent_name: Nome do agente para logging

        Returns:
            tuple: (texto_resposta, usage_dict)
        """
        _enforce_call_spacing()

        # Rate limiting
        if user_id:
            allowed, wait, count = _tenant_rate_check(user_id)
            if not allowed:
                _tenant_rate_alert(user_id, wait, count)
                _time.sleep(min(wait, TENANT_THROTTLE_WAIT))

        # Determina providers a tentar
        providers_to_try = [provider]
        if fallback_providers:
            providers_to_try.extend(fallback_providers)

        # Remove duplicatas mantendo ordem
        seen = set()
        providers_to_try = [p for p in providers_to_try if not (p in seen or seen.add(p))]

        last_error = None

        for try_provider in providers_to_try:
            # Check circuit breaker
            if _circuit_breaker.is_open(try_provider):
                remaining = _circuit_breaker.get_cooldown_remaining(try_provider)
                print(f"[Router] Circuit breaker aberto para {try_provider}, aguardando {remaining}s")
                continue

            try:
                result = self._call_provider(
                    try_provider,
                    model_id,
                    system,
                    user,
                    temperature,
                    max_tokens,
                    **kwargs
                )
                _circuit_breaker.record_success(try_provider)
                return result

            except Exception as e:
                last_error = e
                _circuit_breaker.record_failure(try_provider)
                error_msg = str(e)

                print(f"[Router] Provider {try_provider} falhou: {error_msg[:100]}")

                # Trata rate limit
                if "429" in error_msg or "rate limit" in error_msg.lower():
                    print(f"[Router] Rate limit detectado, tentando próximo provider")
                    _time.sleep(5)
                continue

        raise AllProvidersFailedError(
            f"Todos os providers falharam. Último erro: {last_error}"
        )

    def _call_provider(
        self,
        provider: str,
        model_id: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> tuple[str, dict]:
        """Executa chamada no provider especificado via services router."""
        return self.services_router(
            provider=provider,
            model_id=model_id,
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
        )


# Instância singleton
_router_instance = None

def get_router() -> LLMRouter:
    """Retorna instância singleton do router."""
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance


# ══════════════════════════════════════════════════════════════════
# FUNÇÃO DE CONVENIÊNCIA
# ══════════════════════════════════════════════════════════════════
def call_llm(
    provider: ProviderType,
    model_id: str,
    system: str,
    user: str,
    temperature: float = 0.7,
    max_tokens: int = 4000,
    fallback_providers: list[ProviderType] = None,
    user_id: str = None,
    **kwargs
) -> tuple[str, dict]:
    """Função de conveniência para chamada LLM via router.

    Args:
        provider: Provider primário (anthropic, openai, google, litellm, groq, openrouter)
        model_id: ID do modelo
        system: Prompt de sistema
        user: Mensagem do usuário
        temperature: Temperatura
        max_tokens: Máximo de tokens
        fallback_providers: Providers para fallback em caso de falha
        user_id: ID do tenant para rate limiting

    Returns:
        tuple: (texto_resposta, usage_dict)
        usage_dict: {"input_tokens": int, "output_tokens": int}
    """
    return get_router().call(
        provider=provider,
        model_id=model_id,
        system=system,
        user=user,
        temperature=temperature,
        max_tokens=max_tokens,
        fallback_providers=fallback_providers,
        user_id=user_id,
        **kwargs
    )
