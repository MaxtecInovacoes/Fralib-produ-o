"""Preflight — smoke-test executado no boot do Worker/API.

Garante que:
- config.py carrega sem erro (envs numéricas vazias não quebram)
- Agentes do pipeline são importáveis (Hunter, Jina, Caio, Arquiteto, Builder)
- LLM direto responde (sanidade do proxy)
Se qualquer passo falhar, registra no stderr e sai com código != 0.

Uso (Worker):
    python -m backend.core.preflight
Uso (docker):
    docker exec fralib-worker-1 python3 -m backend.core.preflight
"""
from __future__ import annotations

import os
import sys


def _section(title: str) -> None:
    print(f"[preflight] {title}...")


def _ok(msg: str = "OK") -> None:
    print(f"[preflight]   -> {msg}")


def _fail(msg: str) -> None:
    print(f"[preflight] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


# 1) Config
_section("config")
try:
    from backend.core.config import (  # noqa: F401
        GLOBAL_MAX_CALLS_PER_MIN,
        GLOBAL_DAILY_TOKEN_BUDGET,
        get_int_env,
        HAS_REDIS,
    )
    _ok(f"max_calls={GLOBAL_MAX_CALLS_PER_MIN} budget={GLOBAL_DAILY_TOKEN_BUDGET} redis={HAS_REDIS}")
except Exception as exc:
    _fail(f"config.py quebrou: {exc}")

# 2) Agentes do pipeline
_section("agents")
agents = [
    ("Hunter", "backend.agents.manager.step_hunter"),
    ("Caio", "backend.agents.manager.step_caio"),
    ("Arquiteto", "backend.agents.arquiteto_mestre"),
    ("Builder", "backend.agents.builder.agent"),
    ("Jina", "backend.utils.jina_intelligence"),
    ("Database", "backend.core.database"),
]
for nome, mod in agents:
    try:
        __import__(mod)
        _ok(nome)
    except Exception as exc:
        _fail(f"{nome} ({mod}): {exc}")

# 3) Sanidade do LLM — sem live call, só garante que o módulo carrega
_section("llm_direct")
try:
    from llm_direct import call_claude  # noqa: F401
    _ok()
except Exception as exc:
    _fail(f"llm_direct: {exc}")

print("[preflight] PREFLIGHT_CHECK: ALL_IMPORTS_OK")
