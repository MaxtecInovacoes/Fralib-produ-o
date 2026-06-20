# FraLib — Contexto Tecnico

Este documento deve contar a mesma historia do `AGENTS.md` e do `README.md`.
Se uma decisao mudar, atualizar os tres no mesmo commit.

## Contrato de Deploy
- Nunca editar direto na VPS, usar SCP ou rsync.
- Fluxo unico: editar local -> commit -> push -> hook de deploy.
- Codigo em producao precisa ser reproduzivel a partir do Git.
- Fonte canonica local: `C:\fralib`; fonte canonica VPS: `/root/fralib`.
- Ignore pastas antigas fora desses caminhos, caches de IDE e backups.

## Pipeline Atual
1. Hunter + Keyword Research
2. Caio
3. Jina + inteligencia de mercado
4. Unsplash + Pexels
5. Agente de Nicho
6. Agente de Variacao
7. Arquiteto Mestre (`DesignerPRD`)
8. Skill Renderer
9. Quality gate
10. Deploy + health check
11. Bryan SDR

## Arquitetura
- Backend: FastAPI em `server.py`.
- Orquestrador: `backend/endpoints/pipeline_endpoints.py`.
- Fila/locks: PostgreSQL, `pipeline_queue` e `pipeline_state`.
- Geracao HTML: `backend/agents/skill_based_renderer.py` via `liam_renderer.py`; sem rota fallback de renderer.
- WhatsApp: `meowhats` em `:3001`; Bryan roda como job separado.
- Smoke oficial: `python pipeline.py smoke --dry-run`.
- O smoke tambem valida contexto canonico e bloqueia nomes/caminhos legados.

## Estado da Estabilizacao
- Branch: `codex/pipeline-stabilization`.
- Foram identificados estado local/VPS fora do Git, lock orfao e docs divergentes.
- Correcoes desta linha de trabalho devem priorizar reproducibilidade antes de benchmark completo.

## Legado
- A lista em "Pipeline Atual" e a unica fonte valida.
- Qualquer agente, arquivo ou flag fora dessa lista e legado ate prova em codigo.
- `*_agent_loop.py` referenciados por flags nao existem; nao habilitar sem implementar.

## Endpoints Principais
- `/api/pipeline/*`: iniciar, status, reset, reprocessar, analytics.
- `/api/leads/*`: CRUD, fila, manual, editar site, envio Bryan.
- `/api/queue/*`: status e falhas.
- `/api/observability/*`: traces e gargalos.
- `/api/whatsapp/*`: status/conexao.
- `/api/agent-configs/*`, `/api/provider-keys/*`: configuracao LLM.
- Plano MVP/tasks: `docs/PRD_MVP_ESTABILIZACAO_FRALIB.md`.

## Alertas
- `pipeline_endpoints.py` esta grande demais e deve ser quebrado por fases.
- Smoke dry-run deve passar antes de rodar pipeline real.
- Qualquer limpeza da VPS deve ser automatizada e versionada, nao manual.
- Multiusuario depende de `tenant_id/user_id` em DB, jobs, arquivos e WhatsApp.

## Sistema Anti-Perda (2026-06-20)

**Problema resolvido:** Modificacoes que se perdiam entre sessoes.

**Regras inviolaveis:**
1. **Nunca** encerrar sessao com working tree sujo. Antes: `git add -A && git commit`
2. **Sempre** rodar `./scripts/check_uncommitted.sh` antes de deploy
3. **Sempre** atualizar `docs/STATUS.md` quando o estado mudar
4. **Nunca** criar branch sem registrar em `docs/STATUS.md`

**Antes de qualquer deploy:**
```bash
./scripts/check_uncommitted.sh   # deve retornar 0
git push origin master
```
