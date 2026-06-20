# FraLib — AGENTS.md
## Regras Absolutas
1. Nunca usar SCP, rsync ou editar arquivos direto na VPS.
2. Fluxo oficial: editar local -> git add -> git commit -> git push.
3. Nunca deployar codigo nao commitado.
4. Se mudou codigo, config, pipeline ou docs, atualizar este arquivo.
5. Este arquivo deve ficar com no maximo 80 linhas.
## Estado Atual
- Branch: codex/pipeline-stabilization-20260613 | Worker: heartbeat thread, timeout 1800s, fase worker_timeout.
- Monolitos quebrados (30+ modulos < 800 linhas):
  - lead_supply_engine.py (8 modulos): filters, events, storage, providers, inventory, etc.
  - vite_react_renderer.py (7 modulos): config, prompts, facts, file_extractor, validator, build_executor, models
  - pipeline_orchestrator_service.py (~30 modulos suporte): executors, phases, state, prd_builder, media, validators, etc.
  - FASE 08 EXTRAÍDA: pipeline_fases/fase_08_arquiteto.py (182 linhas)
- Codigo morto deletado: bloco_prd_compacto.py, brain.py, creative_build_brief.py, html_sanitizer.py (2665 linhas), design_guidelines.py, validation_enforcer.py, openui_renderer.py (2253 linhas), test_builder_worker/phase6/f1_f5_contracts.py.
- Performance: cache node_modules /var/cache/fralib/node_modules_vite.tar.gz, Caio+Jina em asyncio.gather, Design Director cache /tmp/fralib_design_cache (TTL 24h), vite-plugin-prerender-spa.
- Bugs SDR corrigidos: sanitize_reply nao chama 2a LLM, watchdog libera em lead_responded=True, history sincronizada com state LangGraph.
- Pipeline: Hunter (lead_inventory) -> Caio (qualifica) -> Design Director (FASE 2.5, usa design_context.get_design_context()) -> Jina (inteligencia mercado) -> Prompt Agent -> Builder (Vite/React/Tailwind v4) -> Deploy -> Franz/SDR (LangGraph).
- Gate atual: health probe usa endpoint /models canonico, health interno permitido no tenant_scope_audit, pipeline tail preserva Franz nao-bloqueante e credito trial pos-envio.
- Runtime critico: pipeline/renderer sem nomes indefinidos; reprocessamento usa contexto LLM canonico e tracking opcional inicializado.
- Credenciais LLM fallback sao lidas sob demanda; selecao aborta apos 20 chaves invalidas para nao prender worker.
- Contexto LLM consulta tenant dinamicamente; rate limit, budget e alertas nao usam user_id congelado no import.
- Parser do proxy concatena todos os blocos textuais para evitar respostas LLM truncadas.
- Extrator Vite aceita JSON estrito em fence Markdown sem regex truncar chaves do codigo.
- Validator Vite usa import absoluto do pacote e nao depende de sys.path poluido por ordem de testes.
- Gate F821 e bloqueante; wrappers PRD, Hunter e listener WhatsApp estao sem nomes indefinidos.
- LGPD publico: HTML reparado e React gerado usam a chave canonica fralib_lgpd_consent_v1 com fallback seguro.
- Agentes novos: design_director.py, benchmarker.py, trend_watcher.py.
- Docs criados: docs/CONSTITUTION.md, SILENT_FAILURES_AUDIT.md, specs/SPEC_monolitos_quebra.md, SPEC_premium_upgrade.md, SPEC_velocidade_seo.md, AGENT_REGISTRY.md.
- Scripts: verify_all.sh (juiz verde), check_agents_alive.sh, fix_imports.sh, audit_vps.sh, benchmark_pipeline.py.
## Arquivos Chave
- backend/endpoints/pipeline_*_endpoints.py: service executa, helpers em services/pipeline_* e endpoints/pipeline_*_helpers.py.
- backend/agents/: site_prompt_agent.py, caio.py, design_director.py, benchmarker.py, trend_watcher.py, visual_archetypes.py.
- backend/services/: builder_worker.py, vite_react_renderer.py, lead_supply_*.py (8 modulos).
## Spec + Loop
- Spec ANTES de codar: docs/specs/SPEC_<nome>.md para mudancas grandes.
- Verde local = ./scripts/verify_all.sh retorna 0 para commit; deploy exige FRALIB_VERIFY_STRICT=1 e PostgreSQL de teste.
- Loop: implementa -> testa -> le erro -> conserta -> repete. Limite 10 iteracoes.
## Infra
- VPS: root@187.77.37.72 | PM2: fralib 8000, fralib-worker, fralib-franz-worker, meowhats 3001.
- LLM: kpalabz (claude-sonnet-4-6, claude-haiku-4-5), sem LiteLLM.
- WhatsApp keepalive: 30s, reconexao agressiva.
- Frontend admin: Motor FraLib tem CSS responsivo, microcopy, cronometro/ETA no log e dashboard.html para deploy completo.
- Lead supply: sync global ignora Hunter sem nicho/cidade e roda a cada LEAD_SUPPLY_SYNC_SECS.
- Auth: endpoints com @limiter.limit devem receber Request para SlowAPI.
## Legado
- Bryan/agent_loop flags fora do pipeline ativo sao legado.
- LiteLLM removido, kpalabz e provider unico.
