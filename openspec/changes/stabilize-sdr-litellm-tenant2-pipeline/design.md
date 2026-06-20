## Runtime Design

### SDR/Franz

O caminho ativo de atendimento deve ser:

1. `pipeline_orchestrator_service.py` enfileira `franz_outreach`.
2. `fralib-franz-worker` consome apenas jobs SDR novos.
3. `worker.py` cria `FranzInput` e chama `sdr_langgraph.iniciar_contato`.
4. `whatsapp_listener.py` responde inbound chamando `sdr_langgraph.responder_lead` com `sdr_stage` atual do banco e historico recente.
5. `sdr_langgraph.agent.node_load_context` funde memoria flat/nested com dados atuais do banco, preservando tenant e telefone.
6. `services.sdr_gateway.evaluate_sdr_output` valida todo envio real antes de Meowhats.

Compatibilidade com `BryanInput`, `BryanOutput` e `bryan_outreach` pode existir somente para jobs historicos e APIs internas antigas; nenhum fluxo novo deve criar job `bryan_outreach` ou PM2 `fralib-bryan-worker`.

### LLM/Proxy

O caminho de modelo deve ser:

1. `.env` de producao define `ANTHROPIC_BASE_URL` para LiteLLM/APIPROMAX e `ANTHROPIC_API_KEY` para a key do proxy.
2. `agent_model_configs` usa provider `anthropic` e modelos da allowlist do proxy `llm.seunegociofralib.site`.
3. `llm_direct.call_claude` respeita configs do DB e usa fallback hardcoded somente nesses aliases.
4. `vite_react_renderer` faz probe/render somente nesses aliases.
5. Provider keys antigos podem ficar no banco desabilitados, mas endpoints devem impedir reativacao ou uso como fallback.

### Tenant 2 Test

O teste real deve:

1. Validar proxy com completions reais nos aliases canonicos.
2. Garantir que o worker e a app da VPS receberam o commit.
3. Resetar/selecionar lead real tenant 2 sem quebrar outros tenants.
4. Enfileirar pipeline real, acompanhar jobs e logs ate conclusao ou falha externa comprovada.
5. Validar URL publicada, assets, banco, sdr_stage e job `franz_outreach`.
6. Consultar ledger de tokens e custo antes/depois.

## Failure Policy

- Se o proxy APIPROMAX responder 401/403/sem permissao para os aliases permitidos, nao mascarar com provider externo; registrar evidencia antes de gastar pipeline invalida.
- Se Hunter ou Builder travarem por timeout/worker, coletar job id, fase, logs PM2 e erro DB antes de corrigir.
- Se o deploy hook nao atualizar PM2 ou hook instalado, corrigir pelo script versionado do repo na VPS, sem copiar arquivos avulsos.
