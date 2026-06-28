# Sprint 14.x: Expansão do Formulário de Briefing

**Data:** 2026-06-26  
**Status:** ✅ COMPLETO  
**Impacto:** Usuários podem especificar referências visuais e preferência de fonte para o site

---

## RESUMO DAS ALTERAÇÕES

### 1. Frontend: admin.html

#### Campo "REFERÊNCIAS VISUAIS"
```html
<input class="config-input" type="text" id="lm-refs-visuais" 
  placeholder="Ex: Quero um site como Nubank, clean e moderno">
```

#### Campo "PREFERÊNCIA DE FONTE"
```html
<select class="config-input" id="lm-font-preferencia">
  <option value="">Padrão (Sans-serif)</option>
  <option value="sans-serif">Sans-serif</option>
  <option value="serif">Serif</option>
  <option value="display">Display</option>
  <option value="monospace">Monospace</option>
</select>
```

#### Função salvarLeadManual()
- Adicionado `refs_visuais` ao JSON body
- Adicionado `font_preferencia` ao JSON body
- Campos limpos ao fechar modal

---

### 2. Backend: leads_crud_models.py

```python
class LeadManualRequest(BaseModel):
    # ...existing fields...
    refs_visuais: Optional[str] = None  # Sprint 14.x: referências visuais
    font_preferencia: Optional[str] = None  # Sprint 14.x: preferência de fonte

class CamposLeadRequest(BaseModel):
    # ...existing fields...
    refs_visuais: Optional[str] = None  # Sprint 14.x: referências visuais
    font_preferencia: Optional[str] = None  # Sprint 14.x: preferência de fonte
```

---

### 3. Backend: leads_crud.py

#### INSERT statement atualizado
```python
INSERT INTO leads (..., refs_visuais, font_preferencia)
VALUES (..., :refs_visuais, :font_preferencia)
```

#### Parameters
```python
"refs_visuais": req.refs_visuais or "",
"font_preferencia": req.font_preferencia or "",
```

#### Update handler
```python
if req.refs_visuais is not None:
    campos["refs_visuais"] = req.refs_visuais
if req.font_preferencia is not None:
    campos["font_preferencia"] = req.font_preferencia
```

---

### 4. Database Migration

**Arquivo:** `docs/migrations/add_font_preferencia_leads.sql`

```sql
ALTER TABLE leads ADD COLUMN IF NOT EXISTS font_preferencia VARCHAR(50);
```

---

### 5. Pipeline: NichoBriefing (handoff_types.py)

```python
class NichoBriefing(HandoffBase):
    # ...existing fields...
    paleta_cores: Dict[str, str] = Field(default_factory=dict)  # Sprint 14.x
    refs_visuais: str = ""  # Sprint 14.x: referências visuais
    font_preferencia: str = ""  # Sprint 14.x: preferência de fonte
```

#### Markdown output atualizado
```python
def to_markdown(self) -> str:
    # ...existing sections...
    if self.refs_visuais:
        lines.append(f"**Referências visuais:** {self.refs_visuais}")
    if self.font_preferencia:
        lines.append(f"**Preferência de fonte:** {self.font_preferencia}")
```

---

### 6. Pipeline: agente_nicho.py

#### Função gerar_briefing()
```python
def gerar_briefing(
    dados_lead: dict,
    segmento: str,
    cidade: str,
    jina_insights: str = "",
    task_id: str = "",
    refs_visuais: str = "",
    font_preferencia: str = "",
) -> NichoBriefing:
```

#### LLM Prompt atualizado
```python
user_prompt = f"""...
== REFERÊNCIAS VISUAIS DO CLIENTE ==
{refs_visuais if refs_visuais else "nenhuma referência visual informada"}

== PREFERÊNCIA DE FONTE DO CLIENTE ==
{font_preferencia if font_preferencia else "nenhuma preferência de fonte informada"}
...
"""
```

#### NichoBriefing output
```python
return NichoBriefing(
    # ...existing fields...
    paleta_cores=_paleta_cores,
    refs_visuais=refs_visuais,
    font_preferencia=font_preferencia,
)
```

---

### 7. Pipeline: FraLibState (pipeline_orchestrator_service.py)

```python
@dataclass
class FraLibState:
    # ...existing fields...
    paleta_cores: dict = field(default_factory=dict)  # Sprint 14.x
    refs_visuais: str = ""  # Sprint 14.x
    font_preferencia: str = ""  # Sprint 14.x
```

#### Leitura de dados do lead (reprocessamento)
```python
state.lead_raw_data["briefing"] = _ld.get("observacoes", "")  # Sprint 14.x
state.refs_visuais = _ld.get("refs_visuais", "")
state.font_preferencia = _ld.get("font_preferencia", "")
```

---

## FLUXO DE DADOS

```
┌─────────────────────────────────────────────────────────────┐
│ FORMULÁRIO (admin.html)                                     │
│ - briefing (textarea)                                       │
│ - refs_visuais (text)                                       │
│ - font_preferencia (select)                                  │
└────────────────────┬────────────────────────────────────────┘
                     │ POST /api/leads/manual
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ leads_crud.py (INSERT)                                      │
│ - observacoes = briefing                                    │
│ - refs_visuais                                              │
│ - font_preferencia                                          │
└────────────────────┬────────────────────────────────────────┘
                     │ trigger pipeline_lead
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ pipeline_orchestrator_service.py (_lead_id_existente)        │
│ - SELECT * FROM leads                                       │
│ - state.lead_raw_data["briefing"] = observacoes            │
│ - state.refs_visuais                                        │
│ - state.font_preferencia                                     │
└────────────────────┬────────────────────────────────────────┘
                     │ gerar_briefing(refs_visuais, font_preferencia)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ agente_nicho.py (_gerar_briefing_impl)                      │
│ - Extrai paleta_cores do briefing_text                      │
│ - Passa refs_visuais e font_preferencia para LLM           │
│ - Retorna NichoBriefing com todos os campos                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ LLM Prompt inclui:                                         │
│ - "REFERÊNCIAS VISUAIS DO CLIENTE: ..."                    │
│ - "PREFERÊNCIA DE FONTE DO CLIENTE: ..."                  │
│                                                             │
│ LLM pode usar essas informações para:                       │
│ - Inspirar design do site                                   │
│ - Escolher tipografia adequada                              │
│ - Definir estilo visual                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## COMO TESTAR

### 1. Executar migrations
```bash
# Migration refs_visuais (se ainda não executou)
psql -h localhost -U fralib -d fralib_db -f docs/migrations/add_refs_visuais_leads.sql

# Migration font_preferencia
psql -h localhost -U fralib -d fralib_db -f docs/migrations/add_font_preferencia_leads.sql
```

### 2. Verificar colunas
```sql
SELECT id, nome, observacoes, refs_visuais, font_preferencia FROM leads LIMIT 10;
```

### 3. Criar lead manual com briefing
```bash
curl -X POST http://localhost:8000/api/leads/manual \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Academia Fit",
    "nicho": "academia",
    "cidade": "São Paulo",
    "telefone": "11999999999",
    "briefing": "Site moderno para academia feminina, cores roxo e branco",
    "refs_visuais": "Quero um site como Nubank, clean e moderno",
    "font_preferencia": "sans-serif"
  }'
```

### 4. Verificar pipeline output
```python
# Verificar que o NichoBriefing inclui as referências
briefing = state.nicho_briefing
print(f"refs_visuais: {briefing.refs_visuais}")
print(f"font_preferencia: {briefing.font_preferencia}")
print(f"paleta_cores: {briefing.paleta_cores}")
```

---

## ARQUIVOS MODIFICADOS

| Arquivo | Mudanças |
|---------|----------|
| `frontend/admin.html` | Campos refs_visuais, font_preferencia + JS |
| `backend/endpoints/leads_crud_models.py` | LeadManualRequest, CamposLeadRequest |
| `backend/endpoints/leads_crud.py` | INSERT, UPDATE para novos campos |
| `backend/agents/handoff_types.py` | NichoBriefing com novos campos |
| `backend/agents/agente_nicho.py` | gerar_briefing com novos parâmetros |
| `backend/endpoints/pipeline_orchestrator_service.py` | FraLibState + leitura de dados |
| `docs/migrations/add_font_preferencia_leads.sql` | Migration para font_preferencia |

---

## NÃO IMPLEMENTADO (intencional)

- Modificação de mensagens SDR ❌ (SDR segue RAG/prompts)
- Emojis/colorização de mensagens ❌
- Fontes específicas (ex: "Roboto", "Inter") ❌ (usa categorias genéricas)
