# PERF_003_CACHE - Cache Opportunities Audit

**Data**: 2025-01-15
**Auditor**: Performance Engineer (Claude Sonnet 4.6)
**Arquivos analisados**:
- `backend/services/cache_service.py`
- `backend/endpoints/leads_endpoints.py` (wrapper thin - analisa sub-arquivos)
- `backend/endpoints/leads_queries.py`
- `backend/endpoints/leads_crud.py`
- `backend/endpoints/leads_crud_sdr.py`
- `backend/services/pipeline_cache_control.py`
- `backend/services/pipeline_executors.py`
- `backend/agents/sdr_langgraph/agent.py`
- `backend/agents/sdr_langgraph/tools.py`
- `backend/agents/sdr_langgraph/prompts.py`

**Redis disponivel**: SIM (`cache_service.py` ja implementa cliente Redis com fallback em memoria)
**Impacto total estimado**: Reducao de 40-60% no tempo de resposta de endpoints de leads

---

## RESUMO EXECUTIVO

| Severidade | Oportunidade | Estimativa Speedup |
|---|---|---|
| CRITICA | Leads list endpoints sem cache | 200-400ms por req |
| CRITICA | WhatsApp session check sem cache (HTTP redundante) | 300-800ms por req |
| ALTA | Plano de usuario verificado em toda requisicao | 50-150ms por req |
| MEDIA | RAG context lido de arquivo em toda mensagem SDR | 20-50ms por chamada |
| MEDIA | Horario/SDR settings lidos em toda interacao | 10-30ms por chamada |

---

## OPPORTUNIDADE 1 — CRITICA

### Leads List Endpoints sem Cache

**Arquivo**: `backend/endpoints/leads_queries.py`
**Funcao(s)**: `get_leads_capturados`, `get_leads_desqualificados`, `get_leads_incompletos`, `get_fila_qualificados`, `get_descartados`
**Linhas**: 130-312

**Problema**: Todos os 5 endpoints de listagem executam query SQL completa no banco em cada requisicao. Sao chamados repetidamente pelo frontend CRM (polling ou refresh manual). Nao ha cache.

**Cache key sugerida**:
```
fralib:leads:list:{tenant_id}:{status}:{limit}
```

Exemplo: `fralib:leads:list:42:capturados:200`

**TTL sugerido**: `60 segundos` (dados mudam apenas com acao do usuario — invalidador por POST/PATCH/DELETE)

**Invalidacao**: Ao criar/atualizar/deletar um lead, limpar com:
```python
cache.clear_pattern(f"fralib:leads:list:{tenant_id}:*")
```

**Speedup esperado**: 200-400ms por requisicao (query SQL + network DB). Com cache hit: <5ms.

**Implementacao sugerida**:
```python
from backend.services.cache_service import cache

@router.get("/capturados")
async def get_leads_capturados(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    cache_key = f"leads:list:{tenant_id}:capturados:200"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # ... query SQL existente ...
    result = {"leads": leads, "total": len(leads)}

    cache.set(cache_key, result, ttl=60)
    return result
```

**Risco**: Dado potencialmente antigo em ate 60s. Aceitavel para listagens de CRM.

---

## OPPORTUNIDADE 2 — CRITICA

### Conversas e Mensagens sem Cache

**Arquivo**: `backend/endpoints/leads_queries.py`
**Funcao(s)**: `get_conversa` (linha 46), `get_mensagens_novas` (linha 69), `get_lead_chat` (linha 96)
**Linhas**: 46-127

**Problema**: Historico de chat e interacoes consultadas direto no banco a cada abertura do modal CRM. `get_mensagens_novas` faz query agregada custosa com GROUP BY a cada 5-30s de polling.

**Cache key sugerida**:
```
# Conversa individual
fralib:leads:chat:{lead_id}

# Mensagens novas (agregado por tenant)
fralib:leads:mensagens-novas:{tenant_id}
```

**TTL sugerido**:
- `get_conversa` / `get_lead_chat`: `30 segundos` (conversa em tempo real)
- `get_mensagens_novas`: `60 segundos` (janela de 24h, muda pouco)

**Invalidacao**: Ao salvar nova interacao em `_salvar_interacao`:
```python
cache.delete(f"fralib:leads:chat:{lead_id}")
cache.clear_pattern("fralib:leads:mensagens-novas:*")
```

**Speedup esperado**: 100-250ms por chamada. Com cache hit: <5ms.

---

## OPPORTUNIDADE 3 — CRITICA

### WhatsApp Session Check HTTP sem Cache

**Arquivo**: `backend/endpoints/leads_crud_sdr.py`
**Funcao**: `enviar_mensagem_lead` (linha 146)
**Linhas**: 194-212

**Problema**: Em toda chamada de envio de mensagem WhatsApp, faz um GET HTTP sincrono para `meowhats_url/api/sessions` para verificar se a sessao esta connected. Essa informacao muda raramente (minutos), mas e consultada em toda requisicao.

**Cache key sugerida**:
```
fralib:wpp:sessions:{tenant_id}
```

**TTL sugerido**: `120 segundos`

**Speedup esperado**: 300-800ms por requisicao eliminados (round-trip HTTP localhost eliminado). Com cache hit: 0ms overhead.

**Implementacao sugerida**:
```python
WPP_CACHE_KEY = f"fralib:wpp:sessions:{tenant_id}"
cached_status = cache.get(WPP_CACHE_KEY)
if cached_status is not None:
    wpp_ok = cached_status
else:
    async with httpx.AsyncClient(timeout=5) as c:
        r_wpp = await c.get(...)
        # ... extrair wpp_ok ...
    cache.set(WPP_CACHE_KEY, wpp_ok, ttl=120)
```

**Risco**: Baixo — se a sessao cair entre polls, a mensagem falhara no envio mesmo assim.

---

## OPPORTUNIDADE 4 — ALTA

### User Plan Lookup sem Cache em Cada Requisicao

**Arquivo**: `backend/endpoints/leads_crud_sdr.py`
**Funcao**: `enviar_mensagem_lead` (linha 156)
**Linha**: 156-162

**Problema**: Query SQL `SELECT plano, status, trial_expires_at FROM users WHERE id=:id` executada em toda chamada de envio. Plano de usuario raramente muda.

**Cache key sugerida**:
```
fralib:user:plan:{tenant_id}
```

**TTL sugerido**: `300 segundos` (5 minutos)

**Invalidacao**: Quando user atualizar plano (webhook de pagamento, mudanca manual).

**Speedup esperado**: 50-150ms por requisicao eliminados.

---

## OPPORTUNIDADE 5 — ALTA

### Plano Check em Editar Site sem Cache

**Arquivo**: `backend/endpoints/leads_crud.py`
**Funcao**: `editar_site` (linha 181)
**Linhas**: 190-197

**Problema**: Mesma query de plano SQL executada em cada edicao de site.

**Cache key**: Mesma key `fralib:user:plan:{tenant_id}` (compartilhavel com Oportunidade 4).

**TTL sugerido**: `300 segundos`

**Speedup esperado**: 50-150ms por requisicao.

---

## OPPORTUNIDADE 6 — MEDIA

### RAG Context Lido de Arquivo a Cada Mensagem SDR

**Arquivo**: `backend/agents/sdr_langgraph/tools.py`
**Funcao**: `load_rag` (linha 24)
**Chamada em**: `backend/agents/sdr_langgraph/agent.py` linha 259

**Problema**: `load_rag()` abre e le arquivos do disco (`rag_knowledge/franz.md` e `rag_knowledge/sdr_agents/{agent}.md`) em cada interacao inbound ou outbound. Arquivos nao mudam em runtime.

**Cache key sugerida**:
```
fralib:sdr:rag:global
fralib:sdr:rag:agent:{agent_key}
```

**TTL sugerido**: `3600 segundos` (1 hora — invalido apenas em deploy)

**Solucao**: Carregar na inicializacao do modulo ou na primeira chamada e memoizar em memoria. Ja existe `cache_service` com fallback em memoria — usar diretamente.

**Speedup esperado**: 20-50ms por chamada LLM (leitura de disco + concat) eliminados.

---

## OPPORTUNIDADE 7 — MEDIA

### Horario de Atendimento Carregado a Cada Verificacao

**Arquivo**: `backend/agents/sdr_langgraph/tools.py`
**Funcao**: `is_within_schedule` (linha 207)
**Chamada em**: `backend/agents/sdr_langgraph/agent.py` linha 284

**Problema**: `_get_horario_config(user_id)` consultada em toda interacao. Configuracao raramente muda.

**Cache key sugerida**:
```
fralib:sdr:horario:{user_id}
```

**TTL sugerido**: `300 segundos`

**Speedup esperado**: 10-30ms por chamada.

---

## OPPORTUNIDADE 8 — MEDIA

### Agent Name / SDR Settings Carregados Repetidamente

**Arquivo**: `backend/agents/sdr_langgraph/tools.py`
**Funcao**: `get_agent_name` (linha 259)
**Chamada**: Em `get_greeting` output e em logs de `agent.py`

**Problema**: `_get_sdr_settings_for_user(user_id)` chamada em toda mensagem.

**Cache key sugerida**:
```
fralib:sdr:settings:{user_id}
```

**TTL sugerido**: `600 segundos`

**Speedup esperado**: 5-15ms por chamada.

---

## OPPORTUNIDADE 9 — BAIXA

### Intent Detection Cacheavel

**Arquivo**: `backend/agents/sdr_langgraph/tools.py`
**Funcao**: `detect_intent_with_llm` (linha 75)

**Problema**: Para mesma mensagem de lead (ex: "oi" repetido), faz chamada Haiku redundante.

**Cache key sugerida**:
```
fralib:sdr:intent:{_simple_hash(mensagem)}
```

**TTL sugerido**: `86400 segundos` (1 dia — intents sao universais)

**Speedup esperado**: 200-400ms por mensagem duplicada (Haiku call eliminada).

---

## PATTERN: Cache ja existente mas nao utilizado

O arquivo `cache_service.py` ja implementa toda a infraestrutura necessaria:

- Cliente Redis com lazy init
- Fallback em memoria
- Metodos `get/set/delete/clear_pattern`
- Decorator `@cached`
- Decorator `@cached_llm_response` para deduplicacao LLM
- Funcao `invalidate_llm_cache()`

**Proximo passo recomendado**: Aplicar o decorator `@cached` nos endpoints de leads usando o padrao ja existente. Nenhuma mudanca em `cache_service.py` necessaria.

---

## PRIORIDADE DE IMPLEMENTACAO

| # | Oportunidade | Impacto | Esforco | Prioridade |
|---|---|---|---|---|
| 3 | WhatsApp session HTTP cache | CRITICA | Baixo | 1 |
| 1 | Leads list endpoints cache | CRITICA | Baixo | 1 |
| 2 | Chat/mensagens cache | CRITICA | Baixo | 2 |
| 4 | User plan cache (SDR) | ALTA | Baixo | 2 |
| 5 | User plan cache (CRUD) | ALTA | Baixo | 2 |
| 6 | RAG context memoize | MEDIA | Medio | 3 |
| 7 | Horario config cache | MEDIA | Baixo | 3 |
| 8 | SDR settings cache | MEDIA | Baixo | 4 |
| 9 | Intent detection cache | BAIXA | Baixo | 5 |

---

## IMPACTO AGREGADO ESTIMADO

| Cenario | Tempo atual | Tempo com cache (hit) | Reducao |
|---|---|---|---|
| GET /capturados | ~300ms | <5ms | ~98% |
| GET /fila-qualificados | ~250ms | <5ms | ~98% |
| POST /enviar-mensagem | ~1200ms | <400ms | ~67% |
| SDR inbound message | ~100ms | ~60ms | ~40% |
