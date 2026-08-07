# BRIEF CIRÚRGICO — Claude Code (Mecânico) — VPS Nova Tenant 2

## CONTEXTO
Você é o mecânico. O cérebro (Hermes) já diagnosticou os 3 bugs exatos que travam a pipeline do tenant 2 na VPS nova (`100.124.56.36` via Tailscale, SSH: `ssh -i ~/.ssh/id_ed25519 root@100.124.56.36`). O projeto FraLib está em `/opt/fralib/` na VPS. Os containers Docker estão rodando.

## DIAGNÓSTICO (já validado pelo cérebro)

### Bug 1: OPENUI_SERVICE_URL no .env aponta para hostname inexistente
- **Arquivo:** `/opt/fralib/.env`
- **Valor atual:** `OPENUI_SERVICE_URL=http://openui:7878`
- **Problema:** O hostname `openui` não resolve dentro dos containers Docker. Jobs 151 e 146 falharam com `Failed to resolve 'openui'`.
- **Docker-compose.prod.yml** sobrescreve com `http://host.docker.internal:7878` (que funciona — HTTP 200 confirmado de dentro do container).
- **Fix:** No arquivo `/opt/fralib/.env`, alterar a linha `OPENUI_SERVICE_URL=http://openui:7878` para `OPENUI_SERVICE_URL=http://host.docker.internal:7878`.
- **Isso garante que mesmo se o .env for lido sem o override do compose, o valor será correto.**

### Bug 2: lead_supply_engine não hidrata lead_data ao enfileirar pipeline_lead
- **Arquivo:** `/opt/fralib/backend/services/lead_supply_engine.py` (linhas ~754-772 conforme playbook)
- **Problema:** Job 156 (pipeline_lead) tem `payload._lead_id_existente = "236f7cb9-..."` mas `payload.lead_data = {}` (vazio). O Manager FSM em `backend/agents/manager/agent.py:step_hunter` valida `state.lead_data` e se estiver vazio retorna `STATE_FAILED` com erro "Hunter sem lead".
- **Causa raiz:** Quando o `lead_supply_engine` enfileira um job `pipeline_lead` para um lead já existente (que veio do Hunter/Caio), ele não está buscando os dados do lead no banco e injetando em `payload["lead_data"]`.
- **Fix:** Em `lead_supply_engine.py`, na função que enfileira jobs `pipeline_lead` para leads existentes (buscar por onde `pipeline_lead` é enfileirado com `_lead_id_existente`):
  1. Antes de enfileirar, fazer SELECT dos dados do lead na tabela `leads` WHERE `id = _lead_id_existente`
  2. Hidratar `payload["lead_data"]` com: nome, cidade, segmento, telefone, whatsapp, website, rating, reviews_count, fotos, market_intelligence (se existir)
  3. Só enfileirar o job se `lead_data` não estiver vazio (se estiver, logar warning e NÃO enfileirar — evita job fadiga)

### Bug 3: Arquiteto recebe PRD incompleto do LLM (rate limit DeployFlow)
- **Arquivo:** `/opt/fralib/backend/agents/arquiteto/agent.py`
- **Problema:** Job 144 falhou com `Arquiteto: DesignerPRD incompleto: business_name, hero, sections, ctas, faqs, paleta`
- **Causa raiz:** LLM retornou resposta vazia ou incompleta (provavelmente rate limit 503 do DeployFlow ou modelo indisponível). O código do Arquiteto não tem retry para erros transientes (diferente do Manager que já tem retry em `step_arquiteto`).
- **Verificar:** O `step_arquiteto` em `manager/agent.py:191-288` JÁ tem retry com backoff para erros transientes. Mas o erro "DesignerPRD incompleto" é um erro ESTRUTURAL (não transiente) — `gerar_prd` retornou um objeto com campos faltando.
- **Fix:** Em `arquiteto/agent.py`, na função `gerar_prd`:
  1. Se o LLM retornar texto vazio OU JSON incompleto (campos obrigatórios faltando), tratar como erro **transiente** (rate limit provável) e fazer retry interno (2 tentativas com backoff de 5s e 15s)
  2. Se após retry ainda estiver incompleto, lançar exceção clara: `RuntimeError(f"LLM retornou PRD incompleto após {max_attempts} tentativas: campos faltando = {missing}")`
  3. Isso faz o retry do `step_arquiteto` no Manager funcionar corretamente (o erro vira transiente)

## INSTRUÇÕES DE EXECUÇÃO

1. **SSH na VPS:** `ssh -i ~/.ssh/id_ed25519 root@100.124.56.36`
2. **Diretório do projeto:** `/opt/fralib/`
3. **Não alterar lógica de negócio** — apenas corrigir os 3 bugs acima
4. **PT-BR** em comentários e mensagens
5. **Backup antes de editar:** `cp /opt/fralib/.env /opt/fralib/.env.bak.$(date +%Y%m%d_%H%M%S)` e `cp /opt/fralib/backend/services/lead_supply_engine.py /opt/fralib/backend/services/lead_supply_engine.py.bak.$(date +%Y%m%d_%H%M%S)` e `cp /opt/fralib/backend/agents/arquiteto/agent.py /opt/fralib/backend/agents/arquiteto/agent.py.bak.$(date +%Y%m%d_%H%M%S)`
6. **Após edits, reconstruir/restartar containers:** `cd /opt/fralib && docker compose -f docker-compose.prod.yml restart worker-pipeline worker-cron worker-franz app`
7. **Reenfileirar job 156 para teste:** `docker exec fralib-postgres-1 psql -U fralib_user -d fralib_db -c "UPDATE jobs SET status='pending', attempts=0, next_retry_at=NOW() WHERE id = 156;"`
8. **Monitorar:** `docker logs -f fralib-worker-pipeline-1` — observar se o job 156 (ou novo pipeline_lead) progride: Hunter OK → Caio OK → Arquiteto OK → Builder OK → Deploy OK
9. **Validar sucesso:** Verificar se um dos 7 leads do tenant 2 fica com `status='concluido'` e `site_url IS NOT NULL`:
   `docker exec fralib-postgres-1 psql -U fralib_user -d fralib_db -c "SELECT id, nome, status, sdr_stage, site_url IS NOT NULL as has_site FROM leads WHERE user_id = 2 ORDER BY criado_em DESC LIMIT 10;"`

## REGRAS DO PROJETO (NÃO QUEBRAR)
1. NÃO usar LangGraph — orquestrador é FSM pura
2. NÃO usar renderers alternativos — Builder OpenUI é o único caminho
3. NÃO duplicar agentes — melhore agent.py existente
4. NÃO mexer em agents/_shared/
5. Git: `SKIP_V11_PROTECTION=1 git commit -m "..."` se necessário

## ENTREGÁVEL
Relatório com: o que fez, comandos executados, output de cada fix, e estado final da pipeline (lead concluído com site? se não, qual blocker?).
