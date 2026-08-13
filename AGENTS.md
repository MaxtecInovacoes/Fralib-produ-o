# FraLib — Instruções Obrigatórias para IAs

Este arquivo é carregado automaticamente por agentes de código. Ele é operacional e tem prioridade sobre documentos antigos em `docs/`.

Leia também `README.md` antes de alterar qualquer coisa.

## Regras Invioláveis

1. Não crie arquivo paralelo se já existe módulo oficial.
2. Não crie `tmp_*`, `fix_*`, `_debug_*`, `_test_*`, `server_v2*`, `server_new*`, `server_chunked*`.
3. Não edite código direto na VPS; edite localmente em `C:\fralib`, faça commit e push.
4. Não substitua a FSM oficial por LangGraph, script direto ou pipeline alternativo.
5. Não substitua o Builder/OpenUI por renderer novo.
6. Não importe arquivos de `backend/_arquivo/` em produção.
7. Não versionar segredos reais em `.env`, `.env.vps` ou `openui-service-wandb/.env`.
8. Antes de remover/mover arquivo, prove ausência de import ativo com `rg`.
9. Depois de tocar pipeline, rode testes específicos e E2E real.

## Produção Real

| Componente | Oficial |
|---|---|
| API | `server.py` via `fralib-api.service`, porta `8001` |
| Worker | `worker.py` via Docker `fralib-worker-1` |
| OpenUI | `/opt/fralib/openui-wandb/backend/openui/generate.py`, porta `7878` |
| Código VPS | `/opt/fralib/` |
| Sites | `/var/www/fralib/sites/` |
| Banco | Docker `fralib-postgres-1`, DB `fralib_db` |
| Redis | Docker `fralib-redis-1` |
| Admin | `frontend/admin.html` servido por domínio público |

## Pipeline Oficial

```text
Admin/API
→ jobs.pipeline_lead
→ worker.py
→ backend/agents/manager/agent.py
→ step_hunter
→ step_caio
→ step_nicho
→ step_design_director
→ step_variacao
→ step_arquiteto
→ step_builder
→ step_quality_gate
→ step_deploy
→ step_franz
```

Arquivos oficiais:

| Função | Arquivo |
|---|---|
| Orquestração | `backend/agents/manager/agent.py` |
| Estado | `backend/agents/manager/states.py` |
| Job queue | `backend/core/job_queue.py` |
| Endpoints pipeline/admin | `backend/endpoints/pipeline_endpoints.py` |
| Builder | `backend/agents/builder/agent.py` |
| OpenUI versionado | `openui-service-wandb/backend/openui/generate.py` |
| Safe post | `backend/agents/cinematic_post_processor.py` |
| Gates | `backend/agents/manager/step_quality_gate.py` |
| Deploy | `backend/agents/manager/step_deploy.py` |
| Artifacts | `backend/agents/artifact_store.py` |
| Fingerprint | `backend/agents/visual_fingerprint.py` |

## Cadeia de Custódia Visual

Toda alteração visual precisa respeitar:

```text
niche_brief
→ creative_direction
→ variation_blueprint
→ designer_prd
→ openui_payload
→ openui_html
→ post_processed_html
→ final_html
```

`variation_blueprint` é a fonte autoritativa para ordem/composição estrutural. `site_build_plan` não pode reconstruir ordem fixa por conta própria.

O pós-processador deve permanecer `safe_only=True`: ele só corrige problemas técnicos e não redesenha o site.

## Legado

Arquivos legados ficam em `backend/_arquivo/services/`.

Não use em runtime:

- `openui_renderer.py`;
- `pipeline_executors.py`;
- `pipeline_fases/`;
- `pipeline_prompt_agent.py`;
- `pipeline_prd_builder.py`;
- `pipeline_builders.py`;
- `vite_react_renderer.py`;
- `builder_worker.py`;
- `openui_contracts.py`.

Se um teste antigo referenciar esses arquivos, atualize o teste para o fluxo oficial ou marque como legado; não reative o código.

## Deploy Correto

```powershell
git status
pytest tests/unit/test_builder_prd_spec.py tests/unit/test_manager_intent_pipeline.py tests/unit/test_openui_handoff_safe_post.py tests/unit/test_visual_fingerprint_quality_gates.py -q
git add -A
git commit -m "mensagem objetiva"
git push github master
git push vps master
```

O hook da VPS executa:

```bash
git --work-tree=/opt/fralib --git-dir=/root/repos/fralib.git checkout -f master
git --work-tree=/opt/fralib --git-dir=/root/repos/fralib.git clean -fd
cd /opt/fralib && docker compose -f docker-compose.prod.yml up -d worker
systemctl restart fralib-api.service
systemctl restart fralib-openui.service
```

Se mudou `openui-service-wandb/backend/openui/generate.py`, sincronize para o runtime real:

```bash
install -m 0644 /opt/fralib/openui-service-wandb/backend/openui/generate.py \
  /opt/fralib/openui-wandb/backend/openui/generate.py
systemctl restart fralib-openui.service
```

## Validação Obrigatória

Depois de deploy:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
systemctl is-active fralib-api.service
systemctl is-active fralib-openui.service
curl -I https://app.seunegociofralib.site/health
```

Se tocou pipeline:

1. Use o admin ou `POST /api/pipeline/reprocessar/{lead_id}`.
2. Monitore `jobs`.
3. Confirme site público HTTP `200`.
4. Confirme `leads.status='concluido'`.
5. Confirme `leads.erro_pipeline` vazio.

SQL de diagnóstico:

```sql
SELECT id,status,attempts,last_phase,left(coalesce(last_error,''),500)
FROM jobs
ORDER BY id DESC
LIMIT 10;
```

```sql
SELECT id,nome,status,site_url,erro_pipeline
FROM leads
WHERE user_id=2
ORDER BY atualizado_em DESC
LIMIT 10;
```

## Estado Validado

Último E2E real validado em 2026-08-13:

- lead `Legacy Centro de Treinamento`;
- tenant `2`;
- job `480`;
- URL `https://app.seunegociofralib.site/sites/2/legacy-centro-de-treinamento-b0b7a7c0/`;
- HTTP `200`;
- `1` `<main>`, `8` `<section>`, `1` `<h1>`, `9` `<img>`;
- OpenUI, API e worker saudáveis.

## Quando Estiver em Dúvida

Pare e responda com:

1. qual arquivo oficial você encontrou;
2. qual import/rota prova que ele é usado;
3. qual mudança mínima você propõe;
4. quais testes vai rodar.

Não “melhore” criando outro caminho. O sistema funciona quando todo mundo segue o caminho único.
