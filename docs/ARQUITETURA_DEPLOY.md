# ARQUITETURA DE DEPLOY — VPS Nova

**Última atualização:** 2026-07-30 | **Status:** ✅ Validado em produção

---

## 🏗️ TOPOLOGIA

```
┌─────────────────────────────────────────────────────────────────┐
│                          VPS NOVA                                │
│                    104.243.41.166 (Tailscale)                     │
│                  app.seunegociofralib.site                       │
│                                                                  │
│  ┌─────────────────────────┐    ┌─────────────────────────┐     │
│  │  NGINX (host)           │    │  systemd services       │     │
│  │  app.seunegociofralib. │◀──▶│  fralib-openui.service  │     │
│  │  :80/:443 → app:8000   │    │  (Python :7878)          │     │
│  │                        │    │                         │     │
│  │  /sites/<tenant>/...   │    │  /opt/fralib/          │     │
│  │  → volumes/fralib-...  │    │  openui-wandb/   │     │
│  └─────────────────────────┘    └─────────────────────────┘     │
│              │                                │                 │
│              ▼                                ▼                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Docker Compose (projeto: fralib)                        │   │
│  │  /opt/fralib/docker-compose.prod.yml                     │   │
│  │                                                          │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌───────────┐ │   │
│  │  │ fralib-api     │  │   worker-1    │  │ postgres-1│ │   │
│  │  │ (systemd)      │  │ unificado      │  │ :15434    │ │   │
│  │  │ 8001→8000      │  │ (pipeline+     │  │           │ │   │
│  │  │                │  │  supply+Franz) │  │           │ │   │
│  │  └────────────────┘  └────────────────┘  └───────────┘ │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌───────────┐ │   │
│  │  │                  │  │ redis-1       │  │           │ │   │
│  │  │                  │  │ :16379        │  │           │ │   │
│  │  └────────────────┘  └────────────────┘  └───────────┘ │   │
│  │                                                          │   │
│  │  Network: fralib_default (bridge)                        │   │
│  │  DNS interno: postgres, redis, app, worker              │   │
│  └─────────────────────────────────────────────────────────┘   │
│              │                                                   │
│              ▼                                                   │
│  ┌─────────────────────────────���───────────────────────────┐   │
│  │  DeployFlow API                                          │   │
│  │  https://deployflow.com.br/api/public/v1                 │   │
│  │  Claude Sonnet 4.6 (LLM) + Claude Vision (QA)           │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🐳 DOCKER COMPOSE (fralib)

**Arquivo:** `/opt/fralib/docker-compose.prod.yml`

### Serviços

| Serviço | Imagem | Comando | Volumes | Portas |
|---------|--------|---------|---------|--------|
| `postgres` | `postgres:16-alpine` | (default) | `fralib_fralib-postgres:/var/lib/postgresql/data` | `127.0.0.1:15434:5432` |
| `redis` | `redis:7-alpine` | (default) | `fralib-redis:/data` | `127.0.0.1:16379:6379` |
| `app` | (build local) | `python server.py` | `fralib-sites`, `fralib-logs`, `fralib-builder`, `/opt/fralib/data:/app/data` | `8001:8000` |
| `worker` | (build local) | `python worker.py` | `/opt/fralib/backend:/app/backend`, `fralib-sites`, `fralib-logs`, `fralib-builder` | (interno) |

**Worker unificado:** consome todos os tipos via `WORKER_JOB_TYPES` env var:
`pipeline_lead,pipeline_multiplos,pipeline_main,lead_production_tick,lead_supply_caio,lead_supply_hunter,franz_outreach`

### Volumes nomeados (persistidos)

```bash
docker volume ls | grep fralib
# fralib_fralib-postgres    # DB (external: criado fora do compose)
# fralib-redis              # cache
# fralib-sites              # sites deployados
# fralib-logs               # logs da app
# fralib-builder            # sandbox do builder
```

### Rede interna

Containers se comunicam via DNS interno do Docker Compose:
- `postgres:5432` → banco
- `redis:6379` → cache
- `app:8000` → API
- `host.docker.internal:7878` → OpenUI (no host, via systemd)

---

## 🔧 SYSTEMD (host)

### Serviço: fralib-openui

**Arquivo:** `/etc/systemd/system/fralib-openui.service`

```ini
[Unit]
Description=FraLib OpenUI Service - Python HTML generation (wandb/openui + LiteLLM)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fralib/openui-wandb
ExecStart=/root/.local/bin/uv run backend/openui/main.py
Restart=always
RestartSec=5
Environment=NODE_ENV=production
EnvironmentFile=/opt/fralib/openui-wandb/backend/.env

StandardOutput=journal
StandardError=journal
SyslogIdentifier=openui-service

[Install]
WantedBy=multi-user.target
```

### Comandos úteis

```bash
# Status
systemctl status fralib-openui
systemctl is-active fralib-openui

# Reiniciar
systemctl restart fralib-openui

# Logs
journalctl -u fralib-openui -f
journalctl -u fralib-openui -n 50 --no-pager

# Ver env vars do processo
PID=$(systemctl show fralib-openui --property=MainPID | cut -d= -f2)
cat /proc/$PID/environ | tr '\0' '\n' | grep -iE 'MODEL|API|BASE_URL|MAX_TOKENS'
```

---

## 🌐 NGINX (host)

**Arquivo:** `/etc/nginx/sites-enabled/app.seunegociofralib.site.conf` (ou similar)

Regra principal:
```nginx
server {
    listen 80;
    server_name app.seunegociofralib.site;

    location / {
        proxy_pass http://127.0.0.1:8000;  # fralib-api (systemd uvicorn)
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Sites deployados (arquivos estáticos)
    location /sites/ {
        alias /var/lib/docker/volumes/fralib_fralib-sites/_data/;
        try_files $uri $uri/ =404;
    }
}
```

---

## 📂 VOLUMES E CAMINHOS IMPORTANTES

### No host (VPS)

| Caminho | Conteúdo |
|---------|----------|
| `/opt/fralib/` | Projeto FraLib (código fonte, docker-compose) |
| `/opt/fralib/backend/` | Código Python (montado em `/app/backend` nos workers) |
| `/opt/fralib/.env` | Variáveis de ambiente (chaves, URLs) |
| `/opt/fralib/docker-compose.prod.yml` | Orquestração Docker |
| `/opt/fralib/openui-wandb/` | OpenUI Python (wandb/openui + LiteLLM, servido por systemd) |
| `/opt/fralib/openui-wandb/backend/.env` | Env vars do OpenUI |
| `/var/lib/docker/volumes/fralib_fralib-sites/_data/` | Sites gerados (acessíveis via /sites/) |
| `/var/lib/docker/volumes/fralib_fralib-postgres/_data/` | Dados do Postgres |
| `/var/lib/docker/volumes/fralib_fralib-logs/_data/` | Logs da app |

### Dentro do serviço fralib-api (systemd)

| Caminho | Conteúdo |
|---------|----------|
| `/opt/fralib/server.py` | API FastAPI (executada por uvicorn via systemd) |
| `/opt/fralib/backend/` | Código backend |
| `/app/.env` | Não existe (env vars vêm do docker-compose) |
| `/app/test_chain.py` | Script E2E (copiado manualmente) |
| `/var/www/fralib/sites/` | Sites deployados (volume `fralib-sites`) |

---

## 🔄 FLUXO DE DEPLOY

### Atualização de código

```bash
# 1. Local: editar código
# C:\fralib\backend\agents\builder\agent.py
# ...

# 2. Git push (se estiver em repo)
git add -A
SKIP_V11_PROTECTION=1 git commit -m "fix: timeout 600s"
git push origin master

# 3. VPS: pull + rebuild + restart
ssh -i ~/.ssh/id_ed25519 root@104.243.41.166
cd /opt/fralib
git pull
docker compose -f docker-compose.prod.yml build app worker-pipeline worker-cron worker-franz
docker compose -f docker-compose.prod.yml up -d app worker-pipeline worker-cron worker-franz
systemctl restart fralib-openui
```

### Mudança em env vars

```bash
ssh -i ~/.ssh/id_ed25519 root@104.243.41.166

# Editar .env
vi /opt/fralib/.env
vi /opt/fralib/openui-wandb/backend/.env

# Rebuild containers para pegar novas vars
cd /opt/fralib && docker compose -f docker-compose.prod.yml build app worker-pipeline worker-cron worker-franz
docker compose -f docker-compose.prod.yml up -d app worker-pipeline worker-cron worker-franz

# Restart OpenUI para pegar novas vars
systemctl restart fralib-openui
```

---

## 📊 MONITORAMENTO

### Health checks

```bash
# OpenUI
curl -s http://localhost:7878/v1/models

# API
curl -s http://localhost:8001/health
curl -s https://app.seunegociofralib.site/health

# Postgres
docker exec fralib-postgres-1 pg_isready -U fralib_user -d fralib_db

# Redis
docker exec fralib-redis-1 redis-cli ping

# Site deployado
curl -s -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" \
  https://app.seunegociofralib.site/sites/2/nova-imperio-gym-236f7cb9/
```

### Logs em tempo real

```bash
# Worker pipeline (mais importante para monitorar)
docker logs -f fralib-worker-pipeline-1

# OpenUI (chamadas LLM)
journalctl -u fralib-openui -f

# API
journalctl -u fralib-api -f  # API FastAPI (systemd)

# Postgres (queries lentas)
docker logs -f fralib-postgres-1
```

### Métricas de fila

```sql
-- Verificar jobs pendentes vs completed vs failed
docker exec fralib-postgres-1 psql -U fralib_user -d fralib_db -c "
SELECT status, COUNT(*) 
FROM jobs 
WHERE criado_em > NOW() - INTERVAL '1 day'
GROUP BY status
"

-- Leads por tenant com status
docker exec fralib-postgres-1 psql -U fralib_user -d fralib_db -c "
SELECT user_id, status, COUNT(*) 
FROM leads 
GROUP BY user_id, status 
ORDER BY user_id, status
"
```

---

## 🛡️ BACKUP E ROLLBACK

### Backup do projeto

```bash
ssh -i ~/.ssh/id_ed25519 root@104.243.41.166
cd /opt/fralib
tar -czf /tmp/fralib_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  backend/ docker-compose.prod.yml .env worker.py server.py

# Backup do OpenUI
tar -czf /tmp/openui_backup_$(date +%Y%m%d_%H%M%S).tar.gz /opt/fralib/openui-wandb/

# Backup do banco
docker exec fralib-postgres-1 pg_dump -U fralib_user -d fralib_db | \
  gzip > /tmp/fralib_db_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Rollback

```bash
# Restaurar código
cd /opt/fralib
tar -xzf /tmp/fralib_backup_YYYYMMDD_HHMMSS.tar.gz

# Rebuild + restart
docker compose -f docker-compose.prod.yml build app worker-*
docker compose -f docker-compose.prod.yml up -d app worker-*

# Restaurar banco
gunzip -c /tmp/fralib_db_*.sql.gz | \
  docker exec -i fralib-postgres-1 psql -U fralib_user -d fralib_db
```

---

## 🔗 INTEGRAÇÃO COM OUTROS SERVIÇOS

### DeployFlow (LLM provider)

- **Endpoint:** https://deployflow.com.br/api/public/v1
- **Auth:** header `x-api-key: dh-live-...`
- **Modelo principal:** `claude-sonnet-4-6`
- **Modelo Vision (QA):** mesmo `claude-sonnet-4-6` via `/chat/completions`
- **Rate limit:** mother keys com janela de 5h; retorna 503 quando lotado
- **Erros conhecidos:**
  - 401: chave inválida
  - 429: rate limit esgotado
  - 503: mother keys sem janela (esperar ~5h ou trocar chave)
  - 529: modelo sobrecarregado (transiente, retry resolve)

### Tailscale (acesso SSH)

- **IP VPS:** 104.243.41.166
- **SSH público:** bloqueado (firewall Hostinger)
- **SSH key:** `~/.ssh/id_ed25519` (pública em `/root/.ssh/authorized_keys`)

### whatsmeow (WhatsApp bridge)

- **Container:** `open-seo` (separado, fora do projeto `fralib`)
- **Porta:** 3002 (mapeada para 3001 interna)
- **Auth:** API key no `.env` da app (`MEOWHATS_URL=http://host.docker.internal:3001`)
- **Status leads WhatsApp:**
  ```sql
  SELECT sdr_stage, COUNT(*) FROM leads WHERE user_id = 2 GROUP BY sdr_stage
  -- pendente_wpp = aguardando Franz
  -- contatado = Franz enviou primeira msg
  -- respondido = lead respondeu
  -- convertido = lead converteu
  ```

---

## 📞 PONTOS DE FALHA E SOLUÇÕES

| Sintoma | Causa Provável | Solução |
|---------|----------------|---------|
| Container app-1 reiniciando | Porta 8000 ocupada | `lsof -i :8000` dentro do container, matar processo |
| OpenUI retorna 529 | DeployFlow sobrecarregado | Esperar 15min (retry automático no single-shot) |
| Builder timeout | LLM muito lento | Aumentar timeout em `agent.py` |
| Site não acessível | nginx não reiniciado | `systemctl reload nginx` |
| Leads não viram sites | `worker-pipeline` down | `docker compose up -d worker-pipeline` |
| QA v2 falha com Chrome Windows | `runner.py` não foi corrigido | Re-aplicar fix do `executable_path` |
| Erro `reviews_count` | worker.py não foi corrigido | Re-aplicar fix do `dados_completos` |

---

## 📚 DOCUMENTOS RELACIONADOS

- `PLAYBOOK_PIPELINE_VALIDADA.md` — Como executar e validar
- `BUGS_E_ACERTOS.md` — Cronologia da sessão de correção
- `docs/ARCHITECTURE_SPEC.md` — Spec original da plataforma
- `docs/ARCHITECTURE_DIAGRAM.md` — Diagrama de agentes
- `docs/VPS_SETUP.md` — Setup inicial da VPS (legado)
- `docs/SDR_ERROR_REFERENCE.md` — Erros do Franz
