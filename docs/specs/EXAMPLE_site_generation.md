# 📋 SPEC: Site Generation Pipeline (kpalabz)

**Status:** ✅ Aprovada
**Data:** 2026-06-19
**Autor:** Claude (com aprovação do usuário)
**Commit atual:** 0ef2898

---

## 🎯 OBJETIVO (O QUÊ e PORQUÊ)

### O que construir:
Um pipeline que pega um lead (ex: "Nutricionista em Curitiba") e gera um site profissional Vite/React funcional, publicável.

### Por que:
Hoje: 0 leads aprovados de 112 no tenant 2 (47 falhas).
Meta: ≥ 70% de aprovação, ~10s por site, custo < $0.50/site.

---

## ✅ CRITÉRIOS DE ACEITE (como saber que está pronto)

| # | Critério | Métrica | Como medir |
|---|----------|---------|------------|
| 1 | Site é gerado para um lead válido | Build OK + HTML válido | `npm run build` exit 0, dist/index.html presente |
| 2 | Tempo de geração | < 60s | medir em `jobs.last_phase_at` |
| 3 | Custo por site | < $0.50 USD | somar `llm_usage.input + output tokens` × preço |
| 4 | LLM funciona | API kpalabz 200 OK | `curl ANTHROPIC_BASE_URL/models` |
| 5 | Sem falhas 401 | 0 falhas "Unauthorized" | `pipeline_failures.erro_tecnico NOT LIKE '%401%'` |
| 6 | Site tem seções mínimas | home + services + contact | inspeção em dist/index.html |

---

## 🚫 FORA DE ESCOPO (NÃO construir)

- ❌ Sistema de pagamento
- ❌ Dashboard admin
- ❌ Multi-idioma
- ❌ Integração com CRM externo
- ❌ Editor visual drag-and-drop
- ❌ Migração para outro LLM (só kpalabz agora)

---

## 🏗️ RESTRIÇÕES TÉCNICAS

| Restrição | Valor | Razão |
|-----------|-------|-------|
| LLM provider | kpalabz (`https://api.kpalabz.com/v1`) | Plano Max 20x disponível |
| Modelo padrão (opus) | `claude-sonnet-4-6` | Custo-benefício |
| Modelo leve (haiku) | `claude-haiku-4-5` | Para tarefas simples |
| Máx tokens por site | 100K input + 50K output | Controle de custo |
| Timeout por fase | 120s | Evitar travamento |
| Retries por falha | 2x | Balancear resiliência vs custo |
| Stack do site gerado | Vite + React + Tailwind | Já definido |
| WhatsApp keepalive | 30s | Já implementado |

---

## 📐 ARQUITETURA

```
Lead (Postgres)
   │
   ▼
[1] lead_supply ──→ Hunter/Maps/Manual
   │
   ▼
[2] lead_production_tick ──→ Enfileira job
   │
   ▼
[3] pipeline_lead ──→ Gera PRD + HTML + Build
   │   ├─ llm_router (kpalabz)
   │   ├─ vite_react_renderer
   │   └─ builder_worker
   ▼
[4] site publicado ──→ /var/www/fralib/sites/{tenant_id}/{lead_id}/
   │
   ▼
[5] franz_outreach ──→ WhatsApp (se keepalive OK)
```

---

## 🧪 TASKS (quebra do plano)

### Task 1: Verificar imports VPS
- [x] `from core` → `from backend.core` em todos os arquivos
- [x] Testar `python3 -c "from backend.agents import llm_direct"`
- **Verde:** import sem erro

### Task 2: Configurar kpalabz
- [x] `ANTHROPIC_API_KEY=sk-kpa-...` no `.env`
- [x] `ANTHROPIC_BASE_URL=https://api.kpalabz.com/v1`
- [x] Remover LiteLLM (comentado)
- **Verde:** `curl /v1/models` retorna 200

### Task 3: Health check funcional
- [x] `_check_litellm()` simplificado para kpalabz direto
- [x] `/health` retorna `status: ok`
- **Verde:** `curl /health` mostra `litellm: ok`

### Task 4: WhatsApp keepalive
- [x] Adicionar `keepaliveLoop` em `session.go`
- [x] SendPresence a cada 30s
- [x] Reconexão agressiva com backoff
- **Verde:** `journalctl -u whatsmeow` mostra `keepalive OK`

### Task 5: Reprocessar falhas do tenant 2 (PENDENTE)
- [ ] Investigar causa raiz das 47 falhas (FEITO: 401 Namehost)
- [ ] Marcar como resolvidas: `UPDATE pipeline_failures SET resolvido=TRUE WHERE tenant_id=2`
- [ ] Criar jobs de reprocessamento
- **Verde:** 47 leads reprocessados com sucesso

### Task 6: Validar em produção (PENDENTE)
- [ ] Processar 1 lead de teste
- [ ] Medir tempo + tokens
- [ ] Validar site gerado abre no navegador
- **Verde:** site gerado e validado

---

## 🔴 DEFINIÇÃO DE VERDE

O comando **deve** retornar 0:
```bash
./scripts/verify_all.sh
```

Resultado esperado:
```
🟢 VERDE - pode fazer deploy!
```

---

## 📊 MÉTRICAS A monitorar pós-deploy

| Métrica | Como medir | Esperado |
|---------|-----------|----------|
| Taxa de aprovação | `aprovados / total_leads` | ≥ 70% |
| Custo médio por site | `llm_usage / leads_aprovados` | < $0.50 |
| Tempo médio | `created_at - completed_at` | < 60s |
| Falhas/dia | `COUNT(pipeline_failures WHERE criado_em > NOW()-1day)` | < 5 |
| WhatsApp uptime | `journalctl keepalive OK / total` | ≥ 95% |

---

## 🚨 RISCOS e MITIGAÇÕES

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| kpalabz cair | Baixa | Fallback para Sonnet mais barato |
| WhatsApp cair | Média | Keepalive + reconexão já implementados |
| Lead inválido (sem dados) | Alta | Validação prévia (não enviar para pipeline) |
| Token estourar | Média | Limite 100K input + alerta |
| Bug em módulo novo | Média | +130 testes + CI rodando |

---

## 📝 NOTAS

- **NÃO** usar LiteLLM agora (overhead sem ganho)
- **SIM** usar kpalabz direto (simples, barato)
- WhatsApp já tem keepalive - **NÃO** mexer
- Próximo deploy após este SPEC: processar 1 lead real de teste

---

**Aprovação:** Usuário autorizou
**Próxima ação:** Task 5 (reprocessar falhas tenant 2)
