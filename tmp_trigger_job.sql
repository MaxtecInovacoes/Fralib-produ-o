INSERT INTO jobs (tipo, payload, tenant_id, max_attempts, idempotency_key, priority, status, next_retry_at)
VALUES (
  'pipeline_lead',
  '{"_lead_id_existente": "codex-test-barbearia-fio-nobre-pinhais-20260612", "_forcar_renovacao": true, "_prompt_agent_flow": true, "_run_id": "codex-e07c84c1689e", "segmento": "barbearia", "cidade": "Pinhais", "quantidade": 1, "score_minimo": 0}'::jsonb,
  2,
  3,
  'manual-trigger-codex-barbearia-fio-nobre',
  1,
  'pending',
  NOW()
)
RETURNING id, tipo, status, payload;
