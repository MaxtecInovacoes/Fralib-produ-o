# FraLib systemd services

Serviços systemd nativos para substituir PM2 (gradualmente).

## Serviços

| Service | Era (PM2) | Limite RAM | CPU | Restart |
|---------|-----------|-----------|-----|---------|
| fralib-api | fralib | 1G | 150% | on-failure, 5s |
| fralib-worker | fralib-worker | 2G | 200% | on-failure, 10s |
| fralib-franz | fralib-franz-worker | 512M | 100% | on-failure, 15s |
| fralib-wpp-listener | fralib-wpp-listener | 512M | 100% | on-failure, 5s |
| fralib-hermes | fralib-hermes-watchdog | 256M | 50% | always, 30s |

## Instalação

```bash
bash scripts/systemd_install.sh   # Idempotente, NÃO inicia
bash scripts/migrate_pm2_to_systemd.sh  # Migração gradual
```

## Rollback

```bash
bash scripts/systemd_uninstall.sh   # Para systemd, volta PM2
pm2 resurrect                        # Confirma
```

## Logs

```bash
journalctl -u fralib-api -f         # Tail ao vivo da API
journalctl -u fralib-worker --since "10 minutes ago"
```

## Verificação

```bash
systemctl list-units --type=service --state=running | grep fralib
systemctl status fralib-api
bash scripts/systemd_install.sh     # Idempotente
```

## Arquivos

- `*.service` — 5 unidades systemd
- `env-from-dotenv.py` — helper para gerar EnvironmentFile
- `../scripts/systemd_install.sh` — installer idempotente
- `../scripts/systemd_uninstall.sh` — rollback
- `../scripts/migrate_pm2_to_systemd.sh` — migração gradual