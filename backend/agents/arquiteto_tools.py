"""
Arquiteto Mestre Agent Tools — Ferramentas para o Managed Agent do Arquiteto.

O Claude busca ativamente cada recurso via tools e verifica se usou tudo
antes de entregar o PRD. Garante que keywords, design tokens, animações,
SEO e open design sejam SEMPRE utilizados.
"""
import json
import os
import urllib.request
import urllib.parse

from backend.agents.design_context import get_design_context, get_hero_style
from backend.agents.craft_rules import get_craft_rules, get_autocritica
from backend.agents.seo_context import get_seo_context
from backend.agents.open_design_selector import get_open_design_prompt
from backend.agents.animation_profile import get_animation_profile

# ══════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS (schema para a API do Claude)
# ══════════════════════════════════════════════════════════════════

ARQUITETO_TOOLS = [
    {
        "name": "get_keyword_research",
        "description": "Busca keywords transacionais com volume real para o segmento/cidade. Retorna termos do Google Suggest + keywords pesquisadas. Use SEMPRE para garantir que o site tenha SEO com termos que geram tráfego real.",
        "input_schema": {
            "type": "object",
            "properties": {
                "segmento": {"type": "string", "description": "Segmento do negócio (ex: academia, restaurante)"},
                "cidade": {"type": "string", "description": "Cidade do negócio"}
            },
            "required": ["segmento", "cidade"]
        }
    },
    {
        "name": "get_design_system",
        "description": "Retorna tokens OKLch, tipografia, animação e componentes do design system para o segmento. Fonte única de verdade para cores e fontes — NUNCA inventar cores fora daqui.",
        "input_schema": {
            "type": "object",
            "properties": {
                "segmento": {"type": "string", "description": "Segmento do negócio"},
                "nome_negocio": {"type": "string", "description": "Nome do negócio (usado como seed para variância)"},
                "tier": {"type": "string", "enum": ["PREMIUM", "STANDARD", "BASIC"], "description": "Tier do negócio"},
                "dark_mode": {"type": "boolean", "description": "Se deve usar modo escuro"}
            },
            "required": ["segmento", "nome_negocio", "tier"]
        }
    },
    {
        "name": "get_animation_profile",
        "description": "Retorna perfil de animação específico do nicho: intensidade, easing, hero_style, durações, tipos de entrada. Use para definir motion design correto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "segmento": {"type": "string", "description": "Segmento do negócio"}
            },
            "required": ["segmento"]
        }
    },
    {
        "name": "get_seo_context",
        "description": "Retorna schema.org type, template de H1, keywords base, FAQ do nicho e regras de SEO local. Use para garantir SEO técnico correto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "segmento": {"type": "string", "description": "Segmento do negócio"},
                "cidade": {"type": "string", "description": "Cidade"},
                "nome_negocio": {"type": "string", "description": "Nome do negócio"}
            },
            "required": ["segmento", "cidade", "nome_negocio"]
        }
    },
    {
        "name": "get_open_design_reference",
        "description": "Seleciona um DESIGN.md real (de 149 disponíveis) como referência criativa para o segmento. Retorna atmosfera, paleta e tipografia de um design system profissional real.",
        "input_schema": {
            "type": "object",
            "properties": {
                "segmento": {"type": "string", "description": "Segmento do negócio"},
                "nome_negocio": {"type": "string", "description": "Nome do negócio"},
                "tier": {"type": "string", "enum": ["PREMIUM", "STANDARD", "BASIC"], "description": "Tier"}
            },
            "required": ["segmento", "nome_negocio", "tier"]
        }
    },
    {
        "name": "get_craft_rules",
        "description": "Retorna regras anti-slop, tipografia, cores e animação que o PRD DEVE seguir. Inclui padrões bloqueados (indigo, purple gradients, emoji icons).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_jina_insights",
        "description": "Extrai dados estruturados dos insights da Jina: FAQ de concorrentes, keywords SEO e value propositions reais do mercado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "jina_raw": {"type": "string", "description": "Texto bruto dos insights da Jina"}
            },
            "required": ["jina_raw"]
        }
    },
    {
        "name": "verify_prd",
        "description": "Verifica se o PRD gerado usou TODOS os recursos disponíveis. Checa: keywords presentes, design tokens aplicados, animações definidas, SEO completo, FAQ incluído. Use SEMPRE antes de finalizar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prd_json": {"type": "string", "description": "PRD em formato JSON string para verificação"}
            },
            "required": ["prd_json"]
        }
    },
]

# ══════════════════════════════════════════════════════════════════
# TOOL EXECUTION
# ══════════════════════════════════════════════════════════════════

def execute_tool(tool_name: str, tool_input: dict, context: dict = None) -> str:
    """Executa uma tool e retorna resultado como string."""
    try:
        if tool_name == "get_keyword_research":
            return _tool_get_keyword_research(tool_input, context)
        elif tool_name == "get_design_system":
            return _tool_get_design_system(tool_input)
        elif tool_name == "get_animation_profile":
            return _tool_get_animation_profile(tool_input)
        elif tool_name == "get_seo_context":
            return _tool_get_seo_context(tool_input)
        elif tool_name == "get_open_design_reference":
            return _tool_get_open_design_reference(tool_input)
        elif tool_name == "get_craft_rules":
            return _tool_get_craft_rules()
        elif tool_name == "get_jina_insights":
            return _tool_get_jina_insights(tool_input, context)
        elif tool_name == "verify_prd":
            return _tool_verify_prd(tool_input, context)
        else:
            return json.dumps({"error": f"Tool desconhecida: {tool_name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})

# ── get_keyword_research ──────────────────────────────────────────

def _tool_get_keyword_research(tool_input: dict, context: dict = None) -> str:
    """Busca keywords reais: Google Suggest + keyword_research pré-computado."""
    segmento = tool_input.get("segmento", "")
    cidade = tool_input.get("cidade", "")

    # Google Suggest (tempo real)
    suggest_terms = []
    try:
        query = urllib.parse.quote(f"{segmento} {cidade}")
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={query}&hl=pt-BR"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            suggest_terms = [s for s in (data[1] if len(data) > 1 else []) if isinstance(s, str)][:10]
    except Exception as e:
        print(f"[arquiteto_tools] Google suggest falhou: {e}")

    # Keyword research pré-computado (passado via context)
    kw_precomputed = (context or {}).get("keyword_research", "")

    result = {
        "google_suggest": suggest_terms,
        "keyword_research": kw_precomputed[:1500] if kw_precomputed else "",
        "transactional_terms": [
            f"{segmento} {cidade}",
            f"melhor {segmento} {cidade}",
            f"{segmento} perto de mim",
            f"{segmento} aberto agora {cidade}",
        ],
        "total_terms": len(suggest_terms) + 4,
    }
    return json.dumps(result, ensure_ascii=False)

# ── get_design_system ─────────────────────────────────────────────

def _tool_get_design_system(tool_input: dict) -> str:
    """Retorna design system completo do design_context.py."""
    segmento = tool_input.get("segmento", "")
    nome = tool_input.get("nome_negocio", "")
    tier = tool_input.get("tier", "STANDARD")
    dark_mode = tool_input.get("dark_mode", False)

    design = get_design_context(segmento, nome, tier, dark_mode)
    hero_style = get_hero_style(design["dir_key"])

    result = {
        "direction": design["dir_nome"],
        "direction_key": design["dir_key"],
        "tokens": design["tokens"],
        "font_heading": design["font_heading"],
        "font_body": design["font_body"],
        "animation": design["animation"],
        "vibe": design.get("vibe", ""),
        "hero_style": hero_style,
        "tier": tier,
        "dark_mode": dark_mode,
        "instruction": f"OBRIGATÓRIO usar estes tokens CSS: --bg:{design['tokens']['--bg']} --surface:{design['tokens']['--surface']} --fg:{design['tokens']['--fg']} --accent:{design['tokens']['--accent']} --muted:{design['tokens']['--muted']} --border:{design['tokens']['--border']}",
    }
    return json.dumps(result, ensure_ascii=False)

# ── get_animation_profile ─────────────────────────────────────────

def _tool_get_animation_profile(tool_input: dict) -> str:
    """Retorna perfil de animação do nicho."""
    segmento = tool_input.get("segmento", "")
    profile = get_animation_profile(segmento)
    return json.dumps(profile, ensure_ascii=False)

# ── get_seo_context ───────────────────────────────────────────────

def _tool_get_seo_context(tool_input: dict) -> str:
    """Retorna contexto SEO completo."""
    segmento = tool_input.get("segmento", "")
    cidade = tool_input.get("cidade", "")
    nome = tool_input.get("nome_negocio", "")
    seo = get_seo_context(segmento, cidade, nome)
    return json.dumps({"seo_context": seo}, ensure_ascii=False)

# ── get_open_design_reference ─────────────────────────────────────

def _tool_get_open_design_reference(tool_input: dict) -> str:
    """Seleciona design system real como referência criativa."""
    segmento = tool_input.get("segmento", "")
    nome = tool_input.get("nome_negocio", "")
    tier = tool_input.get("tier", "STANDARD")
    ref = get_open_design_prompt(segmento, nome, tier)
    if ref:
        return json.dumps({"open_design": ref[:2000], "loaded": True}, ensure_ascii=False)
    return json.dumps({"open_design": "", "loaded": False, "note": "Nenhum design system encontrado para este segmento"}, ensure_ascii=False)

# ── get_craft_rules ───────────────────────────────────────────────

def _tool_get_craft_rules() -> str:
    """Retorna regras anti-slop e craft."""
    rules = get_craft_rules()
    autocritica = get_autocritica()
    return json.dumps({"craft_rules": rules[:1500], "autocritica": autocritica[:500]}, ensure_ascii=False)

# ── get_jina_insights ─────────────────────────────────────────────

def _tool_get_jina_insights(tool_input: dict, context: dict = None) -> str:
    """Extrai dados estruturados dos insights Jina."""
    import re
    jina_raw = tool_input.get("jina_raw", "") or (context or {}).get("jina_insights", "")

    result = {"faq_questions": [], "seo_keywords": [], "value_props": []}
    if "=== DADOS ESTRUTURADOS PARA SEO ===" not in jina_raw:
        return json.dumps({"data": result, "note": "Bloco estruturado não encontrado no Jina"}, ensure_ascii=False)

    try:
        bloco = jina_raw.split("=== DADOS ESTRUTURADOS PARA SEO ===")[1]
        for key in ("faq_questions", "seo_keywords", "value_props"):
            m = re.search(key.upper() + r": (\[.*?\])", bloco, re.DOTALL)
            if m:
                result[key] = json.loads(m.group(1))
    except Exception as e:
        return json.dumps({"data": result, "error": str(e)}, ensure_ascii=False)

    return json.dumps({"data": result, "total_keywords": len(result["seo_keywords"]), "total_faq": len(result["faq_questions"])}, ensure_ascii=False)

# ── verify_prd ────────────────────────────────────────────────────

def _tool_verify_prd(tool_input: dict, context: dict = None) -> str:
    """Verifica completude do PRD — garante que tudo foi usado."""
    prd_str = tool_input.get("prd_json", "")
    try:
        prd = json.loads(prd_str)
    except json.JSONDecodeError as e:
        return json.dumps({"ok": False, "issues": [f"JSON inválido: {str(e)}"], "critical": True}, ensure_ascii=False)

    issues = []
    warnings = []

    # 1. Sections check
    sections = prd.get("sections", [])
    if len(sections) < 5:
        issues.append(f"Apenas {len(sections)} seções. Mínimo 6 (hero, sobre, servicos, depoimentos/faq, localizacao, contato).")
    section_names = [s.get("name", "") for s in sections]
    for required in ["hero", "servicos", "contato"]:
        if required not in section_names:
            issues.append(f"Seção obrigatória '{required}' ausente.")

    # 2. Keywords/SEO check
    seo_kw = prd.get("seo_keywords", [])
    if not seo_kw or len(seo_kw) < 3:
        issues.append("seo_keywords ausente ou insuficiente (<3). Use keywords do get_keyword_research.")

    # 3. Design tokens check
    palette = prd.get("color_palette", {})
    if not palette.get("tokens_oklch"):
        issues.append("tokens_oklch ausente na color_palette. Use tokens do get_design_system.")
    if not palette.get("background"):
        issues.append("color_palette.background ausente.")

    # 4. Typography check
    typo = prd.get("typography", {})
    if not typo.get("heading") or not typo.get("body"):
        issues.append("typography.heading ou .body ausente. Use fontes do get_design_system.")

    # 5. Animation check
    animations = prd.get("animations", [])
    if not animations or len(animations) < 3:
        warnings.append("Poucas animações (<3). Use perfil do get_animation_profile.")

    # 6. FAQ check
    faq = prd.get("faq_questions", [])
    if not faq or len(faq) < 3:
        warnings.append("FAQ insuficiente (<3 perguntas). Importante para SEO de IA.")

    # 7. Copy check — hero deve ter h1 com cidade
    hero_sec = next((s for s in sections if s.get("name") == "hero"), None)
    if hero_sec:
        h1 = (hero_sec.get("copy") or {}).get("h1", "")
        if len(h1) < 15:
            issues.append("Hero H1 muito curto (<15 chars). Deve ter benefício + cidade.")

    # 8. Layout type check
    for s in sections:
        if not s.get("layout_type") or s.get("layout_type") == "padrao":
            warnings.append(f"Seção '{s.get('name')}' sem layout_type específico.")

    # 9. instrucao_criativa check
    instrucao = prd.get("instrucao_criativa_para_dev", "")
    if len(instrucao) < 50:
        warnings.append("instrucao_criativa_para_dev muito curta. Deve guiar o Liam com detalhes visuais.")

    ok = len(issues) == 0
    return json.dumps({
        "ok": ok,
        "issues": issues,
        "warnings": warnings,
        "sections_count": len(sections),
        "keywords_count": len(seo_kw),
        "animations_count": len(animations),
        "suggestion": "Corrija os issues antes de finalizar." if not ok else "PRD completo e verificado."
    }, ensure_ascii=False)
