# Auditoria de seguranca e escalabilidade - 2026-06-07

## Escopo

Auditoria pratica sobre codigo local em `C:\fralib`, sem editar a VPS direto e sem
depender da API Aibee. O foco foi reduzir risco real em auth, multi-tenant,
Builder, supply chain, Docker, deploy e capacidade operacional.

## Correcoes aplicadas

- Deploy contract agora exige `llms.txt` no hook versionado e no diretorio web.
- Docker passou a rodar o app como usuario `fralib`, com healthcheck em
  `/api/version` e `.dockerignore` cobrindo caches/perfis locais.
- Rate limit passou a aceitar storage distribuido via
  `FRALIB_RATE_LIMIT_STORAGE_URI` ou `REDIS_URL`, mantendo fallback em memoria.
- Pool SQLAlchemy agora so usa parametros de pool Postgres quando a URL e
  Postgres, preservando SQLite em testes.
- Metricas globais ficaram admin-only; `/api/metrics/public` nao expoe stats de
  leads/pipeline.
- Provider `base_url` agora tem allowlist antes de persistir e antes do uso em
  runtime.
- Reenvio de confirmacao passou a exigir senha e resposta generica contra
  enumeracao.
- Anti-abuse de registro so confia em `X-Forwarded-For` vindo de proxy local.
- Editor IA rejeita HTML ativo antes de salvar (`script`, handler inline,
  `javascript:`, `iframe`, `object`, `embed`).
- `python-jose` vulneravel/nao usado saiu das dependencias e `python-dotenv`
  foi atualizado para faixa corrigida.
- Hygiene gate agora bloqueia bancos rastreados (`.db`, `.sqlite`, `.sqlite3`);
  `fralib.db` foi removido do indice Git.
- Builder publish copia o `dist` sem metadados internos
  (`builder-render.json`, `vite-render.json`, `openui-render.json`) e sem
  source maps.
- SSE das telas admin/dashboard passou a usar ticket curto emitido via
  `Authorization`, evitando JWT principal na query string do `EventSource`.
- OpenSpec foi avaliado e documentado como camada de especificacao, nao como
  runtime ou gate.

## Validacao local

- `pytest -q --no-cov --confcutdir=tests\unit tests\unit\test_security_scalability_contract.py tests\unit\test_builder_worker.py tests\unit\test_secret_hygiene_contract.py tests\unit\test_tenant_scope_audit.py tests\unit\test_site_editor_security.py tests\unit\test_auth_security_contract.py`
  - Resultado: 80 passed.
- `pytest -q --no-cov --confcutdir=tests\unit tests\unit\test_phase6_contracts.py -v`
  - Resultado: 30 passed.
- `scripts/check_secret_hygiene.py`
  - Resultado: `secret hygiene ok`.
- `scripts/tenant_scope_audit.py`
  - Resultado: `PASS tenant-scope-audit`.
- `scripts/check_deploy_contract.py`
  - Resultado: `deploy contract ok`.
- `pipeline.py smoke --dry-run`
  - Resultado: sem chamadas LLM e sem deploy; passou env/imports/contratos,
    inclusive Fase 6 30/30; falhou apenas em Postgres local `localhost:5433`
    recusado e timeout de portas locais.

## Capacidade atual

Estado atual e conservador: PM2 com 1 processo web, workers separados e
`MAX_PIPELINES_GLOBAL=1`. Isso protege custo/LLM e evita corrida, mas limita a
producao de sites. Estimativa operacional sem medir p95 real: 2 a 6 sites/hora,
dependendo de Hunter, Caio, Jina, Builder, rede e resposta do provedor LLM.

Usuarios simultaneos de dashboard/API simples dependem do VPS, pool Postgres,
Nginx e latencia. Antes de prometer escala comercial, medir:

- p50/p95/p99 de `/api/version`, login, dashboard e pipeline status.
- conexoes Postgres por processo/worker.
- tamanho e idade da fila `jobs`.
- tempo medio por fase do pipeline.
- taxa de erro de LLM/provider e retries.

## Plano de escala seguro

1. Manter pipeline global em 1 ate medir tempo real e custo por job.
2. Separar readiness: web, DB, fila, workers, Meowhats e LLM/provider.
3. Colocar PgBouncer ou ajustar pool antes de aumentar replicas web.
4. Trocar limite global por semaforo/advisory lock transacional se subir
   `MAX_PIPELINES_GLOBAL`.
5. Isolar listener WhatsApp de replicas web para evitar duplicidade.
6. Ativar Redis para rate limit distribuido em producao.
7. Criar canary pos-deploy que verifique `/llms.txt`, `/api/version`, login,
   stream-token SSE e um site publicado.

## Pendencias e bloqueios

- `/llms.txt` publico ainda depende de instalar/atualizar o hook na VPS pelo
  fluxo Git oficial; nao foi feito `cp` manual por regra do `AGENTS.md`.
- Docker nao foi executado localmente porque o CLI Docker nao esta disponivel no
  ambiente atual.
- Testes que dependem de Postgres local completo nao rodam enquanto
  `localhost:5433` estiver indisponivel.
- 2FA ainda existe como status/config, mas enforcement de login com TOTP exige
  change maior e deve entrar por spec OpenSpec antes de codar.
- Migrar JWT de `localStorage` para cookie HttpOnly e CSRF e uma melhoria
  importante, mas exige mudanca coordenada de frontend/backend.

## Veredito OpenSpec

Valido para FraLib como camada leve de especificacao para mudancas grandes:
auth, billing, SDR, Builder, infra e seguranca. O piloto deve ser em branch
separada com `openspec init`, versionando specs e sem colocar OpenSpec no runtime
Docker/PM2.
