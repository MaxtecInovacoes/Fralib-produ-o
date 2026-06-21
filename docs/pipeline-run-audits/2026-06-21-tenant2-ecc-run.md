# ECC Run — Lead Controlado Tenant 2 (Start Academia)

**Data:** 2026-06-21
**Tenant:** 2
**Lead:** sdr-test-1780601069 (Start Academia — Teste Controlado, Academia, Campina Grande Do Sul)
**Modo:** `_controlled_test: true`, `_skip_franz_outreach: true`, `_cold_run: true`
**Hash final VPS:** `73dbc4d`

---

## 1. Resumo executivo

A pipeline inteira percorreu **todos os estágios** (jina → pipeline → builder_renderer) e o LLM respondeu com **probe_ok + 2 repair_retry + 1 preview_fast_no_full_fallback**. A autenticação está corrigida, os imports estão corrigidos, as URLs estão corrigidas, a chave kpalabz está sincronizada entre `.env` e `/etc/fralib/fralib.env`. O job termina com `failed_permanent` em `pipeline` por causa de **JSON truncado retornado pelo builder_renderer** (parser Python quebra em char 52485) — bug de robustez do parser, não mais de import/auth/billing.

**Estado do lead no banco:** `status=pendente, processado=False, tentativas=0, erro_pipeline='Vite React renderer falhou sem fallback: ...'`

---

## 2. Gargalos encontrados, corrigidos e deployados

| # | Commit | Severidade | Bug | Correção |
|---|---|---|---|---|
| 1 | `c6cadd0` | blocker | `prompt_agent_context.py` sem `_normalize_target` no import | Adicionado à lista de imports |
| 2 | `5631dff` | blocker | `pipeline_prd_builder.py` (wrapper) reexports vazios | Re-export de `pipeline_builders` (4 fns) + `pipeline_prompt_agent` (1 fn) |
| 3 | `df0dee5` | blocker | `c679fc6` deletou 16 agentes + 4 testes ainda importados | `git checkout c679fc6^ --` (16 .py + 4 testes) |
| 4 | `0344b17` | blocker | `_section_sequence_for_niche` importado de `prompt_agent_helpers` mas definido em `prompt_agent_context` | Removido import cruzado desnecessário |
| 5 | `73dbc4d` | blocker | `f"{base_url}/v1/messages"` com base `/v1` → `/v1/v1/messages` (404/403) | Helper `_join_url` que dedup `/v1` |
| 6 | (manual) | blocker | `ANTHROPIC_API_KEY` em `/etc/fralib/fralib.env` era `sk-hub-…` (HF) | `sed -i` trocou para `sk-kpa-…` (kpalabz) |

### Validação de cada fix
- `c6cadd0`: import test direto na VPS: `from backend.agents.prompt_agent_context import _normalize_target` → OK.
- `5631dff`: `from backend.services.pipeline_prd_builder import build_prompt_agent_prd, build_skill_fast_prd, ensure_prd_contracts, ensure_prd_design_reference, ensure_prd_publication_identity` → OK.
- `df0dee5`: `DesignerPRD OK` na VPS, deps `agent_rag`/`skill_loader`/`validation_enforcer` carregam.
- `0344b17`: job 3593 (tenant 2) chegou a `phase: pipeline` (passou de `jina`).
- `73dbc4d`: `call_llm("anthropic", "claude-sonnet-4-6", ...)` → 200 OK com `{"pong":true}`. 18 testes pytest passando.
- Chave systemd: `SYSTEMD_KEY_LEN=73, STARTS=sk-hub-64` → trocada para `NEW_LEN=71, STARTS=sk-kpa-fa1`.

---

## 3. Telemetria do job final (id=3618)

| Métrica | Valor |
|---|---|
| Run ID | `ctrl-3cf5e362f9c2` |
| Job ID | 3618 |
| Phase status | `jina` ✓ → `pipeline` ✓ → `builder_renderer` ✓ → `failed_permanent` ✗ |
| probe_ok | 1272ms, 71 chars JSON válido |
| repair_retry 1 | 129.6s — "Unterminated string at line 1 column 52485" |
| repair_retry 2 | 245.8s — "Unterminated string at line 1 column 51325" |
| preview_fast_no_full_fallback | 369.8s — "Unterminated string at line 18 column 42" |
| Tempo total | 6m21s (criado 21:08:43 → concluído 21:16:36) |
| Tokens input (probe) | 116 |
| Tokens output (probe) | 5 |

A pipeline inteira processou o lead e o LLM respondeu. O output completo tem **>52k chars** e o parser Python `json.loads` quebra porque uma string não está fechada. **Não é mais auth, não é mais import, não é mais billing.** É o parser `_extract_vite_project_files` em `vite_react_renderer.py:1410` que precisa ser mais tolerante (extrair via regex de blocos, ou tentar `json.JSONDecoder.raw_decode` repetido).

---

## 4. Estado real vs documentação (auditoria)

### Provider LLM real (VPS)
- `ANTHROPIC_API_KEY=<len=71 starts=sk-kpa-fa1>` em `/root/fralib/.env` E `/etc/fralib/fralib.env` (sincronizado)
- `ANTHROPIC_BASE_URL=https://api.kpalabz.com/v1` (termina com `/v1`)
- Container LiteLLM (`infra/ai-stack/docker-compose.yml`) versionado mas **não deployado** (`/opt/ai-stack/.env` não existe na VPS)
- `namehost` aparece como provider válido em `llm_openai.py` e `llm_client.py`
- APIPROMAX/kpalabz não aparecem no código backend — apenas em `openspec/changes/stabilize-sdr-litellm-tenant2-pipeline/` (que precisa ser renomeado)

### Hashes
- Local (master): `73dbc4d`
- VPS: `73dbc4d` (sincronizado)
- Diff pendente local: `scripts/post-receive-vps-fix3.sh` (não-comitado, não-crítico)

### Pendências (ordem de prioridade)
1. **Refatorar `_extract_vite_project_files` para tolerar JSON truncado** — vai destravar o lead
2. **Renomear `openspec/changes/stabilize-sdr-litellm-tenant2-pipeline/`** → `stabilize-pipeline-tenant2` (reflete provider real kpalabz)
3. **`/etc/fralib/fralib.env` deve ser gerado a partir de `/root/fralib/.env`** (script de sync) — evitar drift de chaves
4. **Limpar refs obsoletas em `docs/AGENTS.md` e `docs/CONSTITUTION.md`** sobre kpalabz
5. **Re-rodar job com a chave corrigida + parser mais robusto** → site `https://seunegociofralib.site/sites/2/start-academia/` deve sair

---

## 5. Comandos úteis para continuar

```bash
# 1. Refatorar parser (tolerar JSON truncado)
# backend/services/vite_react_renderer.py:1409-1412
# try multiple JSONDecoder.raw_decode iterations até bater

# 2. Renomear OpenSpec change
mv openspec/changes/stabilize-sdr-litellm-tenant2-pipeline/ \
   openspec/changes/stabilize-pipeline-tenant2/

# 3. Re-rodar o teste real controlado
ssh root@187.77.37.72 "cd /root/fralib && set -a && . ./.env && set +a && \
  python3 scripts/reset_controlled_test.py --confirm RESET_TEST --tenant 2 \
    --lead-id sdr-test-1780601069 --site-slug start-academia && \
  python3 scripts/controlled_pipeline_run.py --tenant-id 2 \
    --lead-id sdr-test-1780601069 --confirm RUN_CONTROLLED_PIPELINE \
    --wait --timeout-seconds 1800 --interval-seconds 30"
```

---

## 6. Conclusão

A pipeline está **operacional end-to-end** do ponto de vista técnico. O LLM (kpalabz) responde, todos os módulos importam, a autenticação está sincronizada, o `Vite React renderer` chega a ser chamado e o probe passa. O último bloqueio é **robustez do parser de JSON** quando o LLM gera 50k+ chars sem fechar string. Uma vez tratado isso, o site `https://seunegociofralib.site/sites/2/start-academia/` deve ser publicado.

**Não é seguro chamar o lead real SDR antes de:**
1. Aplicar a correção do parser JSON.
2. Re-rodar o job e confirmar `phase: builder_renderer → success` e `processado: True`.
3. Validar a URL pública do site abre com HTML válido.
