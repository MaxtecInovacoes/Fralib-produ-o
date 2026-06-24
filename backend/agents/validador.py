"""Validador Final — revisa HTML antes do deploy: consistência, SEO,
acessibilidade, aderência ao PRD. Saída JSON."""

import sys, os

sys.path.insert(0, os.path.dirname(__file__))

from handoff_types import ValidacaoResultado
from llm_direct import call_claude

# Sprint 5 (v1.8) - tracing opt-in (zero overhead se FRALIB_TRACING=0)
try:
    from backend.services.tracing import trace_run
    _HAS_TRACING = True
except ImportError:
    _HAS_TRACING = False
    from contextlib import contextmanager
    @contextmanager
    def trace_run(*args, **kwargs):
        yield None

SYSTEM_PROMPT = """You are the Final Validator.

Your role is to review the final result before deployment.
You verify consistency, repetition, performance, accessibility, SEO, and PRD adherence.

INPUT:
- Final HTML
- PRD
- Design rules
- Niche rules

OUTPUT:
JSON only - no markdown, no extra explanation.

CHECKLIST:
- Does the page follow the PRD?
- Is the hero coherent with the niche?
- Is there excessive repetition?
- Is there CTA clarity?
- Is there adequate mobile structure?
- Is there clone risk?
- Is basic SEO correct?
- Is the site legible and consistent?

OUTPUT FORMAT JSON:
{
  "status": "approved|changes_required",
  "problemas": [],
  "prioridade": [],
  "observacoes": [],
  "correcoes_sugeridas": []
}

RULE:
If there is a critical error, do not approve.
If the problem is aesthetic, mark as observation.
Do not reject due to uncertainty caused by partial HTML preview; register as
observation. Reject only when the critical problem is visible in the provided
data or stats.

All user-facing copy MUST be in Brazilian Portuguese (pt-BR)."""

def validar(
    html: str,
    prd_text: str = "",
    segmento: str = "",
    task_id: str = "",
) -> ValidacaoResultado:
    _trace_inputs = {
        "segmento": segmento,
        "task_id": task_id,
        "html_len": len(html) if html else 0,
        "prd_len": len(prd_text) if prd_text else 0,
    }
    with trace_run("validador", "validar", inputs=_trace_inputs, metadata={
        "task_id": task_id,
    }):
        return _validar_impl(html, prd_text, segmento, task_id)


def _validar_impl(
    html: str,
    prd_text: str = "",
    segmento: str = "",
    task_id: str = "",
) -> ValidacaoResultado:
    if not html or len(html) < 500:
        return ValidacaoResultado(
            task_id=task_id,
            source_agent="validador",
            target_agent="deploy",
            status="ok",
            task_summary="HTML inválido ou muito curto — validação ignorada",
            aprovado=False,
            problemas=["HTML vazio ou muito curto"],
            prioridade=["crítica"],
            observacoes=["Pipeline deve rejeitar este HTML"],
        )

    _html_preview = html[:8000]
    _prd_preview = prd_text[:2000] if prd_text else "PRD não disponível"

    user_prompt = f"""Valide o HTML final contra o PRD.

== SEGMENTO ==
{segmento}

== PRD (resumo) ==
{_prd_preview}

== HTML (primeiros 8000 chars) ==
{_html_preview}

== HTML stats ==
Total chars: {len(html)}
Tem </html>: {"sim" if "</html>" in html.lower() else "não"}
Tem viewport: {"sim" if "viewport" in html else "não"}
Tem meta description: {"sim" if "description" in html or "descri" in html.lower()[:2000] else "não"}
Tem CTA WhatsApp: {"sim" if "whatsapp" in html.lower() or "+55" in html else "não"}
Tem schema.org: {"sim" if "schema.org" in html or "application/ld+json" in html else "não"}

Retorne APENAS o JSON — sem markdown, sem explicação extra."""
    import time as _time

    _start = _time.time()

    resposta = call_claude(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        model="haiku",
        max_tokens=1000,
        temperature=0.1,
        agent_name="validador",
    )

    _elapsed = _time.time() - _start

    import json as _json, re as _re

    _json_match = _re.search(r"\{.*\}", resposta, _re.DOTALL)
    _dados = {}
    if _json_match:
        try:
            _dados = _json.loads(_json_match.group(0))
        except _json.JSONDecodeError:
            pass

    _problemas = _dados.get("problemas", []) or []
    if not isinstance(_problemas, list):
        _problemas = [str(_problemas)]
    _incertezas = (
        "nao e possivel",
        "não é possível",
        "nao consigo",
        "não consigo",
        "não foi possível verificar",
        "nao foi possivel verificar",
    )
    _tem_problema_concreto = any(
        p and not any(token in str(p).lower() for token in _incertezas)
        for p in _problemas
    )
    _aprovado = _dados.get("status") == "approved" or not _tem_problema_concreto

    # v1.1-baseline-2026-06-23: calcula score 0-10 (LLM-as-judge)
    _score = float(_dados.get("score", 7.0 if _aprovado else 3.0))
    _score = max(0.0, min(10.0, _score))  # clamp [0, 10]
    # Problemas criticos derrubam o score
    if _problemas and any(
        "crític" in str(p).lower() or "critic" in str(p).lower()
        for p in _problemas
    ):
        _score = min(_score, 3.0)
        _aprovado = False

    return ValidacaoResultado(
        task_id=task_id,
        source_agent="validador",
        target_agent="deploy",
        status="ok" if _aprovado else "changes_required",
        task_summary=f"Validação {'aprovada' if _aprovado else 'rejeitada'} em {_elapsed:.1f}s",
        aprovado=_aprovado,
        score=_score,
        problemas=[] if _aprovado and not _tem_problema_concreto else _problemas,
        prioridade=_dados.get("prioridade", []),
        observacoes=_dados.get("observacoes", []),
        correcoes_sugeridas=_dados.get("correcoes_sugeridas", []),
    )
