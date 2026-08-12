# Deploy Pipeline — FraLib

## Arquitetura de Deploy

```
git push origin master
    │
    ▼
GitHub (remote)
    │
    │  (git push vps master)
    ▼
VPS: /root/repos/fralib.git (bare repo)
    │
    ▼  post-receive hook
    ├── git checkout --force
    ├── rsync /root/fralib/ → /opt/fralib/
    ├── docker compose restart worker
    ├── systemctl restart fralib-api.service   ← OBRIGATÓRIO
    └── systemctl restart fralib-openui.service ← OBRIGATÓRIO
```

## Serviços na VPS

| Serviço | Tipo | Porta | Como reiniciar |
|---------|------|-------|----------------|
| fralib-worker | Docker Compose | — | `docker compose restart worker` |
| fralib-api | systemd | 8001 | `systemctl restart fralib-api.service` |
| fralib-openui | systemd | 7878 | `systemctl restart fralib-openui.service` |

## ⚠️ REGRA CRÍTICA: Sempre reiniciar TODOS os serviços

O deploy hook **DEVE** executar todos os 3 restarts após cada push:

```bash
# /root/repos/fralib.git/hooks/post-receive

echo "=== Docker Compose restart worker ==="
cd /opt/fralib && docker compose restart worker

echo "=== Restart fralib-api ==="
systemctl restart fralib-api.service

echo "=== Restart fralib-openui ==="
systemctl restart fralib-openui.service

echo "=== Deploy concluido ==="
```

### Por que?

- `fralib-api` roda via systemd (não Docker). O hook antigo só reiniciava o worker Docker.
- Código atualizado no disco não é carregado pelo processo em execução — precisa de restart.
- Se a API não reiniciar, endpoints novos (ex: `/restart-api`) e fixes de código ficam indisponíveis até restart manual.

## Restart via API (alternativa)

Se `fralib-api` estiver rodando, pode-se usar o endpoint admin:

```
POST /api/admin/pipeline/restart-api
Authorization: Bearer <JWT superadmin>
```

Este endpoint executa `systemctl restart fralib-api.service` internamente.
Disponível desde commit `e4daaeb1`.

## Fluxo de Deploy Manual (emergência)

```bash
# 1. Push do código
git push vps master

# 2. Verificar que código chegou
ssh root@VPS "cd /opt/fralib && git log --oneline -3"

# 3. Reiniciar TODOS os serviços
ssh root@VPS "systemctl restart fralib-api.service && docker compose -f /opt/fralib/docker-compose.prod.yml restart worker"
```
