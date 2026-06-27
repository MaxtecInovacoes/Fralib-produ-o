import re
with open('/root/fralib/.tmp/builder-workspaces/tenant-2/job-v15-real/dist/assets/index-d2IQiDSN.js', encoding='utf-8', errors='ignore') as f:
    js = f.read()

print('=== VALIDACAO COMPLETA DO JS BUNDLE ===')

good = ['Corte', 'Barba', 'Sobrancelha', 'Pigmentacao', 'Agendar horario']
for kw in good:
    found = kw in js
    status = 'OK' if found else 'MISSING!'
    print(f'  GOOD {kw}: {status}')

bad = ['musculacao', 'academia', 'crossfit', 'Spinning', 'Crossfit', 'Treino funcional']
for kw in bad:
    found = kw in js
    status = 'CONTAMINATION!' if found else 'OK (clean)'
    print(f'  BAD  {kw}: {status}')

lead_ok = 'Fio Nobre' in js or 'Barbearia Fio' in js
print(f'  Lead name Fio Nobre: {"OK" if lead_ok else "MISSING!"}')

seg_ok = 'barbearia' in js
print(f'  Segment barbearia: {"OK" if seg_ok else "MISSING!"}')

print()
print(f'JS bundle: {len(js)} bytes')
print()
print(f'SITE: https://seunegociofralib.site/sites/2/barbearia-fio-nobre-v15/')
