"""Script isolado para query do banco - evita problemas de encoding."""
import sys
import os

# Forçar encoding antes de tudo
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'C.UTF-8'

import psycopg2
import psycopg2.extensions

# Registrar handler customizado para passwords
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

# Conexão com encoding explícito
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='fralib_db',
    user='postgres',
    password='fralib2024',
)

cur = conn.cursor()

print('=' * 70)
print('  DASHBOARD DE ANALYTICS - FraLib Landing')
print('=' * 70)

# 1. Visao geral
cur.execute("""
    SELECT
        COUNT(DISTINCT session_id) AS sessoes,
        COUNT(*) FILTER (WHERE evento = 'view') AS views,
        COUNT(*) FILTER (WHERE evento = 'bounce') AS bounces,
        MIN(criado_em) AS primeiro,
        MAX(criado_em) AS ultimo
    FROM landing_analytics
""")
row = cur.fetchone()
sessoes, views, bounces, primeiro, ultimo = row
print(f'\n[1] VISAO GERAL')
print(f'  Sessoes unicas:   {sessoes or 0}')
print(f'  Pageviews:         {views or 0}')
print(f'  Bounces:           {bounces or 0}')
print(f'  Primeiro registro: {primeiro}')
print(f'  Ultimo registro:   {ultimo}')

# 2. Eventos
cur.execute("""
    SELECT evento, COUNT(*) AS total, COUNT(DISTINCT session_id) AS users
    FROM landing_analytics
    GROUP BY evento
    ORDER BY total DESC
""")
print(f'\n[2] EVENTOS REGISTRADOS')
for ev, total, users in cur.fetchall():
    print(f'  {ev:<40} {total:>6} eventos  ({users} sessoes)')

# 3. Eventos de clique (top 10)
cur.execute("""
    SELECT evento, COUNT(*) AS clicks
    FROM landing_analytics
    WHERE evento LIKE 'click%'
    GROUP BY evento
    ORDER BY clicks DESC
""")
print(f'\n[3] CLIQUES POR TIPO')
for ev, clicks in cur.fetchall():
    print(f'  {ev:<40} {clicks:>6} cliques')

# 4. Scroll depth
cur.execute("""
    SELECT
        SPLIT_PART(valor_extra, '|', 1) AS depth,
        COUNT(DISTINCT session_id) AS users
    FROM landing_analytics
    WHERE evento = 'scroll_depth' AND valor_extra LIKE '%|%'
    GROUP BY depth
    ORDER BY depth
""")
print(f'\n[4] SCROLL DEPTH')
for depth, users in cur.fetchall():
    print(f'  {depth:>4}%  {users:>5} usuarios')

# 5. Funil
cur.execute("""
    SELECT
        COUNT(*) FILTER (WHERE evento = 'view') AS visit,
        COUNT(*) FILTER (WHERE evento = 'funnel_scroll_25') AS s25,
        COUNT(*) FILTER (WHERE evento = 'funnel_scroll_50') AS s50,
        COUNT(*) FILTER (WHERE evento = 'funnel_cta_clicked') AS cta,
        COUNT(*) FILTER (WHERE evento = 'funnel_form_submitted') AS form,
        COUNT(DISTINCT session_id) AS sessoes
    FROM landing_analytics
""")
row = cur.fetchone()
visit, s25, s50, cta, form, sessoes = row
print(f'\n[5] FUNIL DE CONVERSAO')
print(f'  Visit:                {visit} ({sessoes} sessoes)')
print(f'  Scroll 25%:           {s25}')
print(f'  Scroll 50%:           {s50}')
print(f'  CTA clicado:          {cta}')
print(f'  Form enviado:         {form}')

# 6. Sessoes com bounce
cur.execute("""
    SELECT
        COUNT(DISTINCT session_id) FILTER (WHERE evento = 'bounce') AS com_bounce,
        COUNT(DISTINCT session_id) AS total
    FROM landing_analytics
""")
row = cur.fetchone()
com_bounce, total = row
if total:
    print(f'\n[6] BOUNCE RATE')
    print(f'  Sessoes com bounce:  {com_bounce}')
    print(f'  Total sessoes:       {total}')
    print(f'  Bounce rate:         {(com_bounce/total*100):.1f}%')

# 7. Tempo medio
cur.execute("""
    SELECT
        AVG(valor_extra::INT) AS media,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor_extra::INT) AS mediana
    FROM landing_analytics
    WHERE evento = 'time_spent' AND valor_extra ~ '^[0-9]+$'
""")
row = cur.fetchone()
if row and row[0]:
    media, mediana = row
    print(f'\n[7] TEMPO DE PERMANENCIA')
    print(f'  Media:   {media:.1f}s ({media/60:.1f} min)')
    print(f'  Mediana: {mediana:.0f}s')

cur.close()
conn.close()
print('\n' + '=' * 70)