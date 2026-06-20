# llm_direct.py — LLM API wrapper with RAG, Skills, Memory, and Agent Router
"""
Public API module for FraLib LLM client.
Wraps low-level modules and exposes call_claude / call_claude_structured.
"""
from __future__ import annotations

import json
import re as _re
import time as _time
from pathlib import Path
from typing import Callable

import anthropic

# ─────────────────────────────────────────────────────────────────
# PATH SETUP
# ─────────────────────────────────────────────────────────────────
import os
import sys as _sys

_services_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "services")
)
if _services_dir not in _sys.path:
    _sys.path.insert(0, _services_dir)
_agents_dir = os.path.abspath(os.path.dirname(__file__))
if _agents_dir not in _sys.path:
    _sys.path.insert(0, _agents_dir)

# ─────────────────────────────────────────────────────────────────
# IMPORTS FROM MODULES
# ─────────────────────────────────────────────────────────────────
from backend.agents import llm_config
from backend.agents.llm_config import (
    AGENT_MODEL_MAP,
    AIBEE_MODEL_MAP,
    LITELLM_MODEL_MAP,
    MODEL_MAP,
    BUILDER_RENDERER_AGENT,
    PROXY_BUILDER_MODEL,
    PROXY_PROVIDER,
    LITELLM_API_KEY,
    LITELLM_BASE_URL,
    ANTHROPIC_API_KEY,
    ANTHROPIC_BASE_URL,
    RateLimitError,
    invalidate_agent_config_cache,
    fallbacks_disabled,
    _load_agent_configs,
)

from backend.agents.llm_context import (
    set_current_user_id,
    set_llm_context,
    clear_llm_context,
    _llm_context_value,
    _enforce_call_spacing,
    _tenant_rate_check,
    _tenant_rate_alert,
    get_current_user_id,
    invalidar_byok_cache,
    _get_byok_key,
    _resolve_anthropic,
)

from backend.agents.llm_client import (
    _create_client,
    _is_litellm_openai_chat_base,
    _litellm_chat_url,
    _call_litellm_openai_chat,
    _llm_error_status,
    _llm_error_text,
    _llm_alert_type,
    _alert_llm_provider_failure,
    _extract_text_from_tool_use,
)

from backend.agents.llm_tracking import (
    _salvar_uso_llm,
    _registrar_llm_budget,
)


# ─────────────────────────────────────────────────────────────────
# PUBLIC API — call_claude
# ─────────────────────────────────────────────────────────────────
def call_claude(
    system,
    user,
    model="opus",
    max_tokens=4000,
    temperature=0.7,
    agent_name=None,
    base_url=None,
    respect_agent_config=True,
    enable_context=True,
):
    """Chama Claude API via SDK com RAG, Skills, Memory, Agent Router e key rotation."""
    request_user_id = get_current_user_id()

    # ── RAG + Skills injection (fast skip if no file/config) ──
    rag_block = ""
    if agent_name and enable_context:
        _an = agent_name.lower()
        _rag_file = Path(__file__).parent / "rag_knowledge" / f"{_an}.md"
        _has_rag = _rag_file.exists()
        _has_skills = (Path(__file__).parent / "skill_loader.py").exists()
        if _has_rag or _has_skills:
            try:
                if _has_rag:
                    from agent_rag import (
                        buscar_contexto_rag,
                        format_rag_prompt,
                        mark_rag_used,
                    )

                    rag_context = buscar_contexto_rag(user, _an)
                    if rag_context:
                        rag_block = f"CONTEXTO RAG (conhecimento da base):\n{rag_context}\n\n---\n\n"
                        mark_rag_used(agent_name)
                        print(
                            f"[LLM Direct] RAG ativado para {agent_name} ({len(rag_block)} chars)"
                        )

                if _has_skills:
                    from skill_loader import get_skills_agente, carregar_skills

                    skills = get_skills_agente(_an)
                    if skills:
                        guidelines = carregar_skills(skills)
                        if guidelines:
                            system = f"{system}\n\n{'=' * 60}\n# SKILLS ATIVADAS\n{'=' * 60}\n{guidelines}"
                            print(
                                f"[LLM Direct] Skills ativadas para {agent_name}: {', '.join(skills)}"
                            )
            except Exception as e:
                print(f"[LLM Direct] Erro RAG/Skills para {agent_name}: {e}")

    # ── Memory injection (PRD #11) ──
    if agent_name and enable_context:
        try:
            from agent_memory import get_memory, gerar_prompt_com_memoria

            _mem_core, _mem_warm, _mem_nicho = get_memory()
            if _mem_core and _mem_warm and _mem_nicho:
                system = gerar_prompt_com_memoria(
                    system, agent_name.lower(), _mem_nicho, _mem_core, _mem_warm
                )
        except Exception:
            pass

    # ── Model routing ──
    _db_config = None
    if agent_name and respect_agent_config:
        _all_configs = _load_agent_configs()
        _db_config = _all_configs.get(agent_name.lower())

    if _db_config:
        _db_provider = (_db_config.get("provider") or "anthropic").lower()
        model_id = _db_config["model_id"]
        if _db_config.get("temperature") is not None:
            temperature = _db_config["temperature"]
        if _db_config.get("max_tokens") is not None:
            if (agent_name or "").lower() == BUILDER_RENDERER_AGENT:
                max_tokens = max(int(max_tokens or 0), int(_db_config["max_tokens"] or 0))
            else:
                max_tokens = _db_config["max_tokens"]
        print(
            f"[LLM Router] {agent_name} -> {_db_config['provider']}/{model_id} (DB config)"
        )
    else:
        _db_provider = "anthropic"
        _routed = False
        if agent_name and respect_agent_config:
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

        if not _routed and agent_name and respect_agent_config and not fallbacks_disabled():
            _auto = AGENT_MODEL_MAP.get(agent_name.lower())
            if _auto:
                model = _auto
                print(f"[LLM Router] {agent_name} -> {model} (hardcoded fallback)")

        current_map = LITELLM_MODEL_MAP if LITELLM_API_KEY else AIBEE_MODEL_MAP
        model_id = current_map.get(model, current_map["opus"])

    if _db_config and _db_provider != "anthropic":
        try:
            from services.llm_router import call_llm
        except Exception:
            from llm_router import call_llm

        routed_user = user
        if rag_block:
            routed_user = f"{rag_block}\n\n{user}"
        routed_started = _time.time()
        try:
            routed_text, routed_usage = call_llm(
                provider=_db_provider,
                model_id=model_id,
                system=system or "",
                user=routed_user,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            _alert_llm_provider_failure(
                _db_provider,
                model_id,
                e,
                source=agent_name or "agent_model_config",
            )
            raise
        input_tokens = int(routed_usage.get("input_tokens", 0) or 0)
        output_tokens = int(routed_usage.get("output_tokens", 0) or 0)
        latency_ms = int((_time.time() - routed_started) * 1000)
        print(
            f"[LLM] provider={_db_provider} model={model_id} in={input_tokens} out={output_tokens} agent={agent_name or '-'}"
        )
        _salvar_uso_llm(model_id, input_tokens, output_tokens, agent_name)
        _registrar_llm_budget(
            model_id,
            input_tokens,
            output_tokens,
            agente=agent_name,
            provider=_db_provider,
            latency_ms=latency_ms,
        )
        try:
            try:
                from agents.token_tracker import get_tracker
            except Exception:
                from token_tracker import get_tracker

            _tracker = get_tracker()
            if _tracker:
                _tracker.registrar(
                    agente=agent_name or "unknown",
                    model=model_id,
                    usage={
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    },
                )
        except Exception:
            pass
        return routed_text

    # ── Resolve key/base_url ──
    if base_url:
        _api_key = _get_byok_key() or ANTHROPIC_API_KEY
        _key_id = None
        _base = base_url
    else:
        _api_key, _base, _key_id = _resolve_anthropic(agent_name)

    # ── Prompt caching: system payload ──
    extra_headers = {}
    cache_ativo = False
    if system and len(system) >= 1024:
        system_payload = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]
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
    if _key_id is not None and request_user_id:
        allowed, wait, count = _tenant_rate_check(request_user_id)
        if not allowed:
            _tenant_rate_alert(request_user_id, wait, count)
            _time.sleep(min(wait, llm_config.TENANT_THROTTLE_WAIT))
            allowed2, wait2, _ = _tenant_rate_check(request_user_id)
            if not allowed2:
                _time.sleep(wait2)

    # ── ia_manager ref ──
    try:
        import ia_manager as _ia
    except Exception:
        _ia = None

    # ── Pre-flight: Circuit Breaker + Budget checks ──
    if _ia and not base_url:
        try:
            # Fase 1: Circuit breaker global
            _cooled, _cd_remaining = _ia.is_globally_cooled_down()
            if _cooled and _cd_remaining > 60:
                print(
                    f"[LLM] Circuit breaker OPEN — cooldown {_cd_remaining}s restantes"
                )
                raise RateLimitError(_cd_remaining)

            # Fase 2: Budget diario global
            _budget_ok, _budget_remaining = _ia.check_daily_budget()
            if not _budget_ok:
                print(f"[LLM] Budget diario ESGOTADO — 0 tokens restantes")
                raise Exception(
                    "Budget diario de tokens esgotado. Aguarde reset (24h rolling window)."
                )

            # Fase 3: Budget por tenant
            if request_user_id:
                _plano = "starter"
                try:
                    from backend.core.database import engine as _budget_engine
                    from sqlalchemy import text as _budget_text

                    with _budget_engine.connect() as _bconn:
                        _prow = _bconn.execute(
                            _budget_text("SELECT plano FROM users WHERE id = :uid"),
                            {"uid": request_user_id},
                        ).fetchone()
                        if _prow:
                            _plano = (_prow[0] or "starter").lower()
                except Exception:
                    pass
                _tenant_ok, _tenant_remaining = _ia.check_tenant_budget(
                    request_user_id, _plano
                )
                if not _tenant_ok:
                    print(
                        f"[LLM] Tenant {request_user_id} budget ESGOTADO (plano={_plano})"
                    )
                    raise Exception(
                        f"Limite diario de tokens atingido para seu plano ({_plano}). Upgrade para mais capacidade."
                    )

            # Fase 5: Coordenacao cross-process
            _rate_ok, _rate_count = _ia.check_global_call_rate()
            if not _rate_ok:
                import time as _time_bp

                _time_bp.sleep(2)
        except RateLimitError:
            raise
        except Exception as _preflight_err:
            if "Budget" in str(_preflight_err) or "Limite" in str(_preflight_err):
                raise
            print(f"[LLM] Pre-flight check erro (ignorando): {_preflight_err}")

    # ── Token Bucket: throttle preventivo ──
    if not base_url:
        try:
            from services.token_bucket import throttle as _tb_throttle

            _input_est = (len(system or "") + len(user or "")) // 4
            _total_est = _input_est + max_tokens
            _tb_throttle(_total_est)
        except Exception:
            pass

    if _is_litellm_openai_chat_base(_base):
        chat_user = f"{rag_block}\n\n{user}" if rag_block else user
        chat_started = _time.time()
        try:
            chat_text, chat_usage = _call_litellm_openai_chat(
                api_key=_api_key,
                base_url=_base,
                model_id=model_id,
                system=system or "",
                user=chat_user,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            _alert_llm_provider_failure(
                PROXY_PROVIDER,
                model_id,
                e,
                key_id=_key_id if isinstance(_key_id, int) else None,
                source=agent_name or "call_claude_openai_chat",
                mark_env_fallback=not isinstance(_key_id, int),
            )
            raise

        input_tokens = int(chat_usage.get("input_tokens", 0) or 0)
        output_tokens = int(chat_usage.get("output_tokens", 0) or 0)
        latency_ms = int((_time.time() - chat_started) * 1000)
        print(
            f"[LLM ChatProxy] model={model_id} in={input_tokens} out={output_tokens} agent={agent_name or '-'}"
        )
        _salvar_uso_llm(model_id, input_tokens, output_tokens, agent_name)
        _registrar_llm_budget(
            model_id,
            input_tokens,
            output_tokens,
            agente=agent_name,
            provider=PROXY_PROVIDER,
            latency_ms=latency_ms,
        )
        try:
            try:
                from agents.token_tracker import get_tracker
            except Exception:
                from token_tracker import get_tracker

            _tracker = get_tracker()
            if _tracker:
                _tracker.registrar(
                    agente=agent_name or "unknown",
                    model=model_id,
                    usage={
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    },
                )
        except Exception:
            pass
        if _ia and isinstance(_key_id, int):
            _ia.mark_success(_key_id)
        return chat_text

    # ── SDK retry loop ──
    MAX_ATTEMPTS = 5
    response = None
    print(
        f"[LLM] model={model_id} cache={'on' if cache_ativo else 'off'} agent={agent_name or '-'}"
    )

    for _attempt in range(1, MAX_ATTEMPTS + 1):
        _enforce_call_spacing()
        client = _create_client(_api_key, _base)
        _call_started = _time.time()
        try:
            response = client.messages.create(
                model=model_id,
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
            cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
            cache_created = getattr(usage, "cache_creation_input_tokens", 0) or 0
            latency_ms = int((_time.time() - _call_started) * 1000)
            if cache_read or cache_created:
                print(
                    f"[LLM] stop={response.stop_reason} in={input_tokens} out={output_tokens} cache_read={cache_read} cache_created={cache_created}"
                )
            else:
                print(
                    f"[LLM] stop={response.stop_reason} in={input_tokens} out={output_tokens}"
                )

            _salvar_uso_llm(model_id, input_tokens, output_tokens, agent_name)
            _registrar_llm_budget(
                model_id,
                input_tokens,
                output_tokens,
                cache_read=cache_read,
                cache_created=cache_created,
                agente=agent_name,
                latency_ms=latency_ms,
            )

            try:
                try:
                    from agents.token_tracker import get_tracker
                except Exception:
                    from token_tracker import get_tracker

                _tracker = get_tracker()
                if _tracker:
                    _tracker.registrar(
                        agente=agent_name or "unknown",
                        model=model_id,
                        usage={
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "cache_read_input_tokens": cache_read,
                            "cache_creation_input_tokens": cache_created,
                        },
                    )
            except Exception:
                pass

            if _ia and _key_id:
                _ia.mark_success(_key_id)

            # ── Extract text from response ──
            for block in response.content:
                if block.type == "text":
                    return block.text

            # ── Proxy workaround: tool_use text extraction ──
            return _extract_text_from_tool_use(
                response,
                client,
                model_id,
                max_tokens,
                temperature,
                system,
                user,
                extra_headers,
            )

        except anthropic.RateLimitError as e:
            cd = 60
            if _ia:
                try:
                    cd = _ia.parse_cooldown_from_response(
                        429, dict(e.response.headers) if e.response else {}
                    )
                except Exception:
                    pass
            if _ia and _key_id:
                _ia.mark_failure(_key_id, "429 rate limit", cd)
                if _attempt == 1:
                    _ia.raise_alert(
                        "rate_limit",
                        _key_id,
                        f"429 em call_claude (cooldown {cd}s)",
                        lead_id=None,
                        user_id=request_user_id,
                    )
            if _attempt >= MAX_ATTEMPTS:
                if _ia:
                    _ia.raise_alert(
                        "all_keys_failed",
                        _key_id,
                        f"Rate limit persistente apos {MAX_ATTEMPTS} tentativas",
                        lead_id=None,
                        user_id=request_user_id,
                    )
                raise RateLimitError(reset_seconds=cd)
            if base_url is None:
                new_key = _resolve_anthropic(agent_name)
                if new_key and new_key[2] != _key_id:
                    _api_key, _base, _key_id = new_key
                    wait = min(10 * _attempt, 20)
                    print(
                        f"[LLM] 429 — trocou key, aguardando {wait}s (tentativa {_attempt}/{MAX_ATTEMPTS})"
                    )
                else:
                    wait = min(cd, 60)
                    print(
                        f"[LLM] 429 — 1 key no pool, aguardando cooldown {wait}s (tentativa {_attempt}/{MAX_ATTEMPTS})"
                    )
            else:
                wait = min(cd, 60)
                print(
                    f"[LLM] 429 — aguardando {wait}s (tentativa {_attempt}/{MAX_ATTEMPTS})"
                )
            _time.sleep(wait)

        except anthropic.APIStatusError as e:
            if e.status_code in (529, 503, 502):
                if _ia and _key_id:
                    _ia.mark_failure(_key_id, f"{e.status_code} overloaded", 30)
                if base_url is None:
                    new_key = _resolve_anthropic(agent_name)
                    if new_key and new_key[2] != _key_id:
                        _api_key, _base, _key_id = new_key
                wait = min(20 * _attempt, 60)
                print(
                    f"[LLM] {e.status_code} Overloaded - aguardando {wait}s (tentativa {_attempt}/{MAX_ATTEMPTS})"
                )
                _time.sleep(wait)
            elif e.status_code == 400:
                print(f"[LLM] 400 Bad Request (tentativa {_attempt}/{MAX_ATTEMPTS})")
                if _attempt < MAX_ATTEMPTS:
                    _time.sleep(5 * _attempt)
                else:
                    raise
            elif e.status_code in (401, 403):
                _alert_llm_provider_failure(
                    "anthropic",
                    model_id,
                    e,
                    key_id=_key_id,
                    source=agent_name or "call_claude",
                    mark_env_fallback=True,
                )
                raise
            else:
                raise
        except (anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
            if _attempt >= MAX_ATTEMPTS:
                raise
            wait = min(15 * _attempt, 60)
            print(
                f"[LLM] timeout/conexao {type(e).__name__} - aguardando {wait}s (tentativa {_attempt}/{MAX_ATTEMPTS})"
            )
            _time.sleep(wait)

    # Esgotou tentativas
    if _ia:
        _ia.raise_alert(
            "all_keys_failed",
            _key_id,
            "Todas as tentativas de call_claude falharam",
            lead_id=None,
            user_id=request_user_id,
        )
    raise RuntimeError(f"[LLM] Falhou apos {MAX_ATTEMPTS} tentativas")


# ─────────────────────────────────────────────────────────────────
# PUBLIC API — call_claude_structured
# ─────────────────────────────────────────────────────────────────
def call_claude_structured(
    system,
    user,
    tool_name,
    tool_description,
    input_schema,
    model="opus",
    max_tokens=8000,
    temperature=0.7,
    agent_name=None,
    enable_context=True,
):
    """Chama Claude com tool_use para forcar retorno de JSON estruturado."""
    request_user_id = get_current_user_id()
    model_map = LITELLM_MODEL_MAP if LITELLM_API_KEY else AIBEE_MODEL_MAP
    if agent_name and enable_context:
        _auto = AGENT_MODEL_MAP.get(agent_name.lower())
        if _auto:
            model = _auto
            print(f"[LLM Structured Router] {agent_name} -> {model} (hardcoded fallback)")
    model_id = model_map.get(model, model_map["opus"])

    _api_key, _base, _key_id = _resolve_anthropic(agent_name)

    # Prompt caching no system
    extra_headers = {}
    if system and len(system) >= 1024:
        system_payload = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]
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
                tools=[
                    {
                        "name": tool_name,
                        "description": tool_description,
                        "input_schema": input_schema,
                    }
                ],
                tool_choice={"type": "tool", "name": tool_name},
                extra_headers=extra_headers if extra_headers else None,
            )

            # Log usage
            usage = response.usage
            input_tokens = usage.input_tokens
            output_tokens = usage.output_tokens
            cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
            cache_created = getattr(usage, "cache_creation_input_tokens", 0) or 0
            if cache_read or cache_created:
                print(
                    f"[LLM Structured] stop={response.stop_reason} in={input_tokens} out={output_tokens} cache_read={cache_read} cache_created={cache_created}"
                )
            else:
                print(
                    f"[LLM Structured] stop={response.stop_reason} in={input_tokens} out={output_tokens}"
                )

            _salvar_uso_llm(
                model_id, input_tokens, output_tokens, f"structured_{tool_name}"
            )

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

            raise RuntimeError(
                f"[LLM Structured] Nenhum tool_use block na resposta (stop={response.stop_reason})"
            )

        except anthropic.RateLimitError as e:
            cd = 60
            if _ia:
                try:
                    cd = _ia.parse_cooldown_from_response(
                        429, dict(e.response.headers) if e.response else {}
                    )
                except Exception:
                    pass
            if _ia and _key_id:
                _ia.mark_failure(_key_id, "429 rate limit", cd)
                _ia.raise_alert(
                    "rate_limit",
                    _key_id,
                    f"429 em call_claude_structured (cooldown {cd}s)",
                    lead_id=None,
                    user_id=request_user_id,
                )
            if _attempt >= 3:
                raise RateLimitError(reset_seconds=cd)
            _api_key, _base, _key_id = _resolve_anthropic(agent_name)
            wait = min(15 * _attempt, 30)
            print(
                f"[LLM Structured] 429 — trocando key, aguardando {wait}s (tentativa {_attempt}/3)"
            )
            _time.sleep(wait)

        except anthropic.APIStatusError as e:
            if e.status_code in (401, 403):
                _alert_llm_provider_failure(
                    "anthropic",
                    model_id,
                    e,
                    key_id=_key_id,
                    source=f"call_claude_structured:{tool_name}",
                    mark_env_fallback=True,
                )
            raise

    raise RuntimeError("[LLM Structured] Falhou apos 3 tentativas")


# ─────────────────────────────────────────────────────────────────
# ADDITIONAL UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────
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
    """Chama Claude e retorna JSON parseado. Retry automatico em parse failure.

    Args:
        output_model: Pydantic BaseModel class (opcional). Se passado, valida e retorna instância.
        retries: Tentativas extras em caso de JSON invalido.

    Returns:
        dict (ou instância Pydantic se output_model passado)
    """
    json_instruction = "\n\nResponda EXCLUSIVAMENTE com JSON valido. Sem markdown, sem texto antes ou depois."
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
                print(
                    f"[LLM JSON] Parse falhou (tentativa {attempt}/{retries + 1}): {e}"
                )
                _time.sleep(2 * attempt)
            else:
                break

    raise RuntimeError(
        f"[LLM JSON] JSON parse falhou apos {retries + 1} tentativas: {last_error}"
    )


def call_claude_stream(
    system: str,
    user: str,
    model: str = "opus",
    max_tokens: int = 16384,
    temperature: float = 0.7,
    agent_name: str = None,
    on_chunk: Callable = None,
    enable_context: bool = True,
) -> str:
    """Streaming com callback por chunk. Retorna texto completo ao final."""

    # Model routing
    _db_config = None
    if agent_name and enable_context:
        _all_configs = _load_agent_configs()
        _db_config = _all_configs.get(agent_name.lower())

    current_map = LITELLM_MODEL_MAP if LITELLM_API_KEY else AIBEE_MODEL_MAP

    if _db_config:
        model_id = _db_config["model_id"]
        if _db_config.get("temperature") is not None:
            temperature = _db_config["temperature"]
        if _db_config.get("max_tokens") is not None:
            max_tokens = _db_config["max_tokens"]
    else:
        model_id = current_map.get(model, current_map["opus"])

    _api_key, _base, _key_id = _resolve_anthropic(agent_name)

    # Prompt caching
    extra_headers = {}
    if system and len(system) >= 1024:
        system_payload = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]
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
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_created = getattr(usage, "cache_creation_input_tokens", 0) or 0
    if cache_read or cache_created:
        print(
            f"[LLM Stream] stop={response.stop_reason} in={input_tokens} out={output_tokens} cache_read={cache_read}"
        )
    else:
        print(
            f"[LLM Stream] stop={response.stop_reason} in={input_tokens} out={output_tokens}"
        )
    _salvar_uso_llm(model_id, input_tokens, output_tokens, agent_name)

    if _key_id:
        try:
            import ia_manager as _ia

            _ia.mark_success(_key_id)
        except Exception:
            pass

    return full_text


def call_claude_cached(
    system: str,
    user: str,
    model: str = "sonnet",
    max_tokens: int = 4096,
    temperature: float = 0.7,
    agent_name: str = None,
    cache_user_prefix: str = None,
) -> str:
    """Chamada com prompt caching explicito. Cacheia system + opcionalmente prefixo do user.

    Args:
        cache_user_prefix: Se passado, este texto e cacheado como primeiro bloco do user message.
    """
    _api_key, _base, _key_id = _resolve_anthropic(agent_name)

    current_map = LITELLM_MODEL_MAP if LITELLM_API_KEY else AIBEE_MODEL_MAP
    model_id = current_map.get(model, current_map["opus"])

    system_payload = [
        {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
    ]

    if cache_user_prefix:
        messages_content = [
            {
                "type": "text",
                "text": cache_user_prefix,
                "cache_control": {"type": "ephemeral"},
            },
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
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_created = getattr(usage, "cache_creation_input_tokens", 0) or 0
    print(
        f"[LLM Cached] in={input_tokens} out={output_tokens} cache_read={cache_read} cache_created={cache_created}"
    )
    _salvar_uso_llm(model_id, input_tokens, output_tokens, agent_name)

    for block in response.content:
        if block.type == "text":
            return block.text

    raise RuntimeError("[LLM Cached] Nenhum bloco text na resposta")
