# ROLLOUT_SDR_FLAGS.md — Plano de Ativação das Flags SDR em Produção

**Data**: 2026-06-23
**Versão**: v1.6 (Sprint 3A + 3B + 3C)
**Runtime**: PM2 fralib-dreamer
**VPS**: root@100.101.18.1:/root/fralib

---

## 1. Contexto

3 sprints entregues, todos opt-in via env flags (backward-compat total):

| Sprint | Feature | Flag | Default |
|---|---|---|---|
| 3A | 4 tools dinâmicas (playbook, lead quality, etc) | `FRALIB_SDR_USE_TOOLS=1` | `0` (off) |
| 3B | RAG semântico (cosseno + sentence-transformers) | `FRALIB_SDR_USE_RAG=1` | `0` (off) |
| 3C | Telemetria variação (ranking por template) | `FRALIB_SDR_USE_TELEMETRIA=1` | `0` (off) |

**Suite consolidada**: 88/88 testes verde (v1.0..v1.6)
**Tags disponíveis**: v1.4-baseline, v1.5-baseline, v1.6-baseline (e lockpoints)

---

## 2. Estratégia de rollout em 4 fases

### Fase 0 — Pré-flight (DIA 0)
**Duração**: 1 dia
**Owner**: Engenheiro de plantão

- [ ] Coletar baseline de latência SDR (p50/p95/p99) dos últimos 7 dias
- [ ] Coletar baseline de taxa de conversão SDR (won / total conversas) dos últimos 7 dias
- [ ] Coletar baseline de tamanho dos índices `memory/u*/`
- [ ] Definir KPIs de sucesso (meta de +15-25% conversão)
- [ ] Confirmar que tags v1.6 estão no VPS (`ssh root@100.101.18.1 "cd /root/fralib && git tag -l v1.6*"`)
- [ ] Confirmar que 11 checks do pre-commit hook passam localmente

### Fase 1 — Canary (DIA 1-2)
**Escopo**: 1 user_id (Tenant 2)
**Duração**: 24h

```bash
# Ativar em 1 user_id via variavel de ambiente
ssh root@100.101.18.1 "cd /root/fralib && pm2 env fralib-dreamer FRALIB_SDR_USE_TOOLS=1"
ssh root@100.101.18.1 "cd /root/fralib && pm2 env fralib-dreamer FRALIB_SDR_USE_RAG=1"
ssh root@100.101.18.1 "cd /root/fralib && pm2 env fralib-dreamer FRALIB_SDR_USE_TELEMETRIA=1"
```

**Nota**: as flags acima são GLOBAIS no PM2. Para escopo por user_id, é necessário
adicionar lógica no agent.py para checar `memory.user_id` (TODO Sprint 4).

**Monitorar** (a cada 4h):
- Latência p95 (alvo: < 2x baseline)
- Taxa de erro LLM (alvo: < 5%)
- Tamanho dos índices RAG (`du -sh backend/memory/u*/sdr_embeddings_*.json`)

### Fase 2 — Early adopter (DIA 3-5)
**Escopo**: 5 user_ids
**Duração**: 48h

- Comparar taxa de conversão vs baseline 7d
- Comparar duração média de qualificação
- Coletar feedback qualitativo dos 5 leads

### Fase 3 — Maioria (DIA 6-13)
**Escopo**: 50% dos user_ids
**Duração**: 1 semana

- A/B testing: 50% com flags ON, 50% OFF
- Coletar métricas por 7 dias
- Decidir se promove para 100%

### Fase 4 — Full (DIA 14+)
**Escopo**: 100% dos user_ids
**Duração**: contínuo

- Flags viram default ON em produção
- Código opt-in permanece (kill switch)

---

## 3. Métricas a monitorar (com thresholds)

### Latência SDR
- **p50 baseline**: `BASELINE_P50_MS` (preencher com valor real)
- **p95 baseline**: `BASELINE_P95_MS`
- **p99 baseline**: `BASELINE_P99_MS`
- **Alerta**: p95 > 2x baseline por 30min

### Taxa de erro LLM
- **Baseline**: `BASELINE_ERROR_RATE` (preencher)
- **Alerta**: > 5% por 15min
- **Crítico**: > 10% por 15min → rollback

### Taxa de conversão SDR
- **Baseline 7d**: `BASELINE_CONVERSION_RATE` (preencher)
- **Alvo**: +15-25% vs baseline
- **Alerta regressão**: < baseline - 20%

### Tempo médio de qualificação
- **Baseline**: `BASELINE_QUALIFICATION_TIME` (preencher)
- **Alvo**: -30% vs baseline

### Tamanho dos índices RAG
- **Cold start**: 0 (não existe)
- **Crescimento esperado**: ~1KB por conversa
- **Alerta**: > 10MB por arquivo
- **Ação**: limpeza manual + cap automatico (MAX_ENTRIES_PER_FILE=10000 já existe)

### Multiplicador de lessons
- Verificar que `save_sdr_lesson` está sendo chamado em conversas terminais
- Verificar que `score_final` está sendo persistido (verificar `sdr_learning.json`)

---

## 4. Critérios de rollback (kill switch)

| Trigger | Ação | Tempo |
|---|---|---|
| Latência p95 > 3x baseline | Rollback Fase N → Fase N-1 | < 5min |
| Erro LLM > 10% por 15min | Desativar todas as flags | < 5min |
| Conversão caiu > 20% vs baseline | Rollback Fase N → Fase N-1 | < 30min |
| Disco cheio por indices RAG | Limpar + desativar 3B | < 15min |
| Quebra de funcionalidade critica | Rollback total (v1.6 → v1.5-lockpoint) | < 10min |

### Comandos de rollback

```bash
# Desativar todas as flags (rollback suave)
ssh root@100.101.18.1 "cd /root/fralib && pm2 env fralib-dreamer FRALIB_SDR_USE_TOOLS=0"
ssh root@100.101.18.1 "cd /root/fralib && pm2 env fralib-dreamer FRALIB_SDR_USE_RAG=0"
ssh root@100.101.18.1 "cd /root/fralib && pm2 env fralib_SDR_USE_TELEMETRIA=0"

# Rollback total (volta para versao anterior do codigo)
ssh root@100.101.18.1 "cd /root/fralib && git reset --hard v1.5-lockpoint-2026-06-23 && pm2 reload fralib-dreamer"

# Rollback TOTAL (volta para pre-Sprint 3, versao mais estavel)
ssh root@100.101.18.1 "cd /root/fralib && git reset --hard v1.3-lockpoint-2026-06-23 && pm2 reload fralib-dreamer"
```

---

## 5. Comandos de ativação / desativação

### Verificar flags ativas
```bash
ssh root@100.101.18.1 "pm2 env fralib-dreamer | grep -E 'FRALIB_SDR_'"
```

### Ativar tudo de uma vez (modo agressivo)
```bash
ssh root@100.101.18.1 "cd /root/fralib && cat > .env.sdr <<'EOF'
FRALIB_SDR_USE_TOOLS=1
FRALIB_SDR_USE_RAG=1
FRALIB_SDR_USE_TELEMETRIA=1
EOF
pm2 restart fralib-dreamer --update-env"
```

### Desativar tudo
```bash
ssh root@100.101.18.1 "cd /root/fralib && rm -f .env.sdr && pm2 restart fralib-dreamer"
```

---

## 6. Queries de monitoramento (Postgres)

### Conversão SDR por user_id (ultimos 7 dias)
```sql
SELECT
  user_id,
  COUNT(*) FILTER (WHERE stage = 'won') AS converteram,
  COUNT(*) AS total,
  ROUND(100.0 * COUNT(*) FILTER (WHERE stage = 'won') / COUNT(*), 2) AS taxa_pct
FROM sdr_conversations
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY user_id
ORDER BY total DESC
LIMIT 20;
```

### Latência SDR (p50/p95/p99) por turno
```sql
SELECT
  date_trunc('hour', created_at) AS hora,
  ROUND(percentile_cont(0.50) WITHIN GROUP (ORDER BY latency_ms)) AS p50,
  ROUND(percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)) AS p95,
  ROUND(percentile_cont(0.99) WITHIN GROUP (ORDER BY latency_ms)) AS p99
FROM sdr_turns
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY 1
ORDER BY 1 DESC;
```

### Erro LLM SDR (ultimas 24h)
```sql
SELECT
  date_trunc('hour', created_at) AS hora,
  COUNT(*) FILTER (WHERE error IS NOT NULL) AS erros,
  COUNT(*) AS total,
  ROUND(100.0 * COUNT(*) FILTER (WHERE error IS NOT NULL) / COUNT(*), 2) AS taxa_erro_pct
FROM sdr_turns
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY 1
ORDER BY 1 DESC;
```

### Tamanho dos indices RAG
```bash
ssh root@100.101.18.1 "du -sh /root/fralib/backend/memory/u*/sdr_embeddings_*.json 2>/dev/null | sort -h | tail -20"
```

---

## 7. Plano de comunicação

| Dia | Ação | Canal |
|---|---|---|
| DIA 0 | Anuncio: "Sprint 3A/3B/3C entregues, suite 88/88 verde" | Slack #eng |
| DIA 1 | Report canary (1 user_id) | Slack #eng + email |
| DIA 3 | Report early adopter (5 user_ids) | Slack #eng |
| DIA 7 | Review decisao maioria (50%) | Reuniao + doc |
| DIA 14 | Full rollout (100%) | Anuncio formal |
| DIA 21 | Post-mortem + ROI real | Doc publico |

---

## 8. Riscos + mitigação

| Risco | Mitigação | Probabilidade |
|---|---|---|
| Cold start RAG (sem historico) | Fallback automatico para `retrieve_similar_conversations` (Sprint 3A) | Alta |
| Sentence-transformers pesado (80MB) | Ja validado na VPS, carrega em ~50ms | Media |
| Concorrencia em `_save_index` | Write atomico via `os.replace` | Baixa |
| Multi-tenancy leak (user_id em toda chamada) | Validado por testes v1.4/v1.5/v1.6 | Baixa |
| Tool call falha mid-LLM | Try/except em todos os pontos, nao-bloqueante | Media |
| Disco cheio por crescimento dos indices | Cap automatico 10000 + alerta 10MB | Baixa |
| Latencia acumulada (3 tools no pre-fetch) | Estimado < 50ms (read-only local) | Media |

---

## 9. Proximos passos (checkboxes)

- [ ] **Coletar baselines reais** (latencia, conversao, erros) — pre-Fase 0
- [ ] **Adicionar escopo por user_id** (atual flags sao globais) — Sprint 4
- [ ] **Criar dashboard Grafana** para as queries de monitoramento — Sprint 4
- [ ] **Implementar memory decay** (lessons antigas perdem peso) — Sprint 5
- [ ] **A/B testing framework** (50/50 com mesmo lead) — Sprint 5
- [ ] **Tracing nos nodes LangGraph** (ja tem turn_tracing parcial) — Sprint 4
- [ ] **Documentar caso de uso no README** (como ativar para cliente novo) — Sprint 4

---

## 10. ROI esperado (compilado dos 3 sprints)

| Sprint | Ganho isolado | Ganho composto |
|---|---|---|
| 3A (tools) | +15-25% conversao SDR | base |
| 3B (RAG) | +20-35% precisao retrieval | +10-15% conversao (composto) |
| 3C (telemetria) | +5-10% (ranking de templates) | +5% conversao (composto) |
| **TOTAL estimado** | **+30-50%** | **+30-50% conversao SDR** |

Reduzir tempo medio de qualificacao em **30%** (composto).

---

## 11. Tag de rollback garantido

Sempre que precisar voltar tudo (worst case):
```bash
ssh root@100.101.18.1 "cd /root/fralib && git reset --hard v1.6-lockpoint-2026-06-23 && pm2 reload fralib-dreamer"
```

Para voltar ao pre-Sprint 3 (rollback mais agressivo):
```bash
ssh root@100.101.18.1 "cd /root/fralib && git reset --hard v1.3-lockpoint-2026-06-23 && pm2 reload fralib-dreamer"
```

---

**Fim do documento.** Atualizar este doc apos cada fase de rollout.
