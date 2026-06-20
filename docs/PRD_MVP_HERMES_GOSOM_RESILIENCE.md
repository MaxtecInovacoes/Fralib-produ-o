# PRD MVP - Hermes, Hunter e Provedores de Leads Resilientes

## Objetivo

Garantir que a FraLib nao pare quando um provedor externo travar, quando um
lead for rejeitado pelo Caio, ou quando houver falha parcial em um componente.
O sistema deve preservar progresso, reaproveitar candidatos prontos e trocar de
provedor rapido.

## Diagnostico

- GoSom ficou com fila interna travada (`working` antigo + varios `pending`).
- O Hunter tratava GoSom como disponivel e esperava ate 180s antes do fallback.
- Quando o cliente pedia 1 lead, o cache podia retornar apenas 1 candidato; se
  Caio rejeitasse, a job acabava sem tentar outros prontos.
- O controle governado/Hermes antigo usava health checks incorretos e podia
  executar recuperacao destrutiva (`pm2 kill`, limpar fila/logs).

## Contrato Do Hunter

1. Sempre montar pool de candidatos nesta ordem:
   - leads do proprio tenant em `capturado` ou `pendente`;
   - cache global `leads_cache`;
   - provedor rapido pago, quando configurado;
   - GoSom apenas se saudavel;
   - Playwright como ultimo recurso local.
2. Mesmo se o usuario pedir 1 lead, Hunter deve buscar buffer minimo de
   candidatos para o Caio poder rejeitar e continuar.
3. Scraping novo so acontece quando pool pronto/cache nao tiver candidatos
   suficientes.
4. Rejeicao do Caio nao deve parar o sistema global; ela descarta o candidato e
   tenta o proximo dentro do buffer.

## Contrato Do GoSom

GoSom e best-effort, nao dependencia critica.

- Default: desativado salvo `GOSOM_ENABLED=1`.
- Timeout curto: `GOSOM_TIMEOUT=45`.
- Circuit breaker:
  - se houver job `working` mais velho que `GOSOM_STALE_WORKING_SECS`;
  - se houver mais que `GOSOM_MAX_PENDING` jobs pendentes;
  - se um job falhar ou der timeout.
- Circuito aberto por `GOSOM_CIRCUIT_OPEN_SECS`; durante esse periodo o Hunter
  pula GoSom imediatamente.
- Nenhum job da pipeline deve aguardar GoSom por minutos se ha cache, leads
  prontos ou fallback.

## Provedor Pago Recomendado

Prioridade sugerida para MVP comercial:

1. DataForSEO Business Listings `search/live`: retorna endereco, contatos,
   rating, horarios e dados de negocios por localidade, com resposta live e
   custo por request.
2. SerpApi Google Maps: retorna `local_results` com telefone, website, rating,
   reviews, horarios, coordenadas e links.
3. Google Places API: oficial, boa para place id/detalhes/fotos, mas exige
   controle fino de fields/custo.
4. GoSom/Playwright: fallback barato, nao caminho principal de producao.

## Contrato Do Hermes

Hermes e supervisor operacional, nao executor destrutivo.

O contrato detalhado dos agentes autorizados fica em
`docs/HERMES_AGENT_CONTRACT.md`. Qualquer script antigo do Controle Governado
que nao obedecer esse contrato e legado e deve permanecer desativado ate ser
reescrito.

Equipe aprovada:

- Hermes Monitor: somente leitura sobre PM2, banco, logs, health e spans.
- Hermes Diagnostico: classifica incidente e sugere playbook, sem executar.
- Hermes Executor De Playbooks: executa apenas acoes allowlist e idempotentes.
- Hermes Guard: bloqueia denylist e exige confirmacao humana quando necessario.
- Hermes Custos E Capacidade: mede gargalo, tokens, custo e concorrencia segura.
- Lead Provider Router: servico de pipeline para escolher fonte de leads.

Permitido:

- ler PM2, health endpoints, banco e logs;
- abrir incidente com causa provavel e acao sugerida;
- reiniciar apenas um componente especifico com playbook aprovado;
- abrir circuit breaker de provedor;
- executar `python pipeline.py recover-runtime`;
- pausar intake de novas jobs mantendo jobs existentes.

Proibido:

- `pm2 kill`;
- apagar logs recentes;
- limpar fila ou jobs automaticamente;
- remover checkpoints;
- resetar runtime sem comando oficial e confirmacao explicita;
- reiniciar todos os servicos por falso negativo de health.

## Playbooks Seguros

### GoSom travado

1. Detectar job `working` velho ou muitos `pending`.
2. Abrir circuito do GoSom.
3. Pular para pool/cache/provedor alternativo.
4. Reiniciar somente `gosom-scraper` se necessario.
5. Registrar incidente, sem derrubar `fralib-worker`.

### Caio rejeitou candidato

1. Marcar candidato como `descartado`.
2. Tentar proximo candidato do pool.
3. Se pool acabar, buscar complemento com provider alternativo.
4. Encerrar job como sem lead apenas depois de esgotar pool + complemento.

### Worker travado

1. Verificar heartbeat de job e `JOB_MAX_SECS`.
2. Rodar `recover-runtime`.
3. Reprocessar a partir do checkpoint.
4. Reiniciar somente `fralib-worker` se heartbeat continuar stale.

## Criterios De Aceite

- GoSom travado nao segura a pipeline por mais de 45s.
- Pedido de 1 lead avalia buffer minimo antes de falhar.
- Leads capturados/pendentes sao reaproveitados antes de scraping novo.
- Hermes nunca executa acao destrutiva automatica.
- `pre-release-gate` deve passar antes de deploy.
