"""
Auditoria focada: entender se o bug CAUSOU persistencia de dados errados
ou se era apenas um bug de leitura/listagem.
"""
import subprocess

DB = "PGPASSWORD=fralib2024 psql -h localhost -p 5433 -U postgres -d fralib_db -c"

queries = [
    ("Total de leads por tenant",
     "SELECT user_id, COUNT(*) FROM leads GROUP BY user_id ORDER BY user_id"),

    ("Estrutura site_url do tenant 2 (sample)",
     "SELECT id, user_id, nome, site_url, url_site FROM leads WHERE user_id = 2 AND (site_url IS NOT NULL OR url_site IS NOT NULL) ORDER BY criado_em DESC LIMIT 10"),

    ("Estrutura site_url do tenant 31 (sample)",
     "SELECT id, user_id, nome, site_url, url_site FROM leads WHERE user_id = 31 AND (site_url IS NOT NULL OR url_site IS NOT NULL) ORDER BY criado_em DESC LIMIT 10"),

    ("Quantos leads o tenant 2 tem COM site_url (antes do get_sites)",
     "SELECT COUNT(*) FROM leads WHERE user_id = 2 AND site_url IS NOT NULL AND site_url != ''"),

    ("Quantos leads o tenant 31 tem COM site_url",
     "SELECT COUNT(*) FROM leads WHERE user_id = 31 AND site_url IS NOT NULL AND site_url != ''"),

    ("Algum lead do 2 tem site_url apontando para pasta 31?",
     "SELECT id, user_id, site_url FROM leads WHERE user_id = 2 AND site_url LIKE '%/sites/31/%'"),

    ("Algum lead do 31 tem site_url apontando para pasta 2?",
     "SELECT id, user_id, site_url FROM leads WHERE user_id = 31 AND site_url LIKE '%/sites/2/%'"),
]

for label, sql in queries:
    print(f"\n{label}")
    print("-" * 70)
    r = subprocess.run(
        ["ssh", "root@187.77.37.72", f"{DB} \"{sql}\""],
        capture_output=True, text=True, timeout=30,
        encoding='latin-1', errors='replace'
    )
    print(r.stdout)