# FraLib — Plano Executivo Design Max

Data: 2026-05-30 America/Sao_Paulo.
Objetivo: elevar a qualidade visual com poucas alavancas fortes, mantendo custo baixo e pipeline previsivel.

## Decisao Central

Parar de aumentar complexidade. O sistema deve concentrar criatividade em:

- arquétipos visuais;
- skills compactas para o Skill Renderer;
- regras universais de composicao;
- media flow por mood;
- quality gate visual deterministico;
- design systems curados como referencia, nao como motor bruto.

## Fase 1 — Agora

1. Travar skills visuais do Skill Renderer:
   - `impeccable`
   - `design-with-taste`
   - `emil-design-eng`
   - `design-motion-principles`

2. Usar packs compactos versionados:
   - evitar depender de instalacao manual em cada VPS;
   - manter `FRALIB_SKILLS_TOTAL_MAX_CHARS` baixo;
   - carregar skill pesada somente em Skill Renderer/Arquiteto, nunca em Hunter/Caio/Jina.

3. Consolidar arquétipos:
   - `BOLD_IMPACT`
   - `TRUST_AUTHORITY`
   - `ZEN_WELLNESS`
   - `MODERN_TECH`
   - `LUXURY_EDITORIAL`

4. Remover fallback de renderer:
   - Skill Renderer e a rota padrao e unica;
   - runtime externo de design nao deve competir como rota paralela.

## Fase 2 — Depois Da Estabilidade

1. Criar `Design DNA Mixer`.
2. Classificar os 149+ design systems em arquétipos e slugs curados.
3. Gerar `visual_seed` por lead para variar:
   - hero;
   - ritmo de secoes;
   - border radius;
   - densidade;
   - uso de imagem;
   - escala tipografica.
4. Nunca usar os 149 systems como massa bruta no prompt principal.

## Fase 3 — Polimento Visual

1. Adicionar etapa de polimento apos Skill Renderer.
2. Comecar deterministico:
   - contraste;
   - motion markers;
   - footer;
   - placeholders;
   - excesso de cards iguais.
3. So usar LLM/visao se o deterministico nao resolver.

## Ruido Para Standby

- Alex, Theo antigo e Liz.
- Validador LLM como rota padrao.
- `design_system_slug` como decisao final.
- Skills novas que so aumentam prompt sem melhorar HTML.
- Mistura aleatoria dos 149 design systems antes da curadoria.

## Arquivos Principais

- `backend/agents/skill_loader.py`
- `backend/agents/skill_packs/*/SKILL.md`
- `backend/agents/visual_archetypes.py`
- `backend/agents/bloco_estrutura.py`
- `backend/agents/liam_renderer.py`
- `backend/agents/html_quality_gate.py`
- `backend/agents/design_system_selector.py`
