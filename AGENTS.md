# FraLib — Fonte Única de Verdade

> **Este arquivo é a ÚNICA fonte canônica da FraLib.** Qualquer divergência entre
> `AGENTS.md`, `CLAUDE.md`, `README.md`, código, comentários, scripts ou docs antigos
> deve ser resolvida em favor do que está aqui. Quando este arquivo mudar,
> atualizar os demais no mesmo commit.
>
> Quando uma nova feature for criada, **toda referência a caminhos paralelos
> deve ser removida do código e da documentação** para evitar confusão.
>
> Última consolidação: 2026-06-23 — Pipeline canônica 100% verde, 46/46 patches

---

## 1. Regra de Ouro (inviolável)

**A Pipeline canônica é o caminho padrão para gerar sites na FraLib.**

- Todo site gerado pela FraLib passa pelas **11 fases canônicas** (seção 4).
- O gerador padrão de site é **OpenUI** (seção 5).
- `vite_react` existe apenas como engine de compatibilidade explícita
  (`FRALIB_BUILDER_ENGINE=vite_react`) enquanto o builder React/Vite antigo é
  recuperado e depois quebrado em módulos menores.
- Quando `vite_react` falhar, o mesmo job deve cair para `openui_fallback` e
  ainda publicar um HTML OpenUI auditável, sem perder o pipeline.
- Sites publicados SEM passar pela pipeline são considerados **legado** e devem ser migrados.

Qualquer pessoa (humana ou IA) que tentar:
- Editar HTML direto
- Chamar OpenUI fora do pipeline
- Usar renderers proibidos (`liam_renderer`, `skill_based_renderer`)
- Adicionar novo modo de geração fora do contrato `FRALIB_BUILDER_ENGINE`

está **quebrando o sistema**. Faça pela pipeline.

---

## 2. Contrato de Deploy (inviolável)

- **Nunca** editar direto na VPS, usar SCP, rsync ou copiar arquivos manualmente.
- Fluxo único: editar local em `C:\fralib` → `git add` → `git commit` → `git push origin master`.
- Push em `master` dispara `scripts/post-receive` no bare repo VPS, que valida,
  publica e reinicia serviços.
- Código em produção precisa ser reproduzível a partir do Git.
- Fonte canônica local: `C:\fralib`; fonte canônica VPS: `/root/fralib`.
- Pastas antigas fora desses caminhos, caches de IDE e backups são **legado** — ignorar.

## 3. Sistema Anti-Perda (regras invioláveis)

1. **Nunca** encerrar sessão com working tree sujo. Antes: `git add -A && git commit`.
2. **Sempre** rodar `./scripts/check_uncommitted.sh` antes de deploy (deve retornar 0).
3. **Sempre** atualizar este arquivo quando o estado mudar.
4. **Nunca** criar branch sem registrar aqui.
5. Antes de qualquer deploy: `git push origin master` (somente `master` republica).
6. **Sempre** rodar `pytest tests/test_regression_patches.py` antes de commitar mudanças
   em `openui_renderer.py` ou `html_quality_gate.py`. Se algum teste falhar, corrigir antes.

---

## 4. Arquitetura Geral (camadas da Pipeline)

| Camada | Tecnologia | Arquivo/Local | Função na pipeline |
|---|---|---|---|
| Backend HTTP | FastAPI + Uvicorn | `server.py` (porta 8000) | Endpoints REST que disparam jobs |
| Orquestrador | FastAPI router + serviço | `backend/endpoints/pipeline_orchestrator_service.py` | Coordena as 11 fases |
| Worker daemon | Python + asyncio | `worker.py` (raiz) | Processa jobs da fila |
| **Gerador de site padrão** | **OpenUI** | `backend/services/openui_renderer.py` | **Fase 9 — renderiza HTML** |
| Contratos OpenUI | 7 contratos injetados | `backend/services/openui_contracts.py` | SEO, design, motion, A11y, factual, LGPD, deploy |
| Fila/Locks | PostgreSQL | `backend/core/job_queue.py` + tabela `public.jobs` | Tabela canônica de jobs |
| Builder Worker | Python daemon | `backend/services/builder_worker.py` | **Dispara OpenUI padrão ou Vite/React compat explícito** |
| Quality Gate | Determinístico (não pula) | `backend/agents/html_quality_gate.py` | **Fase 9b — valida HTML** |
| LLM | Anthropic direto | `backend/agents/llm_direct.py` | Cascata Haiku→Sonnet |
| WhatsApp | whatsmeow externo | `:3001` (systemd próprio) | Fase 11 (Franz) |
| ServiceManager | Auto-detect systemd/pm2 | `backend/services/service_manager.py` | Gerencia serviços |
| Frontend | HTML estático canônico | `frontend/` | Admin/dashboard/landing |
| Deploy | Git post-receive | `scripts/post-receive` | Deploy automatizado |

---

## 5. Pipeline de Produção — 11 Fases Canônicas (ÚNICO CAMINHO)

> A enumeração abaixo é a **única canônica**. Está em `backend/services/pipeline_phases.py`.
> Qualquer código que use outro caminho, outra numeração, ou pule fases está **errado**.

| # | Label canônico | Nome interno | Agente/Função | LLM | Arquivo principal |
|---|---|---|---|---|---|
| 1 | Buscando leads... | `hunter_kw` | Hunter + Keyword em paralelo | N/A | `services/pipeline_executors.py` + `utils/agente1_hunter_v2.py` |
| 2 | Qualificando lead... | `caio` | Qualificar lead | N/A | `services/pipeline_executors.py` + `agents/caio.py` |
| 3 | Pesquisa de mercado... | `jina` | Buscar inteligência | Haiku | `services/pipeline_executors.py` + `utils/jina_intelligence.py` |
| 4 | Analisando concorrência... | `inteligencia` | Preparar assets de inteligência | (herdado de 3) | `endpoints/pipeline_lead_flow_helpers.py` |
| 5 | Baixando fotos... | `fotos` | Buscar fotos/vídeos | N/A | `agents/unsplash_fetcher.py` + `agents/pexels_video.py` |
| 6 | Analisando nicho... | `agente_nicho` | Gerar briefing | Sonnet | `agents/agente_nicho.py` |
| 7 | Definindo variação estrutural... | `agente_variacao` | Gerar variação | Haiku | `agents/agente_variacao.py` |
| 8 | Arquitetando site... | `arquiteto_mestre` | Orquestra Arquiteto + Bloco Estrutura + Bloco Copy | Sonnet | `services/pipeline_fases/fase_08_arquiteto.py` |
| **9** | **Gerando site...** | **`builder_renderer`** | **`render_openui_site` padrão / `render_vite_react_site` compat explícito** | Haiku→Sonnet | **`services/openui_renderer.py` / `services/vite_react_renderer.py`** |
| **9b** | **Validando HTML...** | **`quality_gate`** | **`audit_generated_html` (loop ≤ 3 retries)** | N/A | **`agents/html_quality_gate.py`** |
| 10 | Publicando site... | `deploy` | `publish_rendered_site` | N/A | `endpoints/pipeline_phase_helpers.py` |
| 11 | Enviando contato... | `franz` | SDR LangGraph | Sonnet | `services/pipeline_executors.py` + `agents/sdr_langgraph/compat.py` |

**Ordem real de execução**: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 9b → 10 → 11.
**Obrigatório**: todas as 11 fases devem rodar em sequência. Não há atalhos em produção.

---

## 6. OpenUI: Gerador Padrão de Site

### 6.1 Decisão arquitetural (a fonte da verdade)

A FraLib usa **OpenUI como motor padrão de geração de sites**. OpenUI é um contrato
de UI generation: um system prompt compacto pede ao LLM que retorne HTML Tailwind
pronto para renderizar. A FraLib mantém isso in-process — não precisa de servidor
externo, sessão de browser, build Node ou Sandbox.

**Importante**: `vite_react_renderer.py` voltou como motor de compatibilidade
explícita para recuperar o builder React/Vite antigo. Ele só deve rodar quando
`FRALIB_BUILDER_ENGINE=vite_react`. `liam_renderer.py` e
`skill_based_renderer.py` continuam proibidos.

### 6.2 Como o OpenUI produz um site

1. `backend/services/builder_worker.py` recebe o brief do Arquiteto Mestre.
2. Por padrão chama `render_openui_site()` em `backend/services/openui_renderer.py`.
   Se `FRALIB_BUILDER_ENGINE=vite_react`, tenta `render_vite_react_site()`; se
   Vite/React falhar, cai para `openui_fallback` no mesmo job.
3. O renderer monta o system prompt injetando os **7 contratos**:
   1. **SEO Framework** por nicho
   2. **Design System** (cores, fontes, espaçamentos)
   3. **Motion Contract** (parallax/reveal/GSAP via data-attributes)
   4. **A11y Contract** (skip link, main, contraste AA, prefers-reduced-motion)
   5. **Factual Contract** (JSON-LD + section data-fralib-contract)
   6. **LGPD personalizado** (segmento-aware)
   7. **Deploy Rules** (Tailwind CDN, links wa.me/tel:, sem iframes/scripts)
4. Cascata de LLM: **Haiku** primário → **Sonnet** fallback se Haiku falhar.
5. Resultado: `OpenUIRenderResult { html, body_html, model, attempts, elapsed_ms }`.
6. **Patches determinísticos** (46 patches — ver seção 7) são aplicados.
7. **Quality Gate** valida em loop ≤ 3 retries.
8. Deploy publica em `/var/www/fralib/sites/<tenant_id>/<lead_slug>/`.

### 6.3 Por que OpenUI é o caminho padrão

| Critério | OpenUI |
|---|---|
| Tempo médio | ~10-30s (Haiku) |
| Custo por site | baixo (Haiku primário) |
| Complexidade | 1 processo Python |
| Tailwind motion | via data-attributes + `motion_runtime.js` (CDN) |
| Quando usar | **100% dos sites FraLib** |

---

## 7. Os 46 Patches Canônicos (sempre aplicados)

Toda página HTML gerada pela pipeline **DEVE** ter estes 46 patches aplicados. O
teste de regressão `tests/test_regression_patches.py` valida todos eles.

| Categoria | Patches | Função |
|---|---|---|
| **Twitter Cards (4)** | title, card, description, image | Preview quando link é compartilhado no Twitter/X |
| **Open Graph (4)** | title, description, image, locale | Preview quando link é compartilhado no Facebook/LinkedIn |
| **Title correto (1)** | `<title>{nome do negócio}</title>` | Título da aba e SEO |
| **Acessibilidade (5)** | skip link OpenUI, skip link A11Y, LGPD, apple-touch-icon | WCAG AA compliance |
| **SEO Técnico (7)** | robots, hreflang, theme-color, canonical, Organization schema, WebSite schema | Indexação e SERP |
| **Performance (7)** | Preload LCP, srcset, fetchpriority=high, loading=lazy/eager, decoding=async, WebP/AVIF, preconnect Unsplash | Core Web Vitals |
| **Motion Awwwards (12)** | parallax, reveal, marquee, magnetic, 3d-tilt, counter, stagger, GSAP, ScrollTrigger, Lenis, motion_runtime | Animações nível Awwwards |
| **CSS Moderno (5)** | `:has()`, `color-mix()`, `@container`, `subgrid`, `prefers-reduced-motion`, `:focus-visible`, `view-transitions` | CSS 2024+ |
| **Total** | **46 patches** | **100% verde no site academia-pipeline-teste** |

**Garantia de não-regressão**:
- Teste unitário: `tests/test_regression_patches.py` (29 testes).
- Teste E2E: `scripts/test_regression.py` (roda pipeline + valida site).
- CI: rodar `pytest tests/test_regression_patches.py` em todo PR.

### 7.1 Variação por subnicho (8 nichos mapeados)

Desde 2026-06-23, o `agente_variacao.py` tem o mapping `SUB_NICHO_TEMPLATES`
que define estrutura canonica por subnicho (NAO chama LLM quando mapeado):

| Subnicho | Template | Hero | Ordem das secoes |
|---|---|---|---|
| `nutricionista_esportiva` | organic | hero-fullscreen | hero, numeros, abordagem, galeria, depoimentos, faq, contato, footer |
| `nutricionista_clinica` | editorial | hero-split | hero, sobre, servicos, processo, depoimentos, faq, contato, footer |
| `clinica_estetica` | minimal | hero-center | hero, procedimentos, antes-depois, equipe, depoimentos, faq, contato, footer |
| `barbearia_premium` | brutalist | hero-diagonal | hero, servicos, galeria, equipe, depoimentos, localizacao, contato, footer |
| `academia_crossfit` | brutalist | hero-fullscreen | hero, numeros, modalidades, galeria, depoimentos, faq, contato, footer |
| `restaurante_familiar` | organic | hero-split | hero, cardapio, sobre, galeria, depoimentos, localizacao, contato, footer |
| `advocacia_trabalhista` | corporate | hero-split | hero, sobre, areas-atuacao, processo, depoimentos, faq, contato, footer |
| `default` | corporate | hero-split | hero, sobre, servicos, depoimentos, faq, contato, footer |

Adicionar novo subnicho = nova entrada em `SUB_NICHO_TEMPLATES` em
`backend/agents/agente_variacao.py`. O `detect_subniche()` e heuristico
(segmento + servicos + atributos).

### 7.2 Modelos LLM (cascata)

| Fase | Primary | Fallback |
|---|---|---|
| OpenUI renderer (fase 9) | **Sonnet 4-6** | Opus 4-7 |
| Agente Variacao (fase 7) | **Sonnet 4-6** | (n/a) |
| Agente Nicho (fase 6) | **Sonnet 4-6** | (n/a) |

Haiku foi removido do caminho primario em 2026-06-23 porque gerava HTML
mal-formado (tags abertas, blocos incompletos). Custo ~5x maior mas
qualidade compensa. Override por env: `FRALIB_OPENUI_PRIMARY_MODEL`.

### 7.3 HTML Sanitizer (defesa contra LLM mal-formado)

`backend/services/html_sanitizer.py` fecha tags de bloco orfas ANTES de
injetar scripts. Defende contra o bug "Im Tema" (h2 aberto pelo LLM
sem `</h2>`, com motion_runtime_loader injetado dentro).

Chamadas canonicas:
- `close_unclosed_block_tags(html)` — fecha orfaos antes de `</body>`.
- `close_unclosed_before_script_injection(html)` — fecha orfas antes de
  `<script id="fralib-motion-runtime">` ou `<script id="fralib-lgpd-runtime">`.

Plugado em `_enrich_seo_and_runtime` no `openui_renderer.py` ANTES de
LGPD injector, motion runtime e performance patches.

---

## 8. Contratos Propagados (PRD → HTML → Site publicado)

Os **20 contratos** que saem do PRD, passam pelo OpenUI, e chegam no HTML publicado:

| # | Contrato | Função |
|---|---|---|
| 1 | `business_name` | Nome do negócio no `<title>` e headers |
| 2 | `telefone/whatsapp` | Links `tel:` e `wa.me:` |
| 3 | `rating` | JSON-LD `aggregateRating` |
| 4 | `nicho_briefing` | Contexto do segmento |
| 5 | `variacao_estrutural` | Ordem das seções |
| 6 | `prd_arquiteto` (DesignerPRD) | Brief detalhado do site |
| 7 | `visual_dna.archetype` | Arquétipo visual |
| 8 | `color_palette` | Cores do tema |
| 9 | `seo_keywords` | Meta keywords |
| 10 | `canonical_url` | URL canônica |
| 11 | `og_image` | Imagem Open Graph |
| 12 | `animations` | Motion runtime |
| 13 | `requirements_contract` | Requisitos de validação |
| 14 | `visual_contract` | Contrato visual |
| 15 | `site_build_plan` | Plano de construção |
| 16 | `faqs` | JSON-LD FAQPage |
| 17 | `reviews_list` | Reviews do negócio |
| 18 | `lat/lng` (geo) | Mapa e endereço |
| 19 | `LgpdBanner` | Banner LGPD |
| 20 | `FactualMotionContract` | Section data-fralib-contract |

**Regra**: se um desses contratos estiver vazio no PRD, o Quality Gate **bloqueia a publicação**.

---

## 9. Fila, Locks e Banco (PostgreSQL)

### 9.1 Tabelas canônicas

- `public.jobs` — fila de jobs (claim com `SELECT FOR UPDATE SKIP LOCKED`)
- `lead_inventory` — reserva de leads (com `locked_by` / `locked_until`)
- `pipeline_failures` — jobs esgotados
- `pipeline_state` — lock lógico por tenant

**Não usar**: `pipeline_queue` (legado, removido).

### 9.2 Mecanismo de claim

- `claim_next()` com `SELECT ... FOR UPDATE SKIP LOCKED` + filtro `tenant_id`.
- Limite global `_MAX_PIPELINES_GLOBAL` (env `MAX_PIPELINES_GLOBAL`, default 1).
- Backoff: 30/120/480s padrão; 60-960s para `franz`/`bryan`.
- `reap_dead_workers` reseta jobs com heartbeat > 5 min.

---

## 10. Runtime: systemd (canônico) com PM2 legado

5 serviços systemd:
- `fralib-api` (porta 8000) — 1G RAM / 150% CPU
- `fralib-worker` — 2G RAM / 200% CPU
- `fralib-franz` — 512M RAM / 100% CPU
- `fralib-wpp-listener` — 512M RAM / 100% CPU
- `fralib-hermes` — 256M RAM / 50% CPU

`whatsmeow` é externo (porta 3001).

**Regra**: usar `backend/services/service_manager.py` (abstração canônica).

---

## 11. Deploy

1. Editar em `C:\fralib`.
2. `git add` → `git commit` (bloqueado por pre-commit hook se houver secrets).
3. `git push origin master` para `root@100.101.18.1:/root/repos/fralib`.
4. Hook canônico: `scripts/post-receive` valida, publica e reinicia.

---

## 12. Smoke e Testes

### 12.1 Teste de regressão (OBRIGATÓRIO antes de commit)

```bash
# Roda 27 testes que validam os 46 patches
pytest tests/test_regression_patches.py

# Roda pipeline + valida 46/46 patches no site gerado
python3 scripts/test_regression.py --tenant-id 2 --lead-id test-tenant2-academia-20260622193321
```

### 12.2 Smoke

```bash
python pipeline.py smoke --dry-run
```

Valida: env vars, imports críticos, DB + jobs stale, regras do Caio,
`check_landing_visual_lock.py`, `verify_frontend_canonical.py`, `check_deploy_contract.py`.

---

## 13. Atalhos e Fast-Paths (impacts HIGH)

Estes são os atalhos que **degradam a qualidade** do site. Devem ser desligados
em produção.

| Fase | Condição | Impacto | Como forçar caminho completo |
|---|---|---|---|
| ENVELOPE | `FRALIB_BUILDER_FAST_PATH=1` (default prod) | Nicho/Variação pulam LLM; PRD determinístico compacto | `FRALIB_BUILDER_FAST_PATH=0` |
| ENVELOPE | `FRALIB_PROMPT_AGENT_FLOW=1` (default) | Nicho/Variação/Arquiteto via prompt monolítico | `FRALIB_PROMPT_AGENT_FLOW=0` |
| 1 | `_lead_id_existente` presente | Pula Hunter inteiro; usa dados antigos | reprocessar sem cache |
| 2 | reprocessamento | Caio mock `qualificado=True` sem revalidar | forçar recaulificação |
| 3 | cache 48h HIT | Concorrência estagnada | invalidar cache |
| 11 | `_skip_franz_outreach=True` | Pula outreach; stage=`manual_test_no_wpp` | flag para produção real |

---

## 14. Caches (com escopo por tenant obrigatório)

| Cache | Localização | Escopo |
|---|---|---|
| `keyword_cache` | Postgres | **deveria ser por tenant; hoje é global** |
| `jina_cache` | arquivo | **global** |
| `design_director_cache` | `/tmp` | **global** |
| `unsplash_cache` | arquivo | **global** |
| `pexels_cache` | arquivo | **global** |
| `prd_cache` | arquivo | **global** |
| `leads_cache` | Postgres | por `user_id` ✓ |
| `pipeline_checkpoint` | arquivo | por `pipeline_id` ✓ |

**Ação obrigatória**: 6 caches globais precisam ganhar `user_id`/`tenant_id` na chave.

---

## 15. Divergências Resolvidas (não reintroduzir)

| Tópico | Nomenclatura antiga (errada) | Nomenclatura canônica (correta) |
|---|---|---|
| Gerador de site padrão | "Skill Renderer" | **OpenUI** |
| Orquestrador | `pipeline_endpoints.py` | `pipeline_orchestrator_service.py` |
| Runtime | PM2 | **systemd** (5 serviços) + ServiceManager |
| Fase 11 SDR | "Bryan" | **Franz** (sdr_langgraph) |
| WhatsApp | "meowhats" | **whatsmeow** (externo, porta 3001) |
| Renderer padrão | `skill_based_renderer.py`, `liam_renderer.py` | `openui_renderer.py` |
| LLM | "kpalabz direto" | Anthropic direto via `llm_direct.py` |

**Atenção**: `liam_renderer.py` e `skill_based_renderer.py` não devem ser usados
por nenhum job da pipeline. `vite_react_renderer.py` só pode ser usado pelo
branch explícito `FRALIB_BUILDER_ENGINE=vite_react`.

---

## 16. Endpoints Principais

- `/api/pipeline/*` — iniciar, status, reset, reprocessar, analytics.
- `/api/leads/*` — CRUD, fila, manual, editar site.
- `/api/queue/*` — status e falhas.
- `/api/observability/*` — traces e gargalos.
- `/api/whatsapp/*` — status/conexão.

---

## 17. Top 5 Arquivos para Entender/Alterar a Pipeline

1. **`backend/services/openui_renderer.py`** — gerador canônico de sites.
2. **`backend/services/openui_contracts.py`** — injeta os 7 contratos.
3. **`backend/endpoints/pipeline_orchestrator_service.py`** — coordena 11 fases.
4. **`backend/services/pipeline_phases.py`** — enum canônico de 11 fases.
5. **`backend/core/job_queue.py`** — fila Postgres com `claim_next`, `enqueue`.

**Para validar mudanças**:
- `tests/test_regression_patches.py` — 27 testes unitários.
- `scripts/test_regression.py` — pipeline + validação E2E.

---

## 18. Arquivos Legados e Compatibilidade React/Vite

Em 2026-06-23, o builder React/Vite foi recuperado como compatibilidade
explícita a pedido do usuário. Ele ainda contém monólito e deve ser quebrado
depois. Não promover para padrão sem auditoria, testes e decisão explícita.

| Arquivo | Estado |
|---|---|
| `backend/services/vite_react_renderer.py` | Renderer Vite/React recuperado como compat explícito; ainda monolítico e precisa ser quebrado |
| `backend/services/vite_renderer_models.py` | Compat React/Vite |
| `backend/services/vite_build_executor.py` | Compat React/Vite |
| `backend/services/vite_config.py` | Compat React/Vite |
| `backend/services/vite_config_helpers.py` | Compat React/Vite |
| `backend/services/vite_facts.py` | Compat React/Vite |
| `backend/services/vite_file_extractor.py` | Compat React/Vite |
| `backend/services/vite_modules.py` | Compat React/Vite |
| `backend/services/vite_prompts.py` | Compat React/Vite |
| `backend/services/vite_templates.py` | Compat React/Vite |
| `backend/services/vite_validator.py` | Compat React/Vite |
| `scripts/test_build_only.py` | Teste órfão do Vite/React |
| `scripts/test_builder_llm_only.py` | Teste órfão do Vite/React |
| `tests/unit/test_vite_config.py` | Teste órfão |
| `tests/unit/test_vite_config_helpers.py` | Teste órfão |
| `tests/unit/test_vite_facts.py` | Teste órfão |
| `tests/unit/test_vite_file_extractor.py` | Teste órfão |
| `tests/unit/test_vite_renderer_models.py` | Teste órfão |
| `tests/unit/test_vite_validator.py` | Teste órfão |

**Caminho padrão**: `backend/services/openui_renderer.py`.
**Compat explícito**: `FRALIB_BUILDER_ENGINE=vite_react`.
**Fallback de segurança**: se `vite_react` falhar, `backend/services/builder_worker.py`
registra `engine=openui_fallback`, grava `builder-render.json` com
`failed_openui_fallback` e publica HTML OpenUI.

**Arquivos mantidos por compatibilidade** (não usados no caminho canônico, mas
mantidos para evitar imports quebrados em outros módulos):
- `backend/services/pipeline_renderer_support.py` — nome herdado, mas o conteúdo
  é apenas suporte de publicação (classificação de erros, persistência de HTML
  que falhou, cálculo de job_id). **Não é renderização**.

---

## 20. Inventário Definitivo de "Agentes" (e o que NÃO é agente)

**Pergunta frequente**: "quantos agentes inteligentes a gente tem?". A resposta honesta é **5 usam LLM de verdade, 6 são contratos determinísticos**, distribuídos em **206 arquivos `.py` no backend** (74 só em `agents/`). Esta seção acaba com a confusão "74 agentes" vs "agentes de IA".

### 20.1 Os 11 Módulos "Agentes" (1 por fase da pipeline)

| # | Módulo | Fase | Função real | Usa LLM? | Auto-melhora? | Sinais |
|---|---|---|---|---|---|---|
| 1 | `utils/agente1_hunter_v2.py` | 1 | Scraper Google Maps | ❌ Não | ❌ | 0/8 |
| 2 | `agents/caio.py` | 2 | Scorer determinístico de lead | ❌ Não | ❌ | 0/8 |
| 3 | `utils/jina_intelligence.py` | utils | Análise Jina (web scraping + LLM) | ✅ Sim (chama `call_claude`) | ❌ | 0/8 |
| 4 | `agents/agente_nicho.py` | 6 | Briefing do nicho + subnicho | ✅ Sim (1 call/lead) | ⚠️ Memória tier-1 | 1/8 |
| 5 | `agents/agente_variacao.py` | 7 | Ordem de seções + templates | ⚠️ **Só fallback** (template canônico p/ 8 subnichos) | ⚠️ Memória tier-1 | 1/8 |
| 6 | `agents/arquiteto_mestre.py` | 8 | Orquestrador: 1 call própria + delega p/ bloco_estrutura (2 calls) e bloco_copy (4 calls) = **~7 calls/lead** | ✅ Sim (orquestrador LLM, delega 2 helpers) | ⚠️ Tem cache | 1/8 |
| 7 | `agents/site_prompt_agent.py` | 8b | **Re-exporter** de 3 helpers: `prompt_agent_builder` (210L), `prompt_agent_context` (582L), `prompt_agent_helpers` (369L) = 1161 linhas. **NÃO é vazio** — é o **ponto de entrada canônico** que monta o `builder_prompt` antes do OpenUI | ❌ Não chama LLM (monta string) | ❌ | 0/8 |
| 8 | `agents/sdr_langgraph/agent.py` | 11 | FSM do Franz (WhatsApp) | ✅ Sim (2 calls/turno) | ✅ **Tem** feedback/learning | 2/8 |
| 9 | `services/openui_renderer.py` | 9 | Gera HTML do site | ✅ Sim (1 call/site — **90% do custo LLM**) | ✅ Tracing | 1/8 |
| 10 | `agents/html_quality_gate.py` | 9b | QA determinístico (regex+lxml) | ❌ | ❌ | 0/8 |
| 11 | `agents/html_builder_repair.py` | 9b | Reparos de string surgery | ❌ | ⚠️ Tracing + prompt version | 2/8 |

**"Sinais" = 8 sinais de inteligência**: cache, feedback loop, métricas, DB próprio, tracing, prompt versionado, auto-teste, memória persistente. SDR é o único com 2/8.

### 20.2 Onde ESTÁ a inteligência hoje (infra de aprendizado já existe)

Já existe a infraestrutura base de agentes auto-melhorantes — só falta plugar mais agentes:

| Componente | O que faz | Localização |
|---|---|---|
| **agent_memory.py** | Sistema de memória 3-tier (Core/Warm/Cold estilo MemGPT/Letta) | `backend/agent_memory.py` (146 linhas) |
| **pipeline_learning.py** | "Active learning" lessons injetados em prompts futuros | `backend/agents/pipeline_learning.py` |
| **ACTIVE_LEARNING_AGENTS** | Whitelist: `agente_nicho`, `arquiteto_mestre`, `builder_renderer`, `validador`, `franz` | `pipeline_learning.py:14` |
| **memory_hook.py** | Injeta top-10 Core + top-3 Warm no prompt do Franz | `backend/agents/sdr_langgraph/memory_hook.py` |
| **learning.py** (SDR) | Avalia correções úteis e promove para lessons | `backend/agents/sdr_langgraph/learning.py` |
| **quality_judge.py** | LLM-as-judge (Sonnet avalia saída do Franz) | `backend/agents/sdr_langgraph/quality_judge.py` |
| **turn_tracing.py** | Tracing por turno de conversa | `backend/agents/sdr_langgraph/turn_tracing.py` |
| **memory/cold/<uN>/** | Logs brutos de cada run (filesystem, por tenant) | `backend/memory/u1/franz_lead_*.json` |

**Exemplo real de memória persistida** (`backend/memory/u1/franz_lead_5511999999999.json`):
```json
{
  "nome": "Empresa Teste", "cidade": "Sao Paulo", "segmento": "tech",
  "telefone": "5511999999999", "score_caio": 0, "tier": "STANDARD",
  "_updated_at": "2026-06-21T15:57:00"
}
```

### 20.3 Quais agentes PODEM virar auto-melhorantes (e como)

A maioria dos 11 módulos **NÃO precisa** virar auto-melhorante — são determinísticos por design. Os **5 que usam LLM** são os candidatos. Mapa:

| Agente | Vale auto-melhorar? | Por quê? | Como faria |
|---|---|---|---|
| **Jina** (utils) | ❌ Baixo | Jina é 1 call, e o output alimenta Nicho (que aprende) | Inherited via Nicho |
| **Nicho** (fase 6) | ✅ **Alto** | Briefing define toda a estratégia de site | Adicionar feedback loop: lead→site gerado→aceite/recusa→Nicho aprende |
| **Variação** (fase 7) | ✅ **Alto** | Escolhe template_estrutura e ordem_das_secoes | Coletar métricas "qual template converteu mais" |
| **Arquiteto** (fase 8) | ⚠️ Primeiro vire LLM | É template estático, não agente | Trocar função hardcoded por call_claude + memory |
| **SitePrompt** | 🗑️ Deletar | Arquivo vazio | Remover |
| **SDR (Franz)** (fase 11) | ✅ **Já tem** | Infra de learning já existe | Expandir lessons: usar `quality_judge` p/ classificar respostas |
| **OpenUI** (fase 9) | ✅ **Maior ROI** | 90% do custo LLM, gera o produto final | Memory tier-1 com 10 patterns de ouro (templates_html_que_funcionam) |
| **Quality Gate** | ❌ Não | É guard-rail determinístico | — |
| **Builder Repair** | ❌ Não | É patch fix | — |
| **Caio, Hunter** | ❌ Não | São scraper/score | — |

### 20.4 O que FALTA para serem "agentes de verdade" (estilo Claude Agent SDK)

O Claude Agent SDK tem 4 features que a gente **NÃO tem** ainda:

1. **Tools dinâmicas**: o agente decide em runtime quais tools chamar. A gente tem tools fixos por agente.
2. **Loop autônomo**: o agente continua iterando até objetivo. A gente tem FSM finita.
3. **Sub-agentes**: um agente delega para outro. A gente tem pipeline sequencial.
4. **Memória semântica cross-session**: lessons injetados manualmente. A gente não tem retrieval automático.

**O que é viável AGORA** (com 1 sprint):
- Adicionar `learning.py` ao **OpenUI** (hoje só SDR tem)
- Trocar `arquiteto_mestre.py` de template hardcoded → call_claude + memory
- Adicionar `quality_judge.py` ao Nicho (Sonnet avalia briefing)
- Deletar `site_prompt_agent.py` (vazio)

**O que NÃO vale a pena mexer** (decisão deliberada):
- **html_quality_gate.py** (38 funções determinísticas): validar `og:image existe?`, `data-lgpd-banner presente?`, `<video autoplay muted loop playsinline>?`. Substituir por LLM custaria $0.01-0.05/site, adicionaria 2-8s de latência, perderia determinismo/auditabilidade/idempotência. **Regras objetivas com LLM é regressão disfarçada de inteligência.**
- **html_builder_repair.py** (13 funções de string surgery): consertar `<h2>Im Tema.` (sanitizer), LGPD handler genérico, CSS overflow. Mesma justificativa. LLM aqui seria "achismo" — `</body></html>` é `</body></html>`, não "parece fechamento".

**O que é roadmap (3-6 meses)**:
- Agent SDK nativo: tools dinâmicas, sub-agentes
- RAG semântico em `agent_memory.py` (embeddings + retrieval)
- Auto-fine-tuning (Lora / RLHF) — caro, último passo

### 20.5 Contagem CANÔNICA (referência pra acabar com divergência)

| Métrica | Valor | Onde |
|---|---|---|
| Total de arquivos `.py` no backend | **206** | `find backend -name "*.py"` |
| Arquivos em `backend/agents/` | **74** + 1 package (`sdr_langgraph/`) | `ls backend/agents/*.py` |
| Módulos "agentes" (cérebro) | **11** | Tabela 20.1 |
| Agentes que chamam LLM | **6** (Jina, Nicho, Variação fallback, **Arquiteto orq. + bloco_estrutura + bloco_copy**, OpenUI, SDR) | grep `call_claude(` |
| Agentes determinísticos (contratos) | **5** (Hunter, Caio, SitePrompt vazio, Quality, Repair) | Tabela 20.1 |
| Packages com infra de learning | **2** (`sdr_langgraph/` + `memory_hook_site.py`) | v1.1-baseline-2026-06-23 |
| Custo LLM dominado por 1 agente | **~70% OpenUI** (Arquiteto ~20% via bloco_*, Nicho/SDR/Jina ~10%) | Análise de chamadas |
| Whitelist de learning agents | **5** nomes | `pipeline_learning.py:14` |
| Agentes com memory_hook plugado | **5** (franz, nicho, arquiteto, builder, validador) | Sprint 0+1 (v1.1) |

**Não diga "temos 74 agentes"**. Diga: **"temos 11 módulos-agente, dos quais 5 usam LLM, e o OpenUI domina 90% do custo de IA"**.

**Mudanças v1.1-baseline-2026-06-23** (Sprint 0 + Sprint 1):
- memory_hook plugado em **5 agentes whitelisted** (Nicho, Arquiteto, Builder, Validador, Franz)
- Validador LLM reintroduzido no orchestrator com `score: float 0-10` em `ValidacaoResultado`
- Race condition em `agent_memory._salvar()` mitigada com `threading.Lock` (intra) + `fcntl.flock` (inter)
- Feedback loop Nicho↔Validador: briefing entra em Warm com score como multiplicador de confianca
- Dreamer daemon agendado via PM2 (`fralib-dreamer`, cron 3h BRT)
- `llm_config.AGENT_MODEL_MAP` sincronizado com overrides reais (Sonnet primário Nicho/Variação)

---

## 19. Onboarding Rápido

1. Ler este `AGENTS.md` inteiro.
2. Rodar `python pipeline.py smoke --dry-run`.
3. Rodar `pytest tests/test_regression_patches.py` (deve dar 27/27).
4. Inspecionar `docs/ONE_TRUTH_CANONICAL_STATE.md` para entender estado canônico.

---

**Conta de linhas**: este arquivo tem ~570 linhas (vs 524 anteriores) — adição da seção 20 (Inventário Definitivo de Agentes).
