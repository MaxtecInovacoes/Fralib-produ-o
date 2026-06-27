#!/usr/bin/env python3
"""Sprint 12.14: Fix vite_react_renderer.py - segment-aware + literal backslash-n sanitizer."""
import re, sys

fp = 'C:/fralib/backend/services/vite_react_renderer.py'
with open(fp, encoding='utf-8') as f:
    c = f.read()
orig_len = len(c)

# ============================================================
# FIX 1: Add \n literal sanitizer to _normalize_generated_imports_and_hooks
# ============================================================
old_norm_start = 'def _normalize_generated_imports_and_hooks(files: dict[str, str]) -> None:\n    card_stub_needed = False'
new_norm_start = '''def _normalize_generated_imports_and_hooks(files: dict[str, str]) -> None:
    # Sprint 12.14: fix LLM generating literal backslash-n instead of real newlines
    for path in list(files.keys()):
        if path.endswith((".tsx", ".ts")):
            files[path] = files[path].replace("\\\\n", "\\n")

    card_stub_needed = False'''
if old_norm_start in c:
    c = c.replace(old_norm_start, new_norm_start)
    print('FIX 1: backslash-n sanitizer added to normalize')
else:
    print('FIX 1: SKIP (already applied or pattern changed)')

# ============================================================
# FIX 2: Studio fallback - fix Navbar nav items
# ============================================================
old_nav_items = '\t          <a className="hover:text-white" href="#servicos">Treinos</a>\n\t          <a className="hover:text-white" href="#galeria">Galeria</a>\n\t          <a className="hover:text-white" href="#contato">Contato</a>'
if old_nav_items in c:
    c = c.replace(old_nav_items, '{nav_links}')
    print('FIX 2a: Navbar nav_items -> {nav_links}')
else:
    print('FIX 2a: SKIP')

if '>Matricula</a>' in c:
    c = c.replace('>Matricula</a>', '>{cta_primary}</a>')
    print('FIX 2b: Matricula -> {cta_primary}')
else:
    print('FIX 2b: SKIP')

# ============================================================
# FIX 3: HeroSection - fix hardcoded description and CTAs
# ============================================================
old_hero = 'Academia fitness com treino funcional, musculacao, alunos acompanhados, modalidade certa e matricula simples pelo WhatsApp'
if old_hero in c:
    c = c.replace(old_hero, '{hero_desc}')
    print('FIX 3a: hero description -> {hero_desc}')
else:
    print('FIX 3a: SKIP')

if '>Comecar treino</a>' in c:
    c = c.replace('>Comecar treino</a>', '>{cta_primary}</a>')
    print('FIX 3b: Comecar treino -> {cta_primary}')
else:
    print('FIX 3b: SKIP')

if '>Ver estrutura</a>' in c:
    c = c.replace('>Ver estrutura</a>', '>{cta_secondary}</a>')
    print('FIX 3c: Ver estrutura -> {cta_secondary}')
else:
    print('FIX 3c: SKIP')

# ============================================================
# FIX 4: ServicesSection - hardcoded academia content
# ============================================================
old_services = '"src/components/ServicesSection.tsx": component("ServicesSection", """  return <section id="servicos" className="bg-zinc-950 px-6 py-24 text-white"><div className="mx-auto max-w-6xl"><p className="text-sm font-bold uppercase tracking-[0.2em] text-emerald-200">servicos</p><h2 className="mt-3 text-4xl font-black">Treinos claros para cada objetivo</h2><div className="mt-10 grid gap-4 md:grid-cols-3"><article className="rounded-3xl border border-white/10 bg-white/[.04] p-6"><h3 className="text-xl font-bold">Musculacao orientada</h3><p className="mt-3 text-zinc-400">Acompanhamento para alunos e treino seguro.</p></article><article className="rounded-3xl border border-white/10 bg-white/[.04] p-6"><h3 className="text-xl font-bold">Treino funcional</h3><p className="mt-3 text-zinc-400">Modalidade dinamica para evolucao real.</p></article><article className="rounded-3xl border border-white/10 bg-white/[.04] p-6"><h3 className="text-xl font-bold">Matricula simples</h3><p className="mt-3 text-zinc-400">Entrada rapida para comecar hoje.</p></article></div></div></section>;""")'
if old_services in c:
    c = c.replace(old_services, '"src/components/ServicesSection.tsx": component("ServicesSection", f"""  return <section id="servicos" className="bg-zinc-950 px-6 py-24 text-white"><div className="mx-auto max-w-6xl"><p className="text-sm font-bold uppercase tracking-[0.2em] text-emerald-200">servicos</p><h2 className="mt-3 text-4xl font-black">Nossos servicos</h2><div className="mt-10 grid gap-4 md:grid-cols-3">{services_articles}</div></div></section>;""")')
    print('FIX 4: ServicesSection -> services_articles')
else:
    print('FIX 4: SKIP')

# ============================================================
# FIX 5: GallerySection - hardcoded alt text
# ============================================================
if 'alt="Area de musculacao"' in c:
    c = c.replace('alt="Area de musculacao"', 'alt="{alt_img}"')
    print('FIX 5a: gallery alt 1')
if 'alt="Treino funcional"' in c:
    c = c.replace('alt="Treino funcional"', 'alt="{alt_img}"')
    print('FIX 5b: gallery alt 2')
if 'alt="Alunos em treino fitness"' in c:
    c = c.replace('alt="Alunos em treino fitness"', 'alt="{alt_img}"')
    print('FIX 5c: hero alt text')

# ============================================================
# FIX 6: LifestyleSection - hardcoded text
# ============================================================
old_ls_title = '<h2 className="mt-3 text-4xl font-black">Ambiente de treino, energia e constancia</h2>'
if old_ls_title in c:
    c = c.replace(old_ls_title, '<h2 className="mt-3 text-4xl font-black">{lifestyle_title}</h2>')
    print('FIX 6a: lifestyle title')

old_ls_desc = 'Um espaco local para criar rotina, encontrar orientacao e manter frequencia sem complicar'
if old_ls_desc in c:
    c = c.replace(old_ls_desc, '{lifestyle_desc}')
    print('FIX 6b: lifestyle desc')

# ============================================================
# Validate
# ============================================================
try:
    compile(c, fp, 'exec')
    print(f'SYNTAX: OK ({len(c)} chars, delta: +{len(c)-orig_len})')
except SyntaxError as e:
    print(f'SYNTAX ERROR line {e.lineno}: {e.msg}')
    sys.exit(1)

with open(fp, 'w', encoding='utf-8') as f:
    f.write(c)
print('WRITTEN OK')
