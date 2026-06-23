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

**A Pipeline canônica é o ÚNICO caminho para gerar sites na FraLib.**

- Todo site gerado pela FraLib passa pelas **11 fases canônicas** (seção 4).
- O gerador de site é **OpenUI** (seção 5). Não existe outro caminho.
- Sites publicados SEM passar pela pipeline são considerados **legado** e devem ser migrados.

Qualquer pessoa (humana ou IA) que tentar:
- Editar HTML direto
- Chamar OpenUI fora do pipeline
- Usar renderers legados (`vite_react_renderer`, `liam_renderer`, `skill_based_renderer`)
- Adicionar novo "modo" de geração de site

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
| **Gerador de site** | **OpenUI** (único) | `backend/services/openui_renderer.py` | **Fase 9 — renderiza HTML** |
| Contratos OpenUI | 7 contratos injetados | `backend/services/openui_contracts.py` | SEO, design, motion, A11y, factual, LGPD, deploy |
| Fila/Locks | PostgreSQL | `backend/core/job_queue.py` + tabela `public.jobs` | Tabela canônica de jobs |
| Builder Worker | Python daemon | `backend/services/builder_worker.py` | **Dispara `render_openui_site`** |
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
| **9** | **Gerando site no OpenUI...** | **`builder_renderer`** | **`render_openui_site` (ÚNICO)** | Haiku→Sonnet | **`services/openui_renderer.py`** |
| **9b** | **Validando HTML...** | **`quality_gate`** | **`audit_generated_html` (loop ≤ 3 retries)** | N/A | **`agents/html_quality_gate.py`** |
| 10 | Publicando site... | `deploy` | `publish_rendered_site` | N/A | `endpoints/pipeline_phase_helpers.py` |
| 11 | Enviando contato... | `franz` | SDR LangGraph | Sonnet | `services/pipeline_executors.py` + `agents/sdr_langgraph/compat.py` |

**Ordem real de execução**: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 9b → 10 → 11.
**Obrigatório**: todas as 11 fases devem rodar em sequência. Não há atalhos em produção.

---

## 6. OpenUI: O Único Gerador de Site

### 6.1 Decisão arquitetural (a fonte da verdade)

A FraLib usa **OpenUI como motor ÚNICO de geração de sites**. OpenUI é um contrato
de UI generation: um system prompt compacto pede ao LLM que retorne HTML Tailwind
pronto para renderizar. A FraLib mantém isso in-process — não precisa de servidor
externo, sessão de browser, build Node ou Sandbox.

**Importante**: NÃO existe motor alternativo. Versões legadas como
`vite_react_renderer.py`, `liam_renderer.py`, `skill_based_renderer.py` existem
no código apenas por compatibilidade de imports, mas **NÃO devem ser usados**.
Nenhum job da pipeline canônica deve chamá-los.

### 6.2 Como o OpenUI produz um site

1. `backend/services/builder_worker.py` recebe o brief do Arquiteto Mestre.
2. **SEMPRE** chama `render_openui_site()` em `backend/services/openui_renderer.py:84`.
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

### 6.3 Por que OpenUI é o único caminho

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
- Teste unitário: `tests/test_regression_patches.py` (27 testes).
- Teste E2E: `scripts/test_regression.py` (roda pipeline + valida site).
- CI: rodar `pytest tests/test_regression_patches.py` em todo PR.

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
| Gerador de site | "Vite/React", "Skill Renderer" | **OpenUI** (único) |
| Orquestrador | `pipeline_endpoints.py` | `pipeline_orchestrator_service.py` |
| Runtime | PM2 | **systemd** (5 serviços) + ServiceManager |
| Fase 11 SDR | "Bryan" | **Franz** (sdr_langgraph) |
| WhatsApp | "meowhats" | **whatsmeow** (externo, porta 3001) |
| Renderer HTML | `skill_based_renderer.py`, `liam_renderer.py`, `vite_react_renderer.py` | `openui_renderer.py` (ÚNICO) |
| LLM | "kpalabz direto" | Anthropic direto via `llm_direct.py` |

**Atenção**: arquivos `vite_react_renderer.py`, `liam_renderer.py`,
`skill_based_renderer.py` existem no código mas **não devem ser usados** por
nenhum job da pipeline. Se encontrar imports desses arquivos em código novo,
**rejeitar** o PR.

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

## 18. Onboarding Rápido

1. Ler este `AGENTS.md` inteiro.
2. Rodar `python pipeline.py smoke --dry-run`.
3. Rodar `pytest tests/test_regression_patches.py` (deve dar 27/27).
4. Inspecionar `docs/ONE_TRUTH_CANONICAL_STATE.md` para entender estado canônico.

---

**Conta de linhas**: este arquivo tem ~440 linhas (vs 524 anteriores) — consolidação removeu redundâncias.
