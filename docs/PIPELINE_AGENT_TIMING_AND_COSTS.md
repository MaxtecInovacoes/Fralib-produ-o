# Pipeline: caminho de agentes, tempos e custos

Ultima atualizacao: 2026-05-26

Este documento registra como a pipeline roda em producao, quais marcos observar,
onde medir tempo/custo e quais lacunas ainda precisam ser fechadas. Ele deve ser
usado para investigar lentidao, custo alto, falhas por concorrencia e regressao de
qualidade.

## Teste real controlado

- Ambiente: VPS `root@187.77.37.72`, backend FastAPI `fralib`, worker `fralib-worker`.
- Tenant/user: `2`.
- Job: `122`.
- Pipeline queue: `104`.
- Entrada: `academia`, `Campina Grande do Sul`, `quantidade=1`, `score_minimo=70`.
- Lead selecionado: `Nutrasport - Nutricao e Treino funcional`.
- Inicio da requisicao: 2026-05-26 03:26:52 UTC.
- Inicio do worker: 2026-05-26 03:26:53 UTC.
- Status final: `erro` na fila, com `HTTP Error 404: Not Found`.
- Causa raiz: Open Design rodou em modo interativo, emitiu `question-form`
  de descoberta e nao escreveu `index.html` no projeto.

## Marcos observados no teste

| Marco | Horario UTC | Tempo acumulado | Observacao |
| --- | ---: | ---: | --- |
| API aceitou `/api/pipeline/iniciar` | 03:26:52 | 0s | Criou `queue_id=104`, `job_id=122`. |
| Worker assumiu job | 03:26:53 | 1s | `worker-b10779e3`, attempt `1/3`. |
| Hunter/KW | 03:26:54 | 2s | Cache HIT para lead e keywords. |
| Caio | 03:26:54 | 2s | Score `80`, tier `PREMIUM`, aprovado contra minimo `70`. |
| Jina/Intel | 03:26:54 | 2s | Cache HIT, 1687 chars. |
| Midia/curadoria | 03:26:54 | 2s | Unsplash cache HIT 8 fotos, 5 reviews, maps embed OK. |
| Designer inicial | 03:27:02 | 10s | Primeira montagem de contexto visual OK. |
| Agente Nicho | 03:28:54 | 122s | Haiku, `in=11941`, `out=3250`, `cache_read=4`. |
| Agente Variacao | 03:29:38 | 166s | Sonnet, primeiro retorno `max_tokens`, retry aplicado. |
| Arquiteto Mestre - estrutura | 03:30:24 | 212s | Sonnet, `in=4416`, `out=2981`, `cache_read=3035`. |
| Arquiteto Mestre - copy | 03:32:29+ | 337s+ | Entrou no bloco de copy para 8 secoes. |
| Open Design - tentativa 1 | 03:33:40 | 408s | Run `succeeded`, mas `index.html` ausente. |
| Open Design - tentativa 2 | 03:34:46 | 474s | Run `succeeded`, mas `index.html` ausente. |
| Open Design - tentativa 3 | 03:35:33 | 521s | Run `succeeded`; respondeu discovery form, sem arquivo. |
| Fila encerrou com erro | 03:38:21 | 690s | `HTTP Error 404: Not Found`. |

Observacao: durante chamadas longas de LLM, `jobs.worker_heartbeat` ficou parado
em 03:26:54 apesar de haver progresso nos logs. Isso prejudica diagnostico de
"travou de verdade" versus "esta aguardando LLM".

## Caminho oficial por agente

| Ordem | Fase | O que faz | Como medir | Custo esperado |
| ---: | --- | --- | --- | --- |
| 1 | API `/iniciar` | Valida tenant, sessao WhatsApp, cooldown, creditos e cria job. | `jobs`, resposta HTTP. | Sem LLM. |
| 2 | Worker/job queue | Reivindica job, controla attempts e timeout global. | `jobs.status`, `attempts`, logs do PM2. | Sem LLM. |
| 3 | Hunter + KW | Busca/cacheia leads e palavras-chave, respeitando quantidade e dedupe. | logs `[Hunter V2]`, `[KW]`, leads criados. | Browser/scraper; sem LLM principal. |
| 4 | Caio | Qualifica lead por score/tier e compara com score minimo escolhido. | log `[Caio]`, campos do lead. | Sem LLM. |
| 5 | Jina/Intel | Resume contexto de mercado, concorrencia e sinais locais. | log `[Jina Intel]`, tamanho em chars/cache. | API externa/cache. |
| 6 | Midia | Seleciona imagens/videos e monta curadoria. | logs Unsplash/Pexels/maps/reviews. | API externa/cache. |
| 7 | Agente Nicho | Gera briefing de nicho/marca/posicionamento. | log `[LLM] agent=agente_nicho`, tokens. | LLM Haiku. |
| 8 | Agente Variacao | Decide estrutura visual e variacao de layout. | log `[LLM] agent=agente_variacao`, retries. | LLM Sonnet. |
| 9 | Arquiteto Mestre | Gera DesignerPRD em blocos de estrutura/copy. | logs `arquiteto_mestre`, cache key, tokens. | LLM Sonnet. |
| 10 | Builder Renderer | Gera projeto Vite/React/Tailwind/motion Studio e compila `dist`. | logs `builder_renderer`, `builder-render.json`, ledger LLM, npm/tsc/vite. | Vite renderer exige fonte densa, imagens, navbar, galeria, lifestyle e modal; OpenUI so fallback. |
| 11 | Quality gate | Confere HTML contra PRD e criterios de qualidade. | logs `html_quality_gate`, erros de validacao. | Deterministico; sem reparo LLM padrao. |
| 12 | Deploy | Escreve site final e valida URL. | `url_site`, HTTP 200, arquivo em `/var/www/fralib/sites/{tenant}`. | Sem LLM. |
| 13 | Bryan | Envia abordagem SDR via WhatsApp quando conectado. | logs Bryan/meowhats, status tenant. | LLM Haiku + API WhatsApp. |

## Lacunas e melhorias

- Teste real 2026-05-27, tenant 2, reprocessamento `High Fitness Academia`,
  job `243`, lead `0afe72f4-69ee-4c53-8d71-89181a0a3304`: status final
  `completed`, URL `https://seunegociofralib.site/sites/2/high-fitness-academia/`.
  Tempo total: 16:54:07 -> 17:04:04 UTC, ~9m57s. O HTML publicado tem o
  mesmo hash do artefato do Open Design, confirmando deploy sem pos-edicao
  FraLib. HTTP publicado: 200, TTFB ~194ms, HTML ~23KB.
- Marcos do teste High Fitness: agente_nicho terminou com `in=8490`,
  `out=3313`, `cache_read=3065`; agente_variacao `in=766`, `out=1082`,
  `cache_read=3035`; bloco_estrutura `in=4347`, `out=1601`,
  `cache_read=3035`; bloco_copy `in=5029`, `out=2575`,
  `cache_read=3065`; Bryan `in=7936`, `out=500`, `cache_read=3034`.
  Tokens visiveis excluindo OD: ~26.5K entrada, ~9.1K saida, ~15.2K cache_read.
- Open Design no teste High Fitness: projeto recriado por `forced regenerate`,
  arquivos staged incluiram `creative-direction.json`; OD iniciou 16:58:42,
  criou `index.html` 17:03:43 e a pipeline concluiu 17:04:04. OD levou ~5m01s
  e respondeu antes do status terminal da run.
- Resultado visual do teste High Fitness ainda reprovou direcao criativa:
  apesar de `creative-direction.json` pedir base clara, evitar dark mode total,
  evitar vermelho/preto e evitar Oswald, o HTML saiu com body `oklch(0.12...)`,
  Oswald no H1 e CTA vermelho. Causa raiz: o pacote OD ainda carregava contrato
  visual legado do FraLib (`design_system_slug=nike`, paleta dark, Oswald e
  direcao "Nike") dentro de `design-direction.md`/`site-build-contract.json`.
  Correcao aplicada: remover campos visuais legados antes de montar os arquivos
  OD; manter apenas fatos, copy, SEO, midia, anti-patterns e Brand DNA.
- Reteste real 2026-05-27, tenant 2, `High Fitness Academia`, job `244`:
  status `completed`, tempo total 17:13:31 -> 17:20:55 UTC, ~7m24s. OD iniciou
  17:16:26, gerou `index.html` 17:20:25 e concluiu em ~3m59s. O HTML publicado
  manteve hash identico ao artefato OD, HTTP 200, TTFB ~147ms e ~28.7KB.
  O visual passou a obedecer a direcao principal: base clara
  `oklch(0.98...)`, heading serif `Georgia`, corpo `Sohne`, sem dark mode
  total e sem Oswald como fonte ativa. Problema remanescente: OD ainda criou
  o H2 "Servicos premium...", violando a regra de claim. Correcao aplicada apos
  o teste: remover usos positivos da palavra "premium" nos contratos/skill e
  permitir apenas como termo proibido quando nao estiver nos fatos.
- Teste real 2026-05-26, tenant 2, academia em Campina Grande do Sul:
  Hunter encontrou Nutrasport (score 80) e gerou site, mas o health check
  bloqueou porque o HTML completo do Open Design saiu sem `wa.me`/`tel:`.
  Correção aplicada: preservar o HTML do OD e injetar somente um contact guard
  real quando faltar contato clicavel. Reprocessamento completo ficou bloqueado
  por limite diario de tokens do tenant; validacao sem custo sobre o HTML de
  trace confirmou `wa.me`, `tel:` e `fralib-contact-guard`.
- Persistir spans por fase em tabela propria: `pipeline_run_spans(run_id, lead_id, phase, agent, started_at, finished_at, status, tokens_in, tokens_out, cache_read, cache_created, model, cost_estimate, error)`.
- Atualizar heartbeat antes/depois de cada fase e durante esperas longas de LLM.
- Separar timeout global de timeout por fase; Browser, LLM e deploy devem falhar de modo independente e recuperavel.
- Amarrar checkpoint por `user_id + lead_id + queue_id`; hoje o sistema detecta checkpoint de outro lead e limpa, mas a chave por segmento/cidade ainda e propensa a ruido.
- Persistir custo por agente e exibir no dashboard por pipeline, tenant e periodo.
- Normalizar logs em JSON para permitir consulta por job/lead sem depender de texto do PM2.
- Tratar `Browser.close` do Playwright como erro nao fatal quando dados suficientes ja foram capturados.
- Hunter Playwright tem budget padrao de 150s para captura de 1 lead, pool curto
  e timeout por detalhe; se nao achar lead valido, falha limpo antes de 3min em
  vez de segurar o worker ate o timeout global.
- Dividir `pipeline_orchestrator_service.py` por fases depois desta estabilizacao; o arquivo ainda concentra execucao longa demais.
- Criar gate real controlado separado do smoke: 1 lead, score configuravel, sem Bryan por padrao, com relatorio de tempo/custo.
- Enviar Open Design em modo automatizado: `metadata.kind=prototype`,
  `fidelity=high-fidelity` e prompt explicito para pular perguntas e escrever
  `index.html`.
- Aceitar `index.html` pronto como sucesso antecipado do Open Design; nao
  esperar a run terminal quando o artefato HTML ja existe e tem tamanho valido.
- Em retry, reaproveitar `index.html` existente quando ele pertence ao mesmo
  negocio; nao deletar projeto Open Design se o artefato pronto pode seguir.
- Garantir fallback de Schema.org no sanitizador para nao quebrar deploy por
  segmento desconhecido.
- Ao concluir uma pipeline que estava em retry, o estado operacional vem de
  `jobs` e a falha final vem de `pipeline_failures`.
- Dashboard/status deve consultar `jobs`, `pipeline_failures` e
  `pipeline_state.pausado`; `pipeline_queue` fica legado/auditoria.
- Se o Open Design entregar `<!doctype html>` completo, preservar o documento
  final e nao embrulhar em template/footer legado do FraLib.

## Observabilidade (PRD #10) — Implementado

### Tabela `pipeline_run_spans` (database.py)

Registra cada fase individualmente no DB, permitindo consultas por tenant, run e fase.

| Coluna | Descrição |
| --- | --- |
| `id` | PK auto-increment |
| `run_id` | ID da execução do pipeline |
| `trace_id` | ID do trace (observability.py) |
| `tenant_id` | Cliente dono do span |
| `lead_id` | Lead sendo processado |
| `fase_num` | Número ordinal da fase |
| `fase_nome` | hunter_kw, caio, jina, etc |
| `agente` | Nome do agente executor |
| `modelo` | Modelo LLM (sonnet, opus, haiku) |
| `started_at` | Timestamp de início |
| `finished_at` | Timestamp de fim |
| `duracao_ms` | Duração em ms |
| `status` | running/success/error |
| `input_tokens` | Tokens de entrada |
| `output_tokens` | Tokens de saída |
| `cache_read_tokens` | Tokens de cache lidos |
| `cache_created_tokens` | Tokens de cache criados |
| `custo_usd` | Custo estimado em USD |
| `erro` | Mensagem de erro (se status=error) |
| `metadata` | JSONB com heartbeat e dados extras |

### Persistência (`observability.py`)

- `salvar_span()` — insere span no DB ao iniciar fase
- `finalizar_span()` — atualiza span com métricas ao finalizar
- `atualizar_heartbeat_span()` — atualiza `last_heartbeat` no metadata (chamado pelo daemon)
- `buscar_spans_por_run()` — consulta spans de uma run
- `buscar_custos_por_tenant()` — custo agregado por cliente
- `buscar_gargalos_por_tenant()` — spans mais lentos
- `buscar_fases_lentas_tenant()` — média por fase

### Heartbeat Daemon

Thread daemon no `executar_pipeline_completo` que atualiza a cada 15s:
- `worker_heartbeat` na tabela `jobs`
- `last_heartbeat` no metadata do span atual

### Endpoints (`obs_endpoints.py`)

| Rota | Descrição |
| --- | --- |
| `GET /api/observability/dashboard` | Visão global (admin) |
| `GET /api/observability/por-agente` | Custo/chamadas por agente |
| `GET /api/observability/gargalos` | Top 10 spans mais lentos |
| `GET /api/observability/alertas` | Alertas (custo alto, taxa de falha) |
| `GET /api/observability/traces` | Lista de traces recentes |
| `GET /api/observability/trace/{trace_id}` | Detalhe de um trace |
| `GET /api/observability/spans/{run_id}` | Spans individuais de uma run |
| `GET /api/observability/custos-tenant?tenant_id=N` | Custo por tenant |
| `GET /api/observability/gargalos-tenant?tenant_id=N` | Gargalos por tenant |
| `GET /api/observability/fases-lentas-tenant?tenant_id=N` | Média por fase por tenant |
| `GET /api/observability/resumo-tenant/{tenant_id}` | Resumo completo (1 chamada) |

## Indicadores para acompanhar

- Tempo total por lead (via `pipeline_run_spans.duracao_ms`)
- Tempo por fase e p95/p99 por tenant (via `fases-lentas-tenant`)
- Tokens por agente e taxa de cache hit (via `custos-tenant`)
- Taxa de retry por agente.
- Taxa de leads recusados pelo score minimo.
- Falhas por Browser/Hunter.
- Falhas por Open Design e validador.
- Jobs recuperados por `recover-runtime`.
- Jobs que atingiram `worker_timeout`.
