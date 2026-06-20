# Mercado Pago, legal e hardening de sessao

Status em 2026-06-08: Mercado Pago e o provedor unico de billing do FraLib.

## O que foi implementado

- `/api/credits/criar-checkout` usa Mercado Pago sem fallback de billing alternativo.
- Planos `starter`, `pro` e `agency` usam Assinaturas/Preapproval (`/preapproval`) com cobranca mensal e `notification_url` por assinatura criada.
- Recarga livre e pacotes atuais usam Checkout Pro (`/checkout/preferences`) com PIX e cartao disponiveis pelo checkout Mercado Pago.
- `MERCADOPAGO_ACCESS_TOKEN` e usado apenas no backend.
- Webhook `/api/credits/webhook/mercadopago` valida `x-signature` quando `MERCADOPAGO_WEBHOOK_SECRET` esta configurado.
- Em `FRALIB_ENV=prod`, webhook Mercado Pago sem segredo configurado retorna erro e nao processa.
- Eventos Mercado Pago entram em `mercadopago_events` com idempotencia.
- O webhook consulta `GET /v1/payments/{id}` ou `GET /preapproval/{id}` antes de liberar creditos/plano.

## Variaveis necessarias

```env
MERCADOPAGO_ACCESS_TOKEN=APP_USR...
MERCADOPAGO_WEBHOOK_SECRET=...
MERCADOPAGO_PLAN_STARTER_AMOUNT=97
MERCADOPAGO_PLAN_PRO_AMOUNT=197
MERCADOPAGO_PLAN_AGENCY_AMOUNT=497
MERCADOPAGO_PLAN_TOKENS_AMOUNT=50
MERCADOPAGO_RECHARGE_MAX_AMOUNT=5000
APP_URL=https://seudominio.com
FRALIB_ENV=prod
```

## Webhook Mercado Pago

Configurar no painel Mercado Pago:

- URL: `https://seudominio.com/api/credits/webhook/mercadopago?source_news=webhooks`
- Eventos minimos: pagamentos (`payment`) e assinaturas/preapproval quando disponivel no painel.
- Secret: mesmo valor de `MERCADOPAGO_WEBHOOK_SECRET`

Para Assinaturas, o Mercado Pago pode nao exibir a configuracao de Webhooks no
painel comum. Nesse caso, o FraLib ja envia a URL no campo `notification_url`
ao criar cada Preapproval. Para recarga livre/pacotes, a mesma URL tambem e
enviada na Preference do Checkout Pro.

## Rotina aprovada para habilitar venda real na VPS

Nao cole token Mercado Pago no chat, em commit ou no frontend. Gere o token de
producao no painel Mercado Pago e aplique somente no terminal da VPS:

```bash
cd /root/fralib
./scripts/vps_prepare_redis.sh
python3 scripts/vps_apply_prod_runtime.py --app-url https://seudominio.com --restart
python3 scripts/vps_validate_prod_launch.py --smoke
```

O script `vps_apply_prod_runtime.py` pede `MERCADOPAGO_ACCESS_TOKEN` e
`MERCADOPAGO_WEBHOOK_SECRET` por entrada oculta no terminal, grava apenas o
`.env` preservado da VPS, seta `FRALIB_ENV=prod`, `FRALIB_COOKIE_SECURE=1` e
Redis distribuido, reinicia PM2 se `--restart` for usado e cria backup
permissionado fora do repo em `/root/fralib-env-backups`.

Se o secret do webhook for gerado pelo script, copie o mesmo valor do `.env` da
VPS para o painel Mercado Pago. Se ele for gerado pelo painel, informe esse
valor quando o script perguntar. A validacao final deve terminar com:
`status: LIBERADO TECNICAMENTE PARA COBRANCA REAL`.

## Recorrencia

O codigo atual cria assinaturas nativas via Mercado Pago Preapproval e salva `mercadopago_subscription_id`. Pagamentos mensais aprovados renovam creditos e status; preapproval cancelado/pausado/rejeitado marca a conta como inadimplente.

## Aceite legal

- Cadastro exige `accept_terms=true` e `accept_privacy=true`.
- Banco grava `terms_accepted_at`, `terms_version`, `privacy_accepted_at`, `privacy_version` e `legal_acceptance_ip`.
- Paginas publicas no Nginx atual: `/docs/termos.html` e `/docs/privacidade.html`; o app FastAPI tambem responde aliases `/termos` e `/privacidade` em `:8000`.
- Docs fonte: `docs/TERMOS_USO_FRALIB.md` e `docs/POLITICA_PRIVACIDADE_LGPD_FRALIB.md`.

## Sessao e CSRF

- Login passa a setar `fralib_session` HttpOnly e `fralib_csrf`.
- Endpoints protegidos aceitam Bearer legado ou cookie.
- Se o token vier por cookie em metodo inseguro, `X-CSRF-Token` precisa bater com cookie `fralib_csrf`.
- `/api/csrf-token` agora emite cookie real.
- O frontend usa cookie-first; Bearer em `localStorage` permanece apenas como compatibilidade para sessoes antigas e impersonacao superadmin.

## 2FA

- Login exige TOTP se `users.totp_enabled=true`.
- `FRALIB_REQUIRE_2FA=1` e `FRALIB_REQUIRE_2FA_ROLES=superadmin,admin` podem bloquear acesso sem setup 2FA.
- Antes de ativar obrigatoriedade para todos, criar fluxo de setup com QR/backup codes.

## Gaps que ainda dependem de infra ou fase maior

- Ativar `FRALIB_ENV=prod`, Mercado Pago real e Redis pela rotina
  `scripts/vps_apply_prod_runtime.py` + `scripts/vps_validate_prod_launch.py`.
- HTTPS publico deve ser obrigatorio antes de remover Bearer/localStorage.
- Remover os ultimos usos de `localStorage.getItem('fralib_token')` ligados a SSE/impersonacao quando houver substituto completo.
- Implementar setup 2FA completo com QR, backup codes e politica obrigatoria por plano/role.
- Endurecer CSP removendo scripts inline e CDNs sem SRI onde ainda existirem.
