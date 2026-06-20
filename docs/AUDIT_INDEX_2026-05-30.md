<!--
LEGACY / HISTÓRICO — não use como fonte de verdade.
Ver docs/ONE_TRUTH_CANONICAL_STATE.md e docs/SYSTEM_OPERATIONS_MAP.md para o estado canônico atual.
-->


# FraLib — Indice Das Auditorias De 2026-05-30

Data: 2026-05-30 America/Sao_Paulo.

## Auditorias Salvas

- `docs/SYSTEM_AUDIT.md`: auditoria geral historica, estabilizacao, deploy e direcao visual.
- `docs/SYSTEM_FLOW_AUDIT_2026-05-30.md`: mapa atual de agentes, entradas, saidas, handoffs, fila, checkpoints e deploy.
- `docs/SKILLS_RUNTIME_AUDIT_2026-05-30.md`: skills instaladas, RAG, skills configuradas mas ausentes, e recomendacoes.
- `docs/PLAN_DESIGN_MAX_SYSTEM_2026-05-30.md`: plano executivo para Liam/OD, arquétipos, packs compactos e reducao de ruido.
- `spec/process-experience-driven-design-and-deploy-integrity-mvp.md`: spec MVP das mudancas de design experience-driven e integridade de deploy.

## Entendimento Atual Do Sistema

O caminho canonico e:

API -> fila Postgres -> worker -> Hunter/KW -> Caio -> Jina/Inteligencia -> Midia -> Nicho -> Variacao -> Arquiteto -> Liam -> Quality Gate -> Deploy -> Bryan separado.

Skill Renderer e a unica rota de HTML. Runtime externo de design e rota alternativa foram removidos; Validador LLM, Alex, Theo antigo e Liz sao legado ou compatibilidade, nao caminho padrao.

## Auditorias Que Ainda Precisam Ser Feitas

1. VPS runtime: comparar `/root/fralib` com `C:\fralib`, PM2 envs e commit ativo.
2. Skills na VPS: listar roots e confirmar se `design-system`, `ui-styling`, `design`, `brand` existem.
3. Logs reais: procurar `[Skills] OK`, `[LLM Direct] RAG ativado`, renderer usado e repairs do quality gate.
4. Teste real controlado: rodar uma pipeline curta depois que SSH/credenciais estiverem disponiveis.

## Decisao Operacional

Antes de qualquer deploy, usar o fluxo oficial:

editar local -> testes/smoke -> git add -> git commit -> git push -> hook publica master.

Nunca corrigir direto na VPS.
