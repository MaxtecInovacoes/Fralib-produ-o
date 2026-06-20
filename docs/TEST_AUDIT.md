# FraLib Test Audit

## Objetivo

Esta auditoria separa testes atuais, legados, obsoletos, perigosos e frageis sem
apagar nada na primeira etapa. O objetivo e reduzir falso positivo, custo,
latencia e risco operacional antes de mexer na suite.

## Comando

```powershell
python scripts/pipeline_harness.py audit-tests --json
```

Saida por arquivo:

- `ATUAL`: protege pipeline ativa, seguranca, tenant scope, Builder Vite/React,
  SDR/Franz, Mercado Pago, Hermes ou frontend canonico.
- `LEGADO_SEGURO`: menciona caminho antigo, mas isolado e sem side effect claro.
- `OBSOLETO`: valida fluxo morto ou contrato que nao e pipeline ativa.
- `PERIGOSO`: pode chamar producao, provider real, WhatsApp, deploy, banco real,
  API externa ou alterar estado.
- `DUPLICADO_FRAGIL`: depende de porta, tempo, import amplo, coverage/conftest ou
  detalhe instavel.

## Primeira Leitura Do Repo

O repo ja tem checks uteis que devem ser preservados:

- `pipeline.py smoke --dry-run`
- `scripts/pipeline_smoke.py`
- `tests/unit/test_builder_worker.py`
- `tests/unit/test_lead_supply_engine.py`
- `tests/unit/test_sdr_gateway.py`
- `tests/unit/test_mercadopago_legal_auth_contract.py`
- `tests/unit/test_tenant_scope_audit.py`
- `tests/unit/test_hermes_watchdog.py`
- `tests/integration/test_job_queue_concurrency.py`

Tambem existem candidatos a revisao cuidadosa:

- arquivos com `bryan` no nome ou conteudo;
- testes que ainda tratam HTML gate antigo como fluxo ativo;
- scripts que aceitam `--apply`;
- scripts que usam deploy, WhatsApp, HTTP externo, `DATABASE_URL` real ou
  `subprocess` operacional;
- e2e que depende de servicos locais ou browser sem fixture isolada.

## Politica De Limpeza

Nao remover teste apenas por parecer antigo. A ordem segura e:

1. Rodar auditoria estatica.
2. Conferir evidencias por arquivo.
3. Marcar legado com skip/xfail explicito quando ainda documenta historia.
4. Ajustar teste util para a pipeline ativa.
5. Remover somente quando houver substituto atual ou prova de contrato morto.

## Limpeza Inicial Aplicada

- Testes Bryan/SDR historicos foram marcados com `pytest.mark.legacy`; eles
  preservam evidencia, mas nao definem a pipeline ativa.
- `tests/conftest.py` bloqueia `DATABASE_URL` de teste que nao seja sqlite ou
  Postgres local com nome contendo `test`.
- Integracoes sensiveis de fila/IDOR validam host local e banco test antes de
  abrir conexao.
- `scripts/vps_reconcile_mercadopago_payments.py` bloqueia consulta live ao
  Mercado Pago fora de `FRALIB_ENV=prod`; para harness local use
  `--fixture-json`.
- `scripts/hermes_canary.py --record` bloqueia gravação de incidente fora de
  `FRALIB_ENV=prod`.
- `scripts/vps_validate_prod_launch.py` bloqueia `--base-url` remoto por padrao;
  uso remoto exige `--allow-remote-read`.
- A auditoria agora diferencia melhor contratos read-only/monkeypatch de risco
  operacional real.

## Ganhos Esperados

- Velocidade: rodadas focadas por camada em vez de suite ampla.
- Custo: dry-run impede LLM, Hunter, Jina, Mercado Pago e WhatsApp live.
- Seguranca: bloqueio de producao e side effects no harness.
- Confianca: contratos mortos ficam visiveis antes de influenciar release.
- Concorrencia: cenarios de worker/recover ficam documentados sem reiniciar PM2.
