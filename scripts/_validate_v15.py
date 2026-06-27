import re
import sys
sys.path.insert(0, '/root/fralib/backend')

with open('/root/fralib/.tmp/builder-workspaces/tenant-2/job-v15-real/dist/index.html', encoding='utf-8') as f:
    html = f.read()

print('=== CONTENT VALIDATION ===')
checks = [
    ('Corte (barbearia)', 'Corte'),
    ('Barba (barbearia)', 'Barba'),
    ('Sobrancelha (barbearia)', 'Sobrancelha'),
    ('Agendar horario (barbearia)', 'Agendar horario'),
    ('Tradicao em cada corte', 'Tradicao em cada corte'),
    ('musculacao (BAD)', 'musculacao'),
    ('academia (BAD)', 'academia'),
    ('crossfit (BAD)', 'crossfit'),
]
for label, kw in checks:
    found = kw.lower() in html.lower()
    status = 'OK' if found else 'FAIL'
    note = '' if found else ' <-- MISSING!'
    if 'BAD' in label:
        status2 = 'FAIL (found - contamination!)' if found else 'OK (not found - clean)'
        print(f'  {label}: {status2}')
    else:
        print(f'  {label}: {status}{note}')

m = re.search(r'<title>(.*?)</title>', html)
print(f'Title: {m.group(1) if m else "N/A"}')
m = re.search(r'LocalBusiness', html)
print(f'LocalBusiness schema: {"YES" if m else "NO"}')
m = re.search(r'FAQPage', html)
print(f'FAQ schema: {"YES" if m else "NO"}')
m = re.search(r'lgpd|data-lgpd', html)
print(f'LGPD banner: {"YES" if m else "NO"}')
print(f'HTML size: {len(html)} bytes')
print()
print(f'URL: https://seunegociofralib.site/sites/2/barbearia-fio-nobre-v15/')
