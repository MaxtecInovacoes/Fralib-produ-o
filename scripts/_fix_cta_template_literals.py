#!/usr/bin/env python3
"""
Sprint 14.2: Fix CTAs to use {{}} so they become literals,
then _interpolate_studio_placeholders can override them with LLM content.
"""
with open('backend/services/vite_react_renderer.py', encoding='utf-8') as f:
    src = f.read()

changes = 0

# STEP 1: In _generate_studio_fallback_files templates, change {cta_primary} -> {{cta_primary}}
# These are inside f-string component() calls. The f-string evaluates {} so we need {{}} for literals.
# Find: >{cta_primary}<  (HTML text node)
old1 = 'href="tel:{phone}">{cta_primary}</a>'
new1 = 'href="tel:{phone}">{{cta_primary}}</a>'
if old1 in src:
    src = src.replace(old1, new1, 1)  # Navbar (first occurrence)
    src = src.replace(old1, new1, 1)  # HeroSection (second occurrence)
    changes += 1
    print('Fixed CTA buttons (Navbar + HeroSection)')

# Find: >{cta_secondary}<
old2 = 'href="#galeria">{cta_secondary}</a>'
new2 = 'href="#galeria">{{cta_secondary}}</a>'
if old2 in src:
    src = src.replace(old2, new2, 1)
    changes += 1
    print('Fixed CTA secondary')

# Find: alt="{alt_img}" in HeroSection and GallerySection
old3 = 'alt="{alt_img}" loading="eager"'
new3 = 'alt="{{alt_img}}" loading="eager"'
if old3 in src:
    src = src.replace(old3, new3, 1)
    changes += 1
    print('Fixed alt_img HeroSection')

old4 = 'alt="{alt_img}" loading="lazy" decoding="async"'
new4 = 'alt="{{alt_img}}" loading="lazy" decoding="async"'
if old4 in src:
    src = src.replace(old4, new4, 1)  # first gallery img
    src = src.replace(old4, new4, 1)  # second gallery img
    changes += 1
    print('Fixed alt_img GallerySection')

# BookingModal CTA
old5 = 'onClick={{() => setOpen(true)}}>{cta_primary}</button>'
new5 = 'onClick={{() => setOpen(true)}}>{{cta_primary}}</button>'
if old5 in src:
    src = src.replace(old5, new5, 1)
    changes += 1
    print('Fixed BookingModal CTA')

# LifestyleSection (already double - confirm)
if '{{lifestyle_title}}' in src:
    print('LifestyleSection already uses {{}} - OK')

# STEP 2: Update _interpolate_studio_placeholders var_map to include CTA and alt_img
# The var_map already has cta_primary etc but the literal {cta_primary} won't appear
# in files if we don't add it. Let's check if it's already there.
old_map = '''    var_map = {
        "name": name,
        "phone": phone,
        "rating": rating,
        "city": city,
        "segment": raw_segment,
        "cta_primary": cta_primary,
        "cta_secondary": cta_secondary,
        "alt_img": alt_img,
        "lifestyle_title": lifestyle_title,
        "lifestyle_desc": lifestyle_desc,
    }'''

new_map = '''    # Sprint 14.2: var_map now includes ALL customizable text fields
    # {{cta_primary}}, {{cta_secondary}}, {{alt_img}} are literals in TSX files
    # from the studio fallback templates. This map replaces them.
    var_map = {
        "name": name,
        "phone": phone,
        "rating": rating,
        "city": city,
        "segment": raw_segment,
        "cta_primary": cta_primary,
        "cta_secondary": cta_secondary,
        "alt_img": alt_img,
        "lifestyle_title": lifestyle_title,
        "lifestyle_desc": lifestyle_desc,
    }'''

if old_map in src:
    src = src.replace(old_map, new_map, 1)
    changes += 1
    print('Updated var_map comment')
else:
    print('var_map already updated or not found')
    # Try to find what's there
    idx = src.find('var_map = {')
    if idx >= 0:
        print('Current var_map:', repr(src[idx:idx+300]))

# STEP 3: Add literal-replacement logic for {{var}} in TSX files
# The interpolation uses re to find {var} but our literals are now {{var}}.
# We need to handle both patterns: {var} and {{var}}.
# Find the interpolation loop and update the pattern.
old_pattern = 're.compile(r"\\{(?![{])(" + "|".join(_re.escape(k) for k in var_map) + r")\\}")'
if old_pattern in src:
    print('Found old interpolation pattern - will update')
    # The pattern finds single {var}. Since we now have {{var}}, we need
    # to find {{var}} first and replace with {var}, then find {var} and replace with value.
    # This is a two-pass approach.
else:
    # Find where the interpolation happens
    interp_idx = src.find('re.sub(')
    if interp_idx >= 0:
        print('Interpolation at:', repr(src[interp_idx:interp_idx+200]))

# Verify syntax
try:
    compile(src, 'vite_react_renderer.py', 'exec')
    print('SYNTAX: OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')

with open('backend/services/vite_react_renderer.py', 'w', encoding='utf-8') as f:
    f.write(src)
print(f'Done ({changes} changes)')
