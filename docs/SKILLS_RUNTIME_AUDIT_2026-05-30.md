<!--
LEGACY / HISTÓRICO — não use como fonte de verdade.
Ver docs/ONE_TRUTH_CANONICAL_STATE.md e docs/SYSTEM_OPERATIONS_MAP.md para o estado canônico atual.
-->


# FraLib — Auditoria de Skills, RAG e Recursos Instalados

Data: 2026-05-30 America/Sao_Paulo.
Escopo: local `C:\fralib`, skills Windows do usuario e configuracao runtime do FraLib.

## Dois Tipos De Skill

1. Skills do Codex/gstack
   - Instaladas em `C:\Users\JESUS TE AMA\.agents\skills` e `C:\Users\JESUS TE AMA\.codex\skills`.
   - Servem para este agente trabalhar: QA, browse, review, ship, plan, etc.
   - Nao entram automaticamente no site gerado pelo FraLib.

2. Skills runtime do FraLib
   - Carregadas por `backend/agents/skill_loader.py` e `backend/agents/llm_direct.py`.
   - Entram no prompt dos agentes LLM quando `agent_name` bate com a configuracao.
   - Nao existe mais skill interna de Open Design no caminho de runtime.

## Skills Do Codex Instaladas

Foram encontrados 56 arquivos `SKILL.md` nos roots locais do usuario, incluindo:

- `gstack`, `browse`, `qa`, `qa-only`, `review`, `ship`, `health`, `benchmark`, `canary`.
- `design-review`, `design-shotgun`, `design-html`, `design-consultation`, `plan-design-review`.
- `plan-ceo-review`, `plan-eng-review`, `plan-devex-review`, `autoplan`.
- `investigate`, `cso`, `guard`, `careful`, `freeze`, `unfreeze`.
- `context-save`, `context-restore`, `learn`, `document-release`, `make-pdf`.
- `find-skills` em `C:\Users\JESUS TE AMA\.codex\skills\find-skills`.
- `impeccable` e `design-motion-principles`.

Essas sao boas ferramentas de desenvolvimento, mas nao sao chamadas pelo pipeline FraLib em producao.

## Skills Runtime Esperadas Pelo FraLib

`skill_loader.py` procura estes nomes:

- `agente_nicho`: `brand`, `design`.
- `arquiteto_mestre`: `design-system`.
- `liam`: modo compacto usa apenas `ui-ux-pro-max`.
- `liam` com `FRALIB_LIAM_FULL_SKILLS=1`: `ui-ux-pro-max`, `design-system`, `ui-styling`.
- `validador`: `design-system`.

## O Que Esta Instalado Localmente Para Runtime

Encontrado:

- `ui-ux-pro-max`: `C:\Users\JESUS TE AMA\.claude\skills\ui-ux-pro-max\SKILL.md`.
- `design-taste-frontend`: `C:\Users\JESUS TE AMA\.claude\skills\design-taste-frontend\SKILL.md`.
Nao encontrado localmente nos roots conhecidos:

- `brand`
- `design`
- `design-system`
- `ui-styling`

## Atualizacao De Implementacao

- Skill Renderer usa packs compactos versionados em `backend/agents/skill_packs`.
- Packs ativos: `impeccable`, `design-with-taste`, `emil-design-eng`, `design-motion-principles`.
- O loader tambem procura `.agents/skills` local e roots VPS, mas o deploy nao depende desses diretórios.
- `FRALIB_SKILLS_TOTAL_MAX_CHARS` limita o total carregado por chamada, mantendo custo previsivel.
- Arquiteto Mestre recebe `design-with-taste` como referencia compacta; Hunter/Caio/Jina ficam leves.

## RAG Instalado

Arquivos em `backend/agents/rag_knowledge`:

- Ativos no caminho padrao quando `agent_name` bate: `agente_nicho.md`, `liam.md`.
- Bryan usa `bryan.md` manualmente dentro de `bryan.py`.
- Disponiveis mas hoje legados/opcionais: `validador.md`, `designer.md`, `curadoria.md`, `caio.md`, `seo_local.md`.

## Achados Importantes

1. O carregamento de skills existe e funciona por roots locais/VPS/repo.
2. Liam passou a ser servido por packs versionados, evitando dependencia runtime em skills externas completas.
3. Bryan chama `call_claude` com `agent_name="Franz"`. Isso impede o RAG automatico de `llm_direct` procurar `bryan.md`, embora o proprio Bryan injete `bryan.md` manualmente antes da chamada.
4. O decorator `@require_rag("Bryan")` verifica a chave `Bryan`, mas `mark_rag_used("bryan")` marca lowercase. Isso pode gerar warning falso de RAG nao usado.
5. `caio.md` existe, mas Caio e deterministico e nao usa LLM; isso nao e problema.
6. `validador.md` existe, mas o validador LLM nao e o gate padrao; o gate atual e `html_quality_gate.py`.

## O Que Parece Valer Ativar Ou Corrigir

Prioridade alta:

- Manter os packs compactos como fonte canonica do runtime e usar skills completas apenas para evoluir esses packs.
- Corrigir Bryan para usar um nome canonico: `agent_name="bryan"` e `@require_rag("bryan")`.
- Criar teste/smoke que falhe se skill essencial configurada nao existir no root runtime.

Prioridade media:

- Usar `design-taste-frontend` no Liam full skills ou incorporar partes dela no RAG Liam.
- Criar `rag_knowledge/arquiteto_mestre.md` se a intencao e dar RAG direto ao Arquiteto; hoje ele depende de skills externas e prompts internos.
- Revisar se `agente_nicho` realmente precisa de `brand/design` ou se o novo `visual_archetypes.py` ja cobre o necessario.

Pendente VPS:

- Verificar os roots `/root/.claude/skills`, `/root/.agents/skills`, `/root/.codex/skills` e `FRALIB_SKILLS_DIRS`.
- Confirmar nos logs de producao quais skills sao carregadas de verdade.
