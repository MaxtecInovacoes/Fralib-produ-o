# FraLib AI Stack

Stack versionado para a VPS de LLM:

- `ai-litellm` em `127.0.0.1:4000`
- `ai-litellm-db` interno no Docker
- `STORE_MODEL_IN_DB=true`
- sem Ollama
- sem Open WebUI
- OpenRouter/Groq/Gemini/GitHub Models via LiteLLM; chaves reais so no `.env` da VPS

O arquivo `.env` real fica somente na VPS em `/opt/ai-stack/.env`.
Use `.env.example` como contrato de variaveis, sem commitar segredos.

Estado esperado:

```bash
cd /opt/ai-stack
docker compose up -d
curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://127.0.0.1:4000/v1/models
```

Aliases canonicos:

- `fralib-builder-strong`: Builder/coding e site final.
- `fralib-agent-balanced`: Franz/SDR e agentes com contexto.
- `fralib-fast-cheap`: classificacao e tarefas curtas.
- `fralib-json-repair`: reparo/validacao JSON.
- `fralib-research`: pesquisa/sintese.

Se `chat.seunegociofralib.site` ainda responder `200`, confira se o server
block `nginx-chat-disabled.conf` esta habilitado. O estado aposentado esperado
para esse host e `410 Gone`.
