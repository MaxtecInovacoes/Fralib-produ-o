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
- O gerador padrão de site é **Vite/React** (seção 5).
- `openui` existe como rota alternativa quando `FRALIB_BUILDER_ENGINE=openui`.
- **Fail-fast total**: Se qualquer fase da geração falhar, levanta exceção clara.
  Não usa fallbacks genéricos ("FraLib Site", templates universais).
- Em produção, `FRALIB_STRICT_CANONICAL_PUBLISH=1` ou `FRALIB_ENV=prod`
  fazem a publicação falhar fechado se o artefato final não estiver marcado
  como `vite_react`.
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
  publica, remove processos PM2 legados que tenham equivalente systemd
  (`fralib`, `fralib-worker`, `fralib-franz-worker`, `fralib-bryan-worker`,
  `fralib-wpp-listener`, `fralib-hermes-watchdog`) e reinicia todos os serviços
  systemd (`fralib-api`, `fralib-worker`, `fralib-worker@*.service`,
  `fralib-franz`, `fralib-wpp-listener`, `fralib-hermes`).
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
| **Gerador de site PADRÃO** | **Vite/React** | `backend/services/vite_react_renderer.py` | **Fase 9 — renderiza TSX** |
| **Gerador alternativo** | **OpenUI** | `backend/services/openui_renderer.py` | **Fase 9 — HTML Tailwind** |
| Contratos Vite/React | Contratos injetados | `backend/services/vite_react_renderer.py` + `DESIGN.md` | SEO, design, motion, A11y, factual, LGPD, deploy |
| Fila/Locks | PostgreSQL | `backend/core/job_queue.py` + tabela `public.jobs` | Tabela canônica de jobs |
| Builder Worker | Python daemon | `backend/services/builder_worker.py` | **Dispara Vite/React PADRÃO ou OpenUI alternativo** |
| Quality Gate | Determinístico (não pula) | `backend/agents/html_quality_gate.py` | **Fase 9b — valida HTML** |
| LLM | Anthropic direto | `backend/agents/llm_direct.py` | Cascata Haiku→Sonnet→Opus (fail-fast se todos falham) |
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
| **9** | **Gerando site...** | **`builder_renderer`** | **`render_vite_react_site` PADRÃO / `render_openui_site` alternativo** | Haiku→Sonnet→Opus | **`services/vite_react_renderer.py` / `services/openui_renderer.py`** |
| **9b** | **Validando HTML...** | **`quality_gate`** | **`audit_generated_html` (loop ≤ 3 retries)** | N/A | **`agents/html_quality_gate.py`** |
| 10 | Publicando site... | `deploy` | `publish_rendered_site` | N/A | `endpoints/pipeline_phase_helpers.py` |
| 11 | Enviando contato... | `franz` | SDR LangGraph | Sonnet | `services/pipeline_executors.py` + `agents/sdr_langgraph/compat.py` |

**Ordem real de execução**: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 9b → 10 → 11.
**Obrigatório**: todas as 11 fases devem rodar em sequência. Não há atalhos em produção.

---

## 6. Vite/React: Gerador Padrão de Site

### 6.1 Decisão arquitetural (a fonte da verdade)

A FraLib usa **Vite/React como motor PADRÃO de geração de sites**.
Vite/React gera componentes TSX que são compilados pelo Studio FraLib.
OpenUI (`openui_renderer.py`) existe como **rota alternativa** quando
`FRALIB_BUILDER_ENGINE=openui` — mas **NÃO é mais o padrão**.

**Importante**: `vite_react_renderer.py` é o motor PADRÃO.
`liam_renderer.py` e `skill_based_renderer.py` continuam proibidos.

### 6.2 Como o Vite/React produz um site

1. `backend/services/builder_worker.py` recebe o brief do Arquiteto Mestre.
2. Por padrão chama `render_vite_react_site()` em `backend/services/vite_react_renderer.py`.
   Se `FRALIB_BUILDER_ENGINE=openui`, chama `render_openui_site()` (rota alternativa).
3. O renderer monta o system prompt injetando os **7 contratos**:
   1. **SEO Framework** por nicho
   2. **Design System** (cores, fontes, espaçamentos)
   3. **Motion Contract** (parallax/reveal/GSAP via data-attributes)
   4. **A11y Contract** (skip link, main, contraste AA, prefers-reduced-motion)
   5. **Factual Contract** (JSON-LD + section data-fralib-contract)
   6. **LGPD personalizado** (segmento-aware)
   7. **Deploy Rules** (Tailwind CDN, links wa.me/tel:, sem iframes/scripts)
4. **LLM Cascade**: **Haiku** primário → **Sonnet** fallback → **Opus 4.8** se necessário.
5. **Fail-fast**: Se TODOS os modelos falharem, levanta `ViteReactRenderError`.
   Não há fallback genérico.
6. **Patches determinísticos** (46 patches — ver seção 7) são aplicados.
7. **Quality Gate** valida em loop ≤ 3 retries.
8. Deploy publica em `/var/www/fralib/sites/<tenant_id>/<lead_slug>/`.

### 6.3 Por que Vite/React é o caminho padrão

| Critério | Vite/React |
|---|---|
| Qualidade | Componentes TSX compilados |
| Customização | Variação 4-eixos + 6 archetypes |
| Custo | Previsível (cascata de modelos) |
| Quando usar | **100% dos sites FraLib** |

---

## 6.2 Fail-Fast: Comportamento de Erro

### Filosofia

> "Se a geração falhar, deve falhar com erro claro — nunca publicar site genérico."

### O que NÃO é mais aceito

| Antes (FALLBACK) | Agora (FAIL-FAST) |
|---|---|
| Studio fallback determinístico | Erro claro (`ViteReactRenderError`) |
| Site genérico "FraLib Site" | Exceção com diagnóstico |
| openui_fallback automático | Fail-fast em ambos engines |
| retry infinito | Retry controlado + fail-fast |

### Cascata LLM (Vite/React)

```
Haiku → Sonnet → Opus 4.8
   ↓         ↓         ↓
(ok)     (ok)      (ok)
   └─────────┴─────────┴──→ Sucesso
             
(erro)  (erro)    (erro)
   └─────────┴─────────┴──→ ViteReactRenderError ❌
```

### Arquivos que implementam fail-fast

| Arquivo | Comportamento |
|---------|---------------|
| `vite_react_renderer.py` | `ViteReactRenderError` se cascade falhar |
| `openui_renderer.py` | `OpenUIRenderError` se HTML vazio/inválido |
| `builder_worker.py` | Erro sobe, não cai para fallback |
| `bloco_copy.py` | `CopyGenerationError` após retry |
| `bloco_estrutura.py` | `EstruturaInvalidaError` se parse falhar |

### Fallbacks Técnicos Aceitos

Estes fallbacks são **técnicos**, não de produto:

| Arquivo | Fallback | Justificativa |
|---------|----------|---------------|
| `parse_bloco*_with_fallback` | JSON→Markdown→JSON | Parsing robusto |
| `lead_lock.py` | Redis→threading | Lock local se Redis offline |
| `agent_memory.py` | Windows sem flock | Compatibilidade |

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
- Tenant ilimitado remove trava comercial/cooldown, mas **não** libera duas
  pipelines de site simultâneas para o mesmo tenant. A regra canônica é: vários
  tenants podem rodar em paralelo; o mesmo tenant roda pipeline de site em série.
- Ordem de claim operacional: `pipeline_*` primeiro, depois
  `lead_production_tick`, `lead_supply_caio`, `lead_supply_hunter` e só então
  `franz_outreach`/`bryan_outreach`. Jobs antigos de SDR não podem bloquear
  abastecimento de leads nem geração de sites.
- Lead Supply é contínuo e independente da publicação: `sync_supply()` deve
  recuperar itens `raw`/`error_retry` para o Caio mesmo quando não há pipeline
  ativa, e `_enqueue_caio()` deve reabrir job Caio falhado com a mesma
  idempotência em vez de silenciar conflito.
- Franz reconcile só cria job quando não existe nenhum `franz_outreach` para o
  lead. Ele **não** reabre `failed_permanent` automaticamente; retry de contato
  é ação explícita. `watchdog_blocked/max_2_messages_without_response` significa
  lead já contatado sem resposta e não deve virar falha de pipeline nem novo
  disparo WhatsApp.
- A conexão Postgres deve usar `client_encoding=UTF8`. `LATIN1` quebra jobs
  com payload/erro contendo acentos, travessão ou dados reais de empresas.
- Backoff: 30/120/480s padrão; 60-960s para `franz`/`bryan`.
- `reap_dead_workers` reseta jobs com heartbeat > 5 min.

---

## 10. Runtime: systemd (canônico)

Serviços systemd:
- `fralib-api` (porta 8000) — 1G RAM / 150% CPU
- `fralib-worker` — 2G RAM / 200% CPU
- `fralib-worker@N` — instâncias paralelas opcionais do worker; se estiverem
  ativas, o deploy deve reiniciar todas junto com `fralib-worker`.
- `fralib-franz` — 512M RAM / 100% CPU
- `fralib-wpp-listener` — 512M RAM / 100% CPU
- `fralib-hermes` — 256M RAM / 50% CPU

`whatsmeow` é externo (porta 3001).

PM2 não pode rodar serviços que já têm unit systemd (`fralib`,
`fralib-worker`, `fralib-franz-worker`, `fralib-bryan-worker`,
`fralib-wpp-listener`, `fralib-hermes-watchdog`). O `post-receive` deve
removê-los antes de reiniciar systemd; caso contrário API, WhatsApp, Hermes ou
jobs podem ser processados por código antigo em memória.

**Regra**: usar `backend/services/service_manager.py` (abstração canônica).

---

## 11. Deploy

1. Editar em `C:\fralib`.
2. `git add` → `git commit` (bloqueado por pre-commit hook se houver secrets).
3. `git push origin master` para `root@100.101.18.1:/root/repos/fralib`.
4. Hook canônico: `scripts/post-receive` valida, publica, remove workers PM2
   legados e reinicia todos os workers systemd, inclusive `fralib-worker@N`.

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
| `keyword_cache` | Postgres | por `tenant_id::segmento` ✓ |
| `jina_cache` | arquivo | por `tenant_id+nicho+cidade` ✓ |
| `design_director_cache` | `/tmp` | **global** |
| `unsplash_cache` | arquivo | **global** |
| `pexels_cache` | arquivo | **global** |
| `prd_cache` | arquivo | **global** |
| `leads_cache` | Postgres | por `user_id` ✓ |
| `pipeline_checkpoint` | arquivo | por `pipeline_id` ✓ |

**Ação obrigatória**: 4 caches globais ainda precisam ganhar `user_id`/`tenant_id`
na chave (`design_director_cache`, `unsplash_cache`, `pexels_cache`, `prd_cache`).

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

### 16.1 UI canônica

- `admin.html` é a única UI operacional canônica para tenants e usuários novos.
- `/admin` deve redirecionar para `/admin.html`.
- `/dashboard` e `/dashboard.html` são legado e devem redirecionar para
  `/admin.html`, preservando querystring.
- `dashboard.html` não deve ser publicado em `/var/www/fralib`; o deploy deve
  remover a cópia legada se ela existir.
- `/login.html` deve redirecionar para `/login`, preservando querystring.
- `/planos.html` deve redirecionar para `/planos`, preservando querystring.
- Emails, checkout, onboarding, login e cadastro não devem criar links novos
  para `/dashboard` ou `/dashboard.html`.
- Novos usuários devem nascer com `config_pipeline` e `lead_supply_config`
  criados, para reduzir divergência operacional entre tenants.

---

## 17. Top 5 Arquivos para Entender/Alterar a Pipeline

1. **`backend/services/vite_react_renderer.py`** — gerador canônico de sites.
2. **`DESIGN.md` + `backend/services/vite_react_renderer.py`** — contrato visual raiz e injeção do builder Vite/React.
3. **`backend/endpoints/pipeline_orchestrator_service.py`** — coordena 11 fases.
4. **`backend/services/pipeline_phases.py`** — enum canônico de 11 fases.
5. **`backend/core/job_queue.py`** — fila Postgres com `claim_next`, `enqueue`.

**Para validar mudanças**:
- `tests/test_regression_patches.py` — 27 testes unitários.
- `scripts/test_regression.py` — pipeline + validação E2E.

---

## 18. Arquivos do Builder Vite/React

Vite/React é o builder canônico. Alguns arquivos ainda carregam nomes herdados
como `fallback` por compatibilidade interna, mas isso não autoriza fallback de
produto nem publicação OpenUI automática quando Vite falha.

| Arquivo | Estado |
|---|---|
| `backend/services/vite_react_renderer.py` | Renderer canônico Vite/React; ainda monolítico e deve ser quebrado por módulos menores |
| `backend/services/vite_renderer_models.py` | Tipos/resultado do renderer Vite/React |
| `backend/services/vite_build_executor.py` | Instala/build/teste do projeto Vite |
| `backend/services/vite_config.py` | Configuração do builder Vite |
| `backend/services/vite_config_helpers.py` | Helpers de config |
| `backend/services/vite_facts.py` | Normalização factual do lead |
| `backend/services/vite_file_extractor.py` | Extração/validação de arquivos gerados |
| `backend/services/vite_modules.py` | Dependências e módulos do sandbox |
| `backend/services/vite_prompts.py` | Prompt/contrato do builder Vite |
| `backend/services/vite_templates.py` | Templates auxiliares Vite |
| `backend/services/vite_validator.py` | Validação do projeto Vite |
| `scripts/test_build_only.py` | Teste órfão do Vite/React |
| `scripts/test_builder_llm_only.py` | Teste órfão do Vite/React |
| `tests/unit/test_vite_config.py` | Teste órfão |
| `tests/unit/test_vite_config_helpers.py` | Teste órfão |
| `tests/unit/test_vite_facts.py` | Teste órfão |
| `tests/unit/test_vite_file_extractor.py` | Teste órfão |
| `tests/unit/test_vite_renderer_models.py` | Teste órfão |
| `tests/unit/test_vite_validator.py` | Teste órfão |

**Caminho padrão**: `backend/services/vite_react_renderer.py`.
**Rota alternativa explícita**: `FRALIB_BUILDER_ENGINE=openui`.
**Fail-fast**: se `vite_react` falhar, o job falha com erro claro. Não deve
publicar HTML OpenUI automático para mascarar o erro.

**Variação visual React/Vite**: no modo `creative_plan`, a LLM escolhe apenas
campos de um contrato JSON barato; ela não escreve React/CSS livre. Quando o
contrato não trouxer `visual_lane`, o Studio React deve preencher
deterministicamente a variação por lead antes de resolver tema/blocos. O
`blockPlan` resolvido é a fonte única para hero, about, serviços, reviews,
galeria, FAQ, localização e CTA; componentes não devem voltar a ler defaults
crus de `variation` quando o `blockPlan` já existe.

Desde 2026-06-29, o Studio React também aplica um **diversity planner** antes
do tema: cada lane resolve um pacote coerente de `hero_layout`, `section_order`,
`about_variant`, `services_variant`, `reviews_variant`, `gallery_density`,
`cta_style`, superfície, tipografia e motion. Paletas de lane vencem paletas
genéricas do upstream, salvo quando `palette_locked`/`brand_palette_locked` ou
`color_palette.locked=true` estiverem presentes. Conteúdo essencial não pode
nascer com `opacity: 0`; motion deve animar sem deixar seções invisíveis em QA,
SEO screenshot ou headless full-page capture.

Desde 2026-06-29, o Studio React deve materializar a variação no código
gerado: `motion_mix` precisa virar classe/atributo/CSS reais, LGPD deve usar
tokens do tema (`--bg`, `--accent`, `--text`) em vez de cor padrão fixa, e
fallback de superfície clara não pode misturar vermelho com branco gerando bloco
salmão genérico. Se uma animação for planejada mas não houver elemento compatível
no bloco escolhido, ela não conta como entregue.

Desde 2026-07-01, o caminho oficial promove `copy_only`/políticas antigas para
`creative_plan` no worker canônico, normaliza bases Anthropic antigas
`api.aibee.cloud` para `https://api.kpalabz.com/v1`, e materializa os polos
líquidos no wrapper do app (`data-pole`) para que hero, seções, planos, LGPD e
CTAs herdem a mesma geometria/cor/tipografia. O polo `bold` deve sair com
superfícies sólidas, alto contraste e sem glass padrão em cards críticos.

Desde 2026-07-01, `LocationSection` do Studio React deve renderizar **um único
iframe real do Google Maps** quando houver endereço ou `maps_url`; o link externo
deve abrir no Google Maps e mapas duplicados continuam bloqueados pelo Quality
Gate. Keywords SEO devem incluir intenção local/regional (`perto de mim`,
`agendar`, `preço`, `WhatsApp`, bairro/cidade), não só termos de volume. O CSS
líquido pode usar overlap entre seções, mas **nunca** deve sobrepor a seção que
vem logo após `#stats`; cidades longas precisam quebrar linha sem cortar texto.

Desde 2026-07-02, o caminho `creative_plan` precisa materializar todos os tokens
líquidos escolhidos pela LLM (`aesthetic_mode`, `spacing_density`,
`typography_scale`, `motion_intensity`, `hero_layout`, variantes de bloco,
superfícies e `motion_mix`) no `blockPlan` final. O prompt Vite injeta
`DESIGN.md` como contrato visual raiz. O resolvedor visual cobre 13 famílias
canônicas (`academia`, `advogado`, `barbearia`, `clinica`, `dentista`,
`energia_solar`, `estetica`, `imobiliaria`, `nutricionista`, `oficina`,
`pet_shop`, `restaurante`, `salao`) e o `agente_variacao` cobre 22 subnichos
mapeados, todos com `hero`, `faq`, `contato` e `footer`. Teste canônico:
`tests/test_vite_liquid_contract.py`.

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
| 5 | `agents/agente_variacao.py` | 7 | Ordem de seções + templates | ⚠️ **Só fallback** (template canônico p/ 22 subnichos) | ⚠️ Memória tier-1 | 1/8 |
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

## 21. Sprints SDK 5/6/7/8/9 — Salto de Maturidade (2026-06-24 → 2026-06-25)

> **Resumo executivo**: em 2 dias, a FraLib fechou **13/13 sinais SDK** do
> roadmap definido no Sprint 0. Este bloco documenta **o que existe HOJE**,
> **como ativar** cada feature e **o que ganhamos** com isso.

### 21.1 O que foi entregue (5 sprints, 13 sinais SDK)

| Sprint | Versão | Tema | Sinal SDK | Custo |
|---|---|---|---|---|
| 5 | v1.8 | Tracing dos 4 agentes | Observabilidade | $0 (opt-in) |
| 6 | v1.9 | Sub-agentes por estética | Sub-agentes | $0 (templates) |
| 7 | v1.10 | RAG Templates (embeddings 64d) | RAG semântico | $0 (hash) |
| 8 | v1.11 | Auto-melhoria via traces | Auto-melhoria | $0 (gate conservador) |
| 9 | v1.12 | Edge cases + production hardening | Resiliência | $0 (helpers) |

**Cobertura de testes**: 130/130 verde (era 76 antes dos 5 sprints).
**Pre-commit hook**: 21 checks ativos (era 8 antes).
**Documentação nova**: `docs/ROLLOUT_SPRINT_5.md`, `docs/ROLLOUT_SPRINT_6.md`,
`docs/ROADMAP_SPRINTS_5_6_7_8_9.md`.

### 21.2 Sprint 5 — Tracing (v1.8)

**O que**: `backend/services/tracing.py` + 4 endpoints SuperAdmin JSON.

```bash
# Ativar (VPS)
FRALIB_TRACING=1

# Inspecionar
curl http://localhost:8000/api/admin/tracing/summary
# {"enabled":true, "total_traces":42, "total_cost_usd":0.12, "agents":{...}}
```

**Ganho**: debug time -93% (de ~30min para ~2min), custo LLM rastreado por
agente, latência p95 visível.

### 21.3 Sprint 6 — Sub-agentes por Estética (v1.9)

**O que**: 6 sub-agentes + router + mapping nicho → estética.

| Nicho | Estética |
|---|---|
| academia_crossfit | BOLD_ENERGY (dark + neon) |
| barbearia_premium | EDITORIAL (serif + bento) |
| restaurante_familiar | KINETIC (vibrant + shimmer) |
| saas_premium | IMMERSIVE_3D (R3F hero) |
| default | MINIMAL |

```python
from backend.agents.sub_agent_router import route_to_sub_agent
html = route_to_sub_agent("BOLD_ENERGY", prd, facts)
```

**Ganho**: latência -99.98% (10-30s → 5ms), custo -100% ($0.003 → $0),
variedade visual +500% (1 → 6 estilos Awwwards).

### 21.4 Sprint 7 — RAG Templates (v1.10)

**O que**: `backend/services/template_embeddings.py` com embeddings 64d
para matching semântico nicho ↔ template.

```bash
# Ativar (VPS)
FRALIB_USE_TEMPLATE_RAG=1
```

**Ganho**: auto-seleção de estética sem LLM, cold-start coberto
(embedding vazio → fallback `default`).

### 21.5 Sprint 8 — Auto-melhoria (v1.11)

**O que**: traces do dia anterior alimentam v2 do prompt automaticamente,
se a performance melhorar ≥ 5% em ≥ 10 samples (gate conservador).

```bash
# Ativar (VPS)
FRALIB_AUTO_IMPROVE=1
# Endpoints: /api/admin/prompts/list, /get, /apply, /rollback
```

**Ganho**: evolução automática de prompts com rollback seguro. Tempo
até improvement cai de semanas para dias.

### 21.6 Sprint 9 — Edge Cases + Hardening (v1.12)

**O que**: `backend/services/edge_cases.py` com 8 hardenings:
`safe_write_file`, `safe_jsonl_iter`, `safe_dict_get`, `truncate_for_log`,
`rate_limit_check`, `tenant_isolation_guard`, `circuit_breaker`,
`health_snapshot`.

**Ganho**: zero-downtime em disco cheio, self-healing em LLM 5xx,
anti-vazamento cross-tenant.

### 21.7 Como o sistema funciona HOJE (visão unificada)

```
[Lead] → Hunter → Caio → Jina → Nicho → Variação → Arquiteto
                                              ↓
                          [Builder — Vite/React + Studio React]
                                              ↓
                                       QA → Deploy → Franz (SDR)
                                              ↓
                            [Tracing dos 4 agentes (Sprint 5)]
                                              ↓
                            [Auto-melhoria → prompts v2 (Sprint 8)]
                                              ↓
                            [Edge cases protegem tudo (Sprint 9)]
```

### 21.8 Onde a documentação completa vive

| Doc | O que tem |
|---|---|
| `docs/ROLLOUT_SPRINT_5.md` | Tracing: estratégia 4 fases, smoke VPS, comandos |
| `docs/ROLLOUT_SPRINT_6.md` | Sub-agentes: API, mapping, ROI, rollout |
| `docs/ROADMAP_SPRINTS_5_6_7_8_9.md` | Visão unificada dos 5 sprints + ROI acumulado |

### 21.9 ROI acumulado (Sprints 5-9)

| Métrica | Antes | Depois | Delta |
|---|---|---|---|
| Latência média render | 10-30s (LLM) | **5ms** (template) | **-99.98%** |
| Custo por site | $0.003 | **$0** | **-100%** |
| Debug time | 30min | **2min** | **-93%** |
| Variedade visual | 1 genérico | **6 Awwwards** | **+500%** |
| Sinais SDK | 4/13 | **13/13** | **+225%** |
| Cobertura testes | 76 | **130** | **+71%** |
| Pre-commit checks | 8 | **21** | **+162%** |

### 21.10 Caminho futuro (Sprint 10+)

- **Sprint 10**: Dashboard visual (substituir botões JSON por gráficos)
- **Sprint 11**: LangSmith cloud (rastreamento premium)
- **Sprint 12**: Multi-agentes conversando (debate Nicho ↔ Arquiteto)
- **Sprint 13**: A/B test de sub-agentes com métricas reais
- **Sprint 14**: Auto-fine-tuning (LoRA / RLHF) — caro, último passo

---

## 22. Sprints 11-12 — Migração Vite/React + 26 Segmentos + Caroço Rico (2026-06-25)

> Esta seção **SUBSTITUI** a visão anterior de que OpenUI é o "único gerador".
> A partir do Sprint 12.9, **Vite/React é o engine padrão** e OpenUI é apenas
> fallback. O sistema produz sites React/Vite de alta qualidade, com 26
> segmentos cobertos e briefing real do lead injetado no caroço.

### 22.1 Nova arquitetura: Vite/React como engine padrão

| Aspecto | Antes (até Sprint 12.8) | Depois (Sprint 12.9+) |
|---|---|---|
| Engine padrão | OpenUI (HTML estático) | **Vite/React** (componentes) |
| Tailwind v4 | CDN inline classes | **Build Vite real** |
| Frameworks | Apenas HTML+JS | **React 18 + Vite 6 + shadcn/ui** |
| GSAP / Lenis / Motion | via motion_runtime.js | **GSAP + Lenis + Framer Motion** |
| OpenUI | engine único | rota alternativa explícita (`FRALIB_BUILDER_ENGINE=openui`) |
| Dependências | Zero build | shadcn/ui, GSAP, Lenis, framer-motion |
| Build time | ~10s (OpenUI) | ~30s (Vite/React com build) |
| Quality | HTML 1 arquivo | **Vite projeto completo (10+ TSX)** |
| Deploy | copia HTML | copia `dist/` (HTML + assets) |

### 22.2 Os 26 Segmentos do Studio React Determinístico

O `vite_react_renderer.py:_generate_studio_fallback_files()` tem um
**mapa segment-aware** com 26 nichos. O nome da função é legado; no caminho
canônico ela é o Studio React determinístico. Cada segmento gera svc_labels
customizadas, hero_desc, CTAs, lifestyle_title, nav_items, etc.

| # | Segmento | CTA primário | Cards típicos |
|---|---|---|---|
| 1 | barbearia | Agendar horario | Corte, Barba, Sobrancelha |
| 2 | barbearia_premium | Agendar horario | Corte, Barba, Pigmentacao |
| 3 | academia | Comecar treino | Musculacao, Funcional |
| 4 | crossfit | Comecar treino | WOD, Halterofilismo |
| 5 | musculacao | Comecar treino | Musculacao, Funcional |
| 6 | fitness | Comecar treino | Musculacao, Funcional |
| 7 | restaurante | Fazer reserva | Pratos, Menu, Delivery |
| 8 | pizzaria | Fazer pedido | Pizzas, Bebidas |
| 9 | hamburgueria | Fazer pedido | Hamburgueres, Porcoes |
| 10 | lanchonete | Fazer pedido | Lanches, Bebidas |
| 11 | bar | Ver cardapio | Drinks, Cervejas |
| 12 | cafeteria | Ver cardapio | Cafes, Salgados |
| 13 | clinica | Agendar consulta | Consulta, Tratamento |
| 14 | estetica | Agendar horario | Tratamentos, Estetica |
| 15 | dermatologia | Agendar consulta | Consulta, Procedimentos |
| 16 | psicologia | Agendar sessao | Terapia, Diagnostico |
| 17 | fisioterapia | Agendar sessao | RPG, Acupuntura |
| 18 | imobiliaria | Ver imoveis | Venda, Locacao |
| 19 | nutricionista | Agendar consulta | Plano alimentar |
| 20 | advocacia | Falar com advogado | Consulta, Contratos |
| 21 | dentista | Agendar consulta | Limpeza, Implante |
| 22 | petshop | Agendar servico | Banho, Tosa |
| 23 | hotel | Reservar | Quartos, Cafe |
| 24 | salao_beleza | Agendar horario | Corte, Coloracao |
| 25 | oficina | Agendar servico | Revisao, Reparos |
| 26 | farmacia | Ver produtos | Medicamentos |

No caminho líquido atual, esses termos comerciais são normalizados para 13
famílias canônicas em `vite_visual_lanes.py` e 22 subnichos em
`agente_variacao.py`. **Adicionar novo segmento/subnicho** = mapear família,
lane/remix visual, keywords de intenção e template de subnicho; não criar HTML
paralelo.

### 22.3 O "Caroço" (caroco) — Briefing Real do Lead

Antes (Sprint 12.8): sistema prompt do LLM recebia só dados básicos.

Agora (Sprint 12.12+): `vite_prompts.py` injeta briefing REAL via
`_build_caroço_block(facts)` que agrega:
- **7 contratos canônicos** (premium_delivery_contract, design_system, motion, A11y, factual, LGPD, deploy)
- **Dados do lead** (nome, segmento, cidade, telefone, fotos, SEO, briefing)
- **13 famílias canônicas + 22 subnichos** com conteúdo segment-aware,
  intenção local, svc_labels, hero, CTAs, lifestyle e FAQ
- **Contrato raiz `DESIGN.md`** (spacing, contraste, motion, mapa, footer)
- **GSAP code patterns** (useGSAP, ScrollTrigger, magnetic, useReveal)
- **Modal obrigatório por nicho** (booking, contact, schedule)
- **Blocos pré-fabricados** (Navbar, Hero, Services, Gallery, Lifestyle, Contact, Footer)
- **Cross-contamination guard** (barbearia NUNCA menciona musculacao)

Desde Sprint 14, este caminho rico/full-code é **legado controlado**:
por padrão `FRALIB_VITE_LLM_POLICY=creative_plan` chama o LLM com prompt curto
e pede apenas JSON de copy + direção criativa. O TSX é gerado por
Studio/FraLib. Use o caroço full-code só com
`FRALIB_VITE_LLM_POLICY=full_code` para debug/experimento.

Políticas válidas:

| Policy | Chamada LLM | Quem gera TSX | Uso |
|---|---|---|---|
| `creative_plan` | JSON curto de copy + direção de marca | Studio/FraLib | **Padrão oficial**: LLM escolhe Brand DNA, emoção, hero, blocos, superfícies e motion sem codar TSX |
| `copy_only` | JSON curto de conteúdo | Studio/FraLib | Baixo custo |
| `none` | Nenhuma | Studio/FraLib | Custo zero/contingência |
| `full_code` | Projeto Vite completo | LLM | Legado/debug |

Desde 2026-06-29, `creative_plan` é a política premium recomendada para
sites cinematográficos com baixo custo. O LLM atua como estrategista de marca,
diretor criativo, UX/CRO e SEO local, mas retorna apenas JSON validado. O
renderer determinístico aplica o plano em blocos Vite/React, priorizando:
- Brand DNA antes de nicho/template.
- Hero imersivo conforme a variação (`split`, `center`, `asymmetric`,
  `fullbleed` ou `video`). `video` nunca é padrão; só entra quando
  `hero_layout`/lane/creative_plan pedir explicitamente.
- Footer e seções sempre usando tokens do tema (`--bg`, `--text`,
  `--text-muted`, `--accent`), sem cor padrão solta.
- OG/Twitter e JSON-LD alinhados no publicador.

### 22.4 Cross-contamination guard

O `_build_no_contamination_block()` força regras rígidas:
- barbearia → NAO pode mencionar musculacao, crossfit, academia, spinning
- academia → NAO pode mencionar corte, barba, pigmentacao
- restaurante → NAO pode mencionar corte, agendamento, receita
- clinica → NAO pode mencionar prato, menu, reserva

Se detectado, studio fallback falha com `ViteReactRenderError`.

### 22.5 Pipeline nova (Vite/React)

```bash
# Build site vite_react (default)
FRALIB_BUILDER_ENGINE=vite_react python3 pipeline.py builder-job \
    --prd-json prd.json --tenant-id 2 --job-id X --target landing-page \
    --model claude-sonnet-4-6 --execute

# Default Sprint 14 → creative_plan:
# LLM retorna JSON curto; Studio/FraLib gera TSX deterministico
```

Cascata em `creative_plan`/`copy_only`: modelos retornam JSON de conteúdo. Se
todos falharem, o job falha. Em `none`, não há chamada LLM. Em `full_code`, o
comportamento experimental tenta projeto TSX completo; se falhar, o job falha
em vez de publicar um site genérico.

### 22.6 Bug crítico e fix (Sprint 12.19)

**Bug**: o studio fallback gerava `"""..."""` (string normal) ao invés de
`f"""..."""` (f-string) em algumas templates, fazendo `{lifestyle_title}`
ser literal no bundle JS → `ReferenceError: lifestyle_title is not defined`
→ React não monta → tela preta.

**Fix** (commit `84a63d4`): post-process `_interpolate_studio_placeholders()`
em `prepare_vite_project_files()` substitui qualquer `{var}` literal nos
.tsx pelo valor real derivado do segment-aware dict. Safety net para
qualquer f-string esquecida no futuro.

**Validado** em browser via Playwright no site
`https://seunegociofralib.site/sites/2/barbearia-fio-nobre-v15h/`:
- ✅ HTTP 200
- ✅ React monta
- ✅ Title "Barbearia Fio Nobre Pinhais"
- ✅ Conteúdo visível (Navbar, Hero, Cards, Lifestyle)

### 22.7 Outras mudanças estruturais

| Mudança | Commit | Impacto |
|---|---|---|
| Studio catalog segment-aware | `4efbce3` | Zero cross-contaminação |
| Lead name injetado no bundle | `c3a65cb` | Title real do lead no HTML |
| LifestyleSection f-string | `f0147d6` | LifestyleTitle interpolado |
| Import path backend/ | `7a864c3` | Render não falha no import |
| Post-process {var} | `84a63d4` | Safety net definitivo |
| 7 contratos no caroço | `b8bde21` (Sprint 12.14) | Briefing rico pro LLM |
| BookingModal neutro por nicho | Sprint 12.20 | Remove "matricula/treino" hardcoded que contaminava nutricionista |
| Contrato determinístico de mídia | Sprint 12.20 | Injeta Hero/Galeria com fotos aprovadas quando LLM ignora imagens |
| Guard nutrição esportiva | Sprint 12.20 | Permite "musculacao" só para nutricionista esportivo; mantém "matricula" bloqueado |
| LLM policy copy-only | Sprint 14 | LLM preenche JSON curto; Studio/FraLib gera TSX, reduzindo token/custo |
| Blocos líquidos + intenção SEO | 2026-07-02 | 13 famílias, 22 subnichos, `DESIGN.md` injetado, `creative_plan` materializado |

### 22.7.1 Fix Sprint 12.20 — BookingModal sem contaminação

**Bug encontrado em teste real tenant 2**: lead `Vitor Feitosa - Nutricionista
Esportivo` (`nutricionista`) acionou Vite/React, mas o Studio fallback foi
bloqueado pelo guard de contaminação porque `BookingModal.tsx` ainda tinha texto
hardcoded de academia/escola: "Matricula, treino e avaliacao".

**Fix**: `backend/services/vite_react_renderer.py` agora usa `{cta_primary}` no
botão e texto neutro no modal: "Atendimento personalizado com avaliacao".
Regressão: `tests/test_anti_regressao_v114.py::test_9_studio_fallback_nutricionista_sem_contaminacao`.

**Causa raiz seguinte no mesmo lead**: o manifesto tinha fotos reais em
`media.photos`, mas o projeto gerado podia chegar ao gate sem nenhum `<img>` ou
URL editorial. `_rewrite_editorial_images()` só substituía URLs existentes; não
criava superfícies visuais quando o LLM ignorava as imagens. Resultado falso:
`projeto Vite sem galeria/imagens reais: 0 refs`.

**Fix**: `prepare_vite_project_files()` agora chama
`_ensure_editorial_media_contract()` depois de reescrever URLs. Se o source ainda
não tem imagens suficientes, Hero/Galeria determinísticos são materializados com
as fotos aprovadas do lead antes do `validate_vite_project_files()`.
Regressão: `tests/test_anti_regressao_v114.py::test_10_prepare_injeta_midia_aprovada_quando_llm_nao_usa_imagens`.

**Falso positivo do guard**: o primeiro modelo válido podia mencionar
`musculacao` em um lead `Nutricionista Esportivo`; isso é coerente para nutrição
esportiva, mas era bloqueado junto com contaminações reais de academia.

**Fix**: `_forbidden_terms_for_business()` mantém `matricula` proibido para
nutricionista, mas libera `musculacao/musculação` quando o próprio contexto do
lead indica nutrição esportiva (`esportivo`, `performance`, `atleta`,
`hipertrofia`, `suplementacao`). Regressão:
`tests/test_anti_regressao_v114.py::test_11_guard_nutricionista_esportivo_permite_musculacao_sem_matricula`.

### 22.7.2 Sprint 14 — Copy-only como padrão do Vite

**Problema**: mesmo com shadcn/ui, GSAP, templates e blocos pré-fabricados,
o caminho principal ainda pedia ao LLM para gerar arquivos TSX completos. Isso
aumentava custo/tokens e deixava a estrutura vulnerável a falhas como
`ServicesSection` ausente.

**Fix**: `render_vite_react_site()` agora lê `FRALIB_VITE_LLM_POLICY`.
O default é `creative_plan`: `_call_copy_only_llm()` usa system prompt pequeno,
`_parse_content_json()` sanitiza a resposta, `_merge_copy_only_content()` injeta
`_llm_content` nos facts e `_generate_studio_fallback_files()` monta o React.

**Modo zero custo**: `FRALIB_VITE_LLM_POLICY=none` pula qualquer chamada LLM e
gera o site somente com fatos confirmados + defaults segment-aware.

**Modo legado**: `FRALIB_VITE_LLM_POLICY=full_code` mantém o comportamento antigo
em que o LLM tenta devolver projeto Vite completo.

Regressões:
- `tests/test_anti_regressao_v114.py::test_12_vite_copy_only_usa_json_curto_e_codigo_deterministico`
- `tests/test_anti_regressao_v114.py::test_13_vite_policy_none_nao_chama_llm`

### 22.8 Tags v1.14.x (Sprint 12.19)

```
v1.14.0-baseline-2026-06-25  - Migracao Vite/React engine padrao
v1.14.0-lockpoint-2026-06-25 - backup
v1.14.1-baseline-2026-06-25  - wire caroco rico no LLM dispatcher
v1.14.1-lockpoint-2026-06-25
v1.14.2-baseline-2026-06-25  - catalogo segment-aware + clean bundle + deploy
v1.14.2-lockpoint-2026-06-25
v1.14.3-baseline-2026-06-25  - lead name injection (c3a65cb)
v1.14.3-lockpoint-2026-06-25
v1.14.4-baseline-2026-06-25  - post-process {var} placeholders (84a63d4)
v1.14.4-lockpoint-2026-06-25
```

### 22.9 Como verificar a nova pipeline

```bash
# Local: rodar smoke com lead real
ssh root@100.101.18.1 "cd /root/fralib && \
  find . -name '*.pyc' -path '*/services/*' -delete 2>/dev/null; \
  find . -name '__pycache__' -path '*/services/*' -exec rm -rf {} + 2>/dev/null; \
  rm -rf .tmp/builder-workspaces/tenant-2/job-X 2>/dev/null; \
  python3 pipeline.py builder-job \
    --prd-json .tmp/prd_X.json \
    --tenant-id 2 --job-id X --target landing-page \
    --model claude-sonnet-4-6 --execute"

# Validar com Playwright (anti-tela-preta)
cd C:/fralib && python scripts/_investigate_v15d_v2.py
# Esperado: visible text (nome do lead, navegação, hero, etc)
# Se "EMPTY" → bug de template literal ainda existe
```

### 22.10 Decisão arquitetural: por que Vite/React virou padrão

| Critério | OpenUI | Vite/React |
|---|---|---|
| Componentes React reutilizáveis | ❌ | ✅ |
| Tailwind v4 com build | parcial (CDN) | ✅ real |
| shadcn/ui (biblioteca FraLib) | ❌ | ✅ |
| Hooks GSAP/Lenis | parcial | ✅ nativos |
| Reuso de build cache | ❌ | ✅ |
| Browser preview local | ❌ | ✅ |
| Interatividade JS (modais, etc) | ❌ | ✅ React state |
| SEO + A11y (outros 46 patches) | ✅ | ✅ herdado |

**Conclusão**: Vite/React dá mais poder sem perder qualidade SEO/A11y.
OpenUI continua disponível como rota alternativa explícita, não como fallback
automático do Vite/React.

### 22.11 Próximos passos (Sprint 12.20+)

- Sprint 12.20: RAG embeddings por segmento (busca semântica de templates)
- Sprint 12.21: A/B testing automático de headlines
- Sprint 12.22: Multi-tenant cache (template cacheado por nicho)
- Sprint 13:   Ver seção 21.10 (Sprint 14 fine-tuning)

---

**Conta de linhas**: este arquivo tem ~700 linhas (vs 570 anteriores) — adição da seção 22 (Sprint 11-12 Vite/React).
