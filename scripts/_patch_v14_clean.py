#!/usr/bin/env python3
"""
Sprint 12.14: Clean patch - restore from git, then apply fixes only.
Uses git clean version as base (no corruption risk).
"""
import subprocess
import re
import sys

VPS = 'root@100.101.18.1'
REMOTE_PATH = '/root/fralib/backend/services/vite_react_renderer.py'
LOCAL_CLEAN = '/tmp/vite_clean.py'
LOCAL_PATCHED = '/tmp/vite_patched.py'

# Step 1: Already have clean version from git (checked earlier)
# Step 2: Read clean version
with open(LOCAL_CLEAN, 'r', encoding='utf-8') as f:
    content = f.read()
print(f'Loaded clean version: {len(content)} chars')

# ============================================================
# FIX 1: Studio fallback - add segment awareness BEFORE files = {
# Find the "dense_cards" line and replace with segment-aware version
# ============================================================
# Find the old hardcoded dense_cards
old_dense = '    dense_cards = "\\n".join(\n        f\'<div className="rounded-3xl border border-white/10 bg-white/[.04] p-5 text-white"><strong className="block text-xl text-emerald-200">0{i}</strong><span className="text-sm text-zinc-300">academia fitness treino musculacao alunos modalidade matricula</span></div>\'\n        for i in range(1, 10)\n    )'
if old_dense in content:
    content = content.replace(old_dense, '    dense_cards = "\\n".join(\n        f\'<div className="rounded-3xl border border-white/10 bg-white/[.04] p-5 text-white"><strong className="block text-xl text-emerald-200">0{i}</strong><span className="text-sm text-zinc-300">{svc_labels[i-1]}</span></div>\'\n        for i in range(1, 6)\n    )')
    print('FIX 1a: dense_cards now uses svc_labels')
else:
    print('FIX 1a: SKIPPED (pattern not found)')

# Fix HeroSection hardcoded description
old_hero = '<p className="max-w-2xl text-lg leading-8 text-zinc-300">Academia fitness com treino funcional, musculacao, alunos acompanhados, modalidade certa e matricula simples pelo WhatsApp.</p>'
if old_hero in content:
    content = content.replace(old_hero, '<p className="max-w-2xl text-lg leading-8 text-zinc-300">{hero_desc}</p>')
    print('FIX 1b: hero description uses variable')
else:
    print('FIX 1b: SKIPPED (pattern not found)')

# Fix Navbar hardcoded nav items and CTA
old_nav = '''          <a className="hover:text-white" href="#servicos">Treinos</a>
	          <a className="hover:text-white" href="#galeria">Galeria</a>
	          <a className="hover:text-white" href="#contato">Contato</a>
        </div>
        <a className="rounded-full bg-emerald-300 px-4 py-2 text-sm font-bold text-zinc-950 max-sm:px-3 max-sm:text-xs" href="tel:{phone}">Matricula</a>'''
if old_nav in content:
    content = content.replace(old_nav, '''          {nav_links}
        </div>
        <a className="rounded-full bg-emerald-300 px-4 py-2 text-sm font-bold text-zinc-950 max-sm:px-3 max-sm:text-xs" href="tel:{phone}">{cta_primary}</a>''')
    print('FIX 1c: Navbar uses variables')
else:
    print('FIX 1c: SKIPPED (pattern not found)')

# Fix ServicesSection hardcoded
old_services = '"src/components/ServicesSection.tsx": component("ServicesSection", """  return <section id="servicos" className="bg-zinc-950 px-6 py-24 text-white"><div className="mx-auto max-w-6xl"><p className="text-sm font-bold uppercase tracking-[0.2em] text-emerald-200">servicos</p><h2 className="mt-3 text-4xl font-black">Treinos claros para cada objetivo</h2><div className="mt-10 grid gap-4 md:grid-cols-3"><article className="rounded-3xl border border-white/10 bg-white/[.04] p-6"><h3 className="text-xl font-bold">Musculacao orientada</h3><p className="mt-3 text-zinc-400">Acompanhamento para alunos e treino seguro.</p></article><article className="rounded-3xl border border-white/10 bg-white/[.04] p-6"><h3 className="text-xl font-bold">Treino funcional</h3><p className="mt-3 text-zinc-400">Modalidade dinamica para evolucao real.</p></article><article className="rounded-3xl border border-white/10 bg-white/[.04] p-6"><h3 className="text-xl font-bold">Matricula simples</h3><p className="mt-3 text-zinc-400">Entrada rapida para comecar hoje.</p></article></div></div></section>;""")'
if old_services in content:
    content = content.replace(old_services, '"src/components/ServicesSection.tsx": component("ServicesSection", f"""  return <section id="servicos" className="bg-zinc-950 px-6 py-24 text-white"><div className="mx-auto max-w-6xl"><p className="text-sm font-bold uppercase tracking-[0.2em] text-emerald-200">servicos</p><h2 className="mt-3 text-4xl font-black">Nossos servicos</h2><div className="mt-10 grid gap-4 md:grid-cols-3">{services_articles}</div></div></section>;""")')
    print('FIX 1d: ServicesSection uses variable')
else:
    print('FIX 1d: SKIPPED (pattern not found)')

# ============================================================
# FIX 2: Add \n literal sanitizer at top of normalize function
# ============================================================
old_norm = 'def _normalize_generated_imports_and_hooks(files: dict[str, str]) -> None:\n    card_stub_needed = False'
new_norm = 'def _normalize_generated_imports_and_hooks(files: dict[str, str]) -> None:\n    # Sprint 12.14: fix LLM generating literal backslash-n instead of real newlines\n    for path in list(files.keys()):\n        if path.endswith((".tsx", ".ts")):\n            files[path] = files[path].replace("\\\\n", "\\n")\n\n    card_stub_needed = False'
if old_norm in content:
    content = content.replace(old_norm, new_norm)
    print('FIX 2: \\n sanitizer added')
else:
    print('FIX 2: SKIPPED (pattern not found)')

# Validate syntax
try:
    compile(content, LOCAL_PATCHED, 'exec')
    print('SYNTAX: OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')
    sys.exit(1)

# Write patched version
with open(LOCAL_PATCHED, 'w', encoding='utf-8') as f:
    f.write(content)
print(f'Written: {LOCAL_PATCHED} ({len(content)} chars)')

# Copy to VPS
result = subprocess.run(
    ['scp', '-o', 'ConnectTimeout=10', LOCAL_PATCHED, f'{VPS}:{REMOTE_PATH}'],
    capture_output=True, text=True
)
if result.returncode == 0:
    print('Copied to VPS: OK')
else:
    print(f'COPY FAILED: {result.stderr}')
    sys.exit(1)

print('ALL DONE')
