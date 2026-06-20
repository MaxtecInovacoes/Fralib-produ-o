# Pipeline Fases — Arquitetura Modular

> **Status:** 🟡 EM CONSTRUÇÃO — Monolito sendo quebrado incrementalmente
> **Última Atualização:** 2026-06-19
> **Padrão:** ECC (Explicit Code Contracts)

## Visão Geral

Este diretório contém os módulos de **Fases do Pipeline** extraídos do monolito `pipeline_orchestrator_service.py` (3.140 linhas).

### Problema Original

```
pipeline_orchestrator_service.py
├── 3.140 linhas totais
├── 1 função principal (executar_pipeline_completo) com ~2.800 linhas
├── 11 fases misturadas no mesmo arquivo
└── Múltiplos domínios violando SRP
```

### Solução

Cada fase do pipeline agora é um **módulo independente** com:
- Responsabilidade única (SRP)
- Interface padrão
- Testabilidade
- Documentação

---

## Arquitetura

```
backend/services/pipeline_fases/
├── __init__.py           # Exports públicos
├── fase_08_arquiteto.py # ✅ EXTRAÍDA — PRD Builder (182 linhas)
├── fase_09_builder.py    # 🔜 Próxima
└── ...
```

### Interface Padrão de Fase

```python
def executar_fase_XX(
    state: FraLibState,      # Estado do pipeline
    config: dict,            # Configuração
    tenant_id: int,          # ID do tenant
    engine: Any,             # Engine SQLAlchemy
    ledger: Ledger,          # Registro de fases
    get_dados_agente: Callable,  # Cache de agentes
    salvar_checkpoint: Callable,  # Persistência
    tentar: Callable,        # Retry helper
    log_func: Callable,     # Logging
    progress_func: Callable, # SSE progress
    # ...params específicos
) -> dict:
    """Executa fase XX do pipeline."""
    # lógica...
    return {"state": state}
```

---

## Estado Central

O estado é gerenciado por `FraLibState` definido em:

```
backend/services/pipeline_phases.py
```

### Campos do FraLibState

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `segmento` | str | Segmento do lead |
| `cidade` | str | Cidade do lead |
| `pipeline_id` | str | ID único do pipeline |
| `tenant_id` | int | ID do tenant |
| `lead_raw_data` | dict | Dados brutos do Hunter |
| `qualificacao_caio` | CaioOutput | Qualificação do Caio |
| `jina_insights` | str | Insights de mercado |
| `briefing_theo` | str | Briefing de nicho |
| `prd_arquiteto` | DesignerPRD | PRD gerado |
| `html_final` | str | HTML final do site |
| `site_url` | str | URL do site publicado |

---

## Fases do Pipeline

### Fase 8: Arquiteto Mestre (PRD Builder) ✅

**Status:** ✅ EXTRAÍDA
**Arquivo:** `backend/services/pipeline_fases/fase_08_arquiteto.py`
**Linhas:** 182
**Commit:** `refactor: extrair fase 08 para modulo independente`

**Responsabilidades:**
- Gerar PRD (Product Requirements Document)
- Selecionar seed de animações aleatórias
- Aplicar contracts de design
- Aplicar white-label para tenants PRO
- Salvar checkpoint do PRD
- Salvar trace para auditoria

**Parâmetros específicos:**
- `prompt_agent_flow`: Usa fluxo de prompt agent
- `builder_fast_path`: Usa PRD factual compacto
- `arquiteto_agent`: Usa _gerar_prd_agent

---

## Como Integrar no Pipeline Principal

### Antes (Monolito)

```python
# pipeline_orchestrator_service.py — linhas 1675-1851
async def executar_pipeline_completo(...):
    # ... 2800 linhas inline

    # Fase 8 inline
    _arq_cached = get_dados_agente(state.pipeline_id, "arquiteto_mestre")
    state.prd_arquiteto = gerar_arquiteto_mestre_prd(...)
    # ... 176 linhas de lógica
```

### Depois (Modular)

```python
# pipeline_orchestrator_service.py
from backend.services.pipeline_fases import executar_fase_8

async def executar_pipeline_completo(...):
    # Setup e ledger

    # Fase 8 via módulo
    resultado = executar_fase_8(
        state=state,
        config=config,
        tenant_id=tenant_id,
        engine=engine,
        ledger=ledger,
        get_dados_agente=get_dados_agente,
        salvar_checkpoint=salvar_checkpoint,
        tentar=tentar,
        log_func=_log,
        progress_func=_progress,
        iniciar_span=_iniciar_span_com_db if trace else None,
        finalizar_span=_finalizar_span_com_db if trace else None,
        trace=trace,
    )
    state = resultado["state"]
```

---

## Métricas

| Métrica | Antes | Depois |
|---------|-------|--------|
| Linhas em `pipeline_orchestrator_service.py` | 3.140 | 3.140 (ainda não integrado) |
| Linhas em `fase_08_arquiteto.py` | 0 | 182 |
| Módulos de fase | 0 | 1 |
| Verificação | ❌ | ✅ `verify_all.sh` passa |

---

## Próximos Passos

- [ ] **Fase 9 (Builder Renderer)** — Extrair lógica de geração Vite/React
- [ ] **Fase 10 (Deploy)** — Extrair lógica de publicação
- [ ] **Integrar fases extraídas** — Substituir código inline no orchestrator
- [ ] **Testes unitários** — Adicionar testes para cada fase

---

## Verificação

```bash
# Testar imports
python3 -c "from backend.services.pipeline_fases import executar_fase_8; print('OK')"

# Verificação completa
bash scripts/verify_all.sh
```

---

## Contato

Para dúvidas sobre esta arquitetura, consulte:
- `backend/services/pipeline_phases.py` — Estado e constantes
- `backend/pipeline_ledger.py` — Sistema de ledger
- `backend/services/pipeline_executors.py` — Retry e executores
