import re, json

# ── PATCH 1: step_arquiteto.py — normalizar strings JSON ──
p1 = '/app/backend/agents/manager/step_arquiteto.py'
with open(p1) as f:
    s1 = f.read()
if 'import json' not in s1:
    s1 = s1.replace('import logging\nimport time', 'import json\nimport logging\nimport time', 1)

old1 = '''def _prd_to_dict(prd) -> dict:
    """Converte DesignerPRD para dict serializavel."""
    result = {}
    for k, v in vars(prd).items():
        if hasattr(v, "model_dump"):
            result[k] = v.model_dump()
        elif hasattr(v, "dict"):
            result[k] = v.dict()
        elif isinstance(v, list):
            result[k] = [
                item.model_dump() if hasattr(item, "model_dump") else (
                    item.dict() if hasattr(item, "dict") else item
                )
                for item in v
            ]
        else:
            result[k] = v
    sections = result.get("sections")
    if isinstance(sections, list):
        result["sections"] = [
            section
            for section in sections
            if str((section or {}).get("name") if isinstance(section, dict) else getattr(section, "name", "")).strip().lower() != "lgpd"
        ]
    variation = result.get("variation_blueprint")
    if isinstance(variation, dict):
        order = variation.get("ordem_das_secoes")
        if isinstance(order, list):
            variation["ordem_das_secoes"] = [item for item in order if str(item).strip().lower() != "lgpd"]
        required = variation.get("required_sections")
        if isinstance(required, list):
            variation["required_sections"] = [item for item in required if str(item).strip().lower() != "lgpd"]
    return result'''

new1 = '''def _coerce_json_string(v):
    """Se v for string JSON, retorna o objeto parseado; senao retorna v."""
    if not isinstance(v, str):
        return v
    s = v.strip()
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
        try:
            return json.loads(s)
        except Exception:
            pass
    return v

_DICT_FIELDS = frozenset({
    "variation_blueprint", "typography", "color_palette", "media_plan",
    "visual_dna", "creative_direction", "niche_brief", "site_build_plan",
    "requirements_contract", "visual_contract", "layout_blueprint",
    "design_reference_pack", "anti_patterns", "schema_org_types",
    "components_21dev", "faq_questions", "value_props", "seo_keywords",
})

def _prd_to_dict(prd) -> dict:
    """Converte DesignerPRD para dict serializavel, normalizando strings JSON."""
    result = {}
    for k, v in vars(prd).items():
        if hasattr(v, "model_dump"):
            result[k] = v.model_dump()
        elif hasattr(v, "dict"):
            result[k] = v.dict()
        elif isinstance(v, list):
            result[k] = [
                item.model_dump() if hasattr(item, "model_dump") else (
                    item.dict() if hasattr(item, "dict") else _coerce_json_string(item)
                )
                for item in v
            ]
        else:
            result[k] = _coerce_json_string(v)
    # Normaliza campos que devem ser dict mas vieram como string JSON (chunked merge bug)
    for k in _DICT_FIELDS:
        if k in result and isinstance(result[k], str):
            result[k] = _coerce_json_string(result[k])
    sections = result.get("sections")
    if isinstance(sections, list):
        result["sections"] = [
            section
            for section in sections
            if str((section or {}).get("name") if isinstance(section, dict) else getattr(section, "name", "")).strip().lower() != "lgpd"
        ]
    variation = result.get("variation_blueprint")
    if isinstance(variation, dict):
        order = variation.get("ordem_das_secoes")
        if isinstance(order, list):
            variation["ordem_das_secoes"] = [item for item in order if str(item).strip().lower() != "lgpd"]
        required = variation.get("required_sections")
        if isinstance(required, list):
            variation["required_sections"] = [item for item in required if str(item).strip().lower() != "lgpd"]
    # Sanitize footer: se existir sem conteudo, injeta o nome do negocio para evitar
    # footer corrompido (ex: "NÚ QUE FA PONÓ") vindo do chunked merge.
    footer_sec = next((s for s in result.get("sections", []) if isinstance(s, dict) and s.get("name", "").lower() == "footer"), None)
    if footer_sec and not (footer_sec.get("copy") or footer_sec.get("content") or footer_sec.get("text")):
        footer_sec["copy"] = result.get("business_name", "") or ""
        footer_sec["content"] = {"name": "footer", "business_name": result.get("business_name", "")}
    return result'''

if old1 in s1:
    s1 = s1.replace(old1, new1, 1)
    with open(p1, 'w') as f:
        f.write(s1)
    print('PATCH1_OK: step_arquiteto')
else:
    print('PATCH1_FAIL: pattern not found')

# ── PATCH 2: step_builder.py — footer/LGPD com design system via CSS vars ──
p2 = '/app/backend/agents/manager/step_builder.py'
with open(p2) as f:
    s2 = f.read()

# 2a: footer com CSS vars
old2_footer = '''    if not has_semantic_footer:
        footer = (
            f'<footer id="footer" class="px-6 py-12 bg-neutral-950 text-white">'
            f'<div class="mx-auto max-w-6xl grid gap-6 md:grid-cols-3">'
            f'<div><p class="text-lg font-semibold">{name}</p><p>{address or city}</p><p>{phone}</p></div>'
            '<div><p class="font-semibold">Contato e suporte</p><p>Atendimento oficial pelos canais desta página.</p></div>'
            '<div><p class="font-semibold">Privacidade</p><p id="footer-privacy-notice">Dados usados apenas para atendimento, retorno comercial e continuidade da experiência.</p></div>'
            '</div></footer>'
        )
        cleaned = re.sub(r"(?is)</body>", footer + "\n</body>", cleaned, count=1)
        if "<footer" not in cleaned.lower() and 'id="footer"' not in cleaned.lower():
            cleaned += footer'''

new2_footer = '''    if not has_semantic_footer:
        footer = (
            f'<footer id="footer" style="background:var(--bg,#0b0f19);color:var(--text,#e2e8f0)" class="px-6 py-12">'
            f'<div class="mx-auto max-w-6xl grid gap-6 md:grid-cols-3">'
            f'<div><p class="text-lg font-semibold" style="color:var(--accent,#e85d4a)">{name}</p><p>{address or city}</p><p>{phone}</p></div>'
            '<div><p class="font-semibold">Contato e suporte</p><p>Atendimento oficial pelos canais desta página.</p></div>'
            '<div><p class="font-semibold">Privacidade</p><p id="footer-privacy-notice">Dados usados apenas para atendimento, retorno comercial e continuidade da experiência.</p></div>'
            '</div></footer>'
        )
        cleaned = re.sub(r"(?is)</body>", footer + "\n</body>", cleaned, count=1)
        if "<footer" not in cleaned.lower() and 'id="footer"' not in cleaned.lower():
            cleaned += footer'''

if old2_footer in s2:
    s2 = s2.replace(old2_footer, new2_footer, 1)
    print('PATCH2a_OK: footer usa CSS vars')
else:
    print('PATCH2a_FAIL: footer pattern not found')

# 2b: LGPD com CSS vars
old2_lgpd = '''    elif "data-lgpd-banner" not in cleaned.lower():
        banner = (
            '<div data-lgpd-banner class="fixed bottom-4 left-4 right-4 z-50 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-neutral-950/95 px-4 py-3 text-white shadow-2xl backdrop-blur">'
            '<span class="min-w-0 flex-1 text-sm leading-6">Usamos dados apenas para atendimento'''

new2_lgpd = '''    elif "data-lgpd-banner" not in cleaned.lower():
        banner = (
            '<div data-lgpd-banner class="fixed bottom-4 left-4 right-4 z-50 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-neutral-950/95 px-4 py-3 shadow-2xl backdrop-blur" '
            'style="color:var(--text,#e2e8f0);background:color-mix(in srgb, var(--bg,#0b0f19) 92%, transparent)">'
            '<span class="min-w-0 flex-1 text-sm leading-6">Usamos dados apenas para atendimento'''

if old2_lgpd in s2:
    s2 = s2.replace(old2_lgpd, new2_lgpd, 1)
    with open(p2, 'w') as f:
        f.write(s2)
    print('PATCH2b_OK: LGPD usa CSS vars')
else:
    print('PATCH2b_FAIL: LGPD pattern not found')
    with open(p2, 'w') as f:
        f.write(s2)

# ── PATCH 3: arquiteto_agent_loop.py — max_tokens=4096 ──
p3 = '/app/backend/agents/arquiteto_agent_loop.py'
with open(p3) as f:
    s3 = f.read()
old3 = 'max_tokens=2048,'
new3 = 'max_tokens=4096,'
count3 = s3.count(old3)
if count3 > 0:
    s3 = s3.replace(old3, new3, 1)
    with open(p3, 'w') as f:
        f.write(s3)
    print(f'PATCH3_OK: {count3} x max_tokens boosted 2048->4096')
else:
    if 'max_tokens=4096' in s3:
        print('PATCH3_SKIP: ja esta em 4096')
    else:
        print('PATCH3_FAIL: nao achei max_tokens=2048')
