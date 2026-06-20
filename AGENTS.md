# FraLib — AGENTS.md
## Regras Absolutas
1. Nunca usar SCP, rsync ou editar arquivos direto na VPS.
2. Fluxo oficial: editar local -> git add -> git commit -> git push.
3. Nunca deployar codigo nao commitado.
4. Se mudou codigo, config, pipeline ou docs, atualizar este arquivo.
5. Este arquivo deve ficar com no maximo 80 linhas.

## Estado Atual (2026-06-20)
- Branch: master
- Monolitos quebrados (refatoracao em progresso):
  - vite_react_renderer.py (3809 linhas, modulos extraidos)
  - pipeline_orchestrator_service.py (3143 linhas)
  - leads_crud.py (633 linhas)
- Modulos extraidos de vite_react_renderer:
  - vite_config.py, vite_prompts.py, vite_facts.py, vite_file_extractor.py
  - vite_validator.py, vite_build_executor.py, vite_config_helpers.py
- Performance: cache node_modules, Caio+Jina em asyncio.gather, Design Director cache 24h
- Bugs corrigidos: IDOR, OAuth CSRF, CORS, Leads Cache isolation, Revoke Token fail-open

## Pipeline Atual (11 FASES - VERSAO CANONICA)
1. Hunter + Keyword Research (keyword_research.py)
2. Caio (caio.py)
3. Jina + inteligencia de mercado (jina_research.py)
4. Unsplash + Pexels (unsplash_fetcher.py, pexels_video.py)
5. Agente de Nicho (agente_nicho.py)
6. Agente de Variacao (agente_variacao.py)
7. Arquiteto Mestre DesignerPRD (arquiteto_mestre.py)
8. Skill Renderer (vite_react_renderer.py)
9. Quality gate (html_quality_gate.py)
10. Deploy + health check (builder_worker.py)
11. Bryan SDR (sdr_langgraph/)

## Arquitetura
- Backend: FastAPI em `server.py`.
- Orquestrador: `backend/endpoints/pipeline_orchestrator_service.py` (1700+ linhas).
- Fila/locks: PostgreSQL, `pipeline_queue` e `pipeline_state`.
- Geracao HTML: `backend/services/vite_react_renderer.py`.
- SDR: `backend/agents/sdr_langgraph/` (LangGraph multi-agent).
- WhatsApp: `meowhats` em `:3001`.

## Infra
- VPS: root@187.77.37.72 | PM2: fralib 8000, fralib-worker, fralib-franz-worker
- LLM: kpalabz (claude-sonnet-4-6, claude-haiku-4-5)

## Sincronizacao
- VPS sincronizada com GitHub via hook (a cada push)
- Verificar: ssh root@187.77.37.72 "cd /root/fralib && git log -1 --format='%H'"
