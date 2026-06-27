# TAREFA 1: SDR com paleta_cores ✅

**Data:** 2026-06-26  
**Status:** ✅ COMPLETO (sem modificação de mensagens)  
**Impacto:** Paleta de cores disponível no estado do SDR para uso futuro

---

## RESUMO DAS ALTERAÇÕES

> **Nota:** A paleta de cores está disponível no estado do SDR, mas as mensagens são geradas conforme o RAG/prompts do SDR (sem emojis ou formatação extra).

### 1. Migration: leads table
**Arquivo:** `alembic/versions/add_paleta_cores_to_leads.py` + `docs/migrations/add_paleta_cores_leads.sql`

```sql
ALTER TABLE leads ADD COLUMN paleta_cores JSON;
```

### 2. LeadMemory (SDR State)
**Arquivo:** `backend/agents/sdr_langgraph/state.py`

```python
# Adicionado campo:
paleta_cores: Dict[str, str] = Field(default_factory=dict)

# Também adicionado em SDRState:
paleta_cores: Dict[str, str]  # Sprint 14.x: cores do site para SDR
```

### 3. BryanInput (SDR Input Model)
**Arquivo:** `backend/agents/sdr_langgraph/compat.py`

```python
# Sprint 14.x: paleta_cores disponível no estado do SDR
paleta_cores: Optional[Dict[str, str]] = {}
```

### 4. Memory Propagation
**Arquivo:** `backend/agents/sdr_langgraph/compat.py`

- `_lead_payload_from_memory()`: agora inclui `paleta_cores`
- `iniciar_contato()`: propaga `paleta_cores` para memória e estado
- `initial_state`: agora inclui `paleta_cores`

### 5. Agent Context Loading
**Arquivo:** `backend/agents/sdr_langgraph/agent.py`

```python
# Adicionado paleta_cores aos campos que sobrescrevem do state:
for field in ("lead_id", "nome", "cidade", "segmento", "site_url", "paleta_cores"):
    value = state.get(field)
    if value:
        setattr(memory, field, value)
```

### 6. FraLibState (Pipeline)
**Arquivo:** `backend/endpoints/pipeline_orchestrator_service.py`

```python
# Sprint 14.x: cores para SDR
paleta_cores: dict = field(default_factory=dict)
```

### 7. Pipeline → Leads Update
**Arquivos:**
- `backend/endpoints/pipeline_orchestrator_service.py`
- `backend/endpoints/pipeline_execution_core.py`

```python
# UPDATE agora inclui paleta_cores:
UPDATE leads SET ..., paleta_cores=:cores WHERE id=:id
```

### 8. SDR Endpoints
**Arquivos:**
- `backend/endpoints/leads_crud_sdr.py`
- `backend/endpoints/cron_endpoints.py`

```python
# SELECT agora inclui paleta_cores
# FranzInput agora inclui paleta_cores
```

---

## FLUXO DE DADOS

```
Pipeline: nicho_briefing.paleta_cores
    ↓
FraLibState.paleta_cores
    ↓
UPDATE leads SET paleta_cores=:cores
    ↓
SELECT paleta_cores FROM leads
    ↓
FranzInput(..., paleta_cores=...)
    ↓
LeadMemory(..., paleta_cores=...)
    ↓
Disponível para: site_offer, future features
```

---

## COMO TESTAR

1. Executar migration SQL:
```bash
psql -h localhost -U fralib -d fralib_db -f docs/migrations/add_paleta_cores_leads.sql
```

2. Verificar coluna existe:
```sql
SELECT paleta_cores FROM leads LIMIT 5;
```

3. Trigger SDR para um lead:
```bash
curl -X POST http://localhost:8000/api/leads/{lead_id}/send-sdr
```

4. Verificar que paleta_cores está no estado do lead:
```python
memory.paleta_cores  # ex: {"primary": "#800080", "secondary": "#FFFFFF"}
```

---

## USO FUTURO

A paleta de cores está disponível em `memory.paleta_cores`. Possíveis usos futuros:
- Personalização de ofertas de site (site_offer)
- Análise de padrões de cores por nicho
- Relatórios de branding

---

## NÃO IMPLEMENTADO (intencional)

- Emojis/colorização de mensagens SDR ❌
- Branding hints nas mensagens ❌
- Modificação do conteúdo das mensagens ❌

> O SDR segue rigorosamente o RAG/prompts definidos, sem invenções.
