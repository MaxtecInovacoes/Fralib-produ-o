# Franz SDR — Bugs Corrigidos (NUNCA repetir)

> Este doc lista os 7 bugs mais importantes que foram corrigidos no Franz
> SDR. Cada um tem: **sintoma, causa raiz, fix aplicado, como prevenir**.
> Leia antes de mexer em produção.

---

## Bug #1 — Stage-loop (o mais grave)

**Sintoma:** Lead que so cumprimentava (ex: "boa noite", "oi", "eai")
ficava travado em `hook` para sempre. O Franz respondia 5+ vezes a mesma
coisa sem avancar. **Leads reais nao tinham retorno.**

**Causa raiz:** Em `backend/agents/sdr_langgraph/agent.py:170` (codigo antigo),
a funcao `_next_stage()` forçava avanco de 1 step por turno E se o LLM
sugerisse o mesmo stage atual, retornava o stage atual (sem avancar):

```python
def _next_stage(current, suggested, fallback):
    if suggested_idx <= current_idx:
        return current  # <-- BLOQUEAVA AVANCO
    return STAGE_PROGRESSION[min(current_idx + 1, suggested_idx)]
```

Quando o lead dizia "oi", o LLM corretamente sugeria `next_stage=hook` (lead
so cumprimentou, nao engajou). O codigo forçava `return current = hook`.
Proximo turno idem. **Loop eterno.**

**Fix:** Substituir `_next_stage` por FSM + Intent + Orchestrator.
Agora o sistema decide com base em `(state, intent)`, nao em stage linear.
Veja `docs/SDR_STUDIO_10_10.md` secao 2.

**Como prevenir:**
- NUNCA mais criar logica "se stage_atual == suggested: return current"
- SEMPRE passar pelo `orchestrator.orchestrate(...)` que tem loop detection
- Adicionar teste de regressao se mexer no stage logic (veja `TestOrchestratorRegressionHookLoop`)

---

## Bug #2 — `WHATSMEOW_DB_URL` ausente

**Sintoma:** Listener de WhatsApp recebia mensagem do lead mas **nao achava
o lead no banco** e ignorava. `pipeline_traces` cheio de
`Lead nao encontrado para {LID} - ignorando`.

**Causa raiz:** O `meowhats` (serviço que hospeda WhatsApp na porta 3001)
precisa de uma connection string Postgres pra resolver **LID -> telefone**.
O `fralib-wpp-listener.service` carrega env de `/etc/fralib/fralib.env`
(EnvironmentFile do systemd). **Esse arquivo estava sem `WHATSMEOW_DB_URL`.**

**Fix:** Adicionar em `/etc/fralib/fralib.env`:
```
WHATSMEOW_DB_URL=postgresql://postgres:fralib2024@localhost:5433/fralib_db
```
E reiniciar `fralib-wpp-listener`.

**Como prevenir:**
- Quando adicionar nova env var, validar via:
  ```bash
  ssh root@187.77.37.72 "systemctl show fralib-wpp-listener -p EnvironmentFiles"
  ```
- Adicionar log de warning no startup do listener se var critica estiver vazia

---

## Bug #3 — `CRON_SECRET` ausente (cron jobs davam 500)

**Sintoma:** Endpoints `POST /api/cron/followup-bryan` e
`/api/cron/despachar-fila-bryan` retornavam **500** com detalhe
"CRON_SECRET nao configurado no .env".

**Causa raiz:** O codigo em `backend/endpoints/cron_endpoints.py:30`
verifica `CRON_SECRET = os.getenv('CRON_SECRET', '')` e se vazio, retorna
500. O env nao tinha essa var.

**Fix:** Adicionar `CRON_SECRET=...` (32 bytes random) em
`/etc/fralib/fralib.env` e reiniciar `fralib-api`.

**Como prevenir:**
- Script de bootstrap deve setar `CRON_SECRET` automaticamente na primeira instalacao
- Healthcheck deve validar que todas as env vars criticas estao setadas
- Verificar periodicamente:
  ```bash
  curl -X POST -H "X-Cron-Secret: $CRON" http://127.0.0.1:8000/api/cron/followup-bryan
  ```

---

## Bug #4 — `ProtectSystem=full` bloqueia write

**Sintoma:** `OSError: [Errno 30] Read-only file system` ao tentar salvar
prompt via Studio. Tinha `SDR_LAYER = design_system` mas o disco tava
read-only.

**Causa raiz:** O unit file `fralib-api.service` tem `ProtectSystem=full`
+ `ProtectHome=read-only` (boa pratica de segurança do systemd). O
processo do `fralib-api` roda como `root` mas o kernel monta `/root`
como read-only por causa dessas flags.

**Fix:** Criar override em
`/etc/systemd/system/fralib-api.service.d/override.conf`:

```ini
[Service]
ReadWritePaths=/root/fralib/backend/agents
ReadWritePaths=/root/fralib/logs
ReadWritePaths=/tmp
```

E `systemctl daemon-reload && systemctl restart fralib-api`.

**Como prevenir:**
- Documentar em `docs/SDR_STUDIO_10_10.md` secao 4.2
- Se adicionar novo path gravavel, atualizar o override

---

## Bug #5 — Audit log quebra com email como user_id

**Sintoma:** No `agent.py:_audit()`, chamada:
```python
"target_user": target_user_id  # None quando SDR Studio
"actor": actor.get("id")  # int do user_id
```
A funcao `_audit` em `superadmin_endpoints.py:30` faz:
```python
db.execute(text("INSERT INTO audit_log (... target_user_id ...) VALUES (:target_user, ...)"),
          {"target_user": target_user_id, ...})
```
E `target_user` (None) gera SQL `target_user_id=NULL`. Funciona, MAS
quando o actor_id (user_id) e string (ex: 'dezigpi@gmail.com' em vez
de int 2), o Postgres reclama:
`invalid input syntax for type bigint: "dezigpi@gmail.com"`.

**Fix:** `_audit()` em `superadmin_endpoints.py:30` envolve o INSERT
em try/except e imprime warning. Falha silenciosa (nao quebra o endpoint).

**Como prevenir:**
- Garantir que `actor.get("id")` e sempre int. Se vier do JWT, validar
- Schema da tabela `audit_log` deveria aceitar VARCHAR para `actor_id`
  (outro ticket, nao urgente)

---

## Bug #6 — Alembic `down_revision` quebrado

**Sintoma:** `alembic upgrade head` falhava com:
`KeyError: '72bd68b42efe_sync_one_truth_mirrors'`
quando tentava resolver o grafo de migrações.

**Causa raiz:** A migration `perf_idx_2025_01_15.py` tinha:
```python
down_revision = "72bd68b42efe_sync_one_truth_mirrors"  # COM SLUG
```
Mas o `revision` real dela e `72bd68b42efe` (sem slug). Alembic procura
pelo `revision` exato.

**Fix:** Corrigir para `down_revision = "72bd68b42efe"` (sem slug).
Commit `2d11e56`.

**Como prevenir:**
- Convencao: `down_revision` = `revision` da migration anterior SEM slug
- Rodar `alembic check` antes de commitar
- Verificar que o alembic_version no DB bate com a head esperada

---

## Bug #7 — Worker nao pega jobs por transacoes idle

**Sintoma:** Worker `fralib-franz` rodando mas **zero jobs processados
por 2+ horas**. Audit shows 15 jobs `franz_outreach` pendentes.

**Causa raiz:** Conexoes Postgres com `idle in transaction` (transacao
aberta mas sem query) por 5+ minutos. Worker esperava lock em `leads`
ou `jobs`. Causa: codigo antigo que nao comitava apos SELECT.

**Fix:** Identificar PIDs stuck com:
```sql
SELECT pid, state, NOW() - state_change AS dur, LEFT(query, 100) AS q
FROM pg_stat_activity
WHERE datname='fralib_db' AND state != 'idle' AND state_change < NOW() - INTERVAL '1 minute';
```
E matar com `SELECT pg_terminate_backend(<pid>);`

**Como prevenir:**
- Healthcheck diario que detecta idle-in-transaction > 1min
- Adicionar `autocommit=True` em conexoes pontuais de read
- Code review: `with engine.connect() as conn: ...` SEM `conn.commit()`
  e anti-pattern

---

## Como auditar que nenhum desses bugs voltou

```bash
# 1. Stage-loop: rodar testes
ssh root@187.77.37.72 "cd /root/fralib && source venv/bin/activate && python scripts/test_sdr_fsm.py"

# 2. WHATSMEOW_DB_URL: checar se lead e reconhecido
ssh root@187.77.37.72 "journalctl -u fralib-wpp-listener --since '1 hour ago' | grep -c 'Lead nao encontrado'"
# Esperado: 0 (ou numero baixo consistente)

# 3. CRON_SECRET: disparar cron
ssh root@187.77.37.72 "curl -X POST -H 'X-Cron-Secret: $CRON' http://127.0.0.1:8000/api/cron/followup-bryan"

# 4. Read-only fs: salvar no Studio e ver se funciona
# (via superadmin.html aba SDR Studio > Aplicar)

# 5. Audit log: ver ultimas entradas
ssh root@187.77.37.72 "PGPASSWORD=fralib2024 psql -c 'SELECT * FROM audit_log ORDER BY criado_em DESC LIMIT 10'"

# 6. Alembic: verificar head
ssh root@187.77.37.72 "cd /root/fralib && source venv/bin/activate && alembic current"

# 7. Idle transactions: query de healthcheck
ssh root@187.77.37.72 "PGPASSWORD=fralib2024 psql -c \"SELECT count(*) FROM pg_stat_activity WHERE datname='fralib_db' AND state='idle in transaction'\""
# Esperado: 0
```

---

## Bug #8 — Franz nao faz objecao, so aceita opt-out direto

**Sintoma:** Lead diz "no momento nao tem interesse, obrigada" e o Franz
fecha a conversa IMEDIATAMENTE sem tentar contornar uma unica vez.
Tambem classifica "ja tem uma empresa que cuida disso" como gatekeeper
quando na verdade e OBJECAO de "ja tem fornecedor".

**Caso real (Bianca, nutricionista, 2026-06-23):**
- Lead: "A Bianca ja tem uma empresa que cuida dessa parte pra ela"
- Franz: "Tranquilo. Consegue me passar pra ele?" (gatekeeper level 1)
- Lead: "No momento nao tem interesse, obrigada"
- Franz: "Tudo bem, Jhenifer, respeito totalmente! Se um dia fizer sentido..."
- **Resultado: lead perdido, sem tentativa de contornar**

**Causa raiz (3 problemas separados):**

1. **`node_opt_out` (agent.py:796) e terminal**: chamada direta
   `route_by_intent` quando intent == "opt_out". Sem retry, sem contra-argumento.
   O codigo de `opt_out` so faz:
   ```python
   reply = "Entendido! Vou remover seu contato agora..."
   memory.mark_opt_out()
   ```
   Sem tentar uma vez com pergunta de saida (ex: "entao deixa eu te perguntar: e se
   tivesse um resultado X?"), sem classificar tipo de objecao (preco/timing/necessidade).

2. **Confusao gatekeeper vs objecao**: regex de `intent_classifier` classifica
   "A Bianca ja tem uma empresa" como `gatekeeper` (matches "sou...dono"? nao,
   mas cai em "consegue me passar pra ele" matching). Mas e claramente uma
   OBJECAO de "ja tem fornecedor", nao gatekeeper.

3. **`main_objection` nunca e setado**: o campo existe em `LeadMemory`, e
   `is_objetou` le ele (agent.py:1022), mas nenhum lugar do codigo chama
   `memory.main_objection = "..."`. Entao mesmo que o LLM detectasse objecao,
   ela nao seria persistida para analise.

**Fix proposto (3 passos):**

1. Criar `node_objection` (agent.py:850):
   ```python
   @sdr_traced("node_objection")
   def node_objection(state):
       memory = state.get("memory")
       intent_result = state.get("intent_result")  # passa classifier
       if not memory:
           return {}
       # Classificar tipo de objecao (regex simples)
       obj_type = _classify_objection_type(state.get("incoming_message", ""))
       memory.main_objection = obj_type  # PERSISTIR!
       memory.rejection_count += 1
       # Anti-loop: se ja tentou 1x, vai pra opt_out
       if memory.rejection_count >= 2:
           return {"outgoing_message": "...", "next_stage": "opt_out", ...}
       # Tentar contornar 1x com contra-argumento especifico
       reply = _build_objection_counter(obj_type, memory)
       return {"outgoing_message": reply, "memory": memory, "next_stage": "objecting"}
   ```

2. Em `intent_classifier._classify_objection` (intent_classifier.py:80),
   adicionar dicionario `OBJECTION_TYPES = {price, timing, no_need, has_provider, trust}`.
   Quando intent=objection, retorna o tipo especifico (nao so "objection" generico).

3. Em `route_by_intent` (agent.py:368), ANTES do `if intent == "opt_out"`,
   adicionar:
   ```python
   if intent == "objection" and state.get("current_state") != "objecting":
       return "node_objection"  # tenta contornar antes de virar opt_out
   if intent == "objection" and memory.rejection_count >= 1:
       return "node_opt_out"   # ja tentou 1x, aceita
   ```

**Como prevenir:**
- Toda vez que lead disser "nao", "agora nao", "ja tenho", "caro":
  - Confirmar se e opt-out REAL ou objecao disfarçada
  - Tentar 1 contra-argumento ANTES de aceitar
  - Classificar tipo e persistir em `main_objection`
- Code review: `node_opt_out` nunca deve ser chamado sem retry previo
- Adicionar teste: `test_objection_handling.py` com 5 cenario (preco, timing, has_provider, trust, no_need)

---

## Bug #9 — Gatekeeper level nao incrementa corretamente

**Sintoma:** Quando lead diz "nao sou o dono" 2x, o gatekeeper_level
fica em 1 (devia ir pra 2). A fala "Tranquilo. Consegue me passar pra ele?"
se repete identica.

**Causa raiz:** Em `node_gatekeeper` (agent.py:910), `level` e incrementado
a cada chamada. MAS o codigo verifica:
```python
level = min(memory.gatekeeper_level + 1, 5)
```
Se `gatekeeper_level` for reset entre chamadas (limpeza de memoria ou reload),
a progressao quebra. Alem disso, **nao persiste o state corretamente** se
o worker for reiniciado.

**Fix:** Persistir `gatekeeper_level` no LeadMemory.model_dump_json() e
recarregar via `carregar_memoria()` antes de calcular level.

---

## Bug #10 — `node_schedule` agenda sem confirmar horario

**Sintoma:** Lead diz "agenda pra amanha 14h" e o Franz responde "agendado"
sem confirmar AMANHA 14h (data/horario) no agendamento. Pode haver
confusao de timezone ou lead esquecer.

**Causa raiz:** `node_schedule` (agent.py:837) responde "Perfeito, agendado!"
mas nao verifica se a data+horario e futuro, nem confirma explicitamente.

**Fix:** Adicionar validacao: data no futuro, horario no expediente
(8h-21h), timezone do lead. Responder com confirmacao explicita:
"Confirmado: amanha (24/06) as 14h. Te mando mensagem aqui no mesmo
horario."

---

## Bug #11 — LeadMemory `last_intent` nao persistido corretamente

**Sintoma:** Apos o turno, `memory.last_intent` as vezes fica vazio
mesmo quando intent foi classificado. Em sessoes subsequentes, o orchestrator
perde o contexto do intent anterior.

**Causa raiz:** Em `orchestrator.py`, `update_lead_memory_after_turn`
chama `memory.last_intent = orchestrator_decision.intent.value`. MAS
isso so roda no caminho do `node_save_and_send`. Quando o Franz cai em
`node_opt_out` (que retorna antes do save_and_send), o intent NAO e
persistido.

**Fix:** Mover `update_lead_memory_after_turn` pra um lugar que executa
SEMPRE (ex: hook generico no final do `run_sdr_graph`).

---

## Bug #12 — Memoria 3-tier (memory_hook) nao persiste em producao

**Sintoma:** Em testes, `memory_hook.py` carrega Core/Warm. Mas em
producao (VPS), os arquivos `backend/memory/core.json` nao sao
atualizados pelo worker. Entao o Franz nao "aprende" nada entre
atendimentos.

**Causa raiz:** `memory_hook.py` chama `core.adicionar(entry)` em
`extract_and_persist_learning()`. MAS o `Warm.adicionar()` so funciona
se o diretorio `backend/memory/warm/` existir E for writable. Em
producao, esse diretorio nao existe (criado on-the-fly so em dev).

**Fix:** Garantir que `memory_hook.py` cria o diretorio se nao existir:
```python
from pathlib import Path
WARM_DIR = Path(__file__).parent.parent / "memory" / "warm"
WARM_DIR.mkdir(parents=True, exist_ok=True)
```

---

## Como auditar que nenhum desses bugs voltou

```bash
# 1. Stage-loop: rodar testes
ssh root@187.77.37.72 "cd /root/fralib && source venv/bin/activate && python scripts/test_sdr_fsm.py"

# 2. WHATSMEOW_DB_URL: checar se lead e reconhecido
ssh root@187.77.37.72 "journalctl -u fralib-wpp-listener --since '1 hour ago' | grep -c 'Lead nao encontrado'"
# Esperado: 0 (ou numero baixo consistente)

# 3. CRON_SECRET: disparar cron
ssh root@187.77.37.72 "curl -X POST -H 'X-Cron-Secret: $CRON' http://127.0.0.1:8000/api/cron/followup-bryan"

# 4. Read-only fs: salvar no Studio e ver se funciona
# (via superadmin.html aba SDR Studio > Aplicar)

# 5. Audit log: ver ultimas entradas
ssh root@187.77.37.72 "PGPASSWORD=fralib2024 psql -c 'SELECT * FROM audit_log ORDER BY criado_em DESC LIMIT 10'"

# 6. Alembic: verificar head
ssh root@187.77.37.72 "cd /root/fralib && source venv/bin/activate && alembic current"

# 7. Idle transactions: query de healthcheck
ssh root@187.77.37.72 "PGPASSWORD=fralib2024 psql -c \"SELECT count(*) FROM pg_stat_activity WHERE datname='fralib_db' AND state='idle in transaction'\""
# Esperado: 0

# 8. Objection handling: contar quantos opt-outs SEM retry
ssh root@187.77.37.72 "PGPASSWORD=fralib2024 psql -d fralib_db -c \"SELECT COUNT(*) FROM leads WHERE sdr_stage = 'opt_out' AND criado_em > NOW() - INTERVAL '7 days' AND user_id IN (SELECT id FROM users WHERE is_superadmin = false)\""
# Investigar: se muitos, Franz ta fechando rapido demais

# 9. main_objection populado: contar quantos tem valor
ssh root@187.77.37.72 "PGPASSWORD=fralib2024 psql -d fralib_db -c \"SELECT COUNT(*) FROM leads WHERE main_objection IS NOT NULL AND main_objection != ''\""
# Esperado: > 0 se houve objecao. Se 0, bug #8 confirmado.
```

---

**Ultima atualizacao:** 2026-06-23.
**Proxima revisao:** quando alguem introduzir um bug novo. Adicione abaixo.