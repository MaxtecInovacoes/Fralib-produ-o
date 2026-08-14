# FraLib — Handoff Operacional para a Próxima IA

Data: 2026-08-14  
Escopo: pipeline oficial, OpenUI oficial, `frontend/admin.html`, esteira multi-tenant, deploy real na VPS `104.243.41.166`

Este documento existe para impedir que a próxima IA:

- recrie caminhos paralelos;
- debugue arquivos errados;
- confunda runtime real com legado;
- repita investigações já concluídas;
- altere produção por fora do fluxo oficial.

Se este arquivo contradizer qualquer documento antigo em `docs/`, siga este arquivo e o `README.md`.

## 1. Estado atual resumido

### 1.1 O que já está provado

- A **pipeline oficial** está viva e processa jobs reais no tenant `2`.
- O **worker oficial** é `C:\fralib\worker.py`, executado na VPS no container `fralib-worker-1`.
- A **API oficial** é `C:\fralib\server.py`, exposta na VPS como `fralib-api.service` na porta `8001`.
- O **OpenUI oficial** versionado é `C:\fralib\openui-service-wandb\backend\openui\generate.py`.
- O **OpenUI runtime real** na VPS é `/opt/fralib/openui-wandb/backend/openui/generate.py`, via `fralib-openui.service`, porta `7878`.
- O **admin oficial** é `C:\fralib\frontend\admin.html`.
- A **fonte canônica da fila** é a tabela `jobs` no Postgres `fralib_db`.
- O **deploy oficial** publica em `/var/www/fralib/sites/`.

### 1.2 O que já foi corrigido localmente e enviado

Os seguintes ajustes já foram feitos localmente, commitados e enviados para `vps master`:

- remoção de `lgpd` como seção obrigatória na cadeia Arquiteto → Builder → OpenUI;
- banner de LGPD tratado como aviso técnico, não como bloco de conteúdo;
- inferência de `segmento` e `cidade` no `worker.py` para reduzir contexto genérico;
- reforços no handoff para o Builder e no filtro de seções;
- testes unitários específicos do handoff/safe-post passando.

### 1.3 O que ainda está em aberto

Existem **dois trilhos abertos**:

1. **Visual final do site**
   - ainda há casos com LGPD residual, blocos visuais ruins, site genérico, contraste fraco ou composição abaixo do esperado.

2. **Admin operacional**
   - a esteira já chama endpoints corretos, mas a UX ainda deixa o tenant “no escuro” em alguns casos.
   - o maior problema real hoje não é “botão quebrado”, e sim **feedback insuficiente** sobre o motivo de não nascer uma nova pipeline.

## 2. Diagnóstico atual do admin e da esteira

### 2.1 O fluxo real do admin

O `admin.html` já chama os endpoints corretos de esteira:

- `POST /api/lead-supply/start`
- `POST /api/lead-supply/production/tick`
- `POST /api/lead-supply/refill`
- `GET /api/lead-supply/status`
- `POST /api/lead-supply/retry-all`

Arquivos reais:

- `C:\fralib\frontend\admin.html`
- `C:\fralib\backend\endpoints\lead_supply_endpoints.py`
- `C:\fralib\backend\services\lead_supply_inventory.py`
- `C:\fralib\backend\services\lead_supply_engine.py`
- `C:\fralib\worker.py`

### 2.2 O que já foi provado em produção

Na VPS `104.243.41.166`, em 2026-08-14:

- `curl http://localhost:8001/health` retornou OK.
- `docker ps` mostrou:
  - `fralib-worker-1` healthy
  - `fralib-postgres-1` healthy
  - `fralib-redis-1` healthy
- jobs recentes do tenant `2`:
  - `576`, `577`, `578`, `579` em `completed`
- eventos da esteira mostraram:
  - `Site concluído. Próximo lead será puxado pelo controle de plano.`
  - `Sem lead aprovado disponível para produção. Hunter/Caio continuam abastecendo em paralelo.`
  - `Hunter não encontrou lead novo nesta rodada`

### 2.3 O motivo de “clicar e parecer que nada aconteceu”

O problema mais importante do admin agora é este:

- **não havia lead `approved` disponível** para nascer uma nova pipeline;
- o tenant tinha:
  - `site_done = 10`
  - `raw = 2`
  - `error_retry = 4`
  - `approved = 0`

Ou seja:

- o clique foi aceito;
- a esteira respondeu;
- mas não havia insumo elegível para criar uma nova pipeline.

Conclusão:

- **não é problema de endpoint errado**;
- **não é problema de worker morto**;
- **não é pipeline travada**;
- é problema de **observabilidade/UX operacional no admin** e de **estoque aprovado zerado**.

## 3. Último ponto exato onde o trabalho parou

### 3.1 Tema em andamento

O próximo trabalho deveria seguir nesta ordem:

1. consolidar handoff para a próxima IA;
2. melhorar o admin operacional;
3. só depois voltar ao refinamento visual do site.

### 3.2 Próximo objetivo recomendado

Objetivo recomendado para a próxima IA:

> tornar o `frontend/admin.html` operacionalmente confiável para tenants, com timeline clara, feedback de clique, motivo de bloqueio, estado da esteira e tratamento visível de erro sem travar o restante da fila.

## 4. Arquivos reais que devem ser usados

### 4.1 Runtime oficial de geração

- `C:\fralib\worker.py`
- `C:\fralib\backend\agents\manager\agent.py`
- `C:\fralib\backend\agents\manager\states.py`
- `C:\fralib\backend\agents\manager\step_nicho.py`
- `C:\fralib\backend\agents\manager\step_design_director.py`
- `C:\fralib\backend\agents\manager\step_variacao.py`
- `C:\fralib\backend\agents\manager\step_arquiteto.py`
- `C:\fralib\backend\agents\manager\step_builder.py`
- `C:\fralib\backend\agents\manager\step_quality_gate.py`
- `C:\fralib\backend\agents\manager\step_deploy.py`
- `C:\fralib\backend\agents\builder\agent.py`
- `C:\fralib\backend\agents\cinematic_post_processor.py`
- `C:\fralib\backend\agents\visual_fingerprint.py`
- `C:\fralib\openui-service-wandb\backend\openui\generate.py`

### 4.2 Runtime oficial da esteira/admin

- `C:\fralib\frontend\admin.html`
- `C:\fralib\backend\endpoints\lead_supply_endpoints.py`
- `C:\fralib\backend\services\lead_supply_engine.py`
- `C:\fralib\backend\services\lead_supply_inventory.py`
- `C:\fralib\backend\services\lead_supply_storage.py`
- `C:\fralib\backend\services\lead_supply_providers\maps.py`
- `C:\fralib\backend\services\lead_supply_providers\hunter.py`
- `C:\fralib\backend\endpoints\pipeline_endpoints.py`

## 5. Arquivos legados ou perigosos

Não reativar nem usar em runtime:

- qualquer coisa em `C:\fralib\backend\_arquivo\`
- `openui_renderer.py`
- `pipeline_executors.py`
- `pipeline_fases\`
- `pipeline_prompt_agent.py`
- `pipeline_prd_builder.py`
- `pipeline_builders.py`
- `vite_react_renderer.py`
- `builder_worker.py`
- `openui_contracts.py`

Também não criar:

- `tmp_*`
- `fix_*`
- `_debug_*`
- `_test_*`
- `server_v2*`
- `server_new*`
- novos renderers
- novas FSMs
- scripts de deploy alternativos

## 6. Como a próxima IA deve trabalhar

### 6.1 Regra de operação

Sempre seguir este fluxo:

1. encontrar o arquivo oficial;
2. provar por import/rota/claim de worker que ele é usado;
3. propor a menor mudança possível;
4. testar localmente;
5. commitar;
6. `git push github master`;
7. `git push vps master`;
8. validar em produção real;
9. registrar o resultado no documento canônico.

### 6.2 Nunca fazer

- não editar direto na VPS como caminho principal;
- não “resolver rápido” criando endpoint paralelo;
- não criar outro admin;
- não criar outro worker;
- não puxar legado de `backend\_arquivo`;
- não fazer debug só lendo código sem provar no banco/logs;
- não assumir que “não aconteceu nada” sem consultar:
  - `jobs`
  - `lead_inventory`
  - `lead_supply_events`

## 7. Como encontrar o problema certo

### 7.1 Ordem de investigação obrigatória

Quando houver bug de pipeline/admin:

1. verificar saúde da infra;
2. verificar jobs;
3. verificar inventário do tenant;
4. verificar eventos da esteira;
5. só depois entrar no HTML/admin/frontend.

### 7.2 Comandos de saúde

```powershell
ssh -i ~/.ssh/id_ed25519 root@104.243.41.166 "curl -s http://localhost:8001/health"
ssh -i ~/.ssh/id_ed25519 root@104.243.41.166 "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep fralib"
```

### 7.3 Comandos de jobs

```powershell
ssh -i ~/.ssh/id_ed25519 root@104.243.41.166 'docker exec fralib-postgres-1 psql -U fralib_user -d fralib_db -At -F "|" -c "SELECT id,status,attempts,last_phase,left(coalesce(last_error,'''') ,180),tipo,tenant_id FROM jobs ORDER BY id DESC LIMIT 12;"'
```

### 7.4 Comandos de eventos da esteira

```powershell
ssh -i ~/.ssh/id_ed25519 root@104.243.41.166 'docker exec fralib-postgres-1 psql -U fralib_user -d fralib_db -At -F "|" -c "SELECT tenant_id,source,level,left(message,160),criado_em FROM lead_supply_events ORDER BY criado_em DESC LIMIT 12;"'
```

### 7.5 Comandos de inventário

```powershell
ssh -i ~/.ssh/id_ed25519 root@104.243.41.166 'docker exec fralib-postgres-1 psql -U fralib_user -d fralib_db -At -F "|" -c "SELECT status,COUNT(*) FROM lead_inventory WHERE tenant_id=2 GROUP BY status ORDER BY status;"'
```

## 8. Como testar antes de produção

### 8.1 Testes mínimos locais

Rodar apenas os testes relacionados ao que foi tocado.

Exemplo já usado neste ciclo:

```powershell
python -m py_compile C:\fralib\backend\agents\manager\step_arquiteto.py C:\fralib\backend\agents\arquiteto_agent_loop.py C:\fralib\backend\agents\builder\agent.py C:\fralib\backend\agents\manager\step_builder.py C:\fralib\backend\agents\html_builder_repair.py C:\fralib\backend\agents\html_publication_helpers.py C:\fralib\worker.py C:\fralib\openui-service-wandb\backend\openui\generate.py
python -m pytest C:\fralib\tests\unit\test_openui_handoff_safe_post.py C:\fralib\tests\unit\test_pipeline_runtime_contracts.py -q
```

### 8.2 Regra de teste

Se tocou:

- handoff visual,
- builder,
- OpenUI,
- post-processor,
- worker,
- admin da esteira,

então precisa ter:

1. validação local;
2. deploy oficial;
3. verificação real na VPS;
4. E2E real com lead do tenant 2 ou clique real no admin.

## 9. Como colocar em produção

### 9.1 Fluxo oficial

```powershell
git -C C:\fralib status
git -C C:\fralib add <arquivos>
git -C C:\fralib commit -m "mensagem objetiva"
git -C C:\fralib push github master
git -C C:\fralib push vps master
```

### 9.2 Se mexer no OpenUI

Depois do hook, sincronizar runtime real:

```powershell
ssh -i ~/.ssh/id_ed25519 root@104.243.41.166 "install -m 0644 /opt/fralib/openui-service-wandb/backend/openui/generate.py /opt/fralib/openui-wandb/backend/openui/generate.py && systemctl restart fralib-openui.service"
```

## 10. Como validar em produção

### 10.1 Saúde básica

```powershell
ssh -i ~/.ssh/id_ed25519 root@104.243.41.166 "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep fralib"
ssh -i ~/.ssh/id_ed25519 root@104.243.41.166 "systemctl is-active fralib-api.service"
ssh -i ~/.ssh/id_ed25519 root@104.243.41.166 "systemctl is-active fralib-openui.service"
ssh -i ~/.ssh/id_ed25519 root@104.243.41.166 "curl -I https://app.seunegociofralib.site/health"
```

### 10.2 E2E real

Usar de preferência:

- o próprio `frontend/admin.html`; ou
- `POST /api/pipeline/reprocessar/{lead_id}` para lead real.

Depois validar:

- job criado ou mensagem explícita de bloqueio;
- `jobs.status`;
- `lead_supply_events`;
- URL pública;
- HTML final.

## 11. Ponto exato do próximo trabalho

### 11.1 Se a próxima IA pegar o admin

Ela deve começar por:

1. revisar `C:\fralib\frontend\admin.html`;
2. revisar `C:\fralib\backend\endpoints\lead_supply_endpoints.py`;
3. revisar `C:\fralib\backend\services\lead_supply_inventory.py`;
4. confirmar no banco se o problema é:
   - `approved = 0`
   - pipeline já em andamento
   - cooldown/crédito
   - `error_retry` acumulado

Depois:

5. melhorar feedback visual e timeline;
6. mostrar motivo exato do bloqueio no admin;
7. mostrar contagem e última ação da esteira;
8. testar com clique real.

### 11.2 Se a próxima IA pegar o visual do site

Ela deve começar por:

1. confirmar se o HTML ruim veio do OpenUI ou do pós-processamento;
2. comparar:
   - `designer_prd`
   - `openui_payload`
   - `openui_html`
   - `post_processed_html`
   - `final_html`
3. não mexer no admin antes de provar o ponto de degradação visual;
4. não reintroduzir `lgpd` como seção.

## 12. Checklist de encerramento para qualquer IA

Antes de encerrar uma tarefa:

- [ ] provei o arquivo oficial usado em runtime;
- [ ] não criei caminho paralelo;
- [ ] rodei teste local mínimo;
- [ ] publiquei pelo fluxo oficial;
- [ ] validei em produção real;
- [ ] consultei banco/logs reais;
- [ ] deixei documentado o que foi feito;
- [ ] deixei documentado o que falta;
- [ ] deixei claro como reproduzir e validar.

## 13. Estado observado no momento deste handoff

Em 2026-08-14, o estado auditado foi:

- infra saudável;
- jobs `576` a `579` completos;
- tenant `2` com:
  - `site_done = 10`
  - `raw = 2`
  - `error_retry = 4`
  - `approved = 0`
- eventos recentes indicando:
  - site concluído;
  - sem lead aprovado para nova produção;
  - hunter sem novos leads na rodada.

Conclusão operacional do momento:

> a prioridade correta agora é **admin operacional e observabilidade da esteira**, não recriação de pipeline.
