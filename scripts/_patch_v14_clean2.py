#!/usr/bin/env python3
"""Sprint 12.14: Fix vite_react_renderer - use raw strings for all patterns."""
import subprocess, sys

VPS = 'root@100.101.18.1'
REMOTE = '/root/fralib/backend/services/vite_react_renderer.py'
CLEAN = '/tmp/vite_clean.py'
PATCHED = '/tmp/vite_patched.py'

with open(CLEAN, 'r', encoding='utf-8') as f:
    c = f.read()
print(f'Clean: {len(c)} chars')

# ---- FIX 1a: dense_cards hardcoded academia ----
# Search for unique marker: "academia fitness treino musculacao alunos modalidade matricula"
marker = 'academia fitness treino musculacao alunos modalidade matricula'
idx = c.find(marker)
if idx > 0:
    # Find the start of this dense_cards line (go back to find "dense_cards =")
    start = c.rfind('    dense_cards =', 0, idx)
    end = c.find('\n    files =', idx)
    if start > 0 and end > 0:
        old_block = c[start:end]
        new_block = r'''    dense_cards = "\n".join(
        f'<div className="rounded-3xl border border-white/10 bg-white/[.04] p-5 text-white"><strong className="block text-xl text-emerald-200">0{i}</strong><span className="text-sm text-zinc-300">{svc_labels[i-1]}</span></div>'
        for i in range(1, 6)
    )'''
        c = c[:start] + new_block + c[end:]
        print('FIX 1a: dense_cards uses svc_labels')
    else:
        print('FIX 1a: SKIP (bounds not found)')
else:
    print('FIX 1a: SKIP (marker not found)')

# ---- FIX 1b: hero hardcoded description ----
old_hero = 'Academia fitness com treino funcional, musculacao, alunos acompanhados, modalidade certa e matricula simples pelo WhatsApp'
idx2 = c.find(old_hero)
if idx2 > 0:
    c = c.replace(old_hero, '{hero_desc}')
    print('FIX 1b: hero uses {hero_desc}')
else:
    print('FIX 1b: SKIP')

# ---- FIX 1c: Navbar hardcoded nav items + Matricula ----
old_nav = 'href="#servicos">Treinos</a>'
if old_nav in c:
    # Replace specific hardcoded parts
    c = c.replace('<a className="hover:text-white" href="#servicos">Treinos</a>', '{nav_links}')
    # Replace the three nav items - find and replace the block
    old_navblock = '<a className="hover:text-white" href="#servicos">Treinos</a>\n\t          <a className="hover:text-white" href="#galeria">Galeria</a>\n\t          <a className="hover:text-white" href="#contato">Contato</a>'
    new_navblock = '{nav_links}'
    if old_navblock in c:
        c = c.replace(old_navblock, new_navblock)
        print('FIX 1c: Navbar nav_items replaced')
    else:
        print('FIX 1c: SKIP (navblock not found as single string)')
    # Fix CTA text
    if '>Matricula</a>' in c:
        c = c.replace('>Matricula</a>', '>{cta_primary}</a>')
        print('FIX 1c: Navbar CTA uses {cta_primary}')
else:
    print('FIX 1c: SKIP')

# ---- FIX 1d: ServicesSection hardcoded academia content ----
marker2 = 'Musculacao orientada'
idx3 = c.find(marker2)
if idx3 > 0:
    # Find the whole ServicesSection string
    start2 = c.rfind('"src/components/ServicesSection.tsx": component', 0, idx3)
    end2 = c.find('",\n        "src/components/GallerySection', idx3)
    if start2 > 0 and end2 > 0:
        old_ss = c[start2:end2]
        new_ss = r'''"src/components/ServicesSection.tsx": component("ServicesSection", f"""  return <section id="servicos" className="bg-zinc-950 px-6 py-24 text-white"><div className="mx-auto max-w-6xl"><p className="text-sm font-bold uppercase tracking-[0.2em] text-emerald-200">servicos</p><h2 className="mt-3 text-4xl font-black">Nossos servicos</h2><div className="mt-10 grid gap-4 md:grid-cols-3">{services_articles}</div></div></section>;""")'''
        c = c[:start2] + new_ss + c[end2:]
        print('FIX 1d: ServicesSection uses services_articles')
    else:
        print('FIX 1d: SKIP (bounds not found)')
else:
    print('FIX 1d: SKIP')

# ---- FIX 2: Add \n literal sanitizer ----
old_norm = 'def _normalize_generated_imports_and_hooks(files: dict[str, str]) -> None:\n    card_stub_needed = False'
if old_norm in c:
    c = c.replace(old_norm,
        'def _normalize_generated_imports_and_hooks(files: dict[str, str]) -> None:\n'
        '    # Sprint 12.14: fix LLM generating literal backslash-n instead of real newlines\n'
        '    for path in list(files.keys()):\n'
        '        if path.endswith((".tsx", ".ts")):\n'
        '            files[path] = files[path].replace("\\\\n", "\\n")\n'
        '\n'
        '    card_stub_needed = False')
    print('FIX 2: \\n sanitizer added')
else:
    print('FIX 2: SKIP')

# Validate
try:
    compile(c, REMOTE, 'exec')
    print('SYNTAX: OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR line {e.lineno}: {e.msg}')
    sys.exit(1)

with open(PATCHED, 'w', encoding='utf-8') as f:
    f.write(c)
print(f'Written: {len(c)} chars')

result = subprocess.run(['scp', '-o', 'ConnectTimeout=10', PATCHED, f'{VPS}:{REMOTE}'],
    capture_output=True, text=True)
if result.returncode == 0:
    print('Copied to VPS: OK')
else:
    print(f'COPY FAILED: {result.stderr}')
    sys.exit(1)

print('ALL DONE')
