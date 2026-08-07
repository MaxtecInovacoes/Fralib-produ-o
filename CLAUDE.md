# FraLib — Índice de Entrada para IAs

Tudo que não está aqui ou em `backend/agents/<nome>/agent.py` é **LEGADO**.

## TL;DR

- **Pipeline**: Hunter → Caio → Arquiteto → Builder → Quality Gate → Deploy → Franz
- **Orquestrador**: `backend/agents/manager/agent.py` (FSM pura, não LangGraph)
- **Entry points**: `server.py` (FastAPI :8000) e `worker.py` (daemon fila)
- **Deploy**: `git push origin master` → `scripts/post-receive`
- **Smoke**: `python pipeline.py smoke --dry-run`
- **Tests**: `pytest tests/agents/`

---

## Estrutura (resumido)

```
backend/agents/ (10 agentes canônicos)
backend/core/ (auth, db, job_queue, jwt)
backend/endpoints/ (64 routes HTTP)
backend/services/ (llm_router, service_manager)
backend/whatsapp/ (listener whatsmeow)
server.py, worker.py, alembic/, tests/agents/
```

Ver arquivo completo: `.claude/projects/.../memory/AUDITORIA_COMPLETA_FRALIB_2026-07-10.md` (removido de contexto).

## Padrão de agente (template)

Cada agente em `backend/agents/<nome>/` tem:

```
agent.py          ← lógica principal
contracts.py      ← (opcional) Pydantic dataclasses
prompts.py        ← (opcional) prompts do LLM
tools.py          ← (opcional) helpers
README.md         ← (opcional) docs do agente
```

## Regras de ouro

1. **NÃO criar arquivos novos** sem antes verificar se há agente/pasta apropriado
2. **NÃO mexer em `agents/_shared/`** — só existe `agents/_text_utils.py` (compat)
3. **NÃO usar LangGraph** — orquestrador é FSM pura
4. **NÃO usar scrapers pagos** — só open-source
5. **NÃO usar renderers alternativos** — Builder (OpenUI) é o único caminho
6. **NÃO duplicar agentes** — se precisar estender, melhore `agent.py` existente

## Onde está cada coisa

| Preciso de... | Olhe em... |
|---|---|
| Caio (qualificar lead) | `backend/agents/caio/agent.py` |
| Gerar site | `backend/agents/builder/agent.py` |
| Validar HTML | `backend/agents/builder/quality_gate.py` |
| Pesquisar mercado | `backend/agents/arquiteto/agent.py` (via lead_data) |
| DesignerPRD | `backend/agents/arquiteto/agent.py` |
| SDR WhatsApp | `backend/agents/franz/agent.py` |
| Orquestrar tudo | `backend/agents/manager/agent.py` |
| Mineração de leads | `backend/agents/hunter/agent.py` |
| Schema DB | `alembic/versions/` |
| Auth, DB, jobs | `backend/core/` |
| WhatsApp listener | `backend/whatsapp/` |
| API endpoints | `backend/endpoints/` |
| Testes | `tests/agents/` |
