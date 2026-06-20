## Why

O SDR/Franz vinha apresentando respostas sem contexto, possiveis vestigios do agente Bryan legado e risco de usar modelos/provedores fora do proxy da VPS. Ao mesmo tempo, a pipeline precisa gerar um site real para o tenant 2 usando `llm.seunegociofralib.site` com aliases APIPROMAX proprios, sem escapar para OpenRouter, Google direto ou Ollama.

Esta mudanca transforma a correcao em contrato auditavel: primeiro estabilizar atendimento SDR, depois travar a hierarquia/modelos da pipeline no LiteLLM/APIPROMAX, por fim executar teste real tenant 2 com site publicado e SDR validado.

## What Changes

- Auditar todos os caminhos ativos do SDR: listener WhatsApp, worker, cron, envio manual, orquestrador, memoria, RAG, filas e PM2.
- Manter apenas compatibilidade historica para nomes Bryan onde necessario para jobs antigos, sem uso em caminho ativo novo.
- Corrigir o LangGraph para usar o `sdr_stage` real do banco, carregar memoria antiga nested, impedir salto indevido de stage, responder decisor/gatekeeper/agendamento e bloquear persona agressiva por default.
- Travar a pipeline em `anthropic` compat via LiteLLM/APIPROMAX com modelos permitidos apenas pelos aliases do proxy `llm.seunegociofralib.site`.
- Bloquear provider/modelos externos em configs de agente, provider keys e fallbacks de renderer.
- Remover Ollama/Open WebUI da stack alvo e manter somente LiteLLM + PostgreSQL no compose versionado.
- Validar local, commit/push/deploy oficial e rodar pipeline real do tenant 2 ate site publicado.
- Medir ledger de tokens/custo e reportar se o proxy trouxe economia real.

## Capabilities

### New Capabilities

- `sdr-franz-runtime-contract`: garante que o atendimento ativo usa Franz/LangGraph com contexto tenant-scoped, stage do banco e guardrails antes de envio.
- `litellm-proxy-model-contract`: garante que agentes de pipeline usam o proxy da VPS e a allowlist APIPROMAX, sem escape para provedores externos.
- `tenant2-real-pipeline-smoke`: executa pipeline real tenant 2, valida site publicado, fila/SDR e custo em ledger.

### Modified Capabilities

- `builder-renderer`: renderer Vite/React passa a resolver aliases de fallback via proxy.
- `agent-model-admin`: admin deixa de permitir modelos/provedores fora do contrato atual.
- `infra-ai-stack`: stack versionada passa a conter apenas LiteLLM + Postgres e Nginx para chat desativado.

## Impact

- `backend/agents/sdr_langgraph/*`: memoria, stage, fallback, persona e roteamento LangGraph.
- `backend/whatsapp_listener.py`, `worker.py`, `backend/endpoints/cron_endpoints.py`, `backend/endpoints/leads_endpoints.py`: caminhos ativos de atendimento.
- `backend/endpoints/pipeline_orchestrator_service.py`, `backend/core/job_queue.py`, `backend/endpoints/queue_endpoints.py`: fila e orquestracao Franz.
- `backend/agents/llm_direct.py`, `backend/services/vite_react_renderer.py`, `backend/endpoints/agent_config_endpoints.py`, `backend/endpoints/provider_keys_endpoints.py`: modelo/proxy.
- `infra/ai-stack/*`: stack LiteLLM/APIPROMAX versionada sem Ollama/Open WebUI.
- VPS `root@187.77.37.72`: deploy via Git e validacao operacional, sem SCP/rsync.
