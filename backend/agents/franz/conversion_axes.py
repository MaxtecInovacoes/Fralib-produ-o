"""30 conversion axes — baked-in prompts (deterministic, não LLM-trained).

Cada eixo tem: label PT, prompt baked-in, peso (0.02–0.08).
Agrupados em 6 categorias: Foundational, Communication, Psychology, Process, Intelligence, Execution.
"""

from __future__ import annotations

__all__ = [
    "_CONVERSION_AXES",
    "_CONVERSION_AXIS_LABELS",
    "_CONVERSION_AXIS_WEIGHTS",
    "normalize_conversion_axis",
    "get_active_conversion_axes",
    "get_conversion_axis_prompts",
    "get_conversion_score_bonus",
]

# ---------------------------------------------------------------------------
# 30 axes em 6 grupos
# ---------------------------------------------------------------------------

_CONVERSION_AXES: tuple[str, ...] = (
    # Foundational (5)
    "authority",
    "scarcity",
    "urgency",
    "social_proof",
    "reciprocity",
    # Communication (6)
    "storytelling",
    "clarity",
    "objection_handling",
    "curiosity_gap",
    "personalization",
    "anchoring",
    # Psychology (6)
    "loss_aversion",
    "confirmation_bias",
    "liking",
    "commitment_consistency",
    "bandwagon",
    "contrast_principle",
    # Process (6)
    "step_by_step",
    "checklist",
    "follow_up",
    "qualification",
    "closing",
    "objection_prevention",
    # Intelligence (4)
    "data_driven",
    "competitive_intel",
    "timing",
    "segmentation",
    # Execution (3)
    "urgency_creation",
    "closing_technique",
    "follow_up_sequence",
)

# Labels PT-BR
_CONVERSION_AXIS_LABELS: dict[str, str] = {
    "authority": "Autoridade",
    "scarcity": "Escassez",
    "urgency": "Urgência",
    "social_proof": "Prova Social",
    "reciprocity": "Reciprocidade",
    "storytelling": "Storytelling",
    "clarity": "Clareza",
    "objection_handling": "Tratamento de Objeções",
    "curiosity_gap": "Curiosity Gap",
    "personalization": "Personalização",
    "anchoring": "Ancoragem",
    "loss_aversion": "Aversão à Perda",
    "confirmation_bias": "Viés de Confirmação",
    "liking": "Liking / Afinidade",
    "commitment_consistency": "Compromisso e Consistência",
    "bandwagon": "Efeito Manada",
    "contrast_principle": "Princípio do Contraste",
    "step_by_step": "Passo a Passo",
    "checklist": "Checklist",
    "follow_up": "Follow-up",
    "qualification": "Qualificação",
    "closing": "Fechamento",
    "objection_prevention": "Prevenção de Objeções",
    "data_driven": "Data-Driven",
    "competitive_intel": "Inteligência Competitiva",
    "timing": "Timing",
    "segmentation": "Segmentação",
    "urgency_creation": "Criação de Urgência",
    "closing_technique": "Técnica de Fechamento",
    "follow_up_sequence": "Sequência de Follow-up",
}

# Pesos padrão (somam-se ao conversion_score)
_CONVERSION_AXIS_WEIGHTS: dict[str, float] = {
    "authority": 0.05,
    "scarcity": 0.04,
    "urgency": 0.06,
    "social_proof": 0.05,
    "reciprocity": 0.04,
    "storytelling": 0.05,
    "clarity": 0.04,
    "objection_handling": 0.06,
    "curiosity_gap": 0.04,
    "personalization": 0.05,
    "anchoring": 0.03,
    "loss_aversion": 0.06,
    "confirmation_bias": 0.03,
    "liking": 0.04,
    "commitment_consistency": 0.05,
    "bandwagon": 0.04,
    "contrast_principle": 0.03,
    "step_by_step": 0.04,
    "checklist": 0.03,
    "follow_up": 0.04,
    "qualification": 0.05,
    "closing": 0.08,
    "objection_prevention": 0.05,
    "data_driven": 0.04,
    "competitive_intel": 0.03,
    "timing": 0.04,
    "segmentation": 0.03,
    "urgency_creation": 0.05,
    "closing_technique": 0.06,
    "follow_up_sequence": 0.04,
}

# Validar integridade
assert len(_CONVERSION_AXES) == 30, f"Esperado 30 axes, got {len(_CONVERSION_AXES)}"
assert len(_CONVERSION_AXIS_LABELS) == 30
assert len(_CONVERSION_AXIS_WEIGHTS) == 30
missing = [a for a in _CONVERSION_AXES if a not in _CONVERSION_AXIS_LABELS or a not in _CONVERSION_AXIS_WEIGHTS]
assert not missing, f"Missing labels/weights for: {missing}"


# ---------------------------------------------------------------------------
# Helpers públicos
# ---------------------------------------------------------------------------

def normalize_conversion_axis(raw: str | None) -> str:
    """Normaliza nome de eixo de venda para slug canônico.

    Aceita: nome canônico, label PT, aliases com/sem acento, case-insensitive.
    Levanta ValueError se não reconhecer.
    """
    if not raw or not isinstance(raw, str):
        raise ValueError("axis vazio")
    slug = raw.strip().lower().replace(" ", "_").replace("-", "_")

    # Remove acentos comuns (ã→a, ç→c, etc.)
    import unicodedata
    slug = "".join(
        c for c in unicodedata.normalize("NFD", slug)
        if unicodedata.category(c) != "Mn"
    )

    alias_map = {
        "autoridade": "authority",
        "escassez": "scarcity",
        "urgencia": "urgency",
        "urg": "urgency",
        "prova_social": "social_proof",
        "prova": "social_proof",
        "reciprocidade": "reciprocity",
        "storytelling": "storytelling",
        "historia": "storytelling",
        "clareza": "clarity",
        "objecoes": "objection_handling",
        "objecao": "objection_handling",
        "objeccoes": "objection_handling",
        "objeccao": "objection_handling",
        "curiosity_gap": "curiosity_gap",
        "curiosidade": "curiosity_gap",
        "personalizacao": "personalization",
        "personaliz": "personalization",
        "ancoragem": "anchoring",
        "ancora": "anchoring",
        "aversao_a_perda": "loss_aversion",
        "aversaoaperda": "loss_aversion",
        "perda": "loss_aversion",
        "vies_de_confirmacao": "confirmation_bias",
        "viesdeconfirmacao": "confirmation_bias",
        "confirmacao": "confirmation_bias",
        "liking": "liking",
        "afinidade": "liking",
        "compromisso_e_consistencia": "commitment_consistency",
        "compromissoeconsistencia": "commitment_consistency",
        "consistencia": "commitment_consistency",
        "bandwagon": "bandwagon",
        "efeito_manada": "bandwagon",
        "manada": "bandwagon",
        "contraste": "contrast_principle",
        "principio_contraste": "contrast_principle",
        "passo_a_passo": "step_by_step",
        "passoapasso": "step_by_step",
        "checklist": "checklist",
        "followup": "follow_up",
        "follow_up": "follow_up",
        "seguimento": "follow_up",
        "qualificacao": "qualification",
        "qualif": "qualification",
        "fechamento": "closing",
        "fecha": "closing",
        "prevencao_objecoes": "objection_prevention",
        "prevencaoobjecoes": "objection_prevention",
        "data_driven": "data_driven",
        "dados": "data_driven",
        "inteligencia_competitiva": "competitive_intel",
        "inteligenciacompetitiva": "competitive_intel",
        "competicao": "competitive_intel",
        "timing": "timing",
        "momento": "timing",
        "segmentacao": "segmentation",
        "segment": "segmentation",
        "criacao_urgencia": "urgency_creation",
        "criacaourgencia": "urgency_creation",
        "urg_create": "urgency_creation",
        "tecnica_fechamento": "closing_technique",
        "tecnicafechamento": "closing_technique",
        "sequencia_followup": "follow_up_sequence",
        "sequenciafollowup": "follow_up_sequence",
        "urg_creation": "urgency_creation",
        "fechamento_tecnica": "closing_technique",
    }

    resolved = alias_map.get(slug, slug)
    if resolved not in _CONVERSION_AXES:
        raise ValueError(
            f"Eixo de venda desconhecido: '{raw}' (normalizado: '{resolved}')"
        )
    return resolved


def get_active_conversion_axes(db, tenant_id: int | None = None) -> list[dict]:
    """Retorna eixos ativos com peso efetivo do DB ou fallback para default."""
    rows = db.execute(
        "SELECT axis, enabled, weight FROM franz_sales_rules WHERE tenant_id IS NOT DISTINCT FROM :tid",
        {"tid": tenant_id},
    ).fetchall()
    active_map = {r["axis"]: (r["enabled"], r["weight"]) for r in rows}

    result = []
    for axis in _CONVERSION_AXES:
        enabled, weight = active_map.get(axis, (False, _CONVERSION_AXIS_WEIGHTS.get(axis, 0.05)))
        result.append({
            "axis": axis,
            "label": _CONVERSION_AXIS_LABELS.get(axis, axis),
            "enabled": bool(enabled),
            "weight": float(weight),
            "default_weight": _CONVERSION_AXIS_WEIGHTS.get(axis, 0.05),
        })
    return result


def get_conversion_axis_prompts(enabled_only: bool = True) -> dict[str, str]:
    """Retorna {axis: prompt} para injeção no system prompt do Franz."""
    prompts: dict[str, str] = {}
    for axis in _CONVERSION_AXES:
        label = _CONVERSION_AXIS_LABELS.get(axis, axis)
        weight = _CONVERSION_AXIS_WEIGHTS.get(axis, 0.05)
        prompts[axis] = (
            f"[{label.upper()}] Aplique a técnica de {label} "
            f"(peso {weight:.0%}) nas respostas ao lead: "
            f"{_get_axis_hint(axis)}"
        )
    return prompts


def get_conversion_score_bonus(db, tenant_id: int | None = None) -> float:
    """Soma dos pesos dos eixos ativos para um tenant."""
    active = get_active_conversion_axes(db, tenant_id)
    return sum(a["weight"] for a in active if a["enabled"])


# ---------------------------------------------------------------------------
# Internos
# ---------------------------------------------------------------------------

def _get_axis_hint(axis: str) -> str:
    """Hint curto de como aplicar cada eixo."""
    hints = {
        "authority": "Cite fontes confiáveis, especialistas ou dados de mercado.",
        "scarcity": "Destaque exclusividade e disponibilidade limitada.",
        "urgency": "Crie senso de tempo limitado para ação.",
        "social_proof": "Mencione clientes similares ou resultados comprovados.",
        "reciprocity": "Ofereça valor primeiro antes de pedir algo.",
        "storytelling": "Use narrativa com personagem, conflito e resolução.",
        "clarity": "Seja direto, evite jargão, use frases curtas.",
        "objection_handling": "Antecipe e responda objeções antes que sejam levantadas.",
        "curiosity_gap": "Deixe uma pergunta implícita que incentive a próxima resposta.",
        "personalization": "Use o nome e dados específicos do lead em cada mensagem.",
        "anchoring": "Primeiro apresente um valor de referência alto antes do preço real.",
        "loss_aversion": "Enfatize o que o lead PERDE ao não agir.",
        "confirmation_bias": "Alinhe argumentos com crenças já manifestadas pelo lead.",
        "liking": "Seja autêntico, encontre pontos em comum, use humor leve.",
        "commitment_consistency": "Pegue pequenos acordos antes do grande fechamento.",
        "bandwagon": "Mostre que outros estão adotando — ninguém quer ficar de fora.",
        "contrast_principle": "Apresente opção premium primeiro para fazer a desejada parecer acessível.",
        "step_by_step": "Divida o processo em passos simples e sequenciais.",
        "checklist": "Apresente itens tangíveis que confirmam valor.",
        "follow_up": "Mantenha contato periódico sem ser intrusivo.",
        "qualification": "Faça perguntas que qualifiquem o lead (BANT).",
        "closing": "Peça a ação diretamente quando o lead estiver pronto.",
        "objection_prevention": "Elimine objeções antes que surjam.",
        "data_driven": "Use números, métricas e dados concretos.",
        "competitive_intel": "Diferencie de concorrentes com argumentos específicos.",
        "timing": "Identifique sinais de prontidão e responda no momento certo.",
        "segmentation": "Adapte a abordagem ao perfil e nicho do lead.",
        "urgency_creation": "Reforce prazos, vagas restantes ou janelas de oportunidade.",
        "closing_technique": "Use técnicas estruturadas de fechamento (assumptive, alternative, etc).",
        "follow_up_sequence": "Planeje sequência multi-toque com intervalos progressivos.",
    }
    return hints.get(axis, "Aplique esta técnica de forma natural na conversa.")
