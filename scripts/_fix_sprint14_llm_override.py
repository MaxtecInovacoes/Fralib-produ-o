#!/usr/bin/env python3
"""Fix: move LLM override BEFORE var_map in _interpolate_studio_placeholders."""
with open('backend/services/vite_react_renderer.py', encoding='utf-8') as f:
    src = f.read()

# 1. Remove the misplaced block (after var_map = {)
misplaced = '''
    # Sprint 14: apply LLM copy_only overrides before building var_map.
    # FraLib code has {cta_primary} etc as literals; copy_only LLM fills them.
    if llm_content:
        hero = llm_content.get("hero", {}) if isinstance(llm_content.get("hero"), dict) else {}
        life = llm_content.get("lifestyle") if isinstance(llm_content.get("lifestyle"), dict) else {}
        if hero.get("cta_primary"):
            cta_primary = str(hero["cta_primary"])
        if hero.get("cta_secondary"):
            cta_secondary = str(hero["cta_secondary"])
        if llm_content.get("gallery_alt"):
            alt_img = str(llm_content["gallery_alt"])
        if life.get("title"):
            lifestyle_title = str(life["title"])
        if life.get("description"):
            lifestyle_desc = str(life["description"])

'''
if misplaced in src:
    src = src.replace(misplaced, '', 1)
    print('Removed misplaced block')
else:
    print('Misplaced block NOT found - may already be correct')

# 2. Add llm_content extraction AFTER import re
old_import = '    import re as _re\n\n    business = facts.get("business")'
new_import = '''    import re as _re

    # Sprint 14: extract LLM copy_only content for content override
    llm_content: dict[str, Any] = {}
    if isinstance(facts.get("_llm_content"), dict):
        llm_content = facts["_llm_content"]

    business = facts.get("business")'''

if old_import in src:
    src = src.replace(old_import, new_import, 1)
    print('Added llm_content extraction')
else:
    print('import block NOT found')

# 3. Add override BEFORE var_map (after the segment if/elif chain ends)
marker = '    # Map of placeholder var name -> replacement value'
idx = src.find(marker)
if idx < 0:
    print('var_map marker NOT found!')
else:
    override_before = '''
    # Sprint 14: apply LLM copy_only overrides before building var_map.
    if llm_content:
        hero = llm_content.get("hero", {}) if isinstance(llm_content.get("hero"), dict) else {}
        life = llm_content.get("lifestyle") if isinstance(llm_content.get("lifestyle"), dict) else {}
        if hero.get("cta_primary"):
            cta_primary = str(hero["cta_primary"])
        if hero.get("cta_secondary"):
            cta_secondary = str(hero["cta_secondary"])
        if llm_content.get("gallery_alt"):
            alt_img = str(llm_content["gallery_alt"])
        if life.get("title"):
            lifestyle_title = str(life["title"])
        if life.get("description"):
            lifestyle_desc = str(life["description"])

'''
    src = src[:idx] + override_before + src[idx:]
    print('Added override block before var_map')

# Verify syntax
try:
    compile(src, 'vite_react_renderer.py', 'exec')
    print('SYNTAX: OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')

# Quick sanity check
func_start = src.find('def _interpolate_studio_placeholders')
func_end = src.find('def ', func_start + 10)
func_src = src[func_start:func_end]
has_llm_early = 'llm_content: dict' in func_src[:300]
has_override = 'if llm_content:' in func_src[300:]
print(f'llm_content defined early: {has_llm_early}')
print(f'override block present: {has_override}')

with open('backend/services/vite_react_renderer.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('Saved.')
