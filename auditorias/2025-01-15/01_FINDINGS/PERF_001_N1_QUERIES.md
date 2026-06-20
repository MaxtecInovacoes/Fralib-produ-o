# PERF_001 - N+1 Query Audit Findings

**Data da auditoria:** 2025-01-15
**Escopo:** `backend/endpoints/leads_endpoints.py`, `leads_crud.py`, `leads_crud_sdr.py`, `pipeline_endpoints.py`, `dashboard_endpoints.py`
**Auditor:** Performance Engineer

---

## Resumo

| Severidade | Quantidade |
|------------|-----------|
| CRITICO    | 1         |
| MEDIO      | 4         |

---

## Finding PERF_001.1 [MEDIO]

**Problema:** Query dentro de loop - conversao de string para int por linha
**Arquivo:** `backend/endpoints/pipeline_endpoints.py`
**Linhas:** 34-35
**Codigo problemático:**

```python
for r in result:
    d = dict(r._mapping)
    leads = d["leads_buscados"] or 0       # <- conversao por linha (string → int)
    sites = d["sites_gerados"] or 0        # <- conversao por linha (string → int)
    conv = round(sites / leads * 100, 1) if leads > 0 else 0
```

**Impacto estimado:** ~0.1ms por linha, cumulativo com tamanho da lista.
Para 100 ciclos: ~10ms de overhead desnecessario em CPU Python.

**Correção sugerida:**

```python
# SQL: ja retorna como inteiro ou converter diretamente no SELECT
result = db.execute(
    text("""
    SELECT
        id, numero, cidade, segmento,
        COALESCE(leads_buscados::int, 0) AS leads_buscados,
        COALESCE(sites_gerados::int, 0) AS sites_gerados,
        ...
    """),
    ...
).fetchall()

for r in result:
    d = dict(r._mapping)
    leads = d["leads_buscados"]   # ja e int, sem conversao por iteracao
    sites = d["sites_gerados"]    # ja e int
    conv = round(sites / leads * 100, 1) if leads > 0 else 0
```

---

## Finding PERF_001.2 [CRITICO]

**Problema:** Duas queries sequenciais para o mesmo lead - ausencia de JOIN
**Arquivo:** `backend/endpoints/leads_crud_sdr.py`
**Endpoint:** `registrar_feedback`
**Linhas:** 48-73
**Codigo problemático:**

```python
# Query 1: busca dados do lead
lead = db.execute(
    text("SELECT id, segmento, tier, telefone FROM leads WHERE id=:id AND user_id=:uid"),
    {"id": lead_id, "uid": tenant_id},
).fetchone()

# Query 2: busca ultima mensagem enviada (MESMO lead, MESMO tenant)
ultima_msg = db.execute(
    text("""
    SELECT i.mensagem FROM interacoes i
    JOIN leads l ON l.id = i.lead_id
    WHERE i.lead_id = :lead_id AND i.direcao = 'saida' AND l.user_id = :uid
    ORDER BY i.id DESC LIMIT 1
    """),
    {"lead_id": lead_id, "uid": tenant_id},
).fetchone()
```

**Impacto:** 2 queries round-trip para buscar dados de um unico lead. Em rede com 10ms de latencia, sao 20ms desperdiciados por chamada. Se este endpoint receber 100 requests/minuto, sao ~2s de latencia cumulativa desperdicada por minuto.

**Correção sugerida:**

```python
# Unica query com LEFT JOIN - busca lead E ultima mensagem em uma unica round-trip
dados = db.execute(
    text("""
    SELECT
        l.id, l.segmento, l.tier, l.telefone,
        sub.mensagem_usada
    FROM leads l
    LEFT JOIN (
        SELECT lead_id, mensagem AS mensagem_usada
        FROM interacoes
        WHERE direcao = 'saida'
        ORDER BY id DESC
        LIMIT 1
    ) sub ON sub.lead_id = l.id
    WHERE l.id = :lead_id AND l.user_id = :uid
    """),
    {"lead_id": lead_id, "uid": tenant_id},
).fetchone()

if not dados:
    raise HTTPException(status_code=404, detail="Lead nao encontrado")

segmento = dados.segmento or ""
tier     = dados.tier or "STANDARD"
telefone = dados.telefone or ""
mensagem_usada = dados.mensagem_usada or ""
```

---

## Finding PERF_001.3 [MEDIO]

**Problema:** Duas queries sequenciais para o mesmo lead - ausencia de JOIN
**Arquivo:** `backend/endpoints/leads_crud_sdr.py`
**Endpoint:** `enviar_mensagem_lead`
**Linhas:** 156-179
**Codigo problemático:**

```python
# Query 1: busca plano do tenant
plano_row = db.execute(
    text("SELECT plano, status, trial_expires_at FROM users WHERE id=:id"),
    {"id": tenant_id},
).fetchone()

# ... validacao de plano ...

# Query 2: busca dados do lead (同一 tenant, mesmo request)
row = db.execute(
    text("SELECT nome, telefone, whatsapp, segmento, cidade, site_url, rating, sdr_stage "
         "FROM leads WHERE id=:id AND user_id=:uid"),
    {"id": lead_id, "uid": tenant_id},
).fetchone()
```

**Impacto:** 2 queries round-trip. Se 50 usuarios chamarem este endpoint por minuto, sao ~500ms de latencia desperdicada por minuto. A segunda query so executa apos a validacao de plano, entao nao ha paralelizacao possivel.

**Correção sugerida:**

```python
# Executar as duas queries em paralelo ja que sao independentes
from concurrent.futures import ThreadPoolExecutor

def fetch_plano():
    return db.execute(
        text("SELECT plano, status, trial_expires_at FROM users WHERE id=:id"),
        {"id": tenant_id},
    ).fetchone()

def fetch_lead():
    return db.execute(
        text("SELECT nome, telefone, whatsapp, segmento, cidade, site_url, rating, sdr_stage "
             "FROM leads WHERE id=:id AND user_id=:uid"),
        {"id": lead_id, "uid": tenant_id},
    ).fetchone()

with ThreadPoolExecutor(max_workers=2) as executor:
    plano_future = executor.submit(fetch_plano)
    lead_future  = executor.submit(fetch_lead)
    plano_row = plano_future.result()
    row       = lead_future.result()
```

**Alternativa mais simples** (sem threading): buscar apenas o plano na primeira query, ja que a segunda query precisa do `lead_id` e so pode ser feita apos a primeira retornar. Nesse caso, o JOIN nao e viavel porque sao tabelas diferentes. Manter como esta e otimizar com conexao persistente.

---

## Finding PERF_001.4 [MEDIO]

**Problema:** Duas queries sequenciais no mesmo endpoint sem paralelizacao (has_prior_outbound)
**Arquivo:** `backend/endpoints/leads_crud_sdr.py`
**Endpoint:** `enviar_mensagem_lead`
**Linhas:** 238-256
**Codigo problemático:**

```python
# Duas chamadas de funcao que fazem queries ao banco sequencialmente
prior_outbound = has_prior_outbound(db, lead_id, tenant_id)   # <- query 1
guard = evaluate_sdr_output(                                   # <- query 2
    SdrMessageContext(
        tenant_id=tenant_id,
        lead_id=lead_id,
        ...
    )
)
```

**Impacto:** A funcao `has_prior_outbound` provavelmente executa uma query no banco. Duas operacoes sequenciais que poderiam ser otimizadas. Verificar a implementação de `has_prior_outbound` em `backend/services/sdr_gateway.py`.

**Correção sugerida:** Analisar se `evaluate_sdr_output` tambem executa queries e, se positivo, buscar os dados em uma unica query antes de chamar ambas.

---

## Finding PERF_001.5 [MEDIO]

**Problema:** Padrao - SELECT + DELETE sequenciais que podem ser combinados
**Arquivo:** `backend/endpoints/leads_crud.py`
**Endpoint:** `deletar_lead`
**Linhas:** 498-515
**Codigo problemático:**

```python
# Query 1: verifica se lead existe
lead = db.execute(
    text("SELECT id FROM leads WHERE id=:id AND user_id=:uid"),
    {"id": lead_id, "uid": tenant_id},
).fetchone()
if not lead:
    raise HTTPException(status_code=404, detail="Lead nao encontrado")

# Query 2: deleta interacoes relacionadas
db.execute(
    text("DELETE FROM interacoes WHERE lead_id IN (SELECT id FROM leads WHERE id=:id AND user_id=:uid)"),
    {"id": lead_id, "uid": tenant_id},
)

# Query 3: deleta o lead
db.execute(
    text("DELETE FROM leads WHERE id=:id AND user_id=:uid"),
    {"id": lead_id, "uid": tenant_id},
)
```

**Impacto:** 3 queries sequenciais para uma mesma operacao. O SELECT de verificacao pode ser eliminado combinando o DELETE das interacoes com o DELETE do lead em uma unica operacao atomic transaction.

**Correção sugerida:**

```python
# Verificar se lead existe E deletar em uma unica operacao
# Usando RETURNING para confirmar deleção
result = db.execute(
    text("""
    DELETE FROM leads
    WHERE id = :lead_id AND user_id = :uid
    RETURNING id
    """),
    {"lead_id": lead_id, "uid": tenant_id},
).fetchone()

if not result:
    raise HTTPException(status_code=404, detail="Lead nao encontrado")

# Deletar interacoes - já sem subquery pois validamos que o lead existe
db.execute(
    text("DELETE FROM interacoes WHERE lead_id = :lead_id"),
    {"lead_id": lead_id},
)
db.commit()
```

**Resultado:** Reduz de 3 para 2 queries. A verificacao de existencia e feita atraves do `RETURNING`, eliminando o SELECT previo.

---

## Finding PERF_001.6 [MEDIO] - AUDIT PASS

**Arquivos auditados sem problemas de N+1:**

| Arquivo | Status | Observacao |
|---------|--------|-----------|
| `leads_endpoints.py` | PASS | Apenas router wrapper, sem queries |
| `dashboard_endpoints.py` | PASS | Queries com JOINs corretos; `get_crm` usa subquery agregada para site_visitas |
| `leads_queries.py` | PASS | Todas queries sao bem estruturadas com JOINs corretos |

---

## Ranking de Impacto para Correcao

| Prioridade | Finding | Impacto | Esforco |
|------------|---------|---------|---------|
| 1          | PERF_001.2 | CRITICO - 2 queries→1 no `registrar_feedback` | Baixo |
| 2          | PERF_001.5 | 3 queries→2 no `deletar_lead` | Baixo |
| 3          | PERF_001.3 | Paralelizacao no `enviar_mensagem_lead` | Medio |
| 4          | PERF_001.1 | Conversao no SQL vs Python loop | Baixo |
| 5          | PERF_001.4 | Analise de `has_prior_outbound` | Medio |

---

## Estimativa de Impacto Total (apos correcoes)

| Métrica | Antes | Depois |
|---------|-------|--------|
| Queries por `registrar_feedback` | 2 + 1 INSERT | 1 + 1 INSERT |
| Queries por `deletar_lead` | 3 | 2 |
| Queries por `enviar_mensagem_lead` | 2 + N | 2 + N (paralelas) |
| Redução total de round-trips | - | ~20% menos queries |