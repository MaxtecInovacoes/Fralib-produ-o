# Professional Ops Docs And Watchdog

## Why

FraLib chegou ao ponto em que produto, billing, pipeline, worker, SDR e Builder
precisam ser compreendidos por qualquer operador ou IA sem depender de memoria
de conversa. O risco atual nao e apenas bug de codigo: e operador ou agente
abrir o repositorio, seguir um documento antigo, ativar um caminho legado ou
tentar corrigir producao fora do fluxo Git.

Esta mudanca cria uma camada operacional canonica e prepara o caminho para um
watchdog 24h real, com playbooks seguros, sem permissao para apagar dados,
editar VPS direto ou tomar decisoes destrutivas.

## What Changes

- Criar indice canonico de documentacao operacional.
- Criar onboarding para humanos e IAs abrirem o repo e entenderem o que e real.
- Criar mapa operacional do sistema: processos, pastas, pipeline, fila, billing,
  seguranca, observabilidade e deploy.
- Criar referencia de agentes por entrada, saida, arquivos, sucesso esperado e
  falhas comuns.
- Criar catalogo gerado dos arquivos rastreados por area.
- Criar runbook Hermes 24h com monitoramento, severidade, playbooks allowlist e
  denylist de acoes proibidas.
- Criar backlog profissional de lacunas para maturidade de SaaS.
- Atualizar `AGENTS.md` para apontar para a documentacao canonica sem estourar
  o limite de 80 linhas.

## Out Of Scope

- Criar automacao 24h que altere dados ou reinicie servicos sem contrato.
- Editar VPS diretamente.
- Substituir PM2, Postgres ou a fila atual.
- Reescrever a pipeline.
- Prometer correcao automatica de todo tipo de incidente.

## Impact

- `docs/DOCS_INDEX.md`
- `docs/ONBOARDING_FOR_AI_AGENTS.md`
- `docs/SYSTEM_OPERATIONS_MAP.md`
- `docs/AGENT_PATHS_REFERENCE.md`
- `docs/HERMES_24H_WATCHDOG_RUNBOOK.md`
- `docs/PROFESSIONAL_SYSTEM_GAPS.md`
- `openspec/changes/professional-ops-docs-and-watchdog/*`
- `AGENTS.md`
