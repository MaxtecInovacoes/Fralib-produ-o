---
title: FraLib Experience-Driven Design And Deploy Integrity MVP
version: 1.0
date_created: 2026-05-30
last_updated: 2026-05-30
owner: FraLib
tags: [mvp, deploy, git, design, archetypes, liam]
---

# Objetivo

Impedir republicacao de frontend antigo e elevar a geracao de sites locais de
layout institucional para composicao editorial guiada por arquétipos visuais,
sem enfraquecer o contrato factual.

# Auditoria

## Achados de deploy

- O hook `scripts/post-receive` executava deploy em qualquer push recebido.
- Mesmo quando a branch enviada nao era `master`, o hook puxava e publicava
  `origin master`. Isso podia republicar uma landing antiga durante trabalho
  em branches de estabilizacao.
- O hook copiava `frontend/*.html`, incluindo artefatos nao canonicos.
- `frontend/build.py` reconstruia `landing.html` a partir dos partials e ainda
  tentava copiar direto para `/var/www/fralib`, criando duas rotas de deploy.
- `frontend/landing2.html` e `frontend/landing_backup.html` estavam soltos no
  workspace e ja eram tratados como artefatos nao canonicos pelo auditor.
- O smoke local ainda bloqueava a string `Liam`, embora Liam seja renderer
  oficial. A denylist foi alinhada para bloquear arquivos legados, nao nomes
  ativos.

## Achados de design

- FraLib ja possui design systems, craft rules, motion GSAP/Lenis, Liam renderer
  e quality gate com repair.
- A lacuna real nao e adicionar outro framework ou um segundo agente caro.
- Faltava uma camada universal e compacta que transforme nicho em intencao
  visual coerente antes do Arquiteto, do renderer e da busca de midia.
- Claims emotivos continuam permitidos somente quando nao se apresentam como
  fatos verificaveis. Servicos, numeros, equipe e resultados continuam exigindo
  evidencia.

# Implementacao MVP

1. Fazer o hook publicar somente quando `refs/heads/master` mudar.
2. Validar frontend canonico antes de publicar.
3. Publicar HTML top-level por whitelist, nunca por glob.
4. Remover deploy direto de `frontend/build.py`.
5. Bloquear HTMLs soltos conhecidos no smoke.
6. Adicionar `visual_archetypes.py` com:
   `BOLD_IMPACT`, `TRUST_AUTHORITY`, `ZEN_WELLNESS`, `MODERN_TECH`,
   `LUXURY_EDITORIAL`.
7. Injetar arquétipo no briefing do Arquiteto e no `visual_recipe` do Liam.
8. Herdar mood do arquétipo nas queries Unsplash.

# Decisoes

- Nao adicionar Framer Motion: o artefato final e HTML estatico e ja usa
  GSAP/Lenis.
- Nao criar agente LLM separado de polimento: o quality gate e o repair Liam
  cumprem esse papel com menos custo e menos variacao.
- Nao editar VPS manualmente: deploy continua sendo local -> commit -> push.

# Criterios de aceite

- Push para branch diferente de `master` nao publica frontend.
- Hook falha se `landing.html` ou `dashboard.html` divergirem dos partials.
- Hook nao publica `landing2.html` nem `landing_backup.html`.
- Build local nao escreve em `/var/www/fralib`.
- Smoke inclui `frontend-canonical`.
- Nutricionista recebe `ZEN_WELLNESS`; academia recebe `BOLD_IMPACT`.
- Query de midia inclui o mood do arquétipo.
- Gate local passa no ambiente com dependencias e a VPS passa pelo
  `python3 pipeline.py pre-release-gate` apos push.

# Teste controlado

1. Rodar testes unitarios do motor de arquétipos e contrato frontend.
2. Rodar `python pipeline.py smoke --dry-run`.
3. Rodar `python pipeline.py pre-release-gate`.
4. Fazer push de branch de teste e confirmar log `deploy ignorado`.
5. Fazer merge/push em `master`, confirmar hash publicado e gerar um lead de
   wellness e um fitness para comparar direção sem inventar fatos.

# Bloqueio Atual

A auditoria remota automatizada nao foi concluida porque a VPS recusou
autenticacao SSH neste ambiente em 2026-05-30. A validacao remota permanece
obrigatoria antes do deploy.
