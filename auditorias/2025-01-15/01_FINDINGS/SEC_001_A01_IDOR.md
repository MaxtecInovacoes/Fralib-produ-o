# SEC-001 — OWASP A01:2021 Broken Access Control
## IDOR CRITICO: Mistura de user_id/tenant_id permite acesso cross-tenant

**Severidade:** CRITICAL
**OWASP Category:** A01:2021 — Broken Access Control
**Subcategoria:** IDOR (Insecure Direct Object Reference)
**Status:** Vulneravel

---

## 1. Localizacao

- **Arquivo:** `backend/endpoints/users_endpoints.py`
- **Endpoints afetados:**
  - `GET /api/users/export` (linha 470)
  - `DELETE /api/users/conta` (linha 555)

---

## 2. Descricao da Vulnerabilidade

A funcao `exportar_dados_usuario` (linha 470) usa `user_id` e `tenant_id` de forma **inconsistente** entre as tabelas, e a funcao `deletar_conta_usuario` (linha 555) replica o mesmo problema.

O token JWT e `get_current_user()` retornam `tenant_id` definido como `users.tenant_id OR user_id`. A不一致ancia ocorre porque algumas tabelas Relacionam dados por `user_id` e outras por `tenant_id`, sem garantir que ambos sejam iguais para o mesmo usuario.

**Query que busca leads** — usa `tenant_id`:
```python
leads = db.execute(
    text("""
        SELECT id, nome, email, telefone, whatsapp, cidade, segmento,
               url_site, site_url, tier, status, created_at, atualizado_em
        FROM leads WHERE user_id = :uid
    """),
    {"uid": tenant_id}   # <-- usa tenant_id
).fetchall()
```

**Query que busca interacoes** — usa `tenant_id`:
```python
interacoes = db.execute(
    text("""
        SELECT id, lead_id, tipo, mensagem, direction, created_at
        FROM interacoes WHERE user_id = :uid
    """),
    {"uid": tenant_id}   # <-- usa tenant_id
).fetchall()
```

**Query que busca pipelines** — usa `tenant_id`:
```python
pipelines = db.execute(
    text("""
        SELECT id, lead_id, fase_atual, status, started_at, finished_at
        FROM pipeline_runs WHERE user_id = :uid
    """),
    {"uid": tenant_id}   # <-- usa tenant_id
).fetchall()
```

**Query que busca usuario** — usa `user_id` diretamente:
```python
user_data = db.execute(
    text("SELECT id, email, name, nome, plano, plan, created_at FROM users WHERE id = :id"),
    {"id": user_id}   # <-- usa user_id, nao tenant_id
).fetchone()
```

**Query que busca credits** — usa `user_id`:
```python
credits = db.execute(
    text("""
        SELECT credits, plano, renovacao, usado_mes
        FROM users WHERE id = :id
    """),
    {"id": user_id}   # <-- usa user_id, nao tenant_id
).fetchone()
```

**Query que busca sdr_settings** — usa `user_id`:
```python
sdr_settings = db.execute(
    text("""
        SELECT config_key, config_value
        FROM user_configs WHERE user_id = :uid
    """),
    {"uid": user_id}   # <-- usa user_id, nao tenant_id
).fetchall()
```

O mesmo problema se repete em `deletar_conta_usuario`:

| Tabela | Campo usado | Inconsistente? |
|--------|------------|---------------|
| `interacoes` | `user_id = :uid` com `uid = tenant_id` | Usa tenant_id |
| `pipeline_runs` | `user_id = :uid` com `uid = tenant_id` | Usa tenant_id |
| `pipeline_failures` | `tenant_id = :tid` com `tid = tenant_id` | Usa tenant_id |
| `leads` | `user_id = :uid` com `uid = tenant_id` | Usa tenant_id |
| `user_configs` | `user_id = :uid` com `uid = user_id` | Usa user_id |
| `licencas` | `user_id = :uid` com `uid = user_id` | Usa user_id |
| `users` | `id = :id` com `id = user_id` | Usa user_id |

---

## 3. Impacto

**Impacto:** Um atacante autenticado pode acceder, exportar ou excluir dados de **OUTRO TENANT** se o `tenant_id` do seu usuario for diferente do seu proprio `user_id`.

**Cenarios de ataque:**

1. Um usuario com `user_id=5` e `tenant_id=3` autenticado na API pode:
   - Exportar todos os leads de quem tem `user_id=3`
   - Exportar todas as interacoes de quem tem `user_id=3`
   - Exportar todos os pipelines de quem tem `user_id=3`

2. O mesmo problema se aplica ao endpoint de exclusao de conta, permitindo que um usuario delete dados de outro tenant.

**Dado comprometido:** Dados pessoais de leads (nome, email, telefone, cidade, segmento), historico de conversas, dados de pipeline, configs SDR — potencialmente de TODOS os tenants no sistema.

---

## 4. Exploit Proof of Concept

```http
# 1. Login como tenant-b (user_id=5, tenant_id=3)
POST /api/auth/login
{"email": "usuario_b@email.com", "password": "..."}

# Resposta contem token JWT com sub=5 e tenant_id=3

# 2. Exportar dados do tenant-a (tenant_id diferente do user_id)
GET /api/users/export
Authorization: Bearer <token_usuario_b>

# Se tenant_id do usuario B for diferente do user_id dele,
# retorna dados do tenant errado
```

---

## 5. Correcao Recomendada

**Opcao A — Uniformizar para `user_id` em todos os endpoints LGPD:**

```python
# Linha 480
tenant_id = user.get("tenant_id", user_id)

# REMOVER esta linha e usar user_id consistentemente:
#uid = user_id  #统一用 user_id do token

# Queries devem usar user_id:
leads = db.execute(
    text("SELECT ... FROM leads WHERE user_id = :uid"),
    {"uid": user_id}  # sempre user_id
).fetchall()

interacoes = db.execute(
    text("SELECT ... FROM interacoes WHERE user_id = :uid"),
    {"uid": user_id}  # sempre user_id
).fetchall()

# O mesmo para deletar_conta_usuario:
db.execute(text("DELETE FROM interacoes WHERE user_id = :uid"), {"uid": user_id})
db.execute(text("DELETE FROM leads WHERE user_id = :uid"), {"uid": user_id})
```

**Opcao B — Uniformizar para `tenant_id` em todas as tabelas:**

Se o modelo de negocio exige multi-tenancy via `tenant_id`, todas as tabelas (`users`, `user_configs`, `licencas`) tambem devem usar `tenant_id` como chave.

---

## 6. Controle de Acesso Verificado (nao vulneravel)

Os seguintes endpoints estao **CORRETAMENTE** protegidos e **NAO** tem IDOR:

| Arquivo | Endpoint | Protecao verificada |
|---------|----------|--------------------|
| `leads_crud.py` linha 105 | `PATCH /api/leads/{lead_id}` | `WHERE id=:lead_id AND user_id=:uid` — CORRETO |
| `leads_crud.py` linha 152 | `POST /api/leads/{lead_id}/reprocessar` | `WHERE id=:id AND user_id=:uid` — CORRETO |
| `leads_crud.py` linha 181 | `POST /api/leads/{lead_id}/editar-site` | `WHERE id=:id AND user_id=:uid` + plano check — CORRETO |
| `leads_crud.py` linha 331 | `POST /api/leads/{lead_id}/upload-foto` | `WHERE id=:id AND user_id=:uid` — CORRETO |
| `leads_crud.py` linha 490 | `DELETE /api/leads/{lead_id}` | `WHERE id=:id AND user_id=:uid` — CORRETO |
| `leads_crud.py` linha 524 | `PATCH /api/leads/{lead_id}/aprovar-pipeline` | `WHERE id=:id AND user_id=:uid` — CORRETO |
| `leads_crud.py` linha 554 | `PATCH /api/leads/{lead_id}/descartar` | `WHERE id=:id AND user_id=:uid` — CORRETO |
| `leads_crud.py` linha 584 | `PATCH /api/leads/{lead_id}/campos` | `WHERE id=:id AND user_id=:uid` — CORRETO |
| `leads_queries.py` linha 46 | `GET /api/leads/{lead_id}/conversa` | `JOIN leads ... WHERE ... AND l.user_id=:uid` — CORRETO |
| `leads_queries.py` linha 96 | `GET /api/leads/{lead_id}/chat` | `WHERE id=:id AND user_id=:uid` + msgs sem filter mas lead ja validado — CORRETO |
| `leads_crud_sdr.py` linha 27 | `POST /api/leads/{lead_id}/feedback` | `WHERE id=:id AND user_id=:uid` + JOIN no SELECT de interacoes — CORRETO |
| `leads_crud_sdr.py` linha 146 | `POST /api/leads/{lead_id}/enviar-mensagem` | `WHERE id=:id AND user_id=:uid` + plano check — CORRETO |
| `users_endpoints.py` linha 113 | `GET /api/users/profile` | `WHERE id=:user_id` — CORRETO (dados proprios) |
| `users_endpoints.py` linha 143 | `PUT /api/users/profile` | `WHERE id=:user_id` — CORRETO (dados proprios) |
| `users_endpoints.py` linha 166 | `PUT /api/users/password` | `WHERE id=:user_id` — CORRETO (dados proprios) |
| `users_endpoints.py` linha 200 | `GET /api/users/onboarding-status` | `WHERE id=:user_id` — CORRETO (dados proprios) |

---

## 7. Metadata

- **Analisado por:** Claude Security Auditor
- **Data:** 2025-01-15
- **Framework:** FastAPI + SQLAlchemy + PostgreSQL
- **Commits verificados:** 6b3dcd3 (SITES_DIR configuravel)
- **Autenticacao:** JWT Bearer + CSRF cookie — funcionando corretamente
- **Bloqueio por status:** Implementado em `auth.py` linha 153 — `BLOCKED_USER_STATUSES` proativamente bloqueia contas inadimplentes
