"""
LLM Providers - Facade unificada para chamadas LLM.

Este módulo fornece uma interface unificada para todos os providers LLM,
encapsulando a lógica de seleção, retry e fallback.

Usage:
    from llm_providers import call_llm, call_llm_structured, call_llm_stream

    # Chamada simples
    text, usage = call_llm("anthropic", "claude-3-opus", system, user)

    # Chamada com fallback automático
    text, usage = call_llm(
        "anthropic",
        "claude-3-opus",
        system, user,
        fallback=["openai"]
    )

    # Chamada estruturada (JSON via tool_use)
    result = call_llm_structured("anthropic", "claude-3-opus", system, user, tool_schema)

    # Streaming
    for chunk in call_llm_stream("anthropic", "claude-3-opus", system, user):
        print(chunk, end="")
"""

import os
import json
import time as _time
import re as _re
from typing import Callable

# Configurações de ambiente
LITELLM_API_KEY = os.getenv('LITELLM_API_KEY')
LITELLM_BASE_URL = os.getenv('LITELLM_BASE_URL', 'https://llm.seunegociofralib.site/v1')

# Import dos módulos
from backend.agents.llm_anthropic import (
    AnthropicProvider,
    AnthropicProviderError,
    AnthropicRateLimitError,
    get_anthropic_provider,
)
from backend.agents.llm_openai import (
    OpenAIProvider,
    OpenAIProviderError,
    OpenAIRateLimitError,
    _is_litellm_openai_chat_base,
)
from backend.agents.llm_router import (
    LLMRouterError,
    AllProvidersFailedError,
    get_router,
    resolve_model_id,
    _enforce_call_spacing,
)

# Re-export providers
__all__ = [
    # Providers
    "AnthropicProvider",
    "OpenAIProvider",
    # Exceptions
    "AnthropicProviderError",
    "OpenAIProviderError",
    "AnthropicRateLimitError",
    "OpenAIRateLimitError",
    "LLMRouterError",
    "AllProvidersFailedError",
    # Functions
    "call_llm",
    "call_llm_json",
    "call_llm_structured",
    "call_llm_stream",
    "call_llm_cached",
    # Utilities
    "get_router",
    "resolve_model_id",
]


# ══════════════════════════════════════════════════════════════════
# CONSTANTES E CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════
DEFAULT_MAX_TOKENS = int(os.environ.get("LLM_DEFAULT_MAX_TOKENS", "4000"))
DEFAULT_TEMPERATURE = float(os.environ.get("LLM_DEFAULT_TEMPERATURE", "0.7"))

# Model aliases
MODEL_ALIASES = {
    "opus": "claude-3-opus-20240229",
    "sonnet": "claude-3-sonnet-20240229",
    "haiku": "claude-3-haiku-20240307",
}


# ══════════════════════════════════════════════════════════════════
# FUNÇÕES DE CHAMADA UNIFICADAS
# ══════════════════════════════════════════════════════════════════
def call_llm(
    provider: str,
    model: str,
    system: str,
    user: str,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    fallback_providers: list = None,
    agent_name: str = None,
    user_id: str = None,
    enable_context: bool = True,
    **kwargs
) -> tuple[str, dict]:
    """Chamada LLM unificada com seleção automática de provider.

    Args:
        provider: Provider primário (anthropic, openai, litellm)
        model: ID do modelo ou alias (opus, sonnet, haiku, etc)
        system: Prompt de sistema
        user: Mensagem do usuário
        temperature: Temperatura (0.0 - 1.0)
        max_tokens: Máximo de tokens de saída
        fallback_providers: Providers para fallback em caso de falha
        agent_name: Nome do agente (para logging/audit)
        user_id: ID do tenant (para rate limiting)
        enable_context: Se True, injeta RAG e skills

    Returns:
        tuple: (texto_resposta, usage_dict)
        usage_dict: {"input_tokens": int, "output_tokens": int, ...}
    """
    _enforce_call_spacing()

    # Resolve model alias
    model_id = MODEL_ALIASES.get(model, model)

    # Se provider não especificado, usa Anthropic por padrão
    if not provider:
        provider = "anthropic"

    # Seleção de provider
    if provider in ("anthropic", "claude"):
        return _call_anthropic(
            model_id, system, user, temperature, max_tokens,
            agent_name=agent_name, user_id=user_id,
            enable_context=enable_context, **kwargs
        )

    elif provider in ("openai", "gpt", "litellm"):
        return _call_openai(
            model_id, system, user, temperature, max_tokens,
            agent_name=agent_name, user_id=user_id, **kwargs
        )

    else:
        # Usa router para provider desconhecido
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
            **kwargs
        )


def _call_anthropic(
    model_id: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    agent_name: str = None,
    user_id: str = None,
    enable_context: bool = True,
    **kwargs
) -> tuple[str, dict]:
    """Chamada Anthropic via SDK com retry e key rotation."""
    from llm_direct import (
        _resolve_anthropic,
    )

    api_key, base_url, key_id = _resolve_anthropic(agent_name)

    # Determina se usa endpoint LiteLLM ou SDK direto
    if _is_litellm_openai_chat_base(base_url):
        return _call_anthropic_via_litellm(
            api_key, base_url, model_id, system, user, temperature, max_tokens,
            agent_name=agent_name
        )

    # SDK direto Anthropic
    provider = get_anthropic_provider()
    provider.api_key = api_key
    provider.base_url = base_url

    return provider.call_with_retry(
        model_id=model_id,
        system=system,
        user=user,
        temperature=temperature,
        max_tokens=max_tokens,
        key_id=key_id,
        agent_name=agent_name,
        **kwargs
    )


def _call_anthropic_via_litellm(
    api_key: str,
    base_url: str,
    model_id: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    agent_name: str = None,
) -> tuple[str, dict]:
    """Chamada Anthropic via endpoint LiteLLM OpenAI-compatible."""
    from llm_openai import call_openai_chat

    text, usage = call_openai_chat(
        api_key=api_key,
        base_url=base_url,
        model_id=model_id,
        system=system,
        user=user,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Log usage
    try:
        from llm_direct import _registrar_uso_completo
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        _registrar_uso_completo(
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            agent_name=agent_name,
            provider="litellm",
        )
    except Exception:
        pass

    return text, usage


def _call_openai(
    model_id: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    agent_name: str = None,
    user_id: str = None,
    **kwargs
) -> tuple[str, dict]:
    """Chamada OpenAI/LiteLLM via endpoint compatível."""
    provider = OpenAIProvider()

    return provider.call_with_retry(
        model_id=model_id,
        system=system,
        user=user,
        temperature=temperature,
        max_tokens=max_tokens,
        max_attempts=3,
    )




# ══════════════════════════════════════════════════════════════════
# CHAMADA ESTRUTURADA (JSON via tool_use)
# ══════════════════════════════════════════════════════════════════
def call_llm_structured(
    provider: str = "anthropic",
    model: str = "opus",
    system: str = "",
    user: str = "",
    tool_name: str = "extract_json",
    tool_description: str = "Extrai dados estruturados",
    input_schema: dict = {"type": "object", "properties": {}},
    temperature: float = 0.5,
    max_tokens: int = 8000,
    agent_name: str = None,
    **kwargs
) -> dict:
    """Chamada LLM que força retorno JSON estruturado via tool_use.

    Args:
        provider: Provider a usar
        model: ID do modelo
        system: Prompt de sistema
        user: Mensagem do usuário
        tool_name: Nome do tool a ser forçado
        tool_description: Descrição do tool
        input_schema: Schema JSON do input esperado
        temperature: Temperatura
        max_tokens: Máximo de tokens

    Returns:
        dict: Input do tool_use block (dados estruturados)
    """
    if provider not in ("anthropic", "claude"):
        raise LLMRouterError(
            "call_llm_structured só suporta provider=anthropic"
        )

    model_id = MODEL_ALIASES.get(model, model)
    anthropic_provider = get_anthropic_provider()

    return anthropic_provider.call_structured(
        model_id=model_id,
        system=system,
        user=user,
        tool_name=tool_name,
        tool_description=tool_description,
        input_schema=input_schema,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )


# ══════════════════════════════════════════════════════════════════
# CHAMADA JSON (parsing robusto)
# ══════════════════════════════════════════════════════════════════
def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` fences."""
    text = text.strip()
    if text.startswith("```"):
        text = _re.sub(r"^```\w*\n?", "", text)
        text = _re.sub(r"\n?```$", "", text)
    return text.strip()


def call_llm_json(
    system: str,
    user: str,
    model: str = "sonnet",
    provider: str = "anthropic",
    max_tokens: int = 4096,
    temperature: float = 0.5,
    agent_name: str = None,
    output_model=None,
    retries: int = 2,
    **kwargs
) -> dict:
    """Chama LLM e retorna JSON parseado com retry automático.

    Args:
        system: Prompt de sistema
        user: Mensagem do usuário
        model: Modelo a usar (opus, sonnet, haiku, etc)
        provider: Provider (anthropic, openai, etc)
        max_tokens: Máximo de tokens
        temperature: Temperatura
        agent_name: Nome do agente
        output_model: Pydantic BaseModel para validação (opcional)
        retries: Número de retries em caso de parse failure

    Returns:
        dict: JSON parseado (ou instância Pydantic se output_model fornecido)
    """
    json_instruction = "\n\nResponda EXCLUSIVAMENTE com JSON válido. Sem markdown, sem texto antes ou depois."
    full_system = system + json_instruction

    model_id = MODEL_ALIASES.get(model, model)
    last_error = None

    for attempt in range(1, retries + 2):
        try:
            raw, usage = call_llm(
                provider=provider,
                model=model_id,
                system=full_system,
                user=user,
                temperature=temperature,
                max_tokens=max_tokens,
                agent_name=agent_name,
                **kwargs
            )

            clean = _strip_markdown_fences(raw)
            parsed = json.loads(clean)

            if output_model:
                return output_model.model_validate(parsed)
            return parsed

        except json.JSONDecodeError as e:
            last_error = e
            if attempt <= retries:
                print(f"[LLM JSON] Parse falhou (tentativa {attempt}/{retries + 1}): {e}")
                _time.sleep(2 * attempt)
        except Exception as e:
            last_error = e
            if attempt <= retries:
                print(f"[LLM JSON] Erro (tentativa {attempt}/{retries + 1}): {e}")
                _time.sleep(2 * attempt)

    raise LLMRouterError(
        f"JSON parse falhou após {retries + 1} tentativas: {last_error}"
    )


# ══════════════════════════════════════════════════════════════════
# STREAMING
# ══════════════════════════════════════════════════════════════════
def call_llm_stream(
    system: str,
    user: str,
    model: str = "opus",
    provider: str = "anthropic",
    max_tokens: int = 16384,
    temperature: float = 0.7,
    agent_name: str = None,
    on_chunk: Callable[[str], None] = None,
    **kwargs
) -> str:
    """Streaming LLM com callback por chunk.

    Args:
        system: Prompt de sistema
        user: Mensagem do usuário
        model: Modelo a usar
        provider: Provider (anthropic, openai, etc)
        max_tokens: Máximo de tokens
        temperature: Temperatura
        agent_name: Nome do agente
        on_chunk: Callback chamado para cada chunk de texto

    Returns:
        str: Texto completo concatenado
    """
    if provider not in ("anthropic", "claude"):
        raise LLMRouterError(
            "call_llm_stream só suporta provider=anthropic"
        )

    model_id = MODEL_ALIASES.get(model, model)
    anthropic_provider = get_anthropic_provider()

    full_text, usage = anthropic_provider.stream(
        model_id=model_id,
        system=system,
        user=user,
        temperature=temperature,
        max_tokens=max_tokens,
        on_chunk=on_chunk,
        **kwargs
    )

    # Log usage
    try:
        from llm_direct import _registrar_uso_completo
        _registrar_uso_completo(
            model_id,
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
            agent_name
        )
    except Exception:
        pass

    return full_text


# ══════════════════════════════════════════════════════════════════
# PROMPT CACHING EXPLÍCITO
# ══════════════════════════════════════════════════════════════════
def call_llm_cached(
    system: str,
    user: str,
    model: str = "sonnet",
    provider: str = "anthropic",
    max_tokens: int = 4096,
    temperature: float = 0.7,
    agent_name: str = None,
    cache_user_prefix: str = None,
    **kwargs
) -> str:
    """Chamada com prompt caching explícito.

    Args:
        system: Prompt de sistema (sempre cacheado)
        user: Mensagem do usuário
        model: Modelo a usar
        provider: Provider
        max_tokens: Máximo de tokens
        temperature: Temperatura
        agent_name: Nome do agente
        cache_user_prefix: Prefixo do user para cachear separadamente

    Returns:
        str: Texto da resposta
    """
    if provider not in ("anthropic", "claude"):
        raise LLMRouterError(
            "call_llm_cached só suporta provider=anthropic"
        )

    model_id = MODEL_ALIASES.get(model, model)
    anthropic_provider = get_anthropic_provider()

    # System payload cacheado
    system_payload = [
        {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
    ]

    # Messages com cache opcional
    if cache_user_prefix:
        messages_content = [
            {"type": "text", "text": cache_user_prefix, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": user},
        ]
    else:
        messages_content = user

    extra_headers = {"anthropic-beta": "prompt-caching-2024-07-31"}

    _enforce_call_spacing()

    client = anthropic_provider.client
    response = client.messages.create(
        model=model_id,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_payload,
        messages=[{"role": "user", "content": messages_content}],
        extra_headers=extra_headers,
    )

    # Log usage
    usage = response.usage
    try:
        from llm_direct import _registrar_uso_completo
        _registrar_uso_completo(
            model_id,
            usage.input_tokens,
            usage.output_tokens,
            agent_name
        )
    except Exception:
        pass

    # Extrai texto
    for block in response.content:
        if block.type == "text":
            return block.text

    raise LLMRouterError("Nenhum bloco text na resposta")


# ══════════════════════════════════════════════════════════════════
# COMPATIBILIDADE COM llm_direct
# ══════════════════════════════════════════════════════════════════
# Aliases para funções do llm_direct
def call_claude(system, user, model="opus", max_tokens=4000, temperature=0.7,
                agent_name=None, base_url=None, respect_agent_config=True,
                enable_context=True):
    """Alias para call_llm com provider=anthropic.

    Mantém compatibilidade com código existente que usa call_claude.
    """
    from llm_direct import call_claude as _original_call_claude
    return _original_call_claude(
        system=system,
        user=user,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        agent_name=agent_name,
        base_url=base_url,
        respect_agent_config=respect_agent_config,
        enable_context=enable_context,
    )


def call_claude_structured(system, user, tool_name, tool_description, input_schema,
                           model="opus", max_tokens=8000, temperature=0.7,
                           agent_name=None, enable_context=True):
    """Alias para call_llm_structured.

    Mantém compatibilidade com código existente.
    """
    return call_llm_structured(
        provider="anthropic",
        model=model,
        system=system,
        user=user,
        tool_name=tool_name,
        tool_description=tool_description,
        input_schema=input_schema,
        temperature=temperature,
        max_tokens=max_tokens,
        agent_name=agent_name,
    )


def call_claude_json(system, user, model="sonnet", max_tokens=4096, temperature=0.5,
                     agent_name=None, output_model=None, retries=2):
    """Alias para call_llm_json.

    Mantém compatibilidade com código existente.
    """
    return call_llm_json(
        system=system,
        user=user,
        model=model,
        provider="anthropic",
        max_tokens=max_tokens,
        temperature=temperature,
        agent_name=agent_name,
        output_model=output_model,
        retries=retries,
    )


def call_claude_stream(system, user, model="opus", max_tokens=16384, temperature=0.7,
                       agent_name=None, on_chunk=None, enable_context=True):
    """Alias para call_llm_stream.

    Mantém compatibilidade com código existente.
    """
    return call_llm_stream(
        system=system,
        user=user,
        model=model,
        provider="anthropic",
        max_tokens=max_tokens,
        temperature=temperature,
        agent_name=agent_name,
        on_chunk=on_chunk,
    )


def call_claude_cached(system, user, model="sonnet", max_tokens=4096, temperature=0.7,
                       agent_name=None, cache_user_prefix=None):
    """Alias para call_llm_cached.

    Mantém compatibilidade com código existente.
    """
    return call_llm_cached(
        system=system,
        user=user,
        model=model,
        provider="anthropic",
        max_tokens=max_tokens,
        temperature=temperature,
        agent_name=agent_name,
        cache_user_prefix=cache_user_prefix,
    )
