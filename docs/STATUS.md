# FraLib — STATUS (Checkpoint Vivo)

> **Este arquivo é a fonte canônica de "onde está o trabalho agora".**
> Atualizado sempre que algo mudar. Última atualização: ver topo do git log.

---

## 🚦 Estado Atual (2026-06-20)

| Item | Status | Evidência |
|------|--------|-----------|
| Produção VPS | 🟢 Online | pm2 jlist (5 serviços) |
| DNS Email | 🟢 Configurado | SPF+DKIM+DMARC OK |
| Monolitos | 🟢 Quebrados | vite_react_renderer / lead_supply_engine / pipeline_fases/fase_08 |
| Schema site_url | 🟢 Padronizado | COALESCE em todas as queries |
| Segurança | 🟢 Headers+Rate+Brute-force | SlowAPI + security_headers middleware |
| LGPD | 🟢 Implementado | commit 339a588 |
| Branch local | 🟢 master @ d8d84b2 | synced com origin |
| VPS | 🟢 deployado | |
| **Anti-perda** | 🟢 **ATIVO** | `scripts/check_uncommitted.sh` + STATUS.md |

---

## 📋 Próximas Ações Imediatas

### 🔴 CRÍTICO (hoje)
- [ ] Testar envio de email real (Gmail) — confirmar que NÃO cai no spam
- [ ] Mail-tester.com — validar score 9-10

### 🟡 IMPORTANTE (esta semana)
- [ ] Implementar circuit breaker para LLM (fallback provider)
- [ ] Row Level Security no PostgreSQL para multi-tenant

### 🟢 NICE-TO-HAVE
- [ ] Mapear e deletar branches órfãs
- [ ] Aumentar connection pool (50/100)

---

## 🗂️ Branches Ativas

| Branch | Propósito | Status |
|--------|-----------|--------|
| `master` | Produção | 🟢 ativo |
| `codex/pipeline-stabilization` | Estabilização geral | 🟡 revisar |
| `fix/fralib-stability-phase-1` | Refactor fase 1 | 🟡 revisar |
| `codex/od-contract-hardening` | Contratos OD | 🟡 revisar |
| `codex/openui-production-hardening` | OpenUI | 🟡 revisar |
| `feat/sdr-langgraph-migration` | SDR LangGraph | 🟡 revisar |
| (10+ outras) | - | 🔴 candidatas a deletar |

---

## 📦 Último Deploy (2026-06-20)

**Commit:** `d8d84b2` "feat(system): checkpoint vivo + sistema anti-perda"

**Mudanças deployadas:**
- `docs/STATUS.md` (novo) — checkpoint vivo
- `scripts/check_uncommitted.sh` (novo) — bloqueia se houver modificações
- `canva_oauth_auth.py` (novo) — integração Canva
- 13 arquivos atualizados (gate, testes, smoke)

---

## 🛡️ Sistema Anti-Perda (NOVO)

**Problema resolvido:** Modificações não commitadas se perdiam.

**Solução implementada:**

1. **`docs/STATUS.md`** (este arquivo) — checkpoint vivo
2. **`scripts/check_uncommitted.sh`** — bloqueia deploy se houver modificações
3. **Regra:** commit antes de qualquer ação >30min

**Como usar:**
```bash
# Antes de fazer deploy:
./scripts/check_uncommitted.sh
# Se mostrar arquivos modificados, faça commit primeiro
```

---

## 📚 Documentos Canônicos (One Truth)

| Domínio | Fonte |
|---------|-------|
| Estado real do sistema | `docs/STATUS.md` (este) |
| Contratos de domínio | `docs/ONE_TRUTH_CANONICAL_STATE.md` |
| Arquitetura | `CLAUDE.md` + `AGENTS.md` |
| Auditoria monolitos | `docs/AUDITORIA_MONOLITOS.md` |
| Auditoria schema | `docs/AUDIT_2026-06-20_SCHEMA_FIX.md` |
| VPS access | `docs/VPS_ACCESS_GUIDE.md` |

---

## 🔄 Como Atualizar Este Arquivo

**Toda vez que:**
- Deploy for feito
- Branch nova for criada
- Bug crítico for descoberto
- Tarefa for concluída
- Próxima ação mudar

**Comando rápido:**
```bash
# Editar este arquivo + commitar
edit docs/STATUS.md
git add docs/STATUS.md
git commit -m "status: checkpoint de [data] - [resumo]"
```

---

**Última atualização:** 2026-06-20 (commit d8d84b2 - sistema anti-perda)
