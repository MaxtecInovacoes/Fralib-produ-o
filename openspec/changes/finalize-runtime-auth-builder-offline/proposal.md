## Why

FraLib ja esta deployado no commit `960052c`, mas ainda havia quatro limites operacionais que precisavam sair de "pendencia" e virar contrato: validacao Docker fora do Windows local, smoke com Postgres/portas reais, 2FA obrigatorio, migracao de JWT de `localStorage` para cookie HttpOnly e prova offline de que o Builder aplica idioma, SEO e Fase 6 sem Aibee.

Esta mudanca garante que a seguranca aplicada nao quebre a esteira e que o gerador tenha uma trilha verificavel mesmo quando o provedor LLM esta fora.

## What Changes

- Formalizar OpenSpec como camada de planejamento versionada para mudancas de seguranca/runtime/Builder.
- Validar Docker Compose e smoke no ambiente real da VPS quando o host Windows local nao tiver Docker/Postgres.
- Criar contrato para 2FA obrigatorio no login quando o usuario tiver TOTP ativo.
- Criar contrato para migrar sessao do frontend de JWT em `localStorage` para cookie HttpOnly com CSRF, mantendo rollout seguro.
- Criar teste offline de geracao de site que nao chama Aibee e valida idioma pt-BR, bloqueio de mistura portugues/ingles/chines, SEO keywords, schema, GSAP/Lenis, theme toggle e demais marcadores Fase 6.
- Manter as mudancas de seguranca existentes sem regressao: metricas admin-only, SSE ticket curto, provider URL allowlist, editor IA sanitizado e publish sem metadados internos.

## Capabilities

### New Capabilities

- `runtime-validation`: valida Docker Compose, smoke dry-run, portas e deploy health em ambiente que tenha os servicos reais.
- `auth-session-hardening`: define 2FA obrigatorio por usuario e migracao de sessao para cookie HttpOnly/CSRF.
- `offline-builder-contracts`: prova geracao de site sem Aibee e valida contratos de idioma, SEO, schema, GSAP/Lenis, theme toggle e Fase 6.

### Modified Capabilities

- None.

## Impact

- `openspec/changes/finalize-runtime-auth-builder-offline/*`: artefatos de especificacao.
- `tests/unit/*`: novos testes offline ou ajustes de contrato.
- `backend/endpoints/auth_endpoints.py`, `backend/core/auth.py`, frontend auth scripts: futura implementacao de 2FA/cookie HttpOnly.
- `backend/services/builder_worker.py`, `backend/services/vite_react_renderer.py`, `backend/services/openui_renderer.py`, `backend/agents/html_quality_gate.py`: validacao offline e contratos de publicacao.
- VPS `root@187.77.37.72`: validacao read-only/operacional via Git/PM2/Docker/smoke, sem SCP/rsync.
