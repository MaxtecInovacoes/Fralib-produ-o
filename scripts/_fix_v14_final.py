#!/usr/bin/env python3
"""
Sprint 12.14: Fix vite_react_renderer.py - two fixes only:
  1. Studio fallback: segment-aware content (no more hardcoded academia contamination)
  2. Literal \\n sanitizer: convert LLM's literal "\\n" to real newlines
"""
import re

filepath = '/root/fralib/backend/services/vite_react_renderer.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# FIX 1: Studio fallback - replace hardcoded academia content
# ============================================================
# Find the hardcoded dense_cards line with "academia fitness treino musculacao"
old_studio = '    dense_cards = "\\n".join(\n        f\'<div className="rounded-3xl border border-white/10 bg-white/[.04] p-5 text-white"><strong className="block text-xl text-emerald-200">0{i}</strong><span className="text-sm text-zinc-300">academia fitness treino musculacao alunos modalidade matricula</span></div>\'\n        for i in range(1, 10)\n    )'

if old_studio in content:
    content = content.replace(old_studio, '')
    print('FIX 1a: removed hardcoded dense_cards (academia contamination)')
else:
    print('WARNING: could not find hardcoded dense_cards pattern')

# Find the HeroSection body with hardcoded academia text
old_hero = '          <p className="max-w-2xl text-lg leading-8 text-zinc-300">Academia fitness com treino funcional, musculacao, alunos acompanhados, modalidade certa e matricula simples pelo WhatsApp.</p>'
if old_hero in content:
    content = content.replace(old_hero, '<p className="max-w-2xl text-lg leading-8 text-zinc-300"> {hero_desc} </p>')
    print('FIX 1b: replaced hardcoded hero description with variable')
else:
    print('WARNING: could not find hardcoded hero description')

# Find the old ServicesSection with hardcoded academia content
old_services = '        "src/components/ServicesSection.tsx": component("ServicesSection", """  return <section id="servicos" className="bg-zinc-950 px-6 py-24 text-white"><div className="mx-auto max-w-6xl"><p className="text-sm font-bold uppercase tracking-[0.2em] text-emerald-200">servicos</p><h2 className="mt-3 text-4xl font-black">Treinos claros para cada objetivo</h2><div className="mt-10 grid gap-4 md:grid-cols-3"><article className="rounded-3xl border border-white/10 bg-white/[.04] p-6"><h3 className="text-xl font-bold">Musculacao orientada</h3><p className="mt-3 text-zinc-400">Acompanhamento para alunos e treino seguro.</p></article><article className="rounded-3xl border border-white/10 bg-white/[.04] p-6"><h3 className="text-xl font-bold">Treino funcional</h3><p className="mt-3 text-zinc-400">Modalidade dinamica para evolucao real.</p></article><article className="rounded-3xl border border-white/10 bg-white/[.04] p-6"><h3 className="text-xl font-bold">Matricula simples</h3><p className="mt-3 text-zinc-400">Entrada rapida para comecar hoje.</p></article></div></div></section>;"""),'
if old_services in content:
    content = content.replace(old_services, '        "src/components/ServicesSection.tsx": component("ServicesSection", f"""  return <section id="servicos" className="bg-zinc-950 px-6 py-24 text-white"><div className="mx-auto max-w-6xl"><p className="text-sm font-bold uppercase tracking-[0.2em] text-emerald-200">servicos</p><h2 className="mt-3 text-4xl font-black">Nossos servicos</h2><div className="mt-10 grid gap-4 md:grid-cols-3">{services_articles}</div></div></section>;"""),')
    print('FIX 1c: replaced hardcoded ServicesSection with variable')
else:
    print('WARNING: could not find hardcoded ServicesSection')

# Find Navbar hardcoded "Matricula" and nav items
old_nav = '          <a className="hover:text-white" href="#servicos">Treinos</a>\n\t          <a className="hover:text-white" href="#galeria">Galeria</a>\n\t          <a className="hover:text-white" href="#contato">Contato</a>\n        </div>\n        <a className="rounded-full bg-emerald-300 px-4 py-2 text-sm font-bold text-zinc-950 max-sm:px-3 max-sm:text-xs" href="tel:{phone}">Matricula</a>'
if old_nav in content:
    content = content.replace(old_nav, '          {nav_links}\n        </div>\n        <a className="rounded-full bg-emerald-300 px-4 py-2 text-sm font-bold text-zinc-950 max-sm:px-3 max-sm:text-xs" href="tel:{phone}">{cta_primary}</a>')
    print('FIX 1d: replaced hardcoded Navbar with variables')
else:
    print('WARNING: could not find hardcoded Navbar')

# ============================================================
# FIX 2: Add \\n literal sanitizer at top of normalize function
# ============================================================
old_norm_start = 'def _normalize_generated_imports_and_hooks(files: dict[str, str]) -> None:\n    card_stub_needed = False'
new_norm_start = '''def _normalize_generated_imports_and_hooks(files: dict[str, str]) -> None:
    # Sprint 12.14: fix LLM generating literal backslash-n instead of real newlines
    for path in list(files.keys()):
        if path.endswith((".tsx", ".ts")):
            files[path] = files[path].replace("\\\\n", "\\n")

    card_stub_needed = False'''
if old_norm_start in content:
    content = content.replace(old_norm_start, new_norm_start)
    print('FIX 2: added \\n literal sanitizer')
else:
    print('WARNING: could not find _normalize_generated_imports_and_hooks start')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# Validate syntax
try:
    import ast
    ast.parse(content)
    print('SYNTAX: OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR at line {e.lineno}: {e.msg}')
    print(f'  {e.text}')
    exit(1)

print(f'DONE: {len(content)} chars written')
