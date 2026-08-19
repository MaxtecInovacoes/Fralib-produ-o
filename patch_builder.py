"""Patch Builder Agent — 4 upgrades: CSS tokens, hermetic sealing, dynamic order, archetype+FAQ directive."""
import re


def run():
    p = '/app/backend/agents/builder/agent.py'
    with open(p) as f:
        s = f.read()

    # ── UPGRADE 1: CSS tokens in shell ─────────────────────────────────────
    # Update _inject_deterministic_assets to emit unprefixed :root vars
    # AND add font-heading / font-body / radius tokens.
    old_tokens = '''    brand_style = (
        '<style id="brand-design-tokens">'
        f":root{{--brand-primary:{primary};--brand-secondary:{secondary};"
        f"--brand-accent:{accent};--brand-bg:{bg};--brand-surface:{surface};"
        f"--brand-text:{text};--brand-border:{border};--brand-muted:{muted};}}"
        "</style>"
    )'''
    new_tokens = '''    radius = _first("radius", "--radius", "border_radius") or "8px"
    heading_font = _first("heading_font", "--font-heading") or "Inter"
    body_font = _first("body_font", "--font-body") or "Inter"
    # Emite vars SEM prefixo (:root) para o directive consumir com var(--bg)
    # Mantem --brand-* como fallback para estilos legados.
    brand_style = (
        '<style id="design-tokens">'
        f":root{{"
        f"--bg:{bg};--surface:{surface};--foreground:{text};"
        f"--muted:{muted};--primary:{primary};--primary-fg:{text};"
        f"--border:{border};--radius:{radius};"
        f"--font-heading:{heading_font};--font-body:{body_font};"
        f"--brand-primary:{primary};--brand-secondary:{secondary};"
        f"--brand-accent:{accent};--brand-bg:{bg};--brand-surface:{surface};"
        f"--brand-text:{text};--brand-border:{border};--brand-muted:{muted};}}"
        "</style>"
    )'''
    if old_tokens in s:
        s = s.replace(old_tokens, new_tokens, 1)
        print('UPGRADE1_OK: CSS :root tokens injected')
    else:
        print('UPGRADE1_FAIL: brand_style pattern not found')

    # ── UPGRADE 2: Hermetic section sealing ─────────────────────────────────
    old_wrap = (
        'f\'<section id="{sec_id}" class="w-full relative overflow-hidden clear-both block">\\n\''
    )
    new_wrap = (
        'f\'<section id="{sec_id}" class="w-full block clear-both relative overflow-hidden">\\n\''
    )
    if old_wrap in s:
        s = s.replace(old_wrap, new_wrap, 1)
        # also harden: if fragment starts with bare content (no section), already wrapped above.
        # Add a post-wrap sanitize: strip outer <section> if fragment already had one,
        # to avoid <section><section> nesting.
        old_nested = '''        # Se o fragmento ja inicia com <section>, usa ele direto (evita <section><section>)'''
        new_nested = '''        # Se o fragmento ja inicia com <section>, usa ele direto (evita <section><section>)
        # Remove outer <section> do fragmento para evitar <section><section>'''
        if old_nested in s:
            s = s.replace(old_nested, new_nested, 1)
        print('UPGRADE2_OK: hermetic section sealing class reorder')
    else:
        # try alternate quoting
        alt_old = '<section id="{sec_id}" class="w-full relative overflow-hidden clear-both block">'
        alt_new = '<section id="{sec_id}" class="w-full block clear-both relative overflow-hidden">'
        if alt_old in s:
            s = s.replace(alt_old, alt_new, 1)
            print('UPGRADE2_OK: hermetic sealing (alt pattern)')
        else:
            print('UPGRADE2_FAIL: wrap pattern not found')

    # ── UPGRADE 3: Dynamic section order from variation_blueprint ───────────
    # Insert a sort-by-order_index pass right after getting `sections` in
    # _render_section_blocks.
    old_dyn = '''    # Dynamic: one OpenUI call per section
    for s in sections:'''
    new_dyn = '''    # Ordenar secoes pela ordem do variation_blueprint (quando disponivel)
    order_index_map = {}
    try:
        _vb = spec.get("variation_blueprint") or {}
        _order = _vb.get("ordem_das_secoes") or []
        order_index_map = {str(n).strip().lower(): i for i, n in enumerate(_order) if str(n).strip()}
    except Exception:
        pass
    if order_index_map:
        sections = sorted(
            sections,
            key=lambda s: order_index_map.get(str(s.get("name", "")).strip().lower(), 9999),
        )
    # Dynamic: one OpenUI call per section
    for s in sections:'''
    if old_dyn in s:
        s = s.replace(old_dyn, new_dyn, 1)
        print('UPGRADE3_OK: dynamic section order via variation_blueprint')
    else:
        print('UPGRADE3_FAIL: dynamic section pattern not found')

    # ── UPGRADE 4: Archetype briefing + native FAQ + watermark shield in directive
    # (a) inject archetype briefing
    old_directive_start = '''    builder_directive = f"Landing page para {prd.business_name}'''
    new_directive_start = '''    archetype_slug_for_directive = getattr(prd, "design_system_slug", None) or "editorial-asymmetric"
    archetype_briefing = _archetype_briefing(archetype_slug_for_directive)
    builder_directive = f"Landing page para {prd.business_name}'''
    if old_directive_start in s:
        s = s.replace(old_directive_start, new_directive_start, 1)
        # (b) inject archetype + native FAQ + watermark shield before the closing quote of builder_directive
        old_directive_end = '''        "- CTA buttons: hover:brightness-1.1 hover:shadow-lg com transição 200ms.\\n"
    )'''
        new_directive_end = '''        "- CTA buttons: hover:brightness-1.1 hover:shadow-lg com transição 200ms.\\n"
        "ARQUÉTIPO VISUAL ATIVO (OBRIGATÓRIO):\\n"
        f"- {archetype_briefing}\\n"
        f"- Fontes: heading={archetype_system.get('heading_font','Inter')}, "
        f"body={archetype_system.get('body_font','Inter')}, "
        f"border-radius={archetype_system.get('border_radius','8px')}.\\n"
        f"- Card style: {archetype_system.get('card_style','shadow-elevated')}.\\n"
        "FAQ NATIVO HTML5 (OBRIGATÓRIO):\\n"
        "- Cada pergunta do FAQ DEVE usar <details class=\\"bg-[var(--surface)] border border-[var(--border)] "
        'rounded-[var(--radius)] p-4\\"> e <summary class=\\"font-bold text-[var(--foreground)] cursor-pointer\\">.\\n'
        "  Nunca use listas <ul>/<li> ou acordeão JavaScript puro para FAQ.\\n"
        "SHIELD DE TEXTO DECORATIVO (OBRIGATÓRIO):\\n"
        "- Qualquer texto decorativo de fundo (ex: \\'FALE\\', \\'TREINE\\', marca d\\'\\u00e1gua) "
        'DEVE ter exatamente as classes: absolute -z-10 opacity-[0.03] select-none pointer-events-none.\\n'
        "- NUNCA posicione texto decorativo sobre dados de contato, CTA ou áreas de ação.\\n"
    )'''
        if old_directive_end in s:
            s = s.replace(old_directive_end, new_directive_end, 1)
            print('UPGRADE4_OK: archetype + native FAQ + watermark shield in directive')
        else:
            print('UPGRADE4b_FAIL: directive end pattern not found')
    else:
        print('UPGRADE4a_FAIL: directive start pattern not found')

    with open(p, 'w') as f:
        f.write(s)
    print('WRITE_OK: builder/agent.py patched')


if __name__ == '__main__':
    run()
