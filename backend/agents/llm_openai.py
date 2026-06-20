"""
LLM Provider - OpenAI Compatible (LiteLLM).

Chamadas para provedores OpenAI-compatíveis via endpoint /v1/chat/completions.
Suporta LiteLLM, OpenRouter, e outros provedores com API OpenAI-compatible.
"""

import os
import time as _time
import httpx


# LiteLLM configuration
LITELLM_API_KEY = os.getenv('LITELLM_API_KEY')
LITELLM_BASE_URL = os.getenv('LITELLM_BASE_URL', 'https://llm.seunegociofralib.site/v1')

# Rate limit settings
_TENANT_CALLS_LOCK = None  # Inicializado via import
_TENANT_CALLS = None
TENANT_MAX_CALLS_PER_MIN = int(os.environ.get("TENANT_MAX_CALLS_PER_MIN", "40"))


def _is_litellm_openai_chat_base(base_url: str | None) -> bool:
    """Verifica se o base_url é um endpoint LiteLLM/OpenAI-compatível."""
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
    """Constrói URL completa para chat completions."""
    base = (base_url or "").rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


class OpenAIProviderError(Exception):
    """Exceção base para erros do provider OpenAI."""
    def __init__(self, message: str, status_code: int = None, provider: str = "openai"):
        self.message = message
        self.status_code = status_code
        self.provider = provider
        super().__init__(message)


class OpenAIRateLimitError(OpenAIProviderError):
    """Exceção para rate limit (429)."""
    def __init__(self, message: str, reset_seconds: int = 0):
        self.reset_seconds = reset_seconds
        super().__init__(message, status_code=429)


def _alert_openai_failure(provider: str, model_id: str, error: Exception, key_id=None, source="openai_provider"):
    """Reporta falha de provider OpenAI ao ia_manager."""
    try:
        import ia_manager as _ia
        status = getattr(error, "status_code", None)
        alert_type = "rate_limit" if status == 429 else "test_failed"
        cooldown = 60 if status == 429 else 300
        if key_id is not None:
            try:
                _ia.mark_failure(key_id, f"{status or type(error).__name__}", cooldown)
            except Exception:
                pass
        status_label = f"HTTP {status}" if status else type(error).__name__
        message = f"{source}: provider {provider}/{model_id} falhou com {status_label}. {str(error)[:200]}"
        _ia.raise_alert(alert_type, key_id, message, lead_id=None, user_id=None)
    except Exception:
        pass


def call_openai_chat(
    *,
    api_key: str,
    base_url: str,
    model_id: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    extra_headers: dict = None,
) -> tuple[str, dict]:
    """Chama endpoint OpenAI-compatível (LiteLLM).

    Returns:
        tuple: (texto_resposta, usage_dict)
        usage_dict: {"input_tokens": int, "output_tokens": int}
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
    if extra_headers:
        headers.update(extra_headers)

    try:
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

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            reset = e.response.headers.get("x-ratelimit-reset-remaining", 60)
            try:
                reset = int(reset)
            except (ValueError, TypeError):
                reset = 60
            raise OpenAIRateLimitError(
                f"Rate limit atingido. Reset em ~{reset}s",
                reset_seconds=reset
            )
        raise OpenAIProviderError(
            f"HTTP {e.response.status_code}: {str(e)[:200]}",
            status_code=e.response.status_code
        )
    except httpx.TimeoutException as e:
        raise OpenAIProviderError(f"Timeout na requisição: {str(e)[:200]}")
    except Exception as e:
        raise OpenAIProviderError(f"Erro na requisição: {str(e)[:200]}")


class OpenAIProvider:
    """Provider para chamadas OpenAI-compatíveis (LiteLLM, OpenRouter, etc)."""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or LITELLM_API_KEY
        self.base_url = base_url or LITELLM_BASE_URL

    def is_available(self) -> bool:
        """Verifica se o provider está configurado."""
        return bool(self.api_key and self.base_url)

    def call(
        self,
        system: str,
        user: str,
        model_id: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> tuple[str, dict]:
        """Executa chamada LLM via endpoint OpenAI-compatível.

        Returns:
            tuple: (texto_resposta, usage_dict)
        """
        if not self.is_available():
            raise OpenAIProviderError("Provider OpenAI não configurado")

        text, usage = call_openai_chat(
            api_key=self.api_key,
            base_url=self.base_url,
            model_id=model_id,
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return text, usage

    def call_with_retry(
        self,
        system: str,
        user: str,
        model_id: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        max_attempts: int = 3,
        **kwargs
    ) -> tuple[str, dict]:
        """Executa chamada com retry automático.

        Args:
            max_attempts: Número máximo de tentativas

        Returns:
            tuple: (texto_resposta, usage_dict)
        """
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                return self.call(
                    system=system,
                    user=user,
                    model_id=model_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except OpenAIRateLimitError as e:
                last_error = e
                if attempt < max_attempts:
                    wait = min(e.reset_seconds, 60) if e.reset_seconds else 15 * attempt
                    print(f"[OpenAI] Rate limit - aguardando {wait}s (tentativa {attempt}/{max_attempts})")
                    _time.sleep(wait)
            except OpenAIProviderError as e:
                last_error = e
                if attempt < max_attempts:
                    wait = 5 * attempt
                    print(f"[OpenAI] Erro {e.status_code or 'unknown'} - aguardando {wait}s (tentativa {attempt}/{max_attempts})")
                    _time.sleep(wait)

        raise last_error or OpenAIProviderError(f"Falhou após {max_attempts} tentativas")
