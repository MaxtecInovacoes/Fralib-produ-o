#!/usr/bin/env python3
"""Apply Sprint 14.1 fix: LLM content overrides in _interpolate_studio_placeholders."""
import re

with open('backend/services/vite_react_renderer.py', encoding='utf-8') as f:
    src = f.read()

changes = 0

# CHANGE 2: After segment if/elif chain and before var_map, add LLM override
marker = '    # Map of placeholder var name -> replacement value'
idx = src.find(marker)
if idx < 0:
    print('CHANGE 2: marker NOT FOUND')
else:
    override_block = '''
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
    src = src[:idx] + override_block + src[idx:]
    changes += 1
    print('CHANGE 2: Added LLM override block')

# Verify Python syntax
try:
    compile(src, 'vite_react_renderer.py', 'exec')
    print('SYNTAX: OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')

with open('backend/services/vite_react_renderer.py', 'w', encoding='utf-8') as f:
    f.write(src)

print(f'Total changes: {changes}')
