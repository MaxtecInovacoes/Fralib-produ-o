# FraLib - AGENTS.md
## Regras Absolutas
1. Nunca usar SCP, rsync ou editar arquivos direto na VPS.
2. Fluxo oficial: editar local -> git add -> git commit -> git push.
3. Nunca deployar codigo nao commitado.
4. Se mudou codigo, config, pipeline ou docs, atualizar este arquivo.
5. Este arquivo deve ficar com no maximo 80 linhas.

## Estado Atual (2026-06-21)
- Branch: master
- Runtime: **systemd** (5 servicos) - PM2 removido, fallback via ServiceManager
- ServiceManager: backend/services/service_manager.py (auto-detect systemd/pm2)
- Admin API: /api/admin/services, /logs, /restart, /runtime, /incidents
- Frontend: card "Servicos" mostra runtime primario (systemd/pm2)
- Esteira Fra: status agrega jobs/spans/ledger; tempo vem de iniciado/concluido + media historica
- Monolitos quebrados: vite_react_renderer, pipeline_orchestrator_service, leads_crud
- Modulos extraidos de vite: vite_config, vite_prompts, vite_facts, file_extractor, validator, build_executor
- Performance: cache node_modules, Caio+Jina asyncio.gather, Design Director cache 24h
- Backup: PostgreSQL diario 02:00 UTC (7d/4w retencao) - scripts/backup_postgres.sh
- Bugs corrigidos: IDOR, OAuth CSRF, CORS, Leads Cache, Revoke Token fail-open, valor_venda lock

## Decisoes Pausadas (NAO implementar ate gatilho)
| Melhoria | Gatilho para reativar |
|----------|----------------------|
| Prometheus + Grafana (metricas) | Cliente reclamar de lentidao sem causa clara, OU 50+ tenants |
| Auto-detect whatsmeow no ServiceManager | 10+ tenants ativos, ou operador esquecer de monitorar WPP |
| Loki (logs centralizados) | Precisar buscar erro antigo de tenant especifico |
| k8s | 5+ VPS / cluster, ou 100+ servicos |

## Pipeline (11 FASES - VERSAO CANONICA)
1. Hunter + Keyword Research  2. Caio  3. Jina  4. Unsplash+Pexels
5. Agente de Nicho  6. Agente de Variacao  7. Arquiteto Mestre
8. Skill Renderer (Vite)  9. Quality gate  10. Deploy  11. Bryan SDR

## Arquitetura
- Backend: FastAPI em `server.py` (porta 8000, systemd: fralib-api)
- Orquestrador: `backend/endpoints/pipeline_orchestrator_service.py`
- Fila/locks: PostgreSQL, tabelas `pipeline_queue` e `pipeline_state`
- WhatsApp: whatsmeow em `:3001` (systemd proprio, fora do ServiceManager)
- ServiceManager: `backend/services/service_manager.py` (USAR SEMPRE, nao hardcodar pm2/systemctl)

## Infra
- VPS: root@187.77.37.72 (96GB disco, 7.8GB RAM)
- Systemd: fralib-api (1G RAM/150% CPU), fralib-worker (2G/200%), fralib-franz (512M/100%),
  fralib-wpp-listener (512M/100%), fralib-hermes (256M/50%)
- LLM: kpalabz direto (LiteLLM removido em 2026-06-20)
- WhatsApp keepalive: 30s, reconexao agressiva

## Sincronizacao
- VPS sincronizada com GitHub via hook (a cada push)
- Verificar: ssh root@187.77.37.72 "cd /root/fralib && git log -1 --format='%H'"
- Rollback systemd: bash scripts/systemd_uninstall.sh + pm2 resurrect
