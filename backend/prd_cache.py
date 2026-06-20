"""
PRD Semantic Cache — Reutiliza PRDs similares por nicho+tier+direction (PRD #8)
HIT: Haiku adapta template ($0.02). MISS: Sonnet gera completo ($0.15).
Cacheia apos validacao final/quality gate.
"""

import json
import hashlib
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("prd_cache")

CACHE_DIR = Path(__file__).parent / "cache" / "prd_templates"
MAX_TEMPLATES = 100
DESIGN_DNA_CACHE_VERSION = "design-dna-v2"


def _cache_key(
    nicho: str, tier: str, design_direction: str, sub_nicho: str = ""
) -> str:
    raw = f"{DESIGN_DNA_CACHE_VERSION}_{nicho}_{tier}_{design_direction}_{sub_nicho or ''}".lower()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def buscar_prd_cache(
    nicho: str, tier: str, design_direction: str, sub_nicho: str = ""
) -> dict | None:
    key = _cache_key(nicho, tier, design_direction, sub_nicho)
    path = _cache_path(key)

    if not path.exists():
        print(f"[CACHE] MISS | key={key} | nicho={nicho} | sub_nicho={sub_nicho}")
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            entry = json.load(f)
    except (json.JSONDecodeError, OSError):
        path.unlink(missing_ok=True)
        return None

    created = datetime.fromisoformat(entry.get("created_at", "2020-01-01"))
    if (datetime.now() - created).days > 30:
        print(f"[CACHE] EXPIRED | key={key}")
        path.unlink(missing_ok=True)
        return None

    if entry.get("quality_score") and entry["quality_score"] < 7.0:
        print(f"[CACHE] LOW_QUALITY | key={key} | score={entry['quality_score']}")
        path.unlink(missing_ok=True)
        return None
    if entry.get("cache_version") not in (None, DESIGN_DNA_CACHE_VERSION):
        print(f"[CACHE] VERSION_MISMATCH | key={key}")
        path.unlink(missing_ok=True)
        return None

    entry["used_count"] = entry.get("used_count", 0) + 1
    entry["last_used"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)

    print(
        f"[CACHE] HIT | key={key} | nicho={nicho} | sub_nicho={sub_nicho} | usado {entry['used_count']}x"
    )
    return entry


def salvar_prd_cache(
    nicho: str,
    tier: str,
    design_direction: str,
    prd_completo: dict,
    lead_data: dict,
    sub_nicho: str = "",
):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _enforce_max_templates()

    key = _cache_key(nicho, tier, design_direction, sub_nicho)
    template = _generalizar_prd(prd_completo, lead_data)

    cache_entry = {
        "key": key,
        "nicho": nicho,
        "tier": tier,
        "design_direction": design_direction,
        "sub_nicho": sub_nicho,
        "created_at": datetime.now().isoformat(),
        "cache_version": DESIGN_DNA_CACHE_VERSION,
        "design_dna": prd_completo.get("visual_dna") or prd_completo.get("design_dna") or {},
        "used_count": 0,
        "last_used": None,
        "prd_template": template,
        "campos_variaveis": [
            "nome_negocio",
            "endereco",
            "telefone",
            "cidade",
            "servicos",
            "reviews",
        ],
        "quality_score": None,
    }

    # FIX CRÍTICO: escrita de cache pode falhar silenciosamente
    # (disco cheio, permissao negada, diretorio invalido)
    # Logamos para detectar problemas de infraestrutura
    try:
        with open(_cache_path(key), "w", encoding="utf-8") as f:
            json.dump(cache_entry, f, ensure_ascii=False, indent=2)
        print(
            f"[CACHE] SAVED | key={key} | nicho={nicho} | sub_nicho={sub_nicho} | tier={tier}"
        )
    except (OSError, IOError, PermissionError) as e:
        print(f"[CACHE][ERROR] Falha ao salvar cache key={key}: {e}")


def _generalizar_prd(prd: dict, lead_data: dict) -> dict:
    prd_str = json.dumps(prd, ensure_ascii=False, default=str)

    substituicoes = {
        lead_data.get("nome", ""): "{{nome_negocio}}",
        lead_data.get("endereco", ""): "{{endereco}}",
        lead_data.get("telefone", ""): "{{telefone}}",
        lead_data.get("cidade", ""): "{{cidade}}",
    }

    for original, placeholder in substituicoes.items():
        if original and len(original) > 2:
            prd_str = prd_str.replace(original, placeholder)

    return json.loads(prd_str)


def adaptar_prd_template(
    template_entry: dict, lead_data: dict, briefing_theo: str = ""
) -> dict:
    template_str = json.dumps(template_entry["prd_template"], ensure_ascii=False)

    substituicoes = {
        "{{nome_negocio}}": lead_data.get("nome", ""),
        "{{endereco}}": lead_data.get("endereco", ""),
        "{{telefone}}": lead_data.get("telefone", ""),
        "{{cidade}}": lead_data.get("cidade", ""),
    }
    for placeholder, valor in substituicoes.items():
        template_str = template_str.replace(placeholder, valor)

    prd_base = json.loads(template_str)

    system = """Você é o Arquiteto Mestre. Adapte o PRD template para este lead específico:
- Substitua serviços genéricos pelos REAIS do lead
- Adapte copy para diferenciais específicos
- Ajuste depoimentos se houver reviews reais
- Mantenha estrutura e layout intactos
- NÃO invente informações
Retorne APENAS JSON válido (sem markdown, sem ```)."""

    servicos = lead_data.get("servicos", [])
    reviews = lead_data.get("reviews", [])[:3]
    user = f"""PRD Template (adaptar):
{template_str[:3000]}

Dados do lead:
- Nome: {lead_data.get("nome")}
- Cidade: {lead_data.get("cidade")}
- Serviços: {servicos[:10] if servicos else "N/A"}
- Reviews: {reviews if reviews else "N/A"}
- Endereço: {lead_data.get("endereco", "N/A")}
- Telefone: {lead_data.get("telefone", "N/A")}

Adapte e retorne JSON completo."""

    try:
        from llm_direct import call_claude
        import re

        resposta = call_claude(
            system=system,
            user=user,
            model="haiku",
            max_tokens=4000,
            temperature=0.4,
            agent_name="prd_cache_adapt",
        )
        resposta = resposta.strip()
        if resposta.startswith("```"):
            resposta = re.sub(r"^```\w*\n?", "", resposta)
            resposta = re.sub(r"\n?```$", "", resposta)
        return json.loads(resposta)
    except (json.JSONDecodeError, Exception) as e:
        print(f"[CACHE][WARN] Adaptação falhou ({e}). Usando substituição direta.")
        return prd_base


def atualizar_quality_score(
    nicho: str, tier: str, design_direction: str, novo_score: float, sub_nicho: str = ""
):
    key = _cache_key(nicho, tier, design_direction, sub_nicho)
    path = _cache_path(key)
    if not path.exists():
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            entry = json.load(f)
        current = entry.get("quality_score")
        entry["quality_score"] = (
            novo_score
            if current is None
            else round((current * 0.7) + (novo_score * 0.3), 1)
        )
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
    except (OSError, json.JSONDecodeError, Exception) as e:
        # FIX CRÍTICO: quality score nao atualizado silenciosamente
        # Feedback loop de qualidade quebrado - templates ruins continuarao sendo servidos
        # Logamos para detectar problemas de IO ou JSON
        print(f"[CACHE][ERROR] Falha ao atualizar quality_score key={key}: {e}")


def _enforce_max_templates():
    if not CACHE_DIR.exists():
        return
    files = sorted(CACHE_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime)
    while len(files) > MAX_TEMPLATES:
        files[0].unlink(missing_ok=True)
        files.pop(0)
