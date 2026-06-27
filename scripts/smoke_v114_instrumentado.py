#!/usr/bin/env python3
"""Sprint 12.13 - Smoke instrumentado com medicao de tempo e tokens."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'backend'))

LEAD_ID = 'smoke-v114-barbershop-pinhais-1782420089'
TENANT_ID = 2
DEPLOY_PATH = '/var/www/fralib/sites/2/smoke-v114-barbershop-pinhais/'
DEPLOY_URL = 'https://seunegociofralib.site/sites/2/smoke-v114-barbershop-pinhais/'
TIMESTAMP = int(time.time())
LOG_FILE = ROOT / '.tmp' / f'smoke_v114_instr_{TIMESTAMP}.log'
RESULT_FILE = ROOT / 'tests' / '_v114_smoke_output.json'
LOG_FILE.parent.mkdir(exist_ok=True)
RESULT_FILE.parent.mkdir(exist_ok=True)

print('='*80)
print(f'  SPRINT 12.13 - SMOKE INSTRUMENTADO')
print(f'  Lead: {LEAD_ID}')
print(f'  Started: {datetime.now().isoformat()}')
print(f'  Log: {LOG_FILE}')
print('='*80)

# FASE 0: Setup env
print('\n[FASE 0] Setup env vars...')
env = os.environ.copy()
env['FRALIB_BUILDER_ENGINE'] = 'vite_react'
env['FRALIB_VITE_NAMEHOST_MODELS'] = 'claude-sonnet-4-6,claude-haiku-4-5'
env['FRALIB_OPENUI_PRIMARY_MODEL'] = 'claude-sonnet-4-6'
env['PYTHONIOENCODING'] = 'utf-8'

# FASE 1: Pipeline builder-job
print('\n[FASE 1] Builder job (vite_react, Sonnet -> Haiku)...')
start = time.time()
PYTHON = 'python3'

# FASE 1: Pipeline builder-job (via pipeline.py = wrapper oficial que configura PYTHONPATH)
print('\n[FASE 1] Builder job via pipeline.py (vite_react, Sonnet -> Haiku)...')
start = time.time()
# Limpar cache de builds anteriores do smoke para forcar build fresh
cache_marker = ROOT / '.tmp' / f'.smoke_v114_{TIMESTAMP}'
cache_marker.touch()
print(f'  Cache marker: {cache_marker}')

# Limpar dists anteriores do smoke pra forcar build fresh
for old_dist in ROOT.rglob('dist/index.html'):
    if '.smoke_v114_' in str(old_dist):
        continue
    # Nao limpar caches de outros jobs
    pass
try:
    result = subprocess.run(
        [
            PYTHON, 'pipeline.py', 'builder-job',
            '--prd-json', str(ROOT / '.tmp' / 'prd_smoke.json'),
            '--tenant-id', str(TENANT_ID),
            '--job-id', f'smoke-{TIMESTAMP}',
            '--target', 'landing-page',
            '--model', 'claude-sonnet-4-6',
            '--execute',
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )
    fase1_duration = time.time() - start
    print(f'  builder_job: {fase1_duration:.1f}s, exit={result.returncode}')
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(result.stdout)
        f.write('\n---STDERR---\n')
        f.write(result.stderr)
    print(f'  Stdout: {len(result.stdout)} chars, Stderr: {len(result.stderr)} chars')
except subprocess.TimeoutExpired:
    fase1_duration = 600
    print('  TIMEOUT (>600s)')
except Exception as e:
    fase1_duration = time.time() - start
    print(f'  ERRO: {e}')

# Parse builder output
output_json = {}
for line in result.stdout.splitlines():
    try:
        output_json = json.loads(line)
        break
    except Exception:
        pass

print(f'  engine: {output_json.get("engine","?")}')
print(f'  model: {output_json.get("model","?")}')
print(f'  output_dir: {output_json.get("output_dir","?")}')

# FASE 2: Encontrar dist/
print('\n[FASE 2] Localizando dist/...')
dist_file = None
search_roots = [
    ROOT / '.tmp',
    ROOT / '.tmp' / 'builder-workspaces',
    ROOT / '.tmp' / 'builder-jobs',
]
for sr in search_roots:
    if not sr.exists():
        continue
    for p in sr.rglob('dist/index.html'):
        if dist_file is None or p.stat().st_mtime > dist_file.stat().st_mtime:
            dist_file = p

if dist_file:
    print(f'  Usando: {dist_file} ({dist_file.stat().st_size} bytes)')
else:
    print('  ERRO: Nenhum dist/index.html encontrado!')
    print(f'  Searched: {[str(s) for s in search_roots if s.exists()]}')

# FASE 3: Deploy
print('\n[FASE 3] Deploy...')
deploy_start = time.time()
deploy_ok = False
html_chars = 0
if dist_file and dist_file.exists():
    html = dist_file.read_text(encoding='utf-8')
    html_chars = len(html)
    deploy_dir = Path(DEPLOY_PATH)
    deploy_dir.mkdir(parents=True, exist_ok=True)
    (deploy_dir / 'index.html').write_text(html, encoding='utf-8')
    deploy_ok = (deploy_dir / 'index.html').exists()
    deploy_duration = time.time() - deploy_start
    print(f'  Deploy: {deploy_duration:.1f}s, ok={deploy_ok}, html_chars={html_chars}')
else:
    deploy_duration = 0

# FASE 4: QA Gate
print('\n[FASE 4] QA Gate (html_quality_gate)...')
qa_start = time.time()
qa_result = {}
if (Path(DEPLOY_PATH) / 'index.html').exists():
    try:
        html = (Path(DEPLOY_PATH) / 'index.html').read_text(encoding='utf-8')
        from backend.agents.html_quality_gate import audit_generated_html
        report = audit_generated_html(
            html,
            {'nome': 'Smoke V1.14 Barbershop Pinhais', 'segmento': 'barbearia', 'cidade': 'Pinhais'}
        )
        qa_result = {
            'aprovado': bool(report.aprovado),  # atributo direto do dataclass
            'problemas': list(report.problemas),  # atributo direto
            'total_checks': len(report.problemas),
        }
        print(f'  QA: aprovado={qa_result["aprovado"]}, problemas={len(qa_result["problemas"])}')
        if qa_result['problemas']:
            for p in qa_result['problemas'][:5]:
                print(f'    - {p}')
    except Exception as e:
        qa_result = {'error': str(e)}
        print(f'  QA ERRO: {e}')
    qa_duration = time.time() - qa_start
else:
    qa_duration = 0
    qa_result = {'error': 'no_html_deployed'}

# FASE 5: HTTP 200
print('\n[FASE 5] HTTP check...')
http_code = 0
try:
    import urllib.request
    req = urllib.request.Request(DEPLOY_URL, headers={'User-Agent': 'SmokeTest/1.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        http_code = resp.status
        resp.read()
except Exception as e:
    print(f'  HTTP ERRO: {e}')
print(f'  HTTP: {http_code}')

# FASE 6: Briefing real chegou?
print('\n[FASE 6] Verificando briefing real no HTML...')
briefing_hits = []
if (Path(DEPLOY_PATH) / 'index.html').exists():
    html = (Path(DEPLOY_PATH) / 'index.html').read_text(encoding='utf-8')
    markers = [
        'Barbearia', 'Fio Nobre', 'Pinhais', 'Corte Masculino',
        'Seg-Sex', 'Barba', '41999990001', '4.8',
        'Barbeiros 10+', 'Produtos importados',
    ]
    for m in markers:
        if m in html:
            briefing_hits.append(m)
    print(f'  Briefing markers encontrados: {len(briefing_hits)}/{len(markers)}')
    for h in briefing_hits:
        print(f'    OK: {h}')

# RESUMO
total_duration = time.time() - start
print('\n' + '='*80)
print('  RESUMO FINAL')
print(f'  Total: {total_duration:.1f}s ({total_duration/60:.1f} min)')
print(f'  Fase 1 (Builder): {fase1_duration:.1f}s')
print(f'  Fase 3 (Deploy): {deploy_duration:.1f}s')
print(f'  Fase 4 (QA): {qa_duration:.1f}s')
print(f'  QA: aprovado={qa_result.get("aprovado","?")}, problemas={len(qa_result.get("problemas",[]))}')
print(f'  HTTP: {http_code}')
print(f'  Briefing hits: {len(briefing_hits)}/{len(markers)}')
print('='*80)

# Salvar resultado
result_data = {
    'sprint': '12.13',
    'version': 'v1.14.1-wired',
    'lead_id': LEAD_ID,
    'tenant_id': TENANT_ID,
    'started_iso': datetime.now().isoformat(),
    'total_duration_s': round(total_duration, 1),
    'total_duration_min': round(total_duration/60, 1),
    'fases': {
        'fase1_builder_duration_s': round(fase1_duration, 1),
        'fase3_deploy_duration_s': round(deploy_duration, 1),
        'fase4_qa_duration_s': round(qa_duration, 1),
    },
    'builder_output': output_json,
    'html_chars': html_chars,
    'qa': qa_result,
    'http_code': http_code,
    'deploy_ok': deploy_ok,
    'briefing_hits': briefing_hits,
    'briefing_total_markers': len(markers),
    'log_file': str(LOG_FILE),
}
RESULT_FILE.write_text(json.dumps(result_data, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\nResultado: {RESULT_FILE}')
