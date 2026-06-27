#!/usr/bin/env python3
"""Sprint 14.2: Testa Studio fallback com lead real Tenant 2."""
import sys, os, tempfile, shutil
sys.path.insert(0, 'C:/fralib;C:/fralib/backend')
os.environ['FRALIB_VITE_LLM_POLICY'] = 'copy_only'

from backend.services.vite_react_renderer import render_vite_react_site

# Lead real Tenant 2 - Barbearia Fio Nobre
facts = {
    'business': {
        'name': 'Barbearia Fio Nobre Pinhais',
        'segmento': 'barbearia',
        'cidade': 'Pinhais',
        'whatsapp': '41999999999',
        'phone': '41999999999',
        'rating': '4.8',
        'total_avaliacoes': '127',
        'endereco': 'Centro, Pinhais - PR',
        'services': ['Corte masculino', 'Barba', 'Sobrancelha', 'Pigmentacao', 'Platinado'],
        'horarios': 'Seg-Sex 9h-20h | Sab 9h-18h',
        'description': 'Barbearia premium em Pinhais com ambiente moderno e barbeiros certificados.',
        'differentials': ['Atendimento premium', 'Barbeiros certificados', 'Produtos importados'],
    },
    'segmento': 'barbearia',
    'city': 'Pinhais',
    'id': 'sprint14-test-barbearia-20260625',
    'tenant_id': 2,
    'site_build_plan': {
        'section_plan': [
            {'id': 'hero', 'role': 'capture'},
            {'id': 'servicos', 'role': 'information'},
            {'id': 'galeria', 'role': 'trust'},
            {'id': 'contato', 'role': 'conversion'},
        ]
    },
}

print('=== SPRINT 14.2: Studio fallback LEAD REAL Tenant 2 ===')
print()

# Gerar com studio fallback
print('[1/4] Gerando arquivos com Studio fallback...')
workspace = tempfile.mkdtemp(prefix='fralib_s14_')
try:
    result = render_vite_react_site(
        builder_prompt='Gere landing page para Barbearia Fio Nobre Pinhais',
        workspace_dir=workspace,
        facts=facts,
        render_only=True,
    )
    print(f'Result: {result.get("status", "unknown")}')
    errors = result.get('errors', [])
    if errors:
        print(f'Erros: {errors}')
    print()

    # Listar arquivos
    tsx_files = [f for f in os.listdir(workspace) if f.endswith('.tsx') or f.endswith('.ts')]
    print(f'[2/4] Arquivos TSX: {len(tsx_files)}')

    # HeroSection
    hero_path = os.path.join(workspace, 'src', 'components', 'HeroSection.tsx')
    if os.path.exists(hero_path):
        with open(hero_path, encoding='utf-8') as f:
            hero = f.read()
        print(f'[3/4] HeroSection: {len(hero)} chars')
        print()
        print('--- HeroSection CTAs ---')
        for line in hero.splitlines():
            stripped = line.strip()
            if 'Agendar' in stripped or 'Ver' in stripped or 'href=' in stripped:
                print(f'  {stripped[:120]}')
        print()
        print('--- HeroSection title ---')
        for line in hero.splitlines():
            if '<h1' in line.lower() or '<h2' in line.lower():
                print(f'  {line.strip()[:120]}')
    else:
        print('[3/4] HeroSection NAO ENCONTRADO')
        print('Disponiveis:', [f for f in os.listdir(workspace) if 'Hero' in f or 'Section' in f])

    # ServicesSection
    print()
    svc_path = os.path.join(workspace, 'src', 'components', 'ServicesSection.tsx')
    if os.path.exists(svc_path):
        print('[4/4] ServicesSection: PRESENTE')
        with open(svc_path, encoding='utf-8') as f:
            svc = f.read()
        for line in svc.splitlines():
            if 'Corte' in line or 'Barba' in line:
                print(f'  {line.strip()[:100]}')
    else:
        print('[4/4] ServicesSection: AUSENTE')

    # LifestyleSection
    life_path = os.path.join(workspace, 'src', 'components', 'LifestyleSection.tsx')
    if os.path.exists(life_path):
        print()
        print('LifestyleSection: PRESENTE')
        with open(life_path, encoding='utf-8') as f:
            life = f.read()
        for line in life.splitlines():
            if 'Tradicao' in line or 'experiencia' in line:
                print(f'  {line.strip()[:100]}')

finally:
    shutil.rmtree(workspace, ignore_errors=True)
    print()
    print(f'Workspace limpo')
