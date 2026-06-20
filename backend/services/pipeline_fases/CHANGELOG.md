# Changelog — Pipeline Fases

Todas as mudanças neste diretório são documentadas aqui.

## [2026-06-19] — Extraída Fase 8: Arquiteto Mestre

### Adicionado
- `fase_08_arquiteto.py` (182 linhas)
- `__init__.py` com exports
- `README.md` com documentação da arquitetura

### Detalhes da Extração

**O que foi extraído:**
- Função `executar_fase_8()` — interface padrão
- Helper `_salvar_checkpoint_prd()` — persiste PRD em cache
- Helper `_aplicar_white_label()` — aplica white-label para PRO
- Helper `_aplicar_contracts_e_design()` — aplica design contracts
- Helper `_salvar_trace_prd()` — salva trace para auditoria

**O que foi preservado:**
- Lógica original de geração de PRD
- Sistema de cache/checkpoint
- Ledger de fases
- Observabilidade (spans)

**Parâmetros da interface:**
```python
executar_fase_8(
    state,              # FraLibState
    config,             # dict
    tenant_id,          # int
    engine,             # SQLAlchemy engine
    ledger,             # Ledger
    get_dados_agente,   # callable
    salvar_checkpoint,   # callable
    tentar,             # retry helper
    log_func,           # logging
    progress_func,      # SSE progress
    iniciar_span,       # opcional
    finalizar_span,     # opcional
    trace=False,        # bool
    prompt_agent_flow=False,  # bool
    builder_fast_path=False,  # bool
    arquiteto_agent=False,    # bool
)
```

### Testes
- ✅ `from backend.services.pipeline_fases import executar_fase_8` — OK
- ✅ `bash scripts/verify_all.sh` — 18/18 checks passam
