"""LLM-as-judge quality gate (Feature 2 do roadmap 10/10).

Apos cada LLM call do Franz, chama Haiku pra avaliar a resposta (1-5).
Bloqueia envio se score < 3.
Persiste score na LeadMemory.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    score: int  # 1-5
    issues: list[str]
    should_send: bool
    rationale: str = ""


SCORE_PROMPT = """Voce e um auditor de atendimento SDR WhatsApp. Avalie a resposta do bot ao lead.

CRITERIOS (cada um contribui 1 ponto se OK):
1. TOM HUMANO: parece conversa de WhatsApp real, nao corporativo/robótico? Max 3 linhas curtas?
2. REGRAS: respeita regra de ouro (nao revela preco antes de qualify, nao repete pergunta)?
3. CONTEXTO: responde ao que o lead disse agora, nao ignora?
4. PROGRESSO: faz o lead querer responder (pergunta engajante) ou encerra natural?
5. FORMATO: max 1 pergunta, max 1 emoji, sem markdown/links/JSON cru?

LEAD DISSE: {incoming}
STAGE: {stage}
RESPOSTA DO BOT: {reply}

Responda APENAS em JSON valido:
{{"score": 1-5, "issues": ["..."], "rationale": "..."}}

Se score >= 3, o bot pode enviar. Se < 3, liste o que precisa melhorar."""


def evaluate_reply(
    incoming: str,
    reply: str,
    stage: str = "hook",
    segmento: str = "",
    min_score_to_send: int = 3,
    enable_llm: bool = True,
) -> QualityScore:
    """Avalia uma resposta do Franz.

    Args:
        incoming: mensagem do lead.
        reply: resposta do bot.
        stage: stage atual (legado).
        segmento: nicho.
        min_score_to_send: score minimo para enviar (default 3).
        enable_llm: se True, usa Haiku. Se False, fallback heuristico.

    Returns:
        QualityScore com score (1-5), issues, should_send.
    """
    if not reply or not reply.strip():
        return QualityScore(score=0, issues=["resposta_vazia"], should_send=False, rationale="vazio")

    if not enable_llm:
        return _heuristic_evaluate(incoming, reply, min_score_to_send)

    try:
        from agents.llm_direct import call_claude
        prompt = SCORE_PROMPT.format(
            incoming=(incoming or "")[:500],
            stage=stage or "hook",
            reply=reply[:500],
        )
        raw = call_claude(
            system="Voce e um auditor. Responda SOMENTE em JSON valido, sem markdown.",
            user=prompt,
            model="haiku",
            max_tokens=200,
            temperature=0,
            agent_name="sdr_quality_judge",
            respect_agent_config=False,
            enable_context=False,
        )
        return _parse_judge_response(raw, min_score_to_send)
    except Exception as e:
        logger.warning(f"[judge] LLM falhou, usando heuristica: {e}")
        return _heuristic_evaluate(incoming, reply, min_score_to_send)


def _parse_judge_response(raw: str, min_score: int) -> QualityScore:
    """Parse robusto de JSON do LLM (mesmo com markdown ao redor)."""
    import json
    import re
    text = (raw or "").strip()
    # Tentar extrair JSON de dentro de markdown ```json ... ```
    m = re.search(r"\{[^{}]*\"score\"[^{}]*\}", text, re.S)
    if m:
        text = m.group(0)
    try:
        data = json.loads(text)
        score = int(data.get("score", 3))
        score = max(1, min(5, score))
        issues = data.get("issues") or []
        rationale = data.get("rationale", "")
        should_send = score >= min_score
        return QualityScore(
            score=score, issues=issues, should_send=should_send, rationale=rationale
        )
    except Exception as e:
        logger.warning(f"[judge] parse falhou ({e}); raw={raw[:200]}")
        return _heuristic_evaluate("", "", min_score)


def _heuristic_evaluate(incoming: str, reply: str, min_score: int) -> QualityScore:
    """Fallback heuristico sem LLM."""
    issues = []
    score = 5

    # max 1 pergunta
    if reply.count("?") > 1:
        issues.append("multiplas_perguntas")
        score -= 1

    # max 1 emoji (aproximado)
    emoji_count = sum(1 for ch in reply if ord(ch) > 0x2700 and ord(ch) < 0x27BF)
    if emoji_count > 1:
        issues.append("muitos_emojis")
        score -= 1

    # max 3 linhas
    linhas = reply.count("\n") + 1
    if linhas > 3:
        issues.append("muito_longa")
        score -= 1

    # sem markdown/JSON cru
    if reply.startswith("{") or "```" in reply or "**" in reply:
        issues.append("markdown_json_cru")
        score -= 1

    # max 300 chars
    if len(reply) > 300:
        issues.append("muito_longa_chars")
        score -= 1

    score = max(1, score)
    return QualityScore(
        score=score,
        issues=issues,
        should_send=score >= min_score,
        rationale=f"heuristic: {issues}",
    )