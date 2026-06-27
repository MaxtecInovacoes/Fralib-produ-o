"""
LLM Provider - Anthropic (Claude).

Chamadas para API Anthropic usando SDK oficial.
Suporta prompt caching, streaming, tools, e retry com key rotation.
"""

import os
import time as _time
import httpx
import anthropic


# Configurações do ambiente
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.kpalabz.com/v1")

# LiteLLM override
LITELLM_API_KEY = os.getenv('LITELLM_API_KEY')
LITELLM_BASE_URL = os.getenv('LITELLM_BASE_URL', 'https://llm.seunegociofralib.site/v1')


class AnthropicProviderError(Exception):
    """Exceção base para erros do provider Anthropic."""
    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AnthropicRateLimitError(AnthropicProviderError):
    """Exceção para rate limit (429)."""
    def __init__(self, message: str, reset_seconds: int = 0):
        self.reset_seconds = reset_seconds
        super().__init__(message, status_code=429)


class AnthropicTimeoutError(AnthropicProviderError):
    """Exceção para timeout."""
    pass


def _create_client(api_key: str, base_url: str) -> anthropic.Anthropic:
    """Cria cliente Anthropic SDK com timeouts configurados."""
    read_timeout = float(os.getenv("FRALIB_LLM_READ_TIMEOUT", "420"))
    if base_url and base_url.endswith("/v1"):
        base_url = base_url[:-3]
    return anthropic.Anthropic(
        api_key=api_key,
        base_url=base_url,
        max_retries=0,
        timeout=httpx.Timeout(connect=10.0, read=read_timeout, write=60.0, pool=10.0),
    )


def _extract_usage(response) -> dict:
    """Extrai usage do response."""
    usage = response.usage
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cache_created": getattr(usage, "cache_creation_input_tokens", 0) or 0,
    }


def _build_system_payload(system: str) -> tuple[list, dict]:
    """Constrói payload do system message com prompt caching.

    Returns:
        tuple: (system_payload, extra_headers)
    """
    extra_headers = {}
    if system and len(system) >= 1024:
        system_payload = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]
        extra_headers["anthropic-beta"] = "prompt-caching-2024-07-31"
    else:
        system_payload = [{"type": "text", "text": system}] if system else []
    return system_payload, extra_headers


def _build_messages_content(rag_block: str, user: str) -> str | list:
    """Constrói conteúdo das mensagens com cache para RAG.

    Returns:
        str ou list: conteúdo simples ou com blocos cacheados
    """
    if rag_block and len(rag_block) >= 1024:
        return [
            {"type": "text", "text": rag_block, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": user},
        ]
    elif rag_block:
        return rag_block + user
    return user


class AnthropicProvider:
    """Provider para chamadas Claude via SDK Anthropic."""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.base_url = base_url or ANTHROPIC_BASE_URL
        self._client = None

    def is_available(self) -> bool:
        """Verifica se o provider está configurado."""
        return bool(self.api_key)

    @property
    def client(self) -> anthropic.Anthropic:
        """Lazy-load do cliente SDK."""
        if self._client is None:
            self._client = _create_client(self.api_key, self.base_url)
        return self._client

    def call(
        self,
        model_id: str,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        rag_block: str = "",
        extra_headers: dict = None,
        **kwargs
    ) -> tuple[str, dict]:
        """Executa chamada LLM via SDK Anthropic.

        Returns:
            tuple: (texto_resposta, usage_dict)
        """
        system_payload, headers = _build_system_payload(system)
        if extra_headers:
            headers.update(extra_headers)

        messages_content = _build_messages_content(rag_block, user)

        response = self.client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_payload,
            messages=[{"role": "user", "content": messages_content}],
            extra_headers=headers if headers else None,
        )

        # Extrair texto do response
        for block in response.content:
            if block.type == "text":
                return block.text, _extract_usage(response)

        raise AnthropicProviderError("Nenhum bloco text na resposta")

    def call_with_retry(
        self,
        model_id: str,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        max_attempts: int = 5,
        rag_block: str = "",
        key_id=None,
        ia_manager=None,
        agent_name=None,
        **kwargs
    ) -> tuple[str, dict]:
        """Executa chamada com retry automático e key rotation.

        Args:
            max_attempts: Número máximo de tentativas
            key_id: ID da chave para tracking no ia_manager
            ia_manager: Módulo ia_manager para key rotation

        Returns:
            tuple: (texto_resposta, usage_dict)
        """
        from llm_direct import _resolve_anthropic

        api_key = self.api_key
        base_url = self.base_url

        for attempt in range(1, max_attempts + 1):
            client = _create_client(api_key, base_url)
            system_payload, headers = _build_system_payload(system)
            messages_content = _build_messages_content(rag_block, user)

            try:
                response = client.messages.create(
                    model=model_id,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_payload,
                    messages=[{"role": "user", "content": messages_content}],
                    extra_headers=headers if headers else None,
                )

                # Mark success
                if ia_manager and key_id:
                    ia_manager.mark_success(key_id)

                # Extrair texto
                for block in response.content:
                    if block.type == "text":
                        return block.text, _extract_usage(response)

                raise AnthropicProviderError("Nenhum bloco text na resposta")

            except anthropic.RateLimitError as e:
                cd = 60
                if ia_manager:
                    try:
                        cd = ia_manager.parse_cooldown_from_response(
                            429, dict(e.response.headers) if e.response else {}
                        )
                    except Exception:
                        pass
                if ia_manager and key_id:
                    ia_manager.mark_failure(key_id, "429 rate limit", cd)

                if attempt >= max_attempts:
                    raise AnthropicRateLimitError(
                        f"Rate limit persistente após {max_attempts} tentativas",
                        reset_seconds=cd
                    )

                # Key rotation
                new_key = _resolve_anthropic(agent_name)
                if new_key and new_key[2] != key_id:
                    api_key, base_url, key_id = new_key

                wait = min(10 * attempt, 20)
                print(f"[Anthropic] 429 — aguardando {wait}s (tentativa {attempt}/{max_attempts})")
                _time.sleep(wait)

            except anthropic.APIStatusError as e:
                if e.status_code in (529, 503, 502):
                    wait = min(20 * attempt, 60)
                    print(f"[Anthropic] {e.status_code} Overloaded - aguardando {wait}s")
                    _time.sleep(wait)
                elif e.status_code == 400:
                    if attempt < max_attempts:
                        _time.sleep(5 * attempt)
                    else:
                        raise
                else:
                    raise

            except (anthropic.APITimeoutError, anthropic.APIConnectionError):
                if attempt >= max_attempts:
                    raise AnthropicTimeoutError(f"Timeout após {max_attempts} tentativas")
                wait = min(15 * attempt, 60)
                print(f"[Anthropic] Timeout - aguardando {wait}s")
                _time.sleep(wait)

        raise AnthropicProviderError(f"Falhou após {max_attempts} tentativas")

    def call_structured(
        self,
        model_id: str,
        system: str,
        user: str,
        tool_name: str,
        tool_description: str,
        input_schema: dict,
        temperature: float = 0.7,
        max_tokens: int = 8000,
        **kwargs
    ) -> dict:
        """Chama Claude com tool_use para forçar retorno JSON estruturado.

        Returns:
            dict: Input do tool_use block
        """
        system_payload, headers = _build_system_payload(system)
        headers["anthropic-beta"] = "prompt-caching-2024-07-31"

        client = _create_client(self.api_key, self.base_url)

        response = client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_payload,
            messages=[{"role": "user", "content": user}],
            tools=[
                {
                    "name": tool_name,
                    "description": tool_description,
                    "input_schema": input_schema,
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
            extra_headers=headers if headers else None,
        )

        # Extrair tool_use
        for block in response.content:
            if block.type == "tool_use" and block.name == tool_name:
                return block.input

        # Fallback: qualquer tool_use
        for block in response.content:
            if block.type == "tool_use":
                return block.input

        raise AnthropicProviderError(
            f"Nenhum tool_use block na resposta (stop={response.stop_reason})"
        )

    def stream(
        self,
        model_id: str,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 16384,
        on_chunk: callable = None,
        **kwargs
    ) -> tuple[str, dict]:
        """Streaming com callback por chunk.

        Args:
            on_chunk: Callback chamado para cada chunk de texto

        Returns:
            tuple: (texto_completo, usage_dict)
        """
        system_payload, headers = _build_system_payload(system)
        client = _create_client(self.api_key, self.base_url)

        full_text = ""
        with client.messages.stream(
            model=model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_payload,
            messages=[{"role": "user", "content": user}],
            extra_headers=headers if headers else None,
        ) as stream:
            for text in stream.text_stream:
                full_text += text
                if on_chunk:
                    on_chunk(text)

        # Obter usage do stream completo
        response = stream.get_final_message()
        return full_text, _extract_usage(response)


# Instância singleton
_provider_instance = None

def get_anthropic_provider() -> AnthropicProvider:
    """Retorna instância singleton do provider."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = AnthropicProvider()
    return _provider_instance
