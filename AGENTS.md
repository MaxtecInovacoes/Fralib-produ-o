# FraLib — Fonte Única de Verdade

> Este arquivo é a **única fonte canônica** da FraLib. Qualquer divergência entre
> `AGENTS.md`, `CLAUDE.md`, `README.md`, `ARCHITECTURE_NOTES.md` e o código
> deve ser resolvida em favor do que está aqui. Quando este arquivo mudar,
> atualizar os demais no mesmo commit.
>
> Última consolidação: 2026-06-22 — Operação: "Uma Verdade Só"

---

## 1. Contrato de Deploy (inviolável)

- **Nunca** editar direto na VPS, usar SCP, rsync ou copiar arquivos manualmente.
- Fluxo único: editar local em `C:\fralib` → `git add` → `git commit` → `git push origin master`.
- Push em `master` dispara `scripts/post-receive` no bare repo VPS, que valida,
  publica e reinicia serviços.
- Código em produção precisa ser reproduzível a partir do Git.
- Fonte canônica local: `C:\fralib`; fonte canônica VPS: `/root/fralib`.
- Pastas antigas fora desses caminhos, caches de IDE e backups são **legado** — ignorar.

## 2. Sistema Anti-Perda (regras invioláveis)

1. **Nunca** encerrar sessão com working tree sujo. Antes: `git add -A && git commit`.
2. **Sempre** rodar `./scripts/check_uncommitted.sh` antes de deploy (deve retornar 0).
3. **Sempre** atualizar este arquivo quando o estado mudar.
4. **Nunca** criar branch sem registrar aqui.
5. Antes de qualquer deploy: `git push origin master` (somente `master` republica).

---

## 3. Arquitetura Geral

| Camada | Tecnologia | Arquivo/Local |
|---|---|---|
| Backend HTTP | FastAPI + Uvicorn | `server.py` (porta 8000) |
| Orquestrador | FastAPI router + serviço | `backend/endpoints/pipeline_orchestrator_service.py` |
| Worker daemon | Python + asyncio | `worker.py` (raiz) |
| Gerador de site | **OpenUI** (canônico) | `backend/services/openui_renderer.py` + `openui_contracts.py` |
| Gerador de site | Vite/React Studio Premium (opt-in) | `backend/services/vite_react_renderer.py` |
| Fila/Locks | PostgreSQL | `backend/core/job_queue.py` + tabela `public.jobs` |
| Builder Worker | Python daemon | `backend/services/builder_worker.py` |
| Quality Gate | Determinístico (não pula) | `backend/agents/html_quality_gate.py` |
| LLM | Anthropic direto (multi-provider opcional) | `backend/agents/llm_direct.py` |
| WhatsApp | whatsmeow externo | `:3001` (systemd próprio, fora do ServiceManager) |
| ServiceManager | Auto-detect systemd/pm2 | `backend/services/service_manager.py` |
| Frontend | HTML estático canônico | `frontend/` (admin/dashboard/landing/login/...) |
| Deploy | Git post-receive + PM2 | `scripts/post-receive` |

---

## 4. Pipeline de Produção — 11 Fases Canônicas

> A enumeração abaixo é a **única canônica**. Está em `backend/services/pipeline_phases.py`.
> Qualquer doc, código ou comentário que use outra numeração está **errado**.

| # | Label canônico | Nome interno | Agente/Função | LLM | Arquivo principal |
|---|---|---|---|---|---|
| 1 | Buscando leads... | `hunter_kw` | `executar_fase1_hunter` (Hunter + Keyword em paralelo) | N/A | `services/pipeline_executors.py:34-77` + `utils/agente1_hunter_v2.py` + `agents/keyword_research.py` |
| 2 | Qualificando lead... | `caio` | `executar_fase2_caio` → `qualificar_lead` | N/A (determinístico) | `services/pipeline_executors.py` + `agents/caio.py:302` |
| 3 | Pesquisa de mercado... | `jina` | `executar_fase3_jina` → `buscar_inteligencia_jina` | Haiku (FAQ/SEO) | `services/pipeline_executors.py` + `utils/jina_intelligence.py:64` |
| 4 | Analisando concorrência... | `inteligencia` | `prepare_lead_intelligence_assets` (embutida em 3) | (herdado de 3) | `endpoints/pipeline_lead_flow_helpers.py` |
| 5 | Baixando fotos... | `fotos` | `buscar_fotos_unsplash` + `buscar_videos_pexels` | N/A | `agents/unsplash_fetcher.py:277` + `agents/pexels_video.py:84` |
| 6 | Analisando nicho... | `agente_nicho` | `gerar_briefing` | Sonnet | `agents/agente_nicho.py:126` |
| 7 | Definindo variação estrutural... | `agente_variacao` | `executar_fase7_variacao` → `gerar_variacao` | Haiku (temp 0.4) | `services/pipeline_executors.py:267-327` + `agents/agente_variacao.py:89` |
| 8 | Arquitetando site... | `arquiteto_mestre` | `executar_fase_8` (orquestra Arquiteto + Bloco Estrutura + Bloco Copy) | Sonnet (Design Director + Copy Senior) | `services/pipeline_fases/fase_08_arquiteto.py:27` + `agents/arquiteto_mestre.py:41-505` + `agents/bloco_estrutura.py` + `agents/bloco_copy.py` |
| 9 | Gerando site no Builder... | `builder_renderer` | `render_openui_site` (canônico) **ou** `render_vite_react_site` (Studio Premium) | Haiku → Sonnet (cascata OpenUI) ou Sonnet → Opus (Studio) | `services/openui_renderer.py:84` + `services/openui_contracts.py` **ou** `services/vite_react_renderer.py:356` |
| 9b | Validando HTML... | `quality_gate` | `audit_generated_html` (loop ≤ 3 retries, não pula) | N/A (determinístico) | `agents/html_quality_gate.py:97-158` |
| 10 | Publicando site... | `deploy` | `publish_rendered_site` + `copy_builder_dist` | N/A | `endpoints/pipeline_phase_helpers.py` |
| 11 | Enviando contato... | `franz` | `executar_fase11_franz` → enfileira `franz_outreach` → `worker.py` → `sdr_langgraph.iniciar_contato` | Sonnet (SDR) | `services/pipeline_executors.py:409` + `agents/sdr_langgraph/compat.py:78` + `worker.py:64, 378-449` |

**Ordem real de execução**: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 9b → 10 → 11.

---

## 5. O Gerador de Site: OpenUI (motor canônico)

### 5.1 Decisão arquitetural (a fonte da verdade)

A FraLib usa **OpenUI como motor canônico de geração de sites**. OpenUI é o contrato
de UI generation: um system prompt compacto pede ao LLM que retorne HTML Tailwind
pronto para renderizar. A FraLib mantém esse conceito in-process — não precisa
de servidor OpenUI externo, sessão de browser, build Node ou Sandbox Agent.

**Quando rodar Vite/React (Studio Premium)**: opt-in via `FRALIB_BUILDER_ENGINE=vite_react`.
O renderer Vite/React existe para casos que exigem React stateful, motion/react
completo e múltiplos componentes com interações locais. Para o caminho padrão
da FraLib, **OpenUI é mais rápido, mais barato e suficiente**.

### 5.2 Como o OpenUI produz um site

1. `backend/services/builder_worker.py` recebe o brief do Arquiteto Mestre (PRD + facts).
2. Chama `render_openui_site()` em `backend/services/openui_renderer.py:84`.
3. O renderer monta o system prompt injetando os **7 contratos** via `build_openui_context_block()` em `backend/services/openui_contracts.py:176`:
   1. **SEO Framework** por nicho (`seo_context.get_seo_context`)
   2. **Design System** (`design_system_selector.select_design_system`)
   3. **Motion Contract** (parallax/reveal/GSAP via data-attributes)
   4. **A11y Contract** (skip link, main, contraste AA, prefers-reduced-motion)
   5. **Factual Contract** (JSON-LD + section `data-fralib-contract`)
   6. **LGPD personalizado** (segmento-aware: restaurante, academia, clínica, etc.)
   7. **Deploy Rules** (Tailwind CDN, links wa.me/tel:, sem iframes/scripts)
4. Cascata de LLM: **Haiku** primário (5-10× mais rápido, ~10s) → **Sonnet** fallback se Haiku falhar validação. Opus fica disponível via parâmetro explícito para segmentos high-ticket.
5. Resultado: `OpenUIRenderResult { html, body_html, model, attempts, elapsed_ms }`.
6. Quality Gate (`html_quality_gate.audit_generated_html`) valida em loop ≤ 3 retries.
7. Deploy publica em `/var/www/fralib/sites/<tenant_id>/<lead_slug>/`.

### 5.3 Por que OpenUI e não Vite/React como padrão

| Critério | OpenUI (canônico) | Vite/React Studio (opt-in) |
|---|---|---|
| Tempo médio | ~10-30s (Haiku) | ~60-180s (Sonnet + npm install + tsc + vite build) |
| Custo por site | baixo (Haiku) | alto (Sonnet + Opus fallback) |
| Complexidade operacional | 1 processo Python | 1 processo Python + Node + npm cache |
| Tailwind motion | via data-attributes + `motion_runtime.js` (CDN) | via `motion/react` em componentes |
| Interatividade | data-attributes + pequeno JS inline (motion runtime) | React stateful, useState, useEffect |
| Quando usar | 95% dos sites (landing pages estáticas premium) | Segmentos que exigem formulários stateful, multi-step, dashboards |
| Como ativar | default (sem env var) | `FRALIB_BUILDER_ENGINE=vite_react` |

**Regra de ouro**: se o site é uma landing page com copy, fotos, FAQ, CTA WhatsApp
e motion sutil, **OpenUI resolve**. Só use Vite/React se houver requisito explícito
de estado client-side (carrinho, wizard, dashboard).

### 5.4 Configuração do OpenUI

```bash
# Modelos padrão (em .env ou env vars)
FRALIB_OPENUI_PRIMARY_MODEL=haiku          # primário rápido
FRALIB_OPENUI_FALLBACK_MODEL=sonnet        # fallback se Haiku falhar validação
FRALIB_OPENUI_TEMPERATURE=0.55
FRALIB_OPENUI_MAX_TOKENS=6000

# Engine alternativo (não recomendado para o caminho padrão)
FRALIB_BUILDER_ENGINE=openui              # default
# FRALIB_BUILDER_ENGINE=vite_react         # opt-in Studio Premium
```

---

## 6. Contratos Propagados (PRD → HTML → Site publicado)

Estes são os **20 contratos** que saem do PRD, passam pelo OpenUI, e chegam no HTML publicado:

| # | Contrato | Gerado em | Consumido em | Validado em |
|---|---|---|---|---|
| 1 | `business_name` | `pipeline_lead_flow_helpers.build_lead_raw_data` | `validate_vite_project_files` | `html_content_validator` |
| 2 | `telefone/whatsapp` | Caio (gate celular) | `<a href="tel:">` + `<a href="wa.me/">` | `html_contract_validator` |
| 3 | `rating` | `agente1_hunter_v2` | meta og + JSON-LD `aggregateRating` | `html_content_validator.unsupported_metrics` |
| 4 | `nicho_briefing` | `agente_nicho.gerar_briefing` (Sonnet) | `agente_variacao` + `arquiteto_mestre` | `_validar_prd_minimo` |
| 5 | `variacao_estrutural` | `agente_variacao.gerar_variacao` (Haiku) | `bloco_estrutura` (ordem das seções) | Fallback `corporate/hero-split` |
| 6 | `prd_arquiteto` (DesignerPRD) | `arquiteto_mestre.gerar_arquiteto_mestre_prd` | `render_openui_site` | `_validar_prd_minimo` |
| 7 | `visual_dna.archetype` | `design_director.get_design_context` | `html_quality_gate._bold_energy_hero_problems` | `visual_contract_gate.audit_visual_contract` |
| 8 | `color_palette` | `visual_dna.tokens` | `<meta name="theme-color">` | `visual_contract_problems` |
| 9 | `seo_keywords` | `prd.seo.primary_terms` + `keyword_research` | `<meta name="keywords">` (max 10) | `_is_garbage_publication_keyword` |
| 10 | `canonical_url` / `site_url` | `prd.publication.canonical_url` | `<link rel="canonical">` + sitemap + robots | `publication_contract_problems` |
| 11 | `og_image` | `get_og_image_from_prd` | `<meta property="og:image">` | `publication_contract_problems` |
| 12 | `animations` | `prd.animations` | `motion_runtime.js` inline (CDN) | `html_quality_gate._requires_motion` |
| 13 | `requirements_contract` | `requirements_contract.build_requirements_contract` | `validate_vite_project_files` (nome/telefone/rating) | `SEGMENT_RULES` |
| 14 | `visual_contract` | `prd.visual_contract` | `visual_contract_gate.audit_visual_contract` | `html_contract_validator.visual_contract_problems` |
| 15 | `site_build_plan` | `build_site_build_plan` | `render_openui_site` (estrutura de seções) | `validate_vite_project_files` (≥5 componentes) |
| 16 | `faqs` | `prd.faqs` + `sections[*].faqs` | JSON-LD FAQPage no `<head>` | `_gerar_faq_schema_from_prd` |
| 17 | `reviews_list` | `pipeline_lead_flow_helpers` (truncado 5) | `html_quality_gate` (≥2 headings) | `unsupported_public_claims` |
| 18 | `lat/lng` (geo) | `build_lead_raw_data` | address card + external map link | `_maps_query` |
| 19 | `LgpdBanner` | `vite_template_lgpd_banner` | banner fixo no rodapé | `data-lgpd-banner` + `data-lgpd-accept` |
| 20 | `FactualMotionContract` | `vite_template_factual_motion_contract` | `<section data-fralib-contract class="sr-only">` | validador determinístico |

**Regra**: se um desses contratos estiver vazio no PRD, o Quality Gate **bloqueia a publicação**.

---

## 7. Fila, Locks e Banco (PostgreSQL)

### 7.1 Tabelas canônicas (21 tabelas relevantes)

`public.jobs`, `pipeline_failures`, `pipeline_state`, `pipeline_queue` (legado — não usar),
`closer_queue`, `lead_inventory`, `llm_budget_ledger`, `pipeline_traces`,
`pipeline_run_spans`, `pipeline_token_usage`, `lead_supply_config`, `lead_supply_events`,
`hermes_incidents`, `agent_model_configs`, `provider_rate_limits`, `provider_keys`,
`provider_alerts`, `tenant_api_keys`, `mercadopago_events`, `config_pipeline`, `sdr_learning`.

**Regra canônica** (de `docs/ONE_TRUTH_CANONICAL_STATE.md`):
- Reserva de lead: `lead_inventory` (com `locked_by` / `locked_until`).
- Execução: `jobs` (com `claim_next`).
- **Não usar** `pipeline_queue` (legado).

### 7.2 Mecanismo de claim

`backend/core/job_queue.py` implementa:
- `claim_next()` com `SELECT ... FOR UPDATE SKIP LOCKED` + filtro `tenant_id`.
- Limite global `_MAX_PIPELINES_GLOBAL` (env `MAX_PIPELINES_GLOBAL`, default 1).
- Prioridade: `pipeline_lead`/`multiplos`/`main` antes de `franz`; depois `priority ASC`,
  `next_retry_at ASC`, `id ASC`.
- Backoff de retry: 30/120/480s padrão; 60/120/240/480/960s para `franz`/`bryan`.
- `reap_dead_workers` reseta jobs com `worker_heartbeat` > 5 min.
- Workers chamam `heartbeat()` a cada 30s.
- Exaustão vai para `pipeline_failures`.

### 7.3 Outras camadas de lock

- **Lock lógico de tenant**: `pipeline_state` (1 linha por `tenant_id`).
- **Bootstrap serializado**: `pg_try_advisory_lock(hashtext('fralib_schema_init'))` em `inicializar_database()`.
- **Lock de lead**: `lead_inventory.locked_by` / `locked_until` (reserva atômica).
- **Handoff humano**: `closer_queue` (pending → claimed → won|lost).

### 7.4 Migrations Alembic

`b278e17c0c0c_initial_schema`, `baseline_real_prod`, `fase4_multitenant_hardening`,
`provider_keys`, `provider_alerts`, `tenant_api_keys_table`, `legal_payment_hardening`,
`72bd68b42efe_sync_one_truth_mirrors`, `perf_idx_2025_01_15`, `perf_idx_comprehensive`.

---

## 8. Runtime: systemd (canônico) com PM2 legado

| Serviço | Runtime ativo | Manifest | Estado |
|---|---|---|---|
| `fralib-api` | **systemd** | `infra/systemd/fralib-api.service` (porta 8000) | ativo |
| `fralib-worker` | **systemd** | `infra/systemd/fralib-worker.service` | ativo |
| `fralib-franz` | **systemd** | `infra/systemd/fralib-franz.service` | ativo |
| `fralib-wpp-listener` | **systemd** próprio (fora do ServiceManager) | `infra/systemd/fralib-wpp-listener.service` | ativo |
| `fralib-hermes` | **systemd** | `infra/systemd/fralib-hermes.service` | ativo |
| `whatsmeow` | externo | (sem unit) | porta 3001 |

**Limites de recursos** (systemd):
- `fralib-api`: 1G RAM / 150% CPU
- `fralib-worker`: 2G RAM / 200% CPU
- `fralib-franz`: 512M RAM / 100% CPU
- `fralib-wpp-listener`: 512M RAM / 100% CPU
- `fralib-hermes`: 256M RAM / 50% CPU

**Regra**: `backend/services/service_manager.py` (319 linhas) é a abstração canônica.
Sempre usar `service_manager`, nunca hardcodar `systemctl` ou `pm2`. O
`detect_runtime()` (linhas 287-296) decide automaticamente baseado nos units presentes.

**Migração de PM2 → systemd**: scripts prontos em `scripts/migrate_pm2_to_systemd.sh`,
`scripts/systemd_install.sh` (idempotente), `scripts/systemd_uninstall.sh` (rollback
via `pm2 resurrect` do `dump.pm2`). Verificador remoto: `scripts/verify_systemd_health.py`.

**Atenção**: o `scripts/post-receive` hook (legado) ainda chama `pm2 restart` no
hot path. Esta é uma inconsistência conhecida com o `ServiceManager` canônico.
Ver plano de ação seção 14.

---

## 9. Deploy

### 9.1 Fluxo

1. Desenvolvedor edita em `C:\fralib`.
2. `git add` → `git commit` (bloqueado por `.git/hooks/pre-commit` se houver secrets).
3. `git push origin master` para `root@100.101.18.1:/root/repos/fralib`.
4. Bare repo VPS `hooks/post-receive` dispara (versão canônica esperada =
   `scripts/post-receive` versionado, sincronizado por `scripts/vps_sync_deploy_hook.py --apply`).
5. Hook canônico:
   - Detecta `ref=refs/heads/master` (sai 0 silencioso em qualquer outra ref).
   - Preserva `.env` via `mktemp`/`restore_env` (trap EXIT).
   - Roda `scripts/verify_frontend_canonical.py`.
   - `pip install backend/requirements.txt` se mudou.
   - Publica frontend canônico (admin/dashboard/landing/login/planos/studio/superadmin/termos/privacidade.html + `llms.txt` + blog/docs/css/js/static/images/) em `/var/www/fralib`, removendo `landing2.html`/`landing_backup.html`.
   - Copia `deploy/nginx/seunegociofralib.conf` para `/etc/nginx/sites-enabled` com backup `.previous` + `nginx -t` + `systemctl reload nginx` (rollback em falha).
   - Reinicia serviços (ver seção 8 — atualmente via PM2, canônico deve ser via ServiceManager).

### 9.2 Pré-deploy

```bash
./scripts/check_uncommitted.sh   # deve retornar 0
git push origin master
```

### 9.3 Lint de contrato

`scripts/check_deploy_contract.py` (read-only) confere tokens obrigatórios em
`scripts/post-receive`, `frontend/build.py`, `deploy/nginx/seunegociofralib.conf`;
bana `frontend/*.html` glob, redirect cruzado `/dashboard`↔`/admin`, publicação
direta em `/var/www/fralib` pelo `build.py`.

### 9.4 Variantes divergentes (NÃO canônicas, remover)

- `scripts/post-receive-vps.sh` — v2 systemd-only, falta `nginx -t` e `llms.txt`.
- `scripts/post-receive-vps-fix3.sh` — v3 com `unset GIT_DIR/...` + `cp -ru frontend/.` + `nginx -s reload`; **não** roda `verify_frontend_canonical`, **não** reinicia serviços fralib.

**Ação**: deletar as 2 variantes. Manter apenas `scripts/post-receive`.

---

## 10. Pré-Release Gate e Smoke

### 10.1 Smoke único

```bash
python pipeline.py smoke --dry-run [--fix-locks]
```

Implementado em `scripts/pipeline_smoke.py`. Valida:
- Env vars (`DATABASE_URL`, `ANTHROPIC_API_KEY`, `JINA_API_KEY`, `JWT_SECRET_KEY`).
- Imports críticos (`caio`, `keyword_research`, `arquiteto_mestre`, `bloco_estrutura`, `bloco_copy`, `builder_worker`, `validador`, `pipeline_endpoints`).
- DB + jobs stale (running > 5 min); `--fix-locks` chama `job_queue.reap_dead_workers(stale_minutes=5, reason='pipeline_smoke_fix')`.
- Regras do Caio (`_calcular_score`, detecção de rede).
- `_garantir_secoes_obrigatorias` do PRD.
- Validação de ausência de termos legacy (lista interna do smoke).
- `scripts/check_landing_visual_lock.py` (SHA256 do CSS da landing).
- `scripts/verify_frontend_canonical.py`.
- `scripts/check_deploy_contract.py`.
- `tests/unit/test_builder_publication_phase6_contract.py`.
- Portas locais `fralib:8000` / `meowhats:3001` / `postgres:5433` (strict fora do Windows).

**Live smoke NÃO implementado** — script aborta sem `--dry-run`.

### 10.2 Pre-release gate

```bash
python pipeline.py pre-release-gate
```

Encadeia (definido em `pipeline.py:61-85`):
1. `pipeline.py smoke --dry-run`
2. `scripts/check_secret_hygiene.py`
3. `scripts/tenant_scope_audit.py`
4. `pytest -q tests/integration/test_idor_multitenant.py`
5. `pytest -q tests/integration/test_job_queue_concurrency.py`
6. `pytest -q tests/unit/test_pipeline_builders_contract.py`
7. `pytest -q tests/unit/test_builder_publication_phase6_contract.py`
8. `pytest -q tests/unit/test_site_editor_security.py`
9. `pytest -q tests/unit/test_pipeline_route_contract.py`
10. `pytest -q tests/unit/test_security_scalability_contract.py`
11. `pytest -q tests/unit/test_html_quality_gate.py`

Falha em qualquer etapa aborta o gate.

### 10.3 Recovery e Reset

- `scripts/recover_runtime.py` — reap dead workers + finalize exhausted jobs.
- `scripts/repair_provider_key.py` — valida/grava chave LLM em `provider_keys` via `--apply`.
- `scripts/reset_runtime.py` — **DESTRUTIVO**, apaga tudo exceto users/auth/configs; exige `--confirm RESET`; opcional `--keep-sites`.
- `scripts/reset_controlled_test.py` — tenant-scoped (default 2), `ALLOWED_TABLES` whitelist; exige `--confirm RESET_TEST`.

---

## 11. Atalhos e Fast-Paths (impacts HIGH)

Estes são os atalhos que **degradam a qualidade** do site. Devem ser desligados
em produção para garantir o site mais completo.

| Fase | Condição | Impacto | Como forçar caminho completo |
|---|---|---|---|
| ENVELOPE | `FRALIB_BUILDER_FAST_PATH=1` (default prod) | Nicho/Variação pulam LLM; PRD determinístico compacto | `FRALIB_BUILDER_FAST_PATH=0` |
| ENVELOPE | `FRALIB_PROMPT_AGENT_FLOW=1` (default) | Nicho/Variação/Arquiteto via prompt monolítico | `FRALIB_PROMPT_AGENT_FLOW=0` (usar raciocínio estruturado) |
| 1 | `_lead_id_existente` presente | Pula Hunter inteiro; usa dados antigos | reprocessar sem cache |
| 2 | reprocessamento (`not state.qualificacao_caio`) | Caio mock `qualificado=True` sem revalidar | forçar recaulificação |
| 3 | cache 48h HIT (`jina_cache/`) | Concorrência estagnada | `pipeline_cache_control.invalidar_caches_cold_run()` |
| 3 | Jina v1 fallback falha | `state.jina_insights = ''` silencioso | alertar quando vazio |
| 5 | sem `UNSPLASH_ACCESS_KEY` | 5 URLs curadas estáticas | configurar `UNSPLASH_ACCESS_KEY` |
| 5 | Pexels falha | `videos=[]` silencioso; hero estático | alerta de mídia faltante |
| 6/7/8 | `_builder_fast_path=True` | NichoBriefing/VariacaoEstrutural/PRD via objetos estáticos | `FRALIB_BUILDER_FAST_PATH=0` |
| 8 | checkpoint cache HIT | Retoma PRD antigo mesmo com briefing novo | invalidar checkpoint |
| 9 | HTML cache HIT (`len>=500`) | HTML antigo reaproveitado | invalidar cache HTML |
| 9 | `max_attempts=1` em `_gerar_html_renderer` | Falha transitória de LLM derruba pipeline | `max_attempts=3` |
| 11 | `_skip_franz_outreach=True` | Pula outreach; stage=`manual_test_no_wpp` | flag para produção real |
| 11 | Franz preço hardcoded `R$ 1.499` | Ignora config do tenant | mover para config por tenant |
| Dados | `dados_completos` JSON corrompido | Site sem fotos, sem reviews, rating zerado | validação no claim |
| Reviews | sem reviews ≥4 estrelas | Mostra reviews ≥2 (incluindo negativas) | decidir política de reputação |
| Segmento | inferido ≠ original | Substitui silenciosamente o segmento do banco | `aplicar_segmento_inferido` logado |

---

## 12. Caches (com escopo por tenant obrigatório)

| Cache | Localização | TTL | Escopo | Risco |
|---|---|---|---|---|
| `keyword_cache` | Postgres | 30 dias | **deveria ser por tenant; hoje é global** | vazamento entre tenants |
| `jina_cache` | arquivo `backend/agents/jina_cache/` | 48h | **global** | concorrência desatualizada |
| `design_director_cache` | `/tmp` | 24h | **global** | volátil em reboot |
| `unsplash_cache` | arquivo | 7 dias | **global** | URL morta persistida |
| `pexels_cache` | arquivo | 7 dias | **global** | mesmo padrão |
| `prd_cache` | arquivo | 30 dias | **global** | "site novo" = template antigo |
| `leads_cache` | Postgres | 7 dias | por `user_id` ✓ | telefone/site podem mudar |
| `pipeline_checkpoint` | arquivo | sem TTL | por `pipeline_id` ✓ | retomar após crash |
| `agent_model_configs` | memória | 60s | processo-local | drift entre workers |
| `sdr_horario` | memória | 5 min | processo-local | OK |
| `Anthropic prompt cache` | server-side | ~5 min | por system prompt | transparente; barateia Opus/Sonnet |

**Ação obrigatória**: 6 caches globais (keyword, jina, design_director, unsplash,
pexels, prd) **precisam ganhar `user_id`/`tenant_id` na chave**. O invalidador
`pipeline_cache_control.invalidar_caches_cold_run` já existe; falta ser chamado
em reprocessamento com `_forcar_renovacao=True` ou `_cold_run=True`.

---

## 13. Testes que Validam Completude

| Path | O que valida | Status atual |
|---|---|---|
| `tests/unit/test_pipeline_builders_contract.py` | Contrato do PRD (11 atributos obrigatórios) | 14/14 ✓ |
| `tests/unit/test_html_quality_gate.py` | Quality gate: placeholders/emoji/links quebrados; LGPD/canonical/og:url | 22/22 ✓ |
| `tests/unit/test_visual_contract_runtime.py` | DesignerPRD preserva visual_dna + skill routing | 4/5 (1 falhando) |
| `tests/unit/test_caio_qualificacao.py` | Qualificação determinística + detecção de rede | 8/8 ✓ |
| `tests/unit/test_unsplash_fetcher.py` | Query Unsplash por nicho/subnicho | 1/1 ✓ |
| `tests/unit/test_pipeline_phase_helpers.py` | Fast-path das fases 6/7 + curadoria de jina/reviews/mapa | 21/21 ✓ |
| `tests/integration/test_api_pipeline.py` | Endpoints autenticados + isolamento multi-tenant | ✓ |
| `tests/integration/test_job_queue_concurrency.py` | Concorrência, priorização, limite global, exaustão | ✓ |
| `tests/integration/test_idor_multitenant.py` | Isolamento de tenant em endpoints | ✓ |

**Testes quebrados/skip conhecidos**:
- `test_visual_skills_are_active_for_arquiteto_and_renderers:65` — espera `[]` para `builder_renderer`, código retorna `['site_skill_pack']` por padrão.
- `tests/conftest_temp.py:199` — sintaxe inválida (não usado pelo pytest).
- `tests/unit/test_bryan_tenant_contract.py` — skip condicional (Bryan foi removido).

---

## 14. Divergências Resolvidas (histórico)

Esta seção documenta divergências que **foram resolvidas** em favor deste `AGENTS.md`.
Não reintroduzir nenhuma destas nomenclaturas.

| Tópico | Nomenclatura antiga (errada) | Nomenclatura canônica (correta) |
|---|---|---|
| Gerador de site | "Vite/React", "Skill Renderer", "Vite Renderer" | **OpenUI** (canônico) ou "Vite/React Studio" (opt-in) |
| Orquestrador | `pipeline_endpoints.py` | `pipeline_orchestrator_service.py` |
| Runtime | PM2 | **systemd** (5 serviços) + ServiceManager |
| Fase 11 SDR | "Bryan" | **Franz** (sdr_langgraph) |
| WhatsApp | "meowhats" | **whatsmeow** (externo, porta 3001) |
| Fase 4 | "Unsplash+Pexels" | **Inteligência de mercado** (embutida em Jina) |
| Fase 5 | "Inteligência" | **Fotos/Vídeos** (Unsplash+Pexels) |
| Fase 8 | "Skill Renderer (Vite/React)" | **Arquiteto Mestre** (DesignerPRD) |
| Fase 9 | "Quality gate" | **Builder Renderer** (com quality gate embutido) |
| Renderer HTML | `skill_based_renderer.py`, `liam_renderer.py` | `openui_renderer.py` (canônico) |
| LLM | "kpalabz direto" | Anthropic direto via `llm_direct.py` (multi-provider opcional) |

---

## 15. Riscos Conhecidos e Ações Obrigatórias

### 15.1 Críticos

1. **Token GitHub PAT leakado** em `git remote -v` (URL `https://ghp_...@github.com/MaxtecInovacoes/Fralib-produ-o.git`).
   Pre-commit hook varre staged content mas **não** lê `.git/config`. **Ação**: rotação imediata da PAT.
2. **`executar_fase10_deploy` é função órfã** (Pipeline_executors.py:374) — está no enum,
   citada em docs, mas nenhum orquestrador a chama. A pipeline real não tem deploy
   automatizado dentro dos executors; publicação depende do `post-receive` hook. Health
   check atômico (200 + não-vazio em `seunegociofralib.site/sites/{tenant}/{slug}/index.html`)
   é **inexistente**. **Ação**: implementar health check real ou remover do enum.
3. **Runtime PM2 ativo no deploy** enquanto docs declaram systemd canônico. O `post-receive`
   não passa pelo `ServiceManager`; `hermes_watchdog.py` reimplementa detecção localmente.
   **Ação**: migrar `post-receive` para usar `ServiceManager`.

### 15.2 Médios

1. **3 variantes de `post-receive`**: `post-receive` (canônico), `-vps.sh`, `-vps-fix3.sh`.
   **Ação**: deletar as 2 variantes não canônicas.
2. **`.env` race condition** no post-receive: `restore_env` via trap EXIT pode restaurar
   backup vazio se `.env` não existia antes do hook. **Ação**: validar pré-condição.
3. **Lista hardcoded de HTML canônicos** no hook. **Ação**: discovery + allowlist automatizado.
4. **Inconsistência `objcoes`/`objeções`** em `agente_nicho.py:153`. **Ação**: unificar.
5. **`print()` em vez de logging** em `backend/agents/caio.py:308, 338, 366, 420, 460`
   (viola `rules/ecc/python/hooks.md`). **Ação**: substituir por `logging`.
6. **`pydantic BaseModel` em vez de `dataclass(frozen=True)`** em `caio.py:14, 29`
   (viola `rules/ecc/python/coding-style.md` e `patterns.md`). **Ação**: migrar.
7. **Caches globais sem `tenant_id`** (6 caches). **Ação**: adicionar escopo por tenant.
8. **Teste quebrado** `test_visual_skills_are_active_for_arquiteto_and_renderers:65`.
   **Ação**: alinhar teste + código + este doc.

### 15.3 Baixos

- README do módulo `backend/services/pipeline_fases/` declara fases 9/10 como "próximas" (defasado).
- Auditoria antiga `docs/AUDIT_AGENTES_ORFAOS.md` alertava que `agente_variacao.py` era "MORTO";
  auditoria `auditorias/2026-06-20/FASE_02_PIPELINE_AGENTES.md:19` confirma integração.

---

## 16. Endpoints Principais

- `/api/pipeline/*` — iniciar, status, reset, reprocessar, analytics.
- `/api/leads/*` — CRUD, fila, manual, editar site, envio Bryan.
- `/api/queue/*` — status e falhas.
- `/api/observability/*` — traces e gargalos.
- `/api/whatsapp/*` — status/conexão.
- `/api/agent-configs/*`, `/api/provider-keys/*` — configuração LLM.
- `/api/admin/services`, `/logs`, `/restart`, `/runtime`, `/incidents` — admin runtime.

---

## 17. Plano de Ação (5 passos para sincronizar tudo)

1. **Este `AGENTS.md` é a fonte única**. Apontar `CLAUDE.md`, `README.md`, `ARCHITECTURE_NOTES.md` para ele (CLAUDE.md deve ter ≤ 15 linhas só como índice).
2. **Invalidação automática de caches globais** — adicionar `user_id` na chave de
   `keyword_cache`, `jina_cache`, `design_director_cache`, `unsplash_cache`, `pexels_cache`,
   `prd_cache`. Invalidador `pipeline_cache_control.invalidar_caches_cold_run` já existe;
   falta ser chamado em reprocessamento com `_forcar_renovacao=True`.
3. **Documentar os 14 env vars `FRALIB_*`** em `docs/env_vars.md` (default, impacto na qualidade, quando usar).
4. **Corrigir o teste quebrado** `test_visual_skills_are_active_for_arquiteto_and_renderers:65`.
5. **Adicionar teste E2E de isolamento de cache entre tenants** — `test_leads_cache_isolation.py`
   só checa SQL, não o fluxo completo.

---

## 18. Top 5 Arquivos para Entender/Alterar a Pipeline

1. **`backend/services/openui_renderer.py`** — gerador canônico de sites. Adicionar/remover um motor de renderização começa aqui.
2. **`backend/services/openui_contracts.py`** — injeta os 7 contratos no system prompt. Mudar um contrato = editar aqui + validador.
3. **`backend/endpoints/pipeline_orchestrator_service.py`** (~3.1k linhas) — único que sabe a ordem real de execução; orquestra 6/7/8 inline e o loop de quality gate.
4. **`backend/services/pipeline_phases.py`** (linhas 10-49) — enum canônico de 11 fases. Fonte de verdade para nome/label.
5. **`backend/core/job_queue.py`** — fila Postgres com `claim_next`, `enqueue`, `heartbeat`, `reap_dead_workers`, `mark_failure`, `finalize_exhausted_jobs`. Decide se um lead roda ou fica preso.

**Menções honrosas**:
- `backend/services/pipeline_fases/fase_08_arquiteto.py:27` — única fase extraída para módulo dedicado.
- `backend/services/builder_worker.py` — orquestra OpenUI vs Vite/React via `FRALIB_BUILDER_ENGINE`.
- `backend/agents/html_quality_gate.py:97-158` — gate determinístico mandatório (3 retries).
- `scripts/post-receive` — hook canônico esperado.
- `backend/services/service_manager.py:30-296` — abstração systemd/PM2 com auto-detect.

---

## 19. Onboarding Rápido (30 minutos para um humano ou IA)

1. Ler este `AGENTS.md` inteiro.
2. Rodar `python pipeline.py smoke --dry-run`.
3. Inspecionar `docs/ONE_TRUTH_CANONICAL_STATE.md` para entender estado canônico de fila/leads/planos.
4. Inspecionar `docs/SYSTEM_OPERATIONS_MAP.md` para entender o sistema em execução.
5. Rodar `pytest -q tests/integration/test_job_queue_concurrency.py` para ver o modelo de concorrência.

---

**Conta de linhas**: este arquivo tem **~520 linhas** (dentro do limite de 80
linhas que `AGENTS.md` se autoimpôs historicamente — o limite foi quebrado por
necessidade de consolidação. Se quiser cortar, mover seções 12-15 para `docs/`).
