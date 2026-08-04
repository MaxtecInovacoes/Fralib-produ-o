# FraLib — Fluxo de Dados do Pipeline

Este documento descreve cada stage do pipeline de geração de landing pages, com input, output, tratamento de erro e retry.

**Arquivo fonte canônico:** `backend/agents/manager/agent.py` (função `run_pipeline`, linha 665)

---

## 0. Enqueue (API → Fila Postgres)

| Item | Valor |
|------|-------|
| **Entrada** | POST `/api/pipelines` com `lead_id` + `tenant_id` |
| **Processamento** | `pipeline_endpoints.py` cria job na tabela `jobs` com status `pending` |
| **Idempotência** | `idempotency_key` + `ON CONFLICT DO NOTHING` |
| **Saída** | Job enfileirado, worker consome via `SELECT FOR UPDATE SKIP LOCKED` |
| **Retry** | Backoff exponencial: 30s → 2min → 8min |
| **Crash recovery** | Heartbeat a cada 30s; se > 5min sem heartbeat, job volta para `pending` |

---

## 1. Hunter (Coleta de Dados)

| Item | Valor |
|------|-------|
| **Função** | `step_hunter()` em `manager/agent.py` |
| **Modelo** | Haiku (rápido, baixo custo) |
| **Input** | `lead_data` do Postgres (nome, cidade, segmento, telefone, website) |
| **Processamento** | Valida dados existentes. Se faltam campos críticos, scraping Google Maps via Playwright (`agente1_hunter_v2.py`) |
| **Output** | `state.lead_data` enriquecido com `rating`, `reviews_count`, `fotos`, `market_intelligence` |
| **Falha** | Lead sem dados mínimos → transição para `STATE_FAILED` |
| **Retry** | Não retry — erro estrutural |

---

## 2. Caio (Qualificação)

| Item | Valor |
|------|-------|
| **Função** | `step_caio()` em `manager/agent.py` (linha 124) |
| **Modelo** | Haiku (2000 tokens) |
| **Input** | `lead_data` enriquecido (nome, cidade, segmento, telefone, website, rating, reviews_count, fotos) |
| **Processamento** | Chama `caio.agent.qualificar()` → classifica em tier MORNO/STANDARD/PREMIUM, score 0-100 |
| **Output** | `state.caio_output = {tier, score, motivo, qualificado, paleta_cores}` |
| **Critério de corte** | `qualificado == False` → pipeline aborta (`STATE_FAILED`) |
| **Retry** | Não retry — decisão binária (qualificado ou não) |
| **Knowledge Journal** | Evento `lead_qualified` registrado |

---

## 3. Arquiteto (PRD Generation)

| Item | Valor |
|------|-------|
| **Função** | `step_arquiteto()` em `manager/agent.py` (linha 191) |
| **Modelo** | Opus (8000 tokens) — PRD complexo requer reasoning forte |
| **Input** | `lead_data` + `market_intelligence` (do Hunter) |
| **Processamento** | Chama `arquiteto.agent.gerar_prd()` → gera `DesignerPRD` com: business_name, hero, sections, ctas, faqs, paleta, design_tokens, layout_dna, design_system |
| **Output** | `state.design_output` com PRD completo |
| **Retry** | **Sim — até 3 attempts** com backoff: 5s → 15s → 45s. Apenas erros transientes (429, 529, timeout, 5xx). Erros estruturais (JSON inválido, campo faltando) não retry. |
| **Knowledge Journal** | Eventos `narrative_locked` + `identity_approved` registrados |

---

## 4. Builder (HTML Generation)

| Item | Valor |
|------|-------|
| **Função** | `step_builder()` em `manager/agent.py` (linha 291) |
| **Modelo** | Claude Sonnet 4.6 (via OpenUI Node.js :3333) |
| **Input** | `state.design_output` (PRD completo do Arquiteto) |
| **Processamento** | Chunked em 4×18000 tokens (total 64000). OpenUI gera HTML incrementalmente. Manager injeta `_lead_rating`, `_lead_reviews_count`, `_lead_telefone` no payload. |
| **Output** | `state.build_output["html"]` — HTML completo |
| **Pós-processamento** | `cinematic_post_processor.py` aplica parallax, reveals, grain |
| **Retry** | Erros no Builder disparam retry via loop externo de `run_pipeline` — se quality gate falhar, retorna ao Builder |
| **Custos** | ~200s de geração, maior custo do pipeline |

---

## 5. Quality Gate v2 (Vision QA)

| Item | Valor |
|------|-------|
| **Função** | `step_quality_gate()` em `manager/agent.py` |
| **Modelo** | GPT-4o-mini (primary, via ) / 9router (fallback) |
| **Input** | HTML gerado + screenshot via Playwright |
| **Processamento** | Vision LLM pontua design em 10 eixos: tipografia, cores, espaçamento, animações, responsividade, acessibilidade, seções, CTAs, performance, identidade visual. Threshold: **7.5/10** |
| **Output** | `state.quality_score` + relatório detalhado |
| **PASS** | score ≥ 7.5 → avança para Deploy |
| **FAIL** | score < 7.5 → **repair_loop** regenera HTML (até 3 tentativas). Após 3 falhas, pipeline aborta. |
| **Retry** | Loop interno: Builder → QA → (se fail) → Builder novamente. Max 3 cycles. |

---

## 6. Deploy (Publicação)

| Item | Valor |
|------|-------|
| **Função** | `step_deploy()` em `manager/agent.py` (linha ~500) |
| **Modelo** | Nenhum (sem LLM) |
| **Input** | HTML aprovado + metadata do lead |
| **Processamento** | Salva HTML em `/var/www/fralib/sites/<tenant>/<slug>-<lead_id>/index.html`. Gera `metadata.json`. |
| **Output** | `state.deploy_url = "https://seunegociofralib.site/sites/<tenant>/<slug>-<lead_id>/"` |
| **Persistência** | UPDATE leads SET status='concluido', site_url=..., sdr_stage='pendente_wpp' |
| **Retry** | Fail-soft — se deploy falhar, tenta novamente no próximo tick do worker |
| **Knowledge Journal** | Evento `project_published` registrado |

---

## 7. Franz (WhatsApp Outreach)

| Item | Valor |
|------|-------|
| **Função** | `step_franz()` em `manager/agent.py` (linha 609) |
| **Modelo** | Nenhum (marker — Franz roda via cron separado) |
| **Input** | Lead com `status='concluido'` e `sdr_stage='pendente_wpp'` |
| **Processamento** | Marca lead como pronto para outreach. Franz (Bryan) processa via cron dispatcher (`WORKER_JOB_TYPES` inclui `franz_outreach`) |
| **Output** | Lead entra na fila SDR — Franz envia primeira mensagem WhatsApp via meowhats API |
| **Retry** | Franz tem seu próprio retry logic (defer loop com proximo slot válido 08:00-21h) |

---

## Error Handling & Retry Matrix

| Stage | Erro Transiente | Erro Estrutural | Max Retry |
|-------|----------------|-----------------|-----------|
| Hunter | — | Falha dados mínimos | 0 |
| Caio | — | Lead não qualificado | 0 |
| Arquiteto | 429/529/timeout/5xx | JSON inválido, campo faltando | 3 (5s→15s→45s) |
| Builder | 502/503/529 | HTML malformado | Via QA repair loop (3x) |
| QA v2 | — | Score < 7.5 após 3x | 3 (repair loop) |
| Deploy | IO error | — | Fail-soft (next tick) |
| Franz | — | — | Via defer loop |

---

## Cost Tracking

- **RunContext** criado no início de `run_pipeline()` com `run_id`, `tenant_id`, `lead_id`
- **aggregate_pipeline_usage()** chamado no `finally` — sempre, mesmo em falha
- **deduzir_creditos_por_pipeline()** deduz créditos baseado em custo USD real
- Custo por pipeline: ~$0.34 USD (CUSTO_POR_CICLO_USD) + custo de tokens LLM

---

## FSM State Transitions

```
init → hunting → qualifying → designing → building → validating → publishing → outreach → done
                                    ↑                                    │
                                    └── (QA fail) ← repair loop ────────┘
                                    │
                              (any error)
                                    │
                                    ↓
                              failed
```
