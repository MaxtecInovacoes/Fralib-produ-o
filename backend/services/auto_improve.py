"""auto_improve.py - Sprint 8 (v1.11) - Auto-melhoria de prompts via traces.

Analisa traces do `tracing.py` (Sprint 5) e sugere melhorias nos system prompts
dos 4 agentes (nicho / arquiteto / builder / validador) baseadas em padroes
de sucesso/falha observados.

Reuso explicito:
    - `backend.services.tracing.get_stats` — ja agrega metricas por agente/dia.
    - `backend.services.tracing.TRACES_DIR` — diretorio dos JSONL append-only.
    - `backend.services.tracing.trace_run` — usado para tracejar este proprio
      servico (operacao "analyze" / "suggest" / "evolve").

Regras de design:
    - Funcoes PURAS sempre que possivel (testaveis sem I/O).
    - NUNCA modifica system prompts existentes automaticamente — apenas
      persiste versoes v2 em `backend/agents/_prompts_v2/`.
    - Gate conservador: `should_apply_v2` exige `min_samples=10` E `delta>5%`.
    - Comentarios em PT-BR.

Schemas persistidos em `backend/agents/_prompts_v2/<agent>.json`:
    {
      "agent": "nicho",
      "versions": [
        {
          "version": "v2",
          "prompt": "...",
          "created_at": "2026-06-26T...",
          "suggestions": ["..."],
          "stats": {"count": N, "success_rate": 0.91}
        }
      ],
      "active_version": "v1"
    }

Endpoint layer em `backend.endpoints.admin_prompts_endpoints` consome este
modulo (analise + apply + listagem).
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════════

# Gate conservador para aplicar v2
DEFAULT_MIN_SAMPLES = 10          # precisa de pelo menos 10 traces
DEFAULT_DELTA_THRESHOLD = 0.05    # ganho minimo de 5pp em success_rate

# 4 agentes suportados (sincronizado com tracing.KNOWN_AGENTS - sem franz)
SUPPORTED_AGENTS: tuple[str, ...] = ("nicho", "arquiteto", "builder", "validador")

# Diretorio onde os JSON de versoes v2 sao persistidos
PROMPTS_V2_DIR = Path(
    os.getenv("FRALIB_PROMPTS_V2_DIR", "backend/agents/_prompts_v2")
)
PROMPTS_V2_DIR.mkdir(parents=True, exist_ok=True)


# ════════════════════════════════════════════════════════════════════
# TRACING (reuso do tracing.py)
# ════════════════════════════════════════════════════════════════════

def _trace(operation: str, metadata: Optional[dict] = None) -> Any:
    """Wrapper de trace_run do tracing.py — nao quebra se tracing desabilitado.

    Args:
        operation: nome da operacao (analyze / suggest / evolve / persist).
        metadata: contexto extra (agent, min_samples etc).

    Returns:
        Context manager (pode ser `with` ou no-op).
    """
    try:
        from backend.services.tracing import trace_run
        return trace_run("auto_improve", operation, metadata=metadata or {})
    except Exception:
        # tracing desabilitado ou indisponivel — no-op silencioso
        @contextmanager
        def _noop():
            yield None
        return _noop()


# ════════════════════════════════════════════════════════════════════
# LEITURA DE TRACES (funcao de I/O)
# ════════════════════════════════════════════════════════════════════

def _read_traces_for_agent(agent: str, days: int) -> list[dict[str, Any]]:
    """Le traces dos ultimos `days` dias, filtrados por agente.

    Reusa a logica de `tracing.get_stats` porem retorna a lista bruta
    (necessaria para identificar padroes de input/output, nao so medias).
    """
    from backend.services.tracing import TRACES_DIR, TRACING_ENABLED

    if not TRACING_ENABLED:
        return []

    out: list[dict[str, Any]] = []
    try:
        for day_offset in range(days):
            day = time.strftime(
                "%Y-%m-%d", time.localtime(time.time() - day_offset * 86400)
            )
            path = TRACES_DIR / f"traces_{day}.jsonl"
            if not path.is_file():
                continue
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        t = json.loads(line)
                        if t.get("agent") == agent:
                            out.append(t)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.warning(f"[auto_improve] _read_traces_for_agent falhou: {e}")
    return out


# ════════════════════════════════════════════════════════════════════
# ANALYZE — identifica padroes
# ════════════════════════════════════════════════════════════════════

def analyze_traces(days: int = 7, min_samples: int = DEFAULT_MIN_SAMPLES) -> dict[str, Any]:
    """Analisa traces dos ultimos `days` dias para todos os 4 agentes.

    Identifica padroes de:
        - success_rate por agente
        - operacoes com mais falhas
        - latencia media
        - tokens medios
        - inputs com baixa confianca (campo metadata.confianca == "baixa")

    Args:
        days: janela de analise em dias (default 7).
        min_samples: minimo de traces para considerar agente confiavel.

    Returns:
        Dict com:
            {
              "days": int,
              "min_samples": int,
              "agents": {
                "nicho": {"count": N, "success_rate": 0.x, "stats": {...},
                          "patterns": {"low_confianca_pct": 0.x, ...}},
                ...
              }
            }
    """
    with _trace("analyze", {"days": days, "min_samples": min_samples}):
        result: dict[str, Any] = {
            "days": days,
            "min_samples": min_samples,
            "agents": {},
        }

        from backend.services.tracing import get_stats

        for agent in SUPPORTED_AGENTS:
            traces = _read_traces_for_agent(agent, days)
            count = len(traces)

            # Reuso de get_stats — fornece latency/cost agregados
            stats = get_stats(agent=agent, days=days)

            # Calcula success_rate localmente (defensivo)
            if count > 0:
                errors = sum(1 for t in traces if not t.get("success", True))
                success_rate = round(1.0 - (errors / count), 4)
            else:
                success_rate = 1.0

            # Padroes: % de inputs com baixa confianca (heuristica simples)
            low_conf_count = 0
            low_conf_inputs: list[dict] = []
            for t in traces:
                meta = t.get("metadata") or {}
                conf = meta.get("confianca") or meta.get("confidence")
                if conf in ("baixa", "low", 0):
                    low_conf_count += 1
                    if len(low_conf_inputs) < 3:
                        low_conf_inputs.append(t.get("inputs") or {})

            patterns = {
                "low_confianca_pct": round(low_conf_count / count, 4) if count else 0.0,
                "low_confianca_examples": low_conf_inputs,
                "operation_failures": _operation_failures(traces),
            }

            result["agents"][agent] = {
                "count": count,
                "success_rate": success_rate,
                "stats": stats,
                "patterns": patterns,
                "reliable": count >= min_samples,
            }

        return result


def _operation_failures(traces: list[dict[str, Any]]) -> dict[str, int]:
    """Conta falhas por tipo de operacao (funcao pura)."""
    out: dict[str, int] = {}
    for t in traces:
        if t.get("success", True):
            continue
        op = t.get("operation", "unknown")
        out[op] = out.get(op, 0) + 1
    return out


# ════════════════════════════════════════════════════════════════════
# SUGGEST — gera sugestoes em texto (PT-BR)
# ════════════════════════════════════════════════════════════════════

def suggest_prompt_improvements(agent: str) -> list[str]:
    """Gera lista de sugestoes de melhoria para o prompt do agente.

    Heuristicas (testaveis isoladamente via `analyze_traces`):
        - success_rate < 1.0  -> "Adicionar exemplo de tratamento de erro"
        - low_confianca_pct > 0.2 -> "Reforcar instrucoes de inferencia confiavel"
        - operation_failures com chaves -> "Documentar melhor a op X"

    Args:
        agent: nome do agente (nicho/arquiteto/builder/validador).

    Returns:
        Lista de strings (sugestoes em PT-BR).
    """
    with _trace("suggest", {"agent": agent}):
        if agent not in SUPPORTED_AGENTS:
            return [f"Agente '{agent}' nao suportado (esperado: {SUPPORTED_AGENTS})"]

        analysis = analyze_traces(days=7).get("agents", {}).get(agent, {})
        if not analysis.get("reliable"):
            return [
                f"Dados insuficientes para '{agent}' "
                f"(count={analysis.get('count', 0)} < min_samples). "
                "Coletar mais traces antes de sugerir melhorias."
            ]

        suggestions: list[str] = []
        success_rate = analysis.get("success_rate", 1.0)
        patterns = analysis.get("patterns", {}) or {}
        op_failures = patterns.get("operation_failures", {}) or {}

        # Regra 1: success_rate baixo
        if success_rate < 0.95:
            suggestions.append(
                f"Adicionar exemplo explicito de tratamento de erro "
                f"(success_rate atual: {success_rate:.2%})."
            )

        # Regra 2: baixa confianca recorrente
        low_pct = patterns.get("low_confianca_pct", 0.0)
        if low_pct > 0.2:
            suggestions.append(
                f"Reforcar instrucoes de inferencia confiavel "
                f"({low_pct:.0%} dos inputs marcados como 'baixa')."
            )

        # Regra 3: operacoes com falhas
        for op, n_fail in op_failures.items():
            if n_fail >= 2:
                suggestions.append(
                    f"Documentar melhor a operacao '{op}' "
                    f"(falhou {n_fail}x nos ultimos 7 dias)."
                )

        # Regra 4: fallback sempre presente
        if not suggestions:
            suggestions.append(
                "Sem padroes problematicos detectados. Manter prompt atual."
            )

        return suggestions


# ════════════════════════════════════════════════════════════════════
# EVOLVE — gera versao v2 do prompt (funcao pura)
# ════════════════════════════════════════════════════════════════════

def evolve_prompt(agent: str, current_prompt: str, suggestions: list[str]) -> str:
    """Aplica sugestoes ao prompt atual, retornando versao v2.

    A v2 eh o prompt original + secao APPEND-only com as sugestoes em PT-BR.
    NAO remove/modifica nada do prompt original (preserva rastreabilidade).

    Args:
        agent: nome do agente.
        current_prompt: prompt original (v1).
        suggestions: lista de sugestoes (ja geradas por suggest_*).

    Returns:
        String com o prompt v2 (original + apendice).
    """
    with _trace("evolve", {"agent": agent, "n_suggestions": len(suggestions)}):
        if not suggestions:
            return current_prompt

        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        appendix_lines = [
            "",
            "",
            "# ═══════════════════════════════════════════════════════════════",
            f"# AUTO-IMPROVE v2 ({agent}) — gerado em {ts}",
            "# ═══════════════════════════════════════════════════════════════",
            "# As instrucoes abaixo foram acrescentadas automaticamente pelo",
            "# servico auto_improve.py baseando-se em traces recentes.",
            "# NAO remova esta secao sem revisar /api/admin/prompts/analyze.",
            "",
            "## ADDITIONAL GUIDELINES (Sprint 8 v1.11):",
            "",
        ]
        for s in suggestions:
            appendix_lines.append(f"- {s}")

        appendix_lines.append("")
        appendix_lines.append(
            "## RULE: se algum guideline acima conflitar com o corpo do "
            "prompt, siga o guideline (sao instrucoes mais recentes e "
            "baseadas em dados reais de producao)."
        )

        return current_prompt.rstrip() + "\n" + "\n".join(appendix_lines) + "\n"


# ════════════════════════════════════════════════════════════════════
# PERSIST — salva/recupera versoes v2 em JSON
# ════════════════════════════════════════════════════════════════════

def _prompt_path(agent: str) -> Path:
    """Caminho do JSON de versoes para um agente."""
    safe = re.sub(r"[^a-z0-9_]", "", agent.lower())
    return PROMPTS_V2_DIR / f"{safe}.json"


def _load_versions(agent: str) -> dict[str, Any]:
    """Carrega JSON de versoes (retorna skeleton se nao existir)."""
    path = _prompt_path(agent)
    if not path.is_file():
        return {"agent": agent, "versions": [], "active_version": "v1"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Compat: garante chaves basicas
            data.setdefault("versions", [])
            data.setdefault("active_version", "v1")
            return data
    except Exception as e:
        logger.warning(f"[auto_improve] _load_versions falhou para {agent}: {e}")
        return {"agent": agent, "versions": [], "active_version": "v1"}


def _save_versions(agent: str, data: dict[str, Any]) -> None:
    """Persiste JSON de versoes atomicamente."""
    path = _prompt_path(agent)
    tmp = path.with_suffix(".json.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as e:
        logger.error(f"[auto_improve] _save_versions falhou para {agent}: {e}")


def persist_prompt_version(agent: str, version: str, prompt: str) -> None:
    """Persiste uma nova versao (v2/v3/...) para o agente.

    Args:
        agent: nome do agente.
        version: identificador da versao (ex: "v2").
        prompt: texto do prompt.
    """
    with _trace("persist", {"agent": agent, "version": version}):
        data = _load_versions(agent)

        # Coleta stats atuais para registrar junto da versao
        from backend.services.tracing import get_stats

        stats = get_stats(agent=agent, days=7)
        suggestions = suggest_prompt_improvements(agent)

        entry = {
            "version": version,
            "prompt": prompt,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "suggestions": suggestions,
            "stats": {
                "count": stats.get("count", 0),
                "success_rate": stats.get("success_rate", 1.0),
            },
        }
        # Substitui se ja existir
        data["versions"] = [
            v for v in data.get("versions", []) if v.get("version") != version
        ]
        data["versions"].append(entry)
        _save_versions(agent, data)


def get_best_prompt(agent: str) -> str:
    """Retorna a versao com MAIOR success_rate (ou "" se nenhuma persistida).

    Args:
        agent: nome do agente.

    Returns:
        String do prompt escolhido. Se nao ha versoes salvas, retorna "".
    """
    data = _load_versions(agent)
    versions = data.get("versions", [])
    if not versions:
        return ""
    # Ordena por success_rate desc, depois por count desc (mais dados = melhor)
    sorted_v = sorted(
        versions,
        key=lambda v: (
            v.get("stats", {}).get("success_rate", 0.0),
            v.get("stats", {}).get("count", 0),
        ),
        reverse=True,
    )
    return sorted_v[0].get("prompt", "")


# ════════════════════════════════════════════════════════════════════
# GATE — should_apply_v2 (funcao pura, testavel)
# ════════════════════════════════════════════════════════════════════

def should_apply_v2(
    agent: str,
    min_samples: int = DEFAULT_MIN_SAMPLES,
    delta_threshold: float = DEFAULT_DELTA_THRESHOLD,
) -> bool:
    """Decide se a v2 merece ser ativada para o agente.

    Gate conservador:
        1. precisa ter >= min_samples traces no agente
        2. precisa existir versao v2 persistida com stats
        3. success_rate da v2 precisa ser >= success_rate atual + delta_threshold

    Args:
        agent: nome do agente.
        min_samples: minimo de traces (default 10).
        delta_threshold: ganho minimo (default 0.05 = 5pp).

    Returns:
        True se v2 deve ser ativada, False caso contrario.
    """
    data = _load_versions(agent)

    # Sem v2 persistida -> nao aplicar
    v2 = next(
        (v for v in data.get("versions", []) if v.get("version") == "v2"),
        None,
    )
    if v2 is None:
        return False

    # Min samples (medido sobre os traces do agente — mesmo gate de analyze)
    from backend.services.tracing import get_stats

    current_stats = get_stats(agent=agent, days=7)
    if current_stats.get("count", 0) < min_samples:
        return False

    # Delta de success_rate
    current_rate = current_stats.get("success_rate", 1.0)
    v2_rate = v2.get("stats", {}).get("success_rate", 0.0)
    return (v2_rate - current_rate) >= delta_threshold


# ════════════════════════════════════════════════════════════════════
# ACTIVE — get/set versao ativa
# ════════════════════════════════════════════════════════════════════

def get_active_version(agent: str) -> str:
    """Retorna a versao ativa atual (default 'v1' se nenhuma aplicada)."""
    data = _load_versions(agent)
    return data.get("active_version", "v1")


def set_active_version(agent: str, version: str) -> bool:
    """Ativa uma versao persistida para o agente.

    Args:
        agent: nome do agente.
        version: 'v1' (reverte) ou 'v2'/'v3'/... (ativa persistida).

    Returns:
        True se ativou, False se versao nao existe.
    """
    data = _load_versions(agent)
    if version != "v1":
        versions = data.get("versions", [])
        if not any(v.get("version") == version for v in versions):
            return False
    data["active_version"] = version
    _save_versions(agent, data)
    return True


def list_versions(agent: str) -> list[dict[str, Any]]:
    """Lista versoes persistidas (sem o campo 'prompt' para payload leve)."""
    data = _load_versions(agent)
    out = []
    for v in data.get("versions", []):
        out.append({
            "version": v.get("version"),
            "created_at": v.get("created_at"),
            "suggestions": v.get("suggestions", []),
            "stats": v.get("stats", {}),
        })
    return out


def get_active_prompt(agent: str) -> str:
    """Retorna o prompt da versao ativa. Se v1 ativa, retorna '' (prompt canonico)."""
    active = get_active_version(agent)
    if active == "v1":
        return ""
    data = _load_versions(agent)
    for v in data.get("versions", []):
        if v.get("version") == active:
            return v.get("prompt", "")
    return ""