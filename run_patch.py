"""Patch 3-corruption-points para a pipeline do Arquiteto + Builder."""
import re

def run():
    # ── PATCH 1: step_arquiteto.py ────────────────────────────────────────
    p1 = '/app/backend/agents/manager/step_arquiteto.py'
    with open(p1) as f:
        s1 = f.read()
    if 'import json' not in s1:
        s1 = s1.replace('import logging\nimport time', 'import json\nimport logging\nimport time', 1)

    marker = '    return result\n'
    idx = s1.rfind(marker)
    if idx == -1:
        print('PATCH1_FAIL: marker not found')
    else:
        dict_fields_block = (
            "    # normaliza campos que devem ser dict mas vieram como string JSON\n"
            "    _DICT_FIELDS = {\"variation_blueprint\",\"typography\",\"color_palette\",\"media_plan\",\n"
            "        \"visual_dna\",\"creative_direction\",\"niche_brief\",\"site_build_plan\",\n"
            "        \"requirements_contract\",\"visual_contract\",\"layout_blueprint\",\n"
            "        \"design_reference_pack\",\"anti_patterns\",\"schema_org_types\",\n"
            "        \"components_21dev\",\"faq_questions\",\"value_props\",\"seo_keywords\"}\n"
            "    for _k in _DICT_FIELDS:\n"
            "        if _k in result and isinstance(result[_k], str):\n"
            "            _v = result[_k].strip()\n"
            "            if (_v.startswith('{') and _v.endswith('}')) or (_v.startswith('[') and _v.endswith(']')):\n"
            "                try: result[_k] = json.loads(_v)\n"
            "                except Exception: pass\n"
            "    # sanitize footer section (evita 'N\\u00da QUE...' e footer vazio do chunked merge)\n"
            "    _f = next((_s for _s in result.get('sections', []) if isinstance(_s, dict) and _s.get('name','').lower() == 'footer'), None)\n"
            "    if _f and not (_f.get('copy') or _f.get('content') or _f.get('text')):\n"
            "        _f['copy'] = result.get('business_name','') or ''\n"
            "        _f['content'] = {'name':'footer', 'business_name': result.get('business_name','')}\n"
            "    return result\n"
        )
        s1 = s1[:idx] + dict_fields_block + s1[idx + len(marker):]
        with open(p1, 'w') as f:
            f.write(s1)
        print('PATCH1_OK: step_arquiteto normalizacao + footer sanitize')

    # ── PATCH 2: step_builder.py ──────────────────────────────────────────
    p2 = '/app/backend/agents/manager/step_builder.py'
    with open(p2) as f:
        s2 = f.read()

    # 2a: footer design system via CSS vars (replaces classes cruas)
    footer_old = 'bg-neutral-950 text-white'
    footer_new = 'style="background:var(--bg,#0b0f19);color:var(--text,#e2e8f0)"'
    cnt_f = s2.count(footer_old)
    print(f'footer bg-neutral-950 text-white occurrences: {cnt_f}')
    if cnt_f >= 1:
        s2 = s2.replace(footer_old, footer_new, 1)
        # tambem injeta accent no h1 do footer via sutil replace do class font-semibold do nome
        s2 = s2.replace(
            'f\'<div><p class="text-lg font-semibold">{name}</p>',
            'f\'<div><p class="text-lg font-semibold" style="color:var(--accent,#e85d4a)">{name}</p>',
            1
        )
        with open(p2, 'w') as f:
            f.write(s2)
        print('PATCH2a_OK: footer com CSS vars')
    else:
        print('PATCH2a_FAIL')

    # 2b: LGPD banner com CSS vars (ja aplicado no patch anterior, confirmar)
    if 'color-mix' in s2:
        print('PATCH2b_OK: LGPD ja esta com CSS vars')
    else:
        lgpd_old = 'bg-neutral-950/95 px-4 py-3 text-white shadow-2xl backdrop-blur'
        lgpd_new = 'bg-neutral-950/95 px-4 py-3 shadow-2xl backdrop-blur" style="color:var(--text,#e2e8f0)'
        if lgpd_old in s2:
            s2 = s2.replace(lgpd_old, lgpd_new, 1)
            with open(p2, 'w') as f:
                f.write(s2)
            print('PATCH2b_OK: LGPD com CSS vars')
        else:
            print('PATCH2b_FAIL: ja pode ter sido aplicado')

    # ── PATCH 3: arquiteto_agent_loop.py ───────────────────────────────────
    p3 = '/app/backend/agents/arquiteto_agent_loop.py'
    with open(p3) as f:
        s3 = f.read()
    old3 = 'max_tokens=2048,'
    new3 = 'max_tokens=4096,'
    c3 = s3.count(old3)
    if c3 > 0:
        s3 = s3.replace(old3, new3, 1)
        with open(p3, 'w') as f:
            f.write(s3)
        print(f'PATCH3_OK: {c3} x max_tokens boosted')
    elif 'max_tokens=4096' in s3:
        print('PATCH3_SKIP: ja esta em 4096')
    else:
        print('PATCH3_FAIL')


if __name__ == '__main__':
    run()
