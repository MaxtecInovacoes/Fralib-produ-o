# FraLib Pipeline Harness

## Objetivo

O Pipeline Harness e a bancada local e dry-run para validar a pipeline ativa sem
gastar API, tocar producao, enviar WhatsApp ou acionar deploy. Ele existe para
dar velocidade e seguranca antes de qualquer teste real.

Pipeline ativa coberta:

1. Lead Supply
2. Caio
3. Jina/inteligencia de mercado
4. Agente de Prompt
5. Builder Renderer Vite/React
6. Deploy dry-run
7. Franz/SDR simulado

## Comandos

```powershell
python scripts/pipeline_harness.py list
python scripts/pipeline_harness.py run --scenario pizzaria_builder_vite_react --dry-run
python scripts/pipeline_harness.py run --all --dry-run
python scripts/pipeline_harness.py audit-tests --json
```

## Runner Controlado Em Producao

O harness acima e local/dry-run. Para provar uma pipeline real na VPS sem
acionar WhatsApp por acidente, use o runner versionado:

```bash
python3 scripts/controlled_pipeline_run.py \
  --tenant-id 2 \
  --lead-id <lead_uuid> \
  --confirm RUN_CONTROLLED_PIPELINE \
  --wait
```

Esse comando e real: ele enfileira `pipeline_lead` em `jobs`, usa LiteLLM,
Builder e deploy publico. Por padrao ele grava `_skip_franz_outreach` e valida
que o lead pertence ao tenant. Franz/WhatsApp real exige `--allow-franz-outreach`
e `FRALIB_ALLOW_CONTROLLED_FRANZ=1`.

Depois de cada execucao real, verifique:

- `jobs.status`, `jobs.last_phase`, `jobs.last_error`;
- `leads.status`, `site_url`/`url_site`;
- artefatos em `/var/www/fralib/sites/<tenant>/<slug>/`;
- `llm_budget_ledger` e resumo de custo em `jobs`;
- QA visual desktop/mobile do site publicado.

No Windows local, se existirem chaves reais no ambiente apenas como resquicio de
desenvolvimento, o harness bloqueia por padrao. Para auditar somente presenca de
arquivos/cenarios sem usar essas chaves:

```powershell
$env:FRALIB_HARNESS_IGNORE_LOCAL_KEYS='1'
python scripts/pipeline_harness.py run --all --dry-run
```

Isso nao libera chamada externa; apenas ignora a presenca local das chaves no
processo. O harness continua bloqueando LLM real, Hunter, WhatsApp, deploy,
Mercado Pago live, scraper pago e HTTP externo.

## Cenários Versionados

- `tenant_trial_sem_sdr`: prova que trial pula envio SDR real.
- `tenant_pro_com_sdr_simulado`: prova caminho Pro com SDR apenas simulado.
- `pizzaria_builder_vite_react`: prova contrato Builder Vite/React sem LiteLLM.
- `high_fitness_builder_ptbr`: prova contrato Builder EN interno + site pt-BR.
- `pagamento_aprovado_dry_run`: prova reconciliacao apenas dry-run.
- `worker_stale_recover_dry_run`: documenta recover-runtime sem reiniciar PM2.

Cada cenario declara fixtures, fases esperadas, mocks, capacidades proibidas e
criterios de PASS/FAIL.

## Guardrails

O harness falha fechado quando:

- `--dry-run` nao foi informado;
- `DATABASE_URL` aponta para Postgres nao-test;
- existem chaves vivas no processo, salvo auditoria local explicita;
- o cenario permite LLM/Hunter/WhatsApp/deploy/Mercado Pago/scraper/HTTP live;
- uma fase nao pertence a pipeline ativa;
- um comando nao esta na allowlist local.

## Matriz Recomendada

| Camada | Finalidade | Exemplos |
| --- | --- | --- |
| Unitarios de dominio | Regras pequenas sem app completo | planos, Caio, archetypes, tenant scope |
| Contratos da pipeline ativa | Proteger fases atuais | Builder Vite/React, SDR gateway, MP legal/auth |
| Harness/smoke dry-run | Provar fluxo sem side effect | `pipeline_harness.py`, `pipeline.py smoke --dry-run` |
| Integracao local segura | Banco/test DB e filas locais | `tests/integration/*` com DB test |
| Canary producao somente leitura | Evidencia operacional | Hermes snapshot/canary dry-run |

## Uso Com Dify Ou AI Ops Lab

Dify pode prototipar prompts, RAG operacional ou diagnostico, mas o harness
continua sendo a fonte versionada de seguranca. Qualquer fluxo bom descoberto
fora do repo deve virar fixture/cenario/teste antes de entrar na pipeline real.
