# Plano SDR 100% — Spec Implementation-Ready

## Contexto

O SDR está em produção com 18 sprints entregues, 71/71 testes GREEN e 16 hardeners aplicados. Porém, as auditorias adversariais revelam 6 P0/P1 que impedem deployment seguro: (1) escrita JSON não-atômica corrompe memória em crash, (2) debounce buffer causa loop infinito de duplicatas, (3) telefone em plaintext viola LGPD, (4) Redis offline bloqueia todo o fluxo, (5) transação não-atômica causa inconsistência de estado, (6) budget sem teto pode gerar custo ilimitado.

Além dos P0/P1, há 11 P2 de confiabilidade e observabilidade (silent failures, timezone bugs, race conditions) e 0 runbooks para 8 cenários críticos de.ops.

O objetivo: fechar todos os gaps antes de production-ready, com 100% testes GREEN e runbook completo.

## Princípios

- **Fail-Safe First**: qualquer except deve log.error + incluir no state para auditoria, nunca criar estado vazio que mascara o erro
- **Atomicidade obrigatória**: writes de arquivo e DB multi-statement SEMPRE em transação/rename atômico
- **Observabilidade total**: PII (telefone) nunca em logs; todo failure silencioso deve virar logger.warning
- **Budget como firewall**: créditos esgotados bloqueiam TODAS as chamadas LLM, não apenas notificam
- **Testes TDD**: cada sprint tem testes RED antes da implementação
- **Zero regression**: 71 testes GREEN atuais são a base, novos testes não podem quebrar existentes

---

## Sprint 1.0 — Atomicidade de Memória + LGPD

**Objetivo**: Eliminar corrupção de JSON em crash e vazar telefone em logs.

**Por que agora**: Auditoria P0/P1 — crash de processo corrompe memória do lead (LGPD + perda de dados), e telefone em plaintext viola LGPD em todos os logs.

**Escopo**:
- Criar `backend/agents/_atomic_write.py` com função `_atomic_write_json(path, data)` usando padrão write→fsync→rename
- Modificar `backend/agents/memory.py:48-49` para usar `_atomic_write_json` no lugar de `json.dump` direto
- Adicionar lock de arquivo (fcntl.flock) em `salvar_memoria()` para prevenir race condition entre workers simultâneos no mesmo lead
- Criar `backend/utils/pii_masker.py` com função `mask_phone(phone: str) -> str` que retorna `****{last4}`
- Substituir TODOS os `print(f"...{telefone}...")` por `logger.info(f"...{mask_phone(telefone)}...")` em:
  - `backend/whatsapp_listener.py:588-593`
  - `backend/agents/sdr_langgraph/agent.py:267`
  - `backend/agents/watchdog.py:131-147`
- Não logar texto da mensagem, apenas `{msg_len} chars`

**Critérios de aceite**:
- [ ] Processo morto entre open() e json.dump() deixa arquivo original intacto (não corrompido)
- [ ] 2 workers simultâneos no mesmo lead não sobrescrevem dados
- [ ] Telefone nunca aparece completo em stdout/stderr/logs/cloudwatch
- [ ] Logs mostram apenas `****1234` para qualquer telefone

**Testes (TDD)**:
- RED: `test_memory_atomic_write_kills_before_dump` — mock kill entre write e dump, arquivo original preservado
- RED: `test_memory_concurrent_writes_no_data_loss` — 2 threads salvam, ambas completam
- RED: `test_phone_mask_full_number_hidden` — mask_phone("5511945612345") == "****1234"
- RED: `test_logs_never_contain_full_phone` — capture logger output, assert no full phone

**Arquivos**:
- `backend/agents/_atomic_write.py` (criar)
- `backend/utils/pii_masker.py` (criar)
- `backend/agents/memory.py:31-52` (modificar)
- `backend/whatsapp_listener.py:588-593` (modificar)
- `backend/agents/sdr_langgraph/agent.py:264-316` (modificar logging)
- `backend/agents/watchdog.py:131-147` (modificar logging)
- `tests/unit/test_memory_atomic.py` (criar)
- `tests/unit/test_pii_masker.py` (criar)

**Risco**: fcntl.flock pode não funcionar em Windows NFS; fallback para threading.Lock por arquivo
**Dependência**: Nenhuma

---

## Sprint 1.1 — Resiliência Redis + Debounce Infinito

**Objetivo**: Impedir que Redis offline bloqueie o fluxo e que falha no processar cause loop infinito.

**Por que agora**: Auditoria P1 — RuntimeError do lead_lock bloqueia whatsapp_listener inteiro; debounce buffer removido ANTES de processar causa re-disparo infinito.

**Escopo**:
- Modificar `backend/agents/sdr_langgraph/lead_lock.py:147-212`: `_lead_lock_guard` deve retornar `None` (não levantar exceção) após 3 tentativas falhadas, com flag `_lock_acquired=False`
- Modificar callers de `_lead_lock_guard` em `whatsapp_listener.py` e `agent.py` para tratar `lock=None` como "processar com dedup local apenas"
- Modificar `backend/whatsapp_listener.py:1079-1083`: NÃO fazer `_DEBOUNCE_BUFFER.pop()` antes de processar — usar marcação "em_processamento" no buffer, remover APENAS no sucesso, SEMPRE fazer release_wpp_lock no finally
- Adicionar idempotency key no buffer para evitar re-disparo da mesma mensagem

**Critérios de aceite**:
- [ ] Redis offline NÃO causa RuntimeError propagado
- [ ] Redis offline permite processamento (dedup local funciona)
- [ ] Falha em `_processar_mensagem` NÃO causa loop infinito de re-disparo
- [ ] Mensagem fica marcada "em processamento" enquanto é tratada

**Testes (TDD)**:
- RED: `test_redis_offline_returns_none_not_error` — mock Redis down, assert no exception
- RED: `test_processing_failure_no_infinite_loop` — mock process failure, assert only 1 retry
- RED: `test_buffer_cleanup_only_on_success` — verify buffer entry removed only after successful process

**Arquivos**:
- `backend/agents/sdr_langgraph/lead_lock.py:147-212` (modificar)
- `backend/whatsapp_listener.py` (modificar debounce logic)
- `tests/unit/test_lead_lock_graceful.py` (criar)
- `tests/unit/test_debounce_infinite_loop.py` (criar)

**Risco**: Se dedup local falhar também, pode haver duplicatas — aceitar nesse cenário de Redis offline
**Dependência**: Sprint 1.0 (usa masking nos logs)

---

## Sprint 1.2 — Transação Atômica + Budget Teto

**Objetivo**: Garantir consistência de estado em multi-statement DB e impedir custo ilimitado.

**Por que agora**: Auditoria P0/P1 — 3 UPDATEs sem transação causa inconsistência; budget sem teto pode gerar dívida enorme.

**Escopo**:
- Modificar `backend/services/outbound_queue.py:422-446`: wrap os 3 statements (outbound UPDATE + leads UPDATE + interacoes INSERT) em `with engine.begin()` para transação atômica com rollback automático
- Modificar `backend/services/ia_manager.py`: adicionar `hard_cap_monthly_budget` por tenant lido do plano; se `credits_manager.creditos <= 0`, levantar `BudgetExhaustedError` que bloqueia TODAS as chamadas LLM (não apenas logging)
- Adicionar alerta/bloqueio em `credits_manager` quando créditos < 10% do limite mensal
- Implementar `MAX_MONTHLY_SPEND_PER_PLAN` dict: `free: 50, starter: 500, pro: 2000, enterprise: null`

**Critérios de aceite**:
- [ ] Falha no 2º ou 3º UPDATE faz rollback de TODOS os 3
- [ ] Credits = 0 bloqueia 100% das chamadas LLM (não só notifica)
- [ ] Credit alert disparado quando < 10% do teto
- [ ] Custo mensal nunca excede teto do plano

**Testes (TDD)**:
- RED: `test_outbound_transaction_atomic_on_failure` — mock 2nd UPDATE fail, assert rollback
- RED: `test_budget_exhausted_blocks_all_llm` — credits=0, assert LLM call raises
- RED: `test_credit_alert_at_10_percent` — verify alert triggered

**Arquivos**:
- `backend/services/outbound_queue.py:422-446` (modificar)
- `backend/services/ia_manager.py` (modificar budget logic)
- `backend/services/credits_manager.py` (adicionar teto)
- `tests/unit/test_outbound_atomic.py` (criar)
- `tests/unit/test_budget_cap.py` (criar)

**Risco**: Transações longas podem causar locks — manter timeout de 5s
**Dependência**: Sprint 1.0

---

## Sprint 1.3 — Observabilidade: Silent Failures + Runbook

**Objetivo**: Transformar todos os silent failures em logs actionable e criar runbook para 8 cenários.

**Por que agora**: Auditoria P2 — humanization/judge fail silenciosamente; 0 runbooks para Redis down, LLM rate limit, WhatsApp ban, etc.

**Escopo**:
- Modificar `backend/agents/sdr_langgraph/agent.py:1472-1473, 1373-1374, 1316-1317`: trocar `print()` por `logger.warning(...)` com contexto (lead_id, stage, error)
- Modificar `backend/agents/sdr_langgraph/agent.py:264-316`: no except de carregar_memoria, `log.error(...)` e incluir `{has_memory: False, error: str(e)}` no state
- Modificar `backend/agents/sdr_langgraph/agent.py:1390-1405`: `record_sdr_turn` deve log.error se tabela não existir
- Criar `backend/agents/sdr_langgraph/agent.py:_handle_terminal_stage` com retry: se falhar, marcar `needs_outcome_record=True` no lead
- Criar `docs/RUNBOOK.md` cobrindo:
  - Redis indisponível (symptoms → diagnose → recover)
  - LLM rate limit (429) (backoff strategy → quando escalar)
  - LLM 5xx (500/503) (circuit breaker → fallback)
  - WhatsApp ban/restricted (symptoms → cooldown → wait → recover)
  - Franz travado (detect → force restart → verify)
  - Tenant silencioso (debug → unstick → notify)
  - Pipeline jobs estagnados (detect → diagnose → force retry)
  - Outbound_queue DLQ (inspect → reprocess → discard)

**Critérios de aceite**:
- [ ] Humanization failure aparece em logs como WARNING com lead_id
- [ ] Memory corruption aparece em logs como ERROR com stack trace
- [ ] Missing sdr_turns table aparece em logs como ERROR
- [ ] Terminal stage failure é marcado para retry
- [ ] 8 cenários de ops documentados com steps executáveis

**Testes (TDD)**:
- RED: `test_silent_failure_logged_as_warning` — mock humanization fail, verify logger.warning
- RED: `test_memory_error_in_state` — mock json.load fail, verify state has error flag
- RED: `test_terminal_stage_retry_flag` — mock outcome record fail, verify needs_outcome_record=True

**Arquivos**:
- `backend/agents/sdr_langgraph/agent.py` (modificar exception handling)
- `docs/RUNBOOK.md` (criar)
- `tests/unit/test_silent_failure_logging.py` (criar)

**Risco**: Muitos logs de WARNING podem ser barulhentos — usar rate limit de 1/min por lead
**Dependência**: Sprint 1.0

---

## Sprint 1.4 — WhatsApp Rate Limit + Idempotência

**Objetivo**: Evitar ban do WhatsApp por burst de envios e duplicatas por hash exato.

**Por que agora**: Auditoria P1 — 50 msgs sequenciais sem throttle vai bater rate limit do WhatsApp; hash exato permite "Oi" vs "Oi!" como msgs diferentes.

**Escopo**:
- Modificar `backend/services/whatsapp_automation_service.py:69-121`: adicionar throttle de 1 msg a cada 3s usando `asyncio.sleep(3)` entre envios; batch de 50 leads = ~150s total
- Criar `backend/utils/idempotency.py` com função `normalize_for_hash(text: str) -> str`: `text.strip().lower().rstrip('.!?,')`
- Modificar `backend/services/outbound_queue.py:81-101`: usar `normalize_for_hash` ANTES de gerar idempotency_key
- Opcional: adicionar embedding similarity (cosine) para detectar duplicatas semânticas (threshold 0.95)

**Critérios de aceite**:
- [ ] 50 envios em batch respeitam rate limit (3s entre cada)
- [ ] "Oi" e "Oi!" geram mesmo hash (idempotentes)
- [ ] "Olá" e "Oi" são hashes diferentes
- [ ] WhatsApp não retorna 429 com throttle correto

**Testes (TDD)**:
- RED: `test_whatsapp_throttle_respects_3s` — mock 3 msgs, verify sleep called
- RED: `test_idempotency_normalize Oi vs Oi!` — assert same key
- RED: `test_idempotency_different_messages` — assert different keys

**Arquivos**:
- `backend/services/whatsapp_automation_service.py:69-121` (modificar)
- `backend/utils/idempotency.py` (criar)
- `backend/services/outbound_queue.py:81-101` (modificar)
- `tests/unit/test_whatsapp_throttle.py` (criar)
- `tests/unit/test_idempotency.py` (criar)

**Risco**: 3s por msg × 100 leads = 5min; aceitar como trade-off de confiabilidade
**Dependência**: Sprint 1.1

---

## Sprint 1.5 — LLM Fallback + Humanization + Timezone

**Objetivo**: Implementar fallback real para LLM failures e corrigir humanization/humanized_delay.

**Por que agora**: Auditoria P1/P2 — SDRFallbackError sem fallback; humanized_delay fixo em 2.0 (robótico); timezone misto causa comparação errada.

**Escopo**:
- Modificar `backend/agents/sdr_langgraph/agent.py:773-776, 969-972, 551-553, 1178-1179`: implementar fallback de template hardcoded para cada stage (hook, qualify, pain, etc.) quando LLM falha após 2 retries — similar a `node_schedule`
- Templates devem ser definidos em `backend/agents/sdr_langgraph/fallback_templates.py` com um template por stage
- Modificar `backend/whatsapp/rate_limiter.py:118-123`: `humanized_delay` deve usar fórmula real: `delay = max(1.5, min(8.0, len(text) / 90 + 2.0))`
- Modificar `backend/services/outbound_queue.py:195-207`: normalizar para UTC em ambos os lados usando `datetime.now(timezone.utc)` no server e `AT TIME ZONE 'UTC'` no Postgres
- Modificar `backend/whatsapp/response_executor.py:111-113`: mover `set_cooldown_fn` e `increment_daily_fn` para DEPOIS do `send_ok` check

**Critérios de aceite**:
- [ ] LLM failure resulta em resposta via template (não silêncio)
- [ ] humanized_delay varia de 1.5s a 8.0s baseado em texto
- [ ] Timezone UTC em todas comparações datetime
- [ ] Cooldown SOMENTE setado se send_ok=True

**Testes (TDD)**:
- RED: `test_llm_failure_uses_fallback_template` — mock LLM fail, assert template response
- RED: `test_humanized_delay_formula` — verify delay = f(len(text))
- RED: `test_timezone_utc_comparison` — verify UTC normalization
- RED: `test_cooldown_only_on_success` — mock send fail, assert no cooldown

**Arquivos**:
- `backend/agents/sdr_langgraph/agent.py` (modificar stage nodes)
- `backend/agents/sdr_langgraph/fallback_templates.py` (criar)
- `backend/whatsapp/rate_limiter.py:118-123` (modificar)
- `backend/services/outbound_queue.py:195-207` (modificar)
- `backend/whatsapp/response_executor.py:111-113` (modificar)
- `tests/unit/test_llm_fallback.py` (criar)
- `tests/unit/test_humanized_delay.py` (criar)
- `tests/unit/test_timezone_utc.py` (criar)

**Risco**: Templates hardcoded podem ser menos personalizados — aceitar trade-off de disponibilidade
**Dependência**: Sprint 1.3

---

## Sprint 1.6 — Validação Final + Health Check + Migração

**Objetivo**: Garantir que todas as tabelas existem, health checks cobrem gaps, e migration é idempotente.

**Por que agora**: Auditoria P2 — tabela sdr_turns pode não existir; health check não detecta table missing; migration não é idempotente.

**Escopo**:
- Criar migration `backend/migrations/0017_create_sdr_turns.sql` para tabela sdr_turns se não existir
- Criar `backend/services/health_check.py` com verificação de:
  - Tabela sdr_turns existe
  - Tabela leads tem phone_health_score column
  - Redis conectável
  - Postgres conectável
  - WhatsApp WebSocket conectado
- Adicionar health check no startup do servidor
- Modificar `backend/agents/sdr_langgraph/agent.py:1390-1405`: health check no `record_sdr_turn` verifica se tabela existe antes de INSERT
- Criar script `scripts/verify_deployment.py` que roda health check + 71 testes GREEN + smoke test de WhatsApp send

**Critérios de aceite**:
- [ ] Tabela sdr_turns criada automaticamente se não existir
- [ ] Health check detecta Redis down, Postgres down, tabela missing
- [ ] Deployment script passa = sistema pronto para produção
- [ ] 71 testes originais continuam GREEN

**Testes (TDD)**:
- RED: `test_migration_idempotent` — run twice, assert no error
- RED: `test_health_check_detects_missing_table` — mock missing table, assert fail
- RED: `test_health_check_detects_redis_down` — mock Redis fail, assert fail

**Arquivos**:
- `backend/migrations/0017_create_sdr_turns.sql` (criar)
- `backend/services/health_check.py` (criar)
- `backend/agents/sdr_langgraph/agent.py` (adicionar table check)
- `scripts/verify_deployment.py` (criar)
- `tests/unit/test_health_check.py` (criar)

**Risco**: Health check pode ter false positives em startup transitório — usar retry 3x
**Dependência**: Sprint 1.5

---

## Critérios Globais de Aceite

- 100% testes GREEN (71 originais + novos das sprints)
- 0 P0/P1 de segurança (LGPD, budget, transação)
- 0 gaps vermelhos da auditoria
- Runbook cobre 8 cenários de.ops
- Health check detecta Redis/Postgres/tabela missing
- Migration idempotente
- Deployment script valida tudo antes de production
