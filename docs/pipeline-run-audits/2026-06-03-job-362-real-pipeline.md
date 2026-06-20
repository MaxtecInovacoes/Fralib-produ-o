# Auditoria de Run Real - Pipeline 31 / Job 362

Data da auditoria: 2026-06-03  
Ambiente executado: VPS `/root/fralib`  
Repo canonico: `C:\fralib`  
Modo de coleta: somente leitura via SSH; nenhum arquivo foi editado direto na VPS.

## Resumo

- Tenant: `31`
- Queue: `pipeline_queue.id=10`
- Pipeline job: `jobs.id=362`, tipo `pipeline_multiplos`
- SDR job: `jobs.id=363`, tipo `bryan_outreach`
- Run ID: `e2eccfe32e7e`
- Lead escolhido: `Nonnita Pizzaria`
- Nicho/cidade: `pizzaria`, `Curitiba`
- Site publicado: `https://seunegociofralib.site/sites/31/nonnita-pizzaria/`
- Status final da pipeline: `completed`
- Status final do SDR: `completed`
- Erros de execucao: nenhum erro persistido em `jobs.last_error`, `pipeline_queue.erro` ou `pipeline_run_spans.erro`.

## Tempo Medido

| Trecho | Inicio | Fim | Duracao |
| --- | --- | --- | --- |
| Fila total ate site pronto | 2026-06-03 12:05:33.710690 | 2026-06-03 12:18:03.358398 | 12m30s |
| Job pipeline | 2026-06-03 12:05:36.199884 | 2026-06-03 12:18:03.398428 | 12m27s |
| SDR/Bryan separado | 2026-06-03 12:18:04.089725 | 2026-06-03 12:18:38.982943 | 35s |
| Total ate envio SDR | 2026-06-03 12:05:33.710690 | 2026-06-03 12:18:38.982943 | 13m05s |

### Spans Por Fase

| Fase | Agente | Modelo | Status | Duracao |
| --- | --- | --- | --- | --- |
| `hunter_kw` | `hunter` | - | `success` | 171.855s |
| `caio` | `caio` | `haiku` | `success` | 0.004s |
| `jina` | `jina` | - | `success` | 7.097s |
| `unsplash` | `unsplash` | - | `success` | 0.442s |
| `agente_nicho` | `agente_nicho` | `sonnet` | `success` | 0.019s |
| `agente_variacao` | `agente_variacao` | `haiku` | `success` | 0.002s |
| `arquiteto_mestre` | `arquiteto_mestre` | `sonnet` | `success` | 0.013s |
| `builder_renderer` | `builder_renderer` | `sonnet` | `success` | 560.485s |
| `deploy` | `deploy` | - | `success` | 0.026s |
| `bryan` | `bryan` | `sonnet` | `success` | 0.059s |

Observacao: o span `bryan` da pipeline mede o enqueue do job SDR. O envio real aconteceu no job separado `363` e levou 35s.

## Custo Medido

| Fonte | Valor |
| --- | --- |
| `pipeline_token_usage` do run `e2eccfe32e7e` | `0` input, `0` output, `$0.0000` |
| `llm_budget_ledger` com `run_id=e2eccfe32e7e` | sem linhas |
| `llm_usage` na janela do teste | 1 linha, agente `franz`, `6782` input, `500` output |
| `llm_budget_ledger` na janela do teste | 1 linha, agente `franz`, custo `$0.028762` |

Conclusao de custo: o custo confirmado dentro da FraLib para o envio SDR foi `$0.028762`. O custo total real do teste nao esta completamente registrado, porque o Builder rodou via Sandbox/Claude e nao gravou tokens/custo em `pipeline_token_usage`, `llm_usage` ou `llm_budget_ledger`.

O manifesto do Builder tinha `10250` caracteres de prompt, e o Builder gerou `index.html`, `styles.css` e `main.js`, mas o custo de tokens dessa sessao externa nao foi persistido no banco.

## Caminho Percorrido

1. `worker.py` pegou o job `362` da tabela `jobs`.
2. `worker.py` chamou `executar_pipeline_multiplos` em `pipeline_endpoints`.
3. `backend/endpoints/pipeline_orchestrator_service.py` executou a pipeline principal.
4. Hunter usou `utils/agente1_hunter_v2.py` e keyword research em `backend/agents/keyword_research.py`.
5. Caio usou `backend/agents/caio.py`.
6. Jina usou `backend/utils/jina_intelligence.py` e fallback em `backend/agents/jina_research.py`.
7. Midia usou `backend/agents/unsplash_fetcher.py`.
8. O fluxo prompt-agent pulou a montagem visual antiga como decisao final e empacotou os dados em `backend/agents/site_prompt_agent.py`.
9. `backend/services/builder_worker.py` gerou o manifesto e chamou `builder-worker/sandbox_builder_runner.mjs`.
10. `builder-worker/sandbox_builder_runner.mjs` abriu sessao Sandbox Agent com agente `claude`, modelo `sonnet`.
11. O Builder escreveu os arquivos no workspace isolado e gerou `dist/index.html`.
12. `copy_builder_dist` copiou o `dist` para `/var/www/fralib/sites/31/nonnita-pizzaria`.
13. A pipeline enfileirou `jobs.id=363` para `bryan_outreach`.
14. `worker.py` executou Bryan/Franz em `backend/agents/bryan.py`.
15. `worker.py` enviou a mensagem via Meowhats em `http://localhost:3001/api/sessions/fralib_user_31/send`.

## Artefatos e Caminhos

### Builder Manifest

- Manifesto: `/root/fralib/logs/builder_manifests/tenant-31__job-u31-nonnita-pizzaria-pizzaria-curitiba-1d8d23423e.json`
- Tamanho: `32810` bytes
- Mtime: `2026-06-03 12:08:42.553210`
- Contract: `fralib-builder-worker-v1`
- Prompt agent contract: `fralib-prompt-agent-v1`
- Builder job id: `u31-nonnita-pizzaria-pizzaria-curitiba-1d8d23423e`
- Sandbox agent: `claude`
- Sandbox model: `sonnet`
- Prompt final enviado ao Builder: `10250` caracteres

### Workspace Isolado

Base: `/root/fralib/.tmp/builder-workspaces/tenant-31/job-u31-nonnita-pizzaria-pizzaria-curitiba-1d8d23423e`

| Arquivo | Tamanho | Mtime |
| --- | --- | --- |
| `index.html` | 17145 | 2026-06-03 12:13:16.866944 |
| `styles.css` | 16796 | 2026-06-03 12:15:35.564326 |
| `main.js` | 3355 | 2026-06-03 12:15:53.629506 |
| `dist/index.html` | 17145 | 2026-06-03 12:17:58.645424 |
| `dist/styles.css` | 16796 | 2026-06-03 12:17:58.647361 |
| `dist/main.js` | 3355 | 2026-06-03 12:17:58.649255 |

### Publicacao

Base: `/var/www/fralib/sites/31/nonnita-pizzaria`

| Arquivo | Tamanho | Mtime |
| --- | --- | --- |
| `index.html` | 17145 | 2026-06-03 12:18:03.074483 |
| `styles.css` | 16796 | 2026-06-03 12:17:58.647361 |
| `main.js` | 3355 | 2026-06-03 12:17:58.649255 |

HTTP validado: `200 OK`, `Content-Type: text/html`, `Content-Length: 17145`.

## Evidencias de Logs

- `job 362 (pipeline_multiplos) tenant=31 attempt=1/1`
- `Pipeline ID refinado: u31-pizzaria-pizzaria -> u31-nonnita-pizzaria-pizzaria-curitiba-1d8d23423e`
- `Caio: MORNO`
- `Jina AI: OK (810 chars)`
- `BUILDER RENDERER: OK`
- `Deploy: https://seunegociofralib.site/sites/31/nonnita-pizzaria/`
- `job 362 concluido`
- `job 363 (bryan_outreach) tenant=31 attempt=1/5`
- `POST http://localhost:3001/api/sessions/fralib_user_31/send "HTTP/1.1 200 OK"`
- `job 363 concluido`
- Ledger runtime: `Erros: 0`

## Lacunas Encontradas

1. O custo do Builder nao entrou em `pipeline_token_usage`, `llm_usage` nem `llm_budget_ledger`.
2. O ledger por `run_id` ficou vazio, embora tenha havido uma linha de custo do `franz` na janela do teste.
3. O job Bryan registrou `run_id=null`; isso quebra a costura entre pipeline job `362` e SDR job `363`.
4. O span `bryan` da pipeline mede apenas o enqueue, nao o envio real.
5. O log do Bryan ainda mascara o telefone original do lead, mesmo quando `_bryan_test_number` redireciona o envio para numero de teste.

## Ajustes Recomendados

1. Propagar `run_id`, `tenant_id`, `job_id` e `phase` em toda chamada LLM, inclusive Bryan/Franz.
2. Fazer o `builder-worker/sandbox_builder_runner.mjs` devolver usage/custo ou eventos parseaveis para `builder_worker.py`.
3. Gravar uma linha de custo `builder_renderer` em `llm_budget_ledger`.
4. Criar span separado para `bryan_outreach` ou finalizar o span `bryan` apenas depois do envio.
5. Adicionar exportador oficial de run: jobs, spans, ledger, manifest, arquivos publicados e logs resumidos.
