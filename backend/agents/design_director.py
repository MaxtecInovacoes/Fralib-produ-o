"""Design Director Agent.

Decide a DIREÇÃO CRIATIVA única de cada site baseado em:
- Nicho do lead (nutricionista, dentista, academia...)
- Cidade e contexto local
- Briefing de nicho (agente_nicho)
- Tendências atuais
- Design tokens de design_context (fonte única de verdade - OKLch)

Output: VariacaoEstrutural com paleta, tipografia, motion style, tom de voz

Fluxo:
1. Primeiro tenta chamar design_context.get_design_context() para tokens OKLch
2. Se sucesso, usa tokens como base da decisão
3. Se falhar, lança DesignDirectionError (fail-fast)

Fail-fast: não usa fallbacks determinísticos.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.pipeline_exceptions import DesignDirectionError
from llm_direct import call_claude
from backend.agents.design_context import get_design_context

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# DESIGN DIRECTION CACHE (24h TTL)
# ═══════════════════════════════════════════════════════════════════

CACHE_DIR = Path("/tmp/fralib_design_cache")
CACHE_TTL_SECONDS = 86400  # 24h


def _cache_key(nicho: str, cidade: str, segment: str) -> str:
    """Generate cache key from nicho, cidade and segment."""
    raw = f"{nicho}_{cidade}_{segment}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_get(nicho: str, cidade: str, segment: str) -> dict[str, Any] | None:
    """Get cached design direction if valid (24h TTL)."""
    key = _cache_key(nicho, cidade, segment)
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        age = time.time() - path.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            try:
                data = json.loads(path.read_text())
                logger.info(f"[DesignDirector] Cache HIT: nicho={nicho}, cidade={cidade} (age={age:.0f}s)")
                return data
            except Exception as e:
                logger.warning(f"[DesignDirector] Cache read failed: {e}")
    return None


def _cache_set(nicho: str, cidade: str, segment: str, data: dict[str, Any]) -> None:
    """Save design direction to cache."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        key = _cache_key(nicho, cidade, segment)
        path = CACHE_DIR / f"{key}.json"
        path.write_text(json.dumps(data, ensure_ascii=False))
        logger.info(f"[DesignDirector] Cache SET: nicho={nicho}, cidade={cidade}")
    except Exception as e:
        logger.warning(f"[DesignDirector] Cache write failed: {e}")


SYSTEM_PROMPT = """You are the Design Director at FraLib.

Your ONLY role: Decide the CREATIVE DIRECTION of each website, making it UNIQUE
to that business. Never produce a generic site.

INPUT:
- Niche briefing (from agente_nicho)
- Lead context (name, city, segment, rating, photos)
- Competitor data
- Local SEO keywords

OUTPUT (JSON only):
{
  "direcao_visual": {
    "paleta_primaria": "#hex",
    "paleta_secundaria": "#hex",
    "paleta_acento": "#hex",
    "estilo": "minimalista | bold | editorial | organic | corporate",
    "fonte_titulo": "Playfair Display | Inter | Space Grotesk | ...",
    "fonte_corpo": "Inter | Lato | ..."
  },
  "motion_style": {
    "intensidade": "subtle | balanced | bold",
    "efeito_principal": "fade-up | slide-in | mask-reveal | parallax-strong",
    "scroll_speed": "slow | normal | fast",
    "usa_video_hero": true | false,
    "usa_parallax": true | false,
    "usa_cursor_custom": true | false
  },
  "tom_de_voz": {
    "registro": "formal | semi-formal | casual",
    "personalidade": "autoritativo | acolhedor | jovem | premium",
    "frases_chave": ["frase 1", "frase 2", "frase 3"]
  },
  "estrutura_unica": {
    "ordem_secoes": ["hero", "sobre", "servicos", "depoimentos", "faq", "contato"],
    "diferenciador_local": "o que faz ESTE negócio único vs concorrência",
    "cta_principal": "WhatsApp | Formulário | Telefone",
    "cta_secundario": "Agendar consulta | Ver localização | ..."
  },
  "anti_repeticao": {
    "evitar": ["hero fullscreen genérico", "cores azul/branco óbvias", "..."],
    "inspiracoes": ["estilo Awwwards", "tipografia X", "..."]
  }
}

RULES (CRITICAL):
1. SEMPRE analise o nicho antes de decidir.
2. SEMPRE considere o público local.
3. NUNCA use a mesma paleta para 2 leads do mesmo nicho + cidade.
4. SEMPRE justifique cada decisão em 1 frase.
5. NUNCA invente cores - use paleta consistente com o segmento.

EXAMPLES:

Nicho: nutricionista
- Paleta: verde sálvia + creme + terracota (NÃO azul genérico)
- Motion: subtle, mask-reveal em títulos
- Tom: acolhedor, científico

Nicho: dentista premium
- Paleta: navy + dourado + branco
- Motion: balanced, parallax em hero
- Tom: autoritativo, premium

Nicho: academia
- Paleta: preto + amarelo neon + cinza
- Motion: bold, scroll-snap em seções
- Tom: energético, motivacional
"""


def gerar_direcao_criativa(
    nicho: str,
    cidade: str,
    nome_negocio: str,
    briefing_nicho: dict[str, Any] | None = None,
    rating: float = 0.0,
    segment: str = "",
    tier: str = "STANDARD",
    dados_lead: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Decide creative direction for a lead.

    Fluxo:
    1. Checar cache primeiro (nicho + cidade + segment)
    2. Se hit, retorna direto
    3. Se miss, chama LLM com design_context
    4. Salva resultado no cache

    Returns dict with paleta, motion, tom de voz, estrutura.
    """
    # ─── PASSO 0: Checar cache (24h TTL) ───
    cached = _cache_get(nicho, cidade, segment)
    if cached:
        logger.info(f"[DesignDirector] Cache hit para nicho={nicho}, cidade={cidade}")
        return cached

    # ─── PASSO 1: Tentar usar design_context como fonte de tokens OKLch ───
    design_tokens = None
    dark_mode = False

    # Detectar dark mode baseado no nicho
    _dark_niches = {"academia", "crossfit", "churrascaria", "barbearia", "auto_pecas", "pet_shop"}
    if nicho.lower() in _dark_niches:
        dark_mode = True

    try:
        design_tokens = get_design_context(
            segmento=nicho,
            nome_negocio=nome_negocio,
            tier=tier,
            dark_mode=dark_mode,
            dados_lead=dados_lead,
        )
        logger.info(
            f"[DesignDirector] design_context OK: dir={design_tokens.get('dir_key')}, "
            f"tokens={len(design_tokens.get('tokens', {}))} vars"
        )
    except Exception as _dc_err:
        raise DesignDirectionError(
            f"design_context failed for '{nicho}' in '{cidade}'.",
            context={
                "nicho": nicho,
                "cidade": cidade,
                "segmento": segment,
                "erro": str(_dc_err),
                "acao": "Corrigir design_context; nao usar direcao visual generica",
            },
        ) from _dc_err

    # ─── PASSO 2: Decidir direção criativa via LLM (usando tokens se disponível) ───
    _tokens_info = ""
    if design_tokens:
        _tokens = design_tokens.get("tokens", {})
        _tokens_info = f"""
DESIGN TOKENS (OKLch - fonte única de verdade):
- Background: {_tokens.get('--bg', 'N/A')}
- Surface: {_tokens.get('--surface', 'N/A')}
- Foreground: {_tokens.get('--fg', 'N/A')}
- Muted: {_tokens.get('--muted', 'N/A')}
- Border: {_tokens.get('--border', 'N/A')}
- Accent: {_tokens.get('--accent', 'N/A')}
- Fonte Heading: {design_tokens.get('font_heading', 'N/A')}
- Fonte Body: {design_tokens.get('font_body', 'N/A')}
- Direction Key: {design_tokens.get('dir_key', 'N/A')}
- Animation: {design_tokens.get('animation', 'N/A')}
- Vibe: {design_tokens.get('vibe', 'N/A')}
- Hero Style: {design_tokens.get('hero_style', {}).get('layout', 'N/A')}

IMPORTANTE: Use estes tokens OKLch como PALETA BASE. O LLM decide variação,
não os valores absolutos."""

    user_prompt = f"""Decida a direção criativa para:

Nicho: {nicho}
Cidade: {cidade}
Negócio: {nome_negocio}
Segmento: {segment}
Rating: {rating}

{f"Briefing de nicho: {briefing_nicho}" if briefing_nicho else ""}
{_tokens_info}

Retorne APENAS o JSON com a direção criativa."""

    try:
        result = call_claude(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            model="haiku",
            max_tokens=2000,
        )

        import json
        # Tentar parsear JSON
        if isinstance(result, str):
            # Limpar markdown se houver
            text = result.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                text = text.rsplit("```", 1)[0]
            parsed = json.loads(text)
        else:
            parsed = result

        required = ("direcao_visual", "motion_style", "tom_de_voz", "estrutura_unica", "anti_repeticao")
        missing = [key for key in required if not isinstance(parsed.get(key), dict)]
        if missing:
            raise DesignDirectionError(
                f"Design Director retornou JSON incompleto: {', '.join(missing)}",
                context={
                    "nicho": nicho,
                    "cidade": cidade,
                    "segmento": segment,
                    "missing": missing,
                    "acao": "Corrigir prompt/modelo; nao preencher direcao visual generica",
                },
            )

        # ─── INJETAR design_tokens no resultado se disponível ───
        if design_tokens:
            parsed["design_tokens"] = {
                "dir_key": design_tokens.get("dir_key"),
                "tokens": design_tokens.get("tokens"),
                "font_heading": design_tokens.get("font_heading"),
                "font_body": design_tokens.get("font_body"),
                "animation_profile": design_tokens.get("animation_profile"),
                "hero_style": design_tokens.get("hero_style"),
                "craft": design_tokens.get("craft"),
                "vibe": design_tokens.get("vibe"),
                "animation": design_tokens.get("animation"),
                "source": "design_context",
            }
            logger.info("[DesignDirector] Tokens OKLch injetados no resultado")
        else:
            parsed["design_tokens"] = None

        # ─── PASSO 3: Salvar no cache ───
        _cache_set(nicho, cidade, segment, parsed)

        return parsed

    except Exception as e:
        logger.error(f"[DesignDirector] Erro: {e}")
        raise DesignDirectionError(
            f"Design direction failed for '{nicho}' in '{cidade}'.",
            context={
                "nicho": nicho,
                "cidade": cidade,
                "segmento": segment,
                "erro": str(e),
                "acao": "Check design_context connectivity and retry",
            },
        )
