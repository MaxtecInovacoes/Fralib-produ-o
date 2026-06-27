#!/usr/bin/env python3
"""Sprint 12.16: Re-run smoke with name injection fix."""
import sys, os, json, time
sys.path.insert(0, '/root/fralib/backend')
os.environ['DATABASE_URL'] = 'postgresql://postgres:postgres@localhost:5432/postgres'

from services.builder_worker import render_site_with_builder

# PRD com business no top level (como o orchestrator faria)
prd = {
    'id': 'smoke-v15b',
    'tenant_id': 2,
    'business': {
        'name': 'Barbearia Fio Nobre Pinhais',
        'segmento': 'barbearia',
        'cidade': 'Pinhais',
        'whatsapp': '41999999999',
        'phone': '41999999999',
        'endereco': 'Centro, Pinhais - PR',
        'rating': '4.8',
        'total_avaliacoes': '127',
    },
    'segmento': 'barbearia',
}
result = render_site_with_builder(prd, tenant_id='2', job_id='v15b-smoke', target='landing-page')
print('engine:', result.get('engine'))
print('model:', result.get('model'))
print('html_len:', len(result.get('html','')))
print('index_path:', result.get('index_path'))
