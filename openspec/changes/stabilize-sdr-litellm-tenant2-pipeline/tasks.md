## 1. OpenSpec

- [x] 1.1 Criar proposal/design/tasks para SDR + LiteLLM + tenant 2.
- [x] 1.2 Atualizar tarefas conforme achados de auditoria.

## 2. SDR/Franz

- [x] 2.1 Auditar vestigios ativos de Bryan em worker, listener, cron, manual send, orquestrador, PM2 e filas.
- [x] 2.2 Corrigir passagem de `sdr_stage` do banco para `responder_lead`.
- [x] 2.3 Corrigir memoria nested/flat e contexto tenant-scoped no LangGraph.
- [x] 2.4 Garantir respostas deterministicas seguras para decisor, gatekeeper, agendamento, horario bloqueado e fallback sem LLM.
- [x] 2.5 Desativar persona agressiva por default.
- [x] 2.6 Validar que novos jobs usam `franz_outreach` e PM2 usa `fralib-franz-worker`.

## 3. Proxy/Modelos

- [x] 3.1 Auditar configs/fallbacks de agentes, renderer e provider keys.
- [x] 3.2 Travar modelos permitidos nos aliases do proxy `llm.seunegociofralib.site`.
- [x] 3.3 Garantir que Builder Renderer e playground/teste admin nao usam aliases Claude/OpenRouter.
- [x] 3.4 Versionar stack LiteLLM-only em `infra/ai-stack`.

## 4. Validacao Local

- [x] 4.1 Rodar compileall dos modulos alterados.
- [x] 4.2 Rodar pytest focado em SDR, model lock, job queue, provider repair, renderer e pipeline route.
- [x] 4.3 Rodar `git diff --check` e validar `AGENTS.md` <= 80 linhas.

## 5. Deploy

- [x] 5.1 Commitar localmente.
- [x] 5.2 Pushar pelo fluxo oficial.
- [x] 5.3 Validar VPS com commit aplicado, PM2 correto e sem `fralib-bryan-worker`.

## 6. VPS/Proxy

- [ ] 6.1 Validar LiteLLM/APIPROMAX na VPS com alias builder `claude-sonnet-4-6` (bloqueado: APIPROMAX retorna 403 direto).
- [ ] 6.2 Validar LiteLLM/APIPROMAX na VPS com alias leve `claude-haiku-4-5` (bloqueado: APIPROMAX retorna 403 direto).
- [x] 6.3 Confirmar provider_keys externos desativados e agent_model_configs normalizados.

## 7. Pipeline Real Tenant 2

- [x] 7.1 Escolher/resetar lead real tenant 2.
- [ ] 7.2 Rodar pipeline real completa (suspenso ate chave APIPROMAX ter acesso; ultimo job real falhou no builder_renderer por acesso/credito).
- [ ] 7.3 Validar site publicado e assets.
- [x] 7.4 Validar job/stage SDR Franz.
- [x] 7.5 Consultar tokens/custo e concluir se proxy economizou.
