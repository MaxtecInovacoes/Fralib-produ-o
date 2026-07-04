"""Deterministic niche and audience resolver for Builder prompts."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


NICHE_HIERARCHY: dict[str, dict[str, dict[str, Any]]] = {
    "nutricionista": {
        "infantil": {
            "audiences": ["pais_maes", "cuidadores"],
            "tone": "acolhedor, didatico, sem julgamento, baseado em evidencias",
            "hero_pattern": "foto estatica humana com crianca/familia e prova local discreta",
            "forbidden_copy": ["dieta restritiva", "resultado garantido", "criancas atendidas sem dado"],
            "microcopy": {
                "sobre": "formacao de habitos e bem-estar familiar",
                "metodologia": "escuta ativa e rotina possivel",
                "cta": "agende uma conversa inicial",
            },
        },
        "esportiva": {
            "audiences": ["atletas", "praticantes_de_treino", "personal_trainers"],
            "tone": "tecnico, direto, performance sem promessa de resultado",
            "hero_pattern": "movimento treino+food prep quando houver video",
            "forbidden_copy": ["shape garantido", "perda de peso garantida"],
        },
        "clinica": {
            "audiences": ["adultos", "gestantes", "idosos", "pacientes_clinicos"],
            "tone": "calmo, profissional, cientifico e humano",
            "hero_pattern": "foto estatica de ambiente humano e confiavel",
            "forbidden_copy": ["cura", "resultado garantido"],
        },
    },
    "academia": {
        "crossfit": {
            "audiences": ["atletas_amadores", "alta_intensidade"],
            "tone": "energetico, manifesto, comunidade",
            "hero_pattern": "video de treino ou crop de acao",
        },
        "funcional": {
            "audiences": ["adultos_ativos", "iniciantes", "condicionamento"],
            "tone": "energia acessivel e orientacao profissional",
            "hero_pattern": "video de movimento com CTA direto",
        },
        "geral": {
            "audiences": ["alunos_locais", "iniciantes", "treino_recorrente"],
            "tone": "motivador, local e objetivo",
            "hero_pattern": "video de treino quando houver asset",
        },
    },
    "restaurante": {
        "japones": {"audiences": ["casais", "familias", "delivery_local"], "tone": "sensorial e preciso"},
        "hamburgueria": {"audiences": ["jovens", "familias", "grupos"], "tone": "apetite, energia e praticidade"},
        "vegano": {"audiences": ["conscientes", "saude", "gastronomia_autoral"], "tone": "fresco, autoral e claro"},
        "tradicional": {"audiences": ["familias", "almoco_local", "grupos"], "tone": "acolhedor e apetitoso"},
    },
}


def resolve_niche_context(segment: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    data = data or {}
    base = _slug(segment)
    if "nutric" in base:
        base = "nutricionista"
    elif any(token in base for token in ("academia", "crossfit", "funcional", "fitness")):
        base = "academia"
    elif any(token in base for token in ("restaurante", "pizzaria", "cafe", "hamburg", "japones", "vegano")):
        base = "restaurante"

    text = _slug(" ".join(str(v) for v in data.values() if isinstance(v, (str, int, float))))
    explicit = _slug(data.get("subniche") or data.get("sub_nicho") or data.get("subnicho") or "")
    detected = _detect_subniche(base, text)
    generic_explicit = {"", "clinica", "geral", "tradicional", "saude_e_alimentacao", "saude", "alimentacao"}
    sub = detected if explicit in generic_explicit and detected else explicit or detected
    hierarchy = NICHE_HIERARCHY.get(base, {})
    if sub not in hierarchy:
        sub = "clinica" if base == "nutricionista" else "geral" if base == "academia" else "tradicional" if base == "restaurante" else ""
    details = hierarchy.get(sub, {})
    return {
        "segment": base or _slug(segment),
        "sub_niche": sub,
        "audiences": details.get("audiences", []),
        "tone": details.get("tone", ""),
        "hero_pattern": details.get("hero_pattern", ""),
        "forbidden_copy": details.get("forbidden_copy", []),
        "microcopy": details.get("microcopy", {}),
    }


def _detect_subniche(base: str, text: str) -> str:
    if base == "nutricionista":
        if any(token in text for token in ("infantil", "crianca", "kids", "materno", "pediatr")):
            return "infantil"
        if any(token in text for token in ("esport", "atleta", "performance", "treino", "musculacao")):
            return "esportiva"
        return "clinica"
    if base == "academia":
        if "crossfit" in text or "cross" in text:
            return "crossfit"
        if "funcional" in text:
            return "funcional"
        return "geral"
    if base == "restaurante":
        if any(token in text for token in ("japones", "sushi", "temaki")):
            return "japones"
        if "hamburg" in text:
            return "hamburgueria"
        if "vegano" in text or "vegetariano" in text:
            return "vegano"
        return "tradicional"
    return ""


def _slug(value: Any) -> str:
    """Normalize value to a niche resolver key (underscore-joined)."""
    from backend.utils.slug import slugify  # — M4 DRY
    return slugify(value, sep="_", collapse_sep=True)
