#!/usr/bin/env python3
"""Validate copy_only mode: segment defaults vs LLM overrides."""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'backend')
from backend.services.vite_react_renderer import _generate_studio_fallback_files, prepare_vite_project_files

# TEST A: SEM _llm_content (segment defaults)
print('=== TEST A: SEM _llm_content (segment defaults) ===')
facts_a = {
    'business': {
        'name': 'Barbearia Fio Nobre',
        'segmento': 'barbearia',
        'cidade': 'Pinhais',
        'whatsapp': '41999999999'
    }
}
files_a = prepare_vite_project_files(
    _generate_studio_fallback_files(facts_a), facts=facts_a
)
cta_a = 'Agendar horario' in ' '.join(files_a.values())
life_a = 'Tradicao em cada corte' in ' '.join(files_a.values())
all_ok_a = cta_a and life_a
print(f'  CTA segment default (Agendar horario): {cta_a}')
print(f'  Lifestyle segment default (Tradicao em cada corte): {life_a}')

# TEST B: COM _llm_content (copy_only LLM overrides)
print()
print('=== TEST B: COM _llm_content (copy_only LLM overrides) ===')
facts_b = {
    'business': {
        'name': 'Barbearia Fio Nobre',
        'segmento': 'barbearia',
        'cidade': 'Pinhais',
        'whatsapp': '41999999999'
    },
    '_llm_content': {
        'hero': {
            'cta_primary': 'Agendar Corte Premium',
            'cta_secondary': 'Ver Tratamentos'
        },
        'lifestyle': {
            'title': 'Arte em Cada Corte',
            'description': 'Barbearia artesanal em Pinhais.'
        },
        'gallery_alt': 'Barbearia Fio Nobre ambiente'
    }
}
files_b = prepare_vite_project_files(
    _generate_studio_fallback_files(facts_b), facts=facts_b
)
cta_b = 'Agendar Corte Premium' in ' '.join(files_b.values())
cta_sec_b = 'Ver Tratamentos' in ' '.join(files_b.values())
life_b = 'Arte em Cada Corte' in ' '.join(files_b.values())
gallery_b = 'Barbearia Fio Nobre ambiente' in ' '.join(files_b.values())
all_ok_b = cta_b and cta_sec_b and life_b and gallery_b
print(f'  CTA LLM (Agendar Corte Premium): {cta_b}')
print(f'  CTA secondary LLM (Ver Tratamentos): {cta_sec_b}')
print(f'  Lifestyle LLM (Arte em Cada Corte): {life_b}')
print(f'  Gallery alt LLM: {gallery_b}')

# TEST C: Academia segment
print()
print('=== TEST C: Academia segment ===')
facts_c = {
    'business': {
        'name': 'Academia Forte',
        'segmento': 'crossfit',
        'cidade': 'Curitiba',
        'whatsapp': '41999999999'
    }
}
files_c = prepare_vite_project_files(
    _generate_studio_fallback_files(facts_c), facts=facts_c
)
cta_c = 'Comecar treino' in ' '.join(files_c.values())
svc_c = 'ServicesSection.tsx' in files_c
life_c = 'Energia e constancia' in ' '.join(files_c.values())
all_ok_c = cta_c and svc_c and life_c
print(f'  CTA academia (Comecar treino): {cta_c}')
print(f'  ServicesSection presente: {svc_c}')
print(f'  Lifestyle academia: {life_c}')

# SUMMARY
print()
print('=' * 50)
if all_ok_a and all_ok_b and all_ok_c:
    print('TODOS OS TESTES PASSARAM (3/3)')
else:
    print('ALGUNS TESTES FALHARAM')
    print(f'  A: {all_ok_a}, B: {all_ok_b}, C: {all_ok_c}')
