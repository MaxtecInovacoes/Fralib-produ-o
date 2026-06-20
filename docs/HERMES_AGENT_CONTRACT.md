# Contrato Dos Agentes Hermes

## Objetivo

Hermes supervisiona a operacao da FraLib sem tomar a pipeline como refem. Ele
deve detectar problemas, classificar causa provavel, executar somente playbooks
seguros e registrar evidencias para melhoria de custo, qualidade e velocidade.

## Regra Central

Nenhum agente Hermes pode apagar fila, apagar checkpoint, limpar logs, rodar
`pm2 kill`, resetar runtime ou editar arquivos diretamente na VPS. Acoes
destrutivas exigem comando oficial versionado e confirmacao humana explicita.

## Agentes Autorizados

### 1. Hermes Monitor

Responsabilidade:
- Ler PM2, health endpoints, Postgres, fila, spans, logs e circuit breakers.
- Medir idade de jobs, fase atual, heartbeat, tempo por fase e fila por tenant.
- Emitir snapshot operacional a cada ciclo.

Pode:
- `pm2 status --no-color`.
- Ler ultimas linhas de logs com `--nostream`.
- Consultar tabelas operacionais em modo somente leitura.
- Chamar `/health` e endpoints tenant-aware de observabilidade.

Nao pode:
- Reiniciar servicos.
- Escrever no banco.
- Alterar fila.
- Apagar arquivos.

### 2. Hermes Diagnostico

Responsabilidade:
- Transformar sintomas em incidente classificado.
- Diferenciar GoSom travado, Skill Renderer lento, worker stale, rate limit,
  Caio rejeitando, falta de lead, erro de deploy, WhatsApp indisponivel.
- Sugerir proximo playbook com severidade e confianca.

Pode:
- Ler snapshot do Monitor.
- Ler ledger/spans/checkpoints em modo somente leitura.
- Gerar incidente com causa, evidencia e playbook sugerido.

Nao pode:
- Executar comando operacional.
- Marcar job como falho.
- Pular etapa da pipeline.

### 3. Hermes Executor De Playbooks

Responsabilidade:
- Executar somente acoes permitidas e idempotentes.
- Aplicar recuperacao pequena sem perder progresso.
- Registrar antes/depois de cada acao.

Pode:
- Abrir circuit breaker de provider.
- Pausar intake de novas jobs sem mexer nas jobs em andamento.
- Executar `python pipeline.py recover-runtime`.
- Reiniciar um unico processo PM2 quando o playbook permitir:
  `fralib`, `fralib-worker`, `fralib-bryan-worker`, `meowhats` ou
  `gosom-scraper`.
- Rodar reconciliacao Mercado Pago idempotente para pagamentos aprovados que
  nao chegaram via webhook.
- Solicitar reprocessamento a partir de checkpoint existente.

Nao pode:
- `pm2 kill`.
- Reiniciar todos os processos.
- Rodar reset runtime.
- Apagar fila, logs, checkpoints, sites ou cache.
- Editar arquivo local ou remoto.

### 4. Hermes Guard

Responsabilidade:
- Bloquear qualquer acao fora da allowlist.
- Exigir confirmacao humana para reset, limpeza, deploy manual ou mudanca de
  configuracao sensivel.
- Validar tenant scope antes de qualquer acao que envolva job, lead ou site.

Pode:
- Aprovar ou negar comandos solicitados por outros agentes Hermes.
- Abrir alerta `blocked_action`.
- Escalar para humano quando uma acao necessaria for destrutiva.

Nao pode:
- Executar recuperacao.
- Ignorar denylist.

### 5. Hermes Custos E Capacidade

Responsabilidade:
- Medir duracao, tokens, custo estimado e gargalos por fase.
- Recomendar `MAX_PIPELINES_GLOBAL`, cooldown e provider principal com base em
  dados reais.
- Separar gargalo de lead discovery, LLM/Skill Renderer, deploy e Bryan.

Pode:
- Ler `llm_budget_ledger`, spans, jobs e metricas agregadas.
- Gerar recomendacao de capacidade com evidencia.

Nao pode:
- Aumentar concorrencia sozinho.
- Trocar provider sozinho.

### 6. Lead Provider Router

Tipo: servico de pipeline, nao agente autonomo.

Responsabilidade:
- Escolher origem de candidatos nesta ordem:
  1. leads prontos do tenant;
  2. cache global validado;
  3. provider pago configurado;
  4. GoSom saudavel;
  5. Playwright local.
- Nunca deixar um provider externo parar a pipeline global.

Pode:
- Abrir circuit breaker de provider.
- Trocar para proxima origem quando timeout, erro ou fila stale ocorrer.

Nao pode:
- Ignorar score minimo configurado.
- Misturar leads entre tenants.
- Salvar candidato sem dados minimos.

## Mapeamento Dos Agentes Antigos

- `ROBUST-MONITOR`: vira Hermes Monitor. Remover qualquer restart automatico.
- `AUTO-RECOVERY`: legado perigoso. Substituir por Hermes Executor + Guard.
- `INTELLIGENT-ALERTS`: vira Hermes Diagnostico. Sem comandos operacionais.
- `AUTOMATION-CONTROL`: vira orquestrador de playbooks com Guard obrigatorio.
- `KANBAN-DISPLAY`: vira UI/relatorio. Somente leitura.

## Denylist Global

Sempre proibido para agentes Hermes:
- `pm2 kill`.
- `rm`, `find -delete`, limpeza recursiva ou truncamento de logs.
- `DELETE`, `TRUNCATE` ou `UPDATE` amplo sem `tenant_id`/`user_id`.
- Apagar checkpoints.
- Resetar runtime.
- Editar arquivos em `/root/fralib` ou `/var/www/fralib`.
- Marcar job de outro tenant.
- Reprocessar job sem checkpoint ou payload original.

## Playbooks Permitidos

### Provider travado

1. Monitor detecta timeout, fila stale ou excesso de pendentes.
2. Diagnostico classifica provider e evidencia.
3. Guard valida que a acao e allowlist.
4. Executor abre circuit breaker do provider.
5. Pipeline usa proxima origem de candidatos.

### Worker stale

1. Monitor detecta job acima de `JOB_MAX_SECS` ou heartbeat stale.
2. Diagnostico confirma se o processo ainda existe.
3. Executor roda `python pipeline.py recover-runtime`.
4. Se continuar stale, Executor reinicia somente `fralib-worker`.
5. Pipeline retoma por checkpoint.

Automacao atual:
- `HERMES_AUTOREMEDIATE=1` permite o Executor rodar `recover-runtime`.
- Se PM2 mostrar processo critico fora de `online`, o Executor reinicia somente
  o processo allowlistado afetado.
- Cada execucao grava `remediation_applied` ou `remediation_failed`.

### Pagamento aprovado sem credito

1. Monitor detecta erro em evento Mercado Pago.
2. Guard valida `mp_reconcile_apply`.
3. Executor roda a reconciliacao idempotente.
4. O script credita apenas pagamento aprovado com metadata FraLib e ignora
   evento ja processado.
5. Resultado fica registrado como incidente Hermes.

### Skill Renderer lento

1. Monitor mede tempo da fase `builder_renderer` e tokens do ledger.
2. Diagnostico verifica provider/modelo e tamanho dos packs de skill.
3. Executor reinicia somente `fralib-worker` se a fila ficar stale.
4. Pipeline retoma do PRD/checkpoint, sem voltar ao Hunter.

### Caio rejeitando todos

1. Diagnostico registra motivos e score minimo configurado.
2. Provider Router busca complemento de candidatos.
3. Job so falha depois de esgotar pool + complemento.
4. Custos e Capacidade registra taxa de rejeicao por nicho/cidade.

## Criterios De Aceite

- Cada agente tem uma unica responsabilidade primaria.
- Toda acao operacional passa por Guard.
- Toda recuperacao preserva checkpoint e progresso.
- Qualquer comando fora da allowlist vira incidente, nao execucao.
- Producao usa apenas contrato versionado neste repositorio.
