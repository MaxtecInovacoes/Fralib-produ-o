# 📋 SPEC: Migração PM2 → systemd

**Data:** 2026-06-20
**Autor:** ECC Loop
**Status:** Aprovado

---

## 🎯 OBJETIVO (O QUÊ e PORQUÊ)

### O que construir:
Migrar os 5 serviços PM2 do FraLib para systemd nativo do Linux, com limites de recursos, boot order, health checks via watchdog e logs centralizados via journalctl.

### Por que:
- VPS de 7.8GB de RAM sem limites → um worker travado pode derrubar tudo
- Carga média atual 2.13 (alta para 4 cores)
- Logs espalhados em `~/.pm2/logs/` (não centralizados)
- PM2 é Node-first; somos Python-first
- systemd é padrão Linux (Debian/Ubuntu/RHEL) — melhor integração com SO
- `fralib-dashboard.service` já existe como referência

---

## ✅ CRITÉRIOS DE ACEITE

| # | Critério | Métrica | Como medir |
|---|----------|---------|------------|
| 1 | 5 .service files criados | 5 arquivos em infra/systemd/ | `ls infra/systemd/*.service | wc -l` = 5 |
| 2 | Sintaxe systemd válida | 0 erros | `systemd-analyze verify` exit 0 |
| 3 | MemoryMax aplicado | Visível por serviço | `systemctl show -p MemoryMax` retorna valor |
| 4 | CPUQuota aplicado | Visível | `systemctl show -p CPUQuota` retorna valor |
| 5 | .env carregado | Vars presentes | `systemctl show fralib-api -p Environment` lista DATABASE_URL etc |
| 6 | Restart on-failure | Policy correta | `systemctl show -p Restart` retorna on-failure |
| 7 | Boot order OK | Worker após DB | `systemd-analyze dot` grafo |
| 8 | Health check responde | /health 200 | `curl http://127.0.0.1:8000/health` |
| 9 | Auditoria visual 8+ PASS | 8/8 | Playwright screenshot |
| 10 | verify_all verde | Exit 0 | `bash scripts/verify_all.sh` |
| 11 | Testes pytest passam | 100% verde | `pytest tests/systemd/` |
| 12 | Rollback funciona | PM2 retoma | `pm2 resurrect` após uninstall |

---

## 🚫 FORA DE ESCOPO

- ❌ Migrar whatsmeow (Go, roda em systemd próprio)
- ❌ Mudar Docker
- ❌ Refatorar código Python
- ❌ Adicionar Prometheus
- ❌ Mudar FastAPI / endpoints
- ❌ Trocar de VPS

---

## 🏗️ RESTRIÇÕES TÉCNICAS

| Restrição | Valor | Razão |
|-----------|-------|-------|
| Services rodam como | root | Igual PM2 atual |
| .env path | /root/fralib/.env | Já existe |
| Working dir | /root/fralib | Código |
| Python venv | /root/fralib/venv | Já existe |
| PostgreSQL local | porta 5433 | Já configurado |
| Backend app | server.py + worker.py + hermes_daemon.py | Já existem |

---

## 📐 ARQUITETURA

```
┌─────────────────────────────────────────┐
│  systemd (PID 1)                        │
└────────────┬────────────────────────────┘
             │
             ▼
   ┌─── postgresql.service ───┐
   │   (5433, externo ao systemd)
   └────────┬─────────────────┘
            │ After=
            ▼
   ┌──── fralib-api.service ────┐
   │  uvicorn server.py:8000    │
   │  MemoryMax=1G CPUQuota=150%│
   └────────────────────────────┘
   
   ┌─── fralib-worker.service ──┐
   │  worker.py (pipeline)      │
   │  MemoryMax=2G CPUQuota=200%│
   └────────────────────────────┘
   
   ┌─── fralib-wpp-listener ────┐
   │  whatsapp_listener.py      │
   │  MemoryMax=512M            │
   └────────────────────────────┘
   
   ┌──── fralib-franz.service ──┐
   │  worker.py (SDR)           │
   │  MemoryMax=512M            │
   └────────────────────────────┘
   
            │ After= (todos)
            ▼
   ┌──── fralib-hermes.service ─┐
   │  hermes_daemon.py          │
   │  MemoryMax=256M            │
   │  (vigia os outros)         │
   └────────────────────────────┘
```

---

## 🧪 TASKS (quebra do plano)

### Task 1: SPEC (este arquivo) ✅
- [x] Documento escrito
- **Verde:** Criterios mensuráveis definidos

### Task 2: Service files
- [ ] infra/systemd/fralib-api.service
- [ ] infra/systemd/fralib-worker.service
- [ ] infra/systemd/fralib-franz.service
- [ ] infra/systemd/fralib-wpp-listener.service
- [ ] infra/systemd/fralib-hermes.service
- **Verde:** `systemd-analyze verify` exit 0 em todos

### Task 3: Helper env
- [ ] infra/systemd/env-from-dotenv.py
- **Verde:** gera EnvironmentFile válido

### Task 4: Scripts gestão
- [ ] scripts/systemd_install.sh (idempotente)
- [ ] scripts/systemd_uninstall.sh (rollback)
- [ ] scripts/migrate_pm2_to_systemd.sh (gradual)
- **Verde:** install sem erro, uninstall restaura PM2

### Task 5: Testes pytest
- [ ] tests/systemd/test_service_files.py
- [ ] tests/systemd/test_env_helper.py
- [ ] tests/systemd/test_health_check.py
- **Verde:** `pytest tests/systemd/` 100% PASS

### Task 6: Auditoria visual
- [ ] scripts/systemd_health_check.py
- **Verde:** 8+ checks PASS + screenshot

### Task 7: Deploy
- [ ] Validar sintaxe local
- [ ] Install em modo teste (systemd-analyze)
- [ ] Migrar 1 serviço (hermes primeiro)
- [ ] Migrar restantes
- **Verde:** Todos 5 rodando, sem downtime

---

## ⚠️ RISCOS + MITIGAÇÃO

| Risco | Mitigação |
|-------|-----------|
| systemd quebra boot VPS | `systemd-analyze verify` antes |
| .env não carrega | Helper Python valida |
| MemoryMax muito baixo | Começa conservador (1G/2G) |
| CPUQuota trava service | Só limita, não mata |
| Service não sobe | Fallback PM2 via uninstall |
| Watchdog mata serviço são | Só dispara se exceder limite |

---

## 🔐 SEGURANÇA

- `NoNewPrivileges=yes` em todos
- `ProtectSystem=full` em hermes
- `PrivateTmp=yes` em todos
- Sem acesso SSH/TTY

---

## 📊 COMPARAÇÃO

| Aspecto | PM2 | systemd |
|---------|-----|---------|
| RAM limit | ❌ | ✅ |
| CPU limit | ❌ | ✅ |
| Boot order | ❌ | ✅ |
| Logs | ⚠️ | ✅ journalctl |
| Watchdog | ❌ | ✅ |
| Padrão Linux | ❌ | ✅ |

---

## 🛡️ ROLLBACK

```bash
bash scripts/systemd_uninstall.sh   # para systemd
pm2 resurrect                        # PM2 volta do dump.pm2
```

**Tempo:** < 30s. **Perda de dados:** zero.