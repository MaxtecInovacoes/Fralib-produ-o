# FraLib — Índice de Entrada

> **Fonte única de verdade**: [`AGENTS.md`](AGENTS.md).
> Toda a arquitetura, pipeline, contratos, atalhos, caches, testes e plano de ação estão lá.
> Se `CLAUDE.md` e `AGENTS.md` divergirem, **`AGENTS.md` vence**.
>
> **Pipeline atual**: Vite/React como engine PADRÃO (Sprint 12.9+).
> 26 segmentos cobertos via LLM cascade. Fail-fast total implementado.
> Qualquer erro na geração falha fechado — sem fallbacks genéricos.
> Em produção, publicação fora de `vite_react` falha fechado com
> `FRALIB_STRICT_CANONICAL_PUBLISH=1` ou `FRALIB_ENV=prod`.

## TL;DR
- **Pipeline canônica: 11 fases** (Hunter → Caio → Jina → Nicho → Variação → Arquiteto → **Vite/React** → QA → Deploy → Franz).
- **Gerador de site: Vite/React** (`backend/services/vite_react_renderer.py`) — engine PADRÃO desde Sprint 12.9.
- **OpenUI** (`backend/services/openui_renderer.py`) — rota alternativa, também fail-fast.
- **Política LLM do Vite**: `FRALIB_VITE_LLM_POLICY=creative_plan` por padrão. LLM escolhe copy/direção em JSON; Studio React gera TSX.
- **Blocos líquidos**: `creative_plan` agora materializa `data-pole` no app, tokens de geometria/cor/tipografia, LGPD e CTAs do mesmo tema.
- **SEO/localização Vite**: keywords agora combinam nicho + intenção regional (`agendar`, `preço`, `perto de mim`, WhatsApp) e `LocationSection` usa um único Google Maps real quando há endereço.
- **Lead Supply contínuo**: Hunter/Caio alimentam inventário fora do ciclo do site; sync recupera Caio `raw/error_retry`, e Franz não reabre falha permanente automaticamente.
- **Fail-fast total**: qualquer erro na geração levanta exceção clara — sem sites genéricos.
- **7 contratos canônicos** injetados no caroço: SEO, Design, Motion, A11y, Factual, LGPD, Deploy.
- **Briefing real** do lead: nome, segmento, cidade, telefone, fotos, SEO, services, horários.
- **Cross-contamination guard**: barbearia NUNCA menciona musculacao, academia NUNCA menciona corte.
- **Tracing** (Sprint 5) e **Sub-agentes por estética** (Sprint 6) continuam ativos.
- **Deploy**: `git push origin master` → `scripts/post-receive` → publish.
- **Diagnóstico**: `python pipeline.py smoke --dry-run`.
- **Regressão**: 12+ suites anti-regressão (v1.0 → v1.14).
- **Sprints concluídos (SDK)**: 13/13 sinais ativos — Sprints 0-9, 11, 12.

## Regra de ouro
A pipeline canônica é o **ÚNICO** caminho para gerar sites.
Mudou a pipeline, código, config ou docs? Atualizar **`AGENTS.md` primeiro** e propagar.

## Mapa de docs (verdade única)

| Doc | Função |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Fonte canônica — arquitetura, pipeline, sprints 0-12, ROI |
| `AGENTS.md` seção 22 | Sprint 11-12: Migração Vite/React, 26 segmentos, caroço rico |
| `AGENTS.md` seção 21 | Sprints 5-9 SDK: tracing, sub-agentes, RAG, auto-melhoria |
| `AGENTS.md` seção 7 | Os 46 patches canônicos (OpenUI path) |
| [`docs/ONE_TRUTH_CANONICAL_STATE.md`](docs/ONE_TRUTH_CANONICAL_STATE.md) | Estado canônico de filas, locks, billing |
| [`docs/SYSTEM_OPERATIONS_MAP.md`](docs/SYSTEM_OPERATIONS_MAP.md) | Mapa de runtime, request→site flow |
| [`docs/ONBOARDING_FOR_AI_AGENTS.md`](docs/ONBOARDING_FOR_AI_AGENTS.md) | Onboarding de novos agentes IA |
| [`docs/ROLLOUT_SPRINT_5.md`](docs/ROLLOUT_SPRINT_5.md) | Tracing dos 4 agentes |
| [`docs/ROLLOUT_SPRINT_6.md`](docs/ROLLOUT_SPRINT_6.md) | Sub-agentes por estética |
| [`docs/VITE_REACT_DEPLOY.md`](docs/VITE_REACT_DEPLOY.md) | Como Vite/React virou engine padrão e policy copy-only |

## ⚠️ CORREÇÃO IMPORTANTE (2026-06)

> Esta seção foi corrigida após auditoria independente do código-fonte.
> As informações anteriores podem estar **DESATUALIZADAS**.

## Como ativar features novas (VPS)

```bash
# Sprint 12.9+ - Vite/React (engine PADRÃO desde 2026-06-25)
# Produção usa systemd. Depois de mudar env em /etc/fralib/fralib.env,
# reiniciar fralib-worker e todas as instâncias fralib-worker@N.
sudo systemctl restart fralib-worker 'fralib-worker@*.service'

# Política LLM do Vite (padrão oficial: creative_plan)
# Comportamento real (verificado no código):
#   - creative_plan (PADRÃO): LLM escolhe copy + direção criativa em JSON, Studio gera TSX
#   - copy_only: LLM mínimo para copy, TSX gerado localmente
#   - full_code: LLM cascade tenta codar TSX completo; usar só em experimento
FRALIB_VITE_LLM_POLICY=creative_plan

# Sprint 5 — Tracing
FRALIB_TRACING=1

# Sprint 6 — Sub-agentes por estética
FRALIB_USE_SUB_AGENTS=1

# Sprint 7 — RAG Templates
FRALIB_USE_TEMPLATE_RAG=1

# Sprint 8 — Auto-melhoria
FRALIB_AUTO_IMPROVE=1
```

## O que ganhamos (Sprints 5-14)

| Métrica | Antes (Sprint 4) | Depois (Sprint 14+) |
|---|---|---|
| Engine padrão | OpenUI HTML estático | **Vite/React** (componentes) |
| Latência média render | 10-30s (LLM) | **5-30s** (LLM cascade) |
| Custo por site | variável | **Previsível** (Haiku→Sonnet→Opus) |
| Fail-fast | Studio fallback genérico | **Erro claro** se LLM falhar |
| Debug time | 30min | **2min** |
| Variedade visual | 1 genérico | **26 segmentos + 6 Awwwards** |
| Sinais SDK | 4/13 | **13/13** |
| Cobertura testes | 76 | **130+** (12+ suites) |
| Tela preta no site | comum (sem React) | **impossível** (post-process {var}) |
| Lead name injetado | ❌ | ✅ via `_business_context` |
| Fallbacks genéricos | Sim | ❌ **Fail-fast total** |

## Sistema de Variação Visual (Sprint 14.6+)

> **⚠️ PROBLEMA REPORTADO**: Sites saindo iguais!
> Verificar: `docs/DIAGNOSTICO_VARIACAO_SITES.md`

### 4 Eixos de Variação:
```python
hero_layout:     split | center | asymmetric | fullbleed | video
motion_style:    sharp | smooth | minimal
copy_voice:      aggressive | friendly | authoritative
color_emphasis:  primary_dominant | secondary_dominant | balanced
```

### 6 Archetypes Visuais:
| Archetype | Segmentos | Estilo |
|-----------|-----------|--------|
| BOLD_ENERGY | academia, fitness, crossfit | Alto impacto |
| WARM_LOCAL | barbearia, salao_beleza | Tons quentes |
| ZEN_PURE | clinica, estetica, nutri | Minimalista |
| LUXURY_ELITE | restaurante, pizzaria | Premium |
| MODERN_TECH | energia solar, mecanica | Tech |
| PROFESSIONAL_TRUST | advocacia, contabilidade | Profissional |

### Arquivos de Variação:
- `variation_seed.py` - Geração determinística
- `studio_archetypes.json` - 6 archetypes
- `archetype_resolver.py` - Seleção por segmento

## Regras de Auditoria (ANTI-FALSOS POSITIVOS)

> **PROBLEMA CONHECIDO**: Claude tende a declarar "pronto" ou "fail-fast total" sem verificar contradições, documentação desatualizada e código ainda existente.
> Estas regras PREVINEM falsos positivos.

### Antes de Declarar "Pronto", "Feito", "Completo" ou "Fail-Fast Total"

**OBRIGATORIAMENTE, use estas skills nesta ordem:**

1. **`/the-fool`** — Advocado do diabo
   - Desafie SUA própria conclusão
   - Liste evidências CONTRA o que você acabou de afirmar
   - Se não conseguir listar 3+ evidências contra, você está sendo tendencioso

2. **`/fp-check`** — Verificação de falsidade
   - Para CADA claim feito ("foi removido", "não existe mais", "passou")
   - Produza evidência CONCRETA: arquivo, linha, git diff
   - "O código mostra" não é evidência — mostre a linha exata

3. **`/completion-verifier`** — Verificação de completude
   - Testes novos foram adicionados para provar o novo contrato?
   - Documentação foi atualizada no mesmo commit?
   - Contradições com AGENTS.md foram resolvidas?
   - Testes em timeout foram tratados (deletados ou corrigidos)?

4. **`/agent-self-evaluation`** — Auto-avaliação crítica
   - Avalie-se em 5 eixos com NOTA e EVIDÊNCIA
   - Se dar nota 5 em qualquer eixo, prove com citação de linha

### Checklist Anti-Falso-Positivo

Para commits técnicos, antes de declarar "pronto", verificar:

- [ ] **Documentação atualizada?** AGENTS.md, CLAUDE.md, docs/ — todos no mesmo commit?
- [ ] **Código ainda existe?** Buscar por funções/variáveis que "foram removidas"
- [ ] **Testes timeout?** Testes em timeout não são "pass" — precisam de atenção
- [ ] **Contradições resolvidas?** AGENTS.md linha 24 e 773 dizem X, commit fez Y?
- [ ] **Variáveis de ambiente?** `FRALIB_ALLOW_OPENUI_FALLBACK` ainda existe?

### Quando USAR estas skills

- Após qualquer commit
- Quando Claude disser "pronto", "completo", "fail-fast total"
- Antes de fazer merge ou deploy
- Ao auditar código de outro agente

### Quando NÃO USAR

- Correções triviais (typos, formatação)
- Tarefas de busca sem claim de completude

---

## Status atual

- ✅ **Site v15h deployado e FUNCIONANDO** (`seunegociofralib.site/sites/2/barbearia-fio-nobre-v15h/`)
- ✅ **130+ testes verdes** (12+ suites anti-regressão)
- ✅ **21+ checks** no pre-commit hook
- ✅ **VPS rodando** com `FRALIB_BUILDER_ENGINE=vite_react`
- ✅ **Política LLM real**: `creative_plan` (JSON criativo + Studio React)
- ✅ **Fail-fast total**: Qualquer erro na geração levanta exceção clara — sem sites genéricos
- ⚠️ **SITES SAINDO IGUAIS?** → Verificar `docs/DIAGNOSTICO_VARIACAO_SITES.md`

## Tags v1.14.x (Sprint 12.19)

| Tag | Descrição |
|---|---|
| `v1.14.0-baseline` | Migração Vite/React engine padrão |
| `v1.14.1-baseline` | Wire caroço rico no LLM dispatcher |
| `v1.14.2-baseline` | 26 segmentos + clean bundle + deploy |
| `v1.14.3-baseline` | Lead name injection (Fio Nobre) |
| `v1.14.4-baseline` | Post-process {var} placeholders |

Todas em `2026-06-25`. Pronto para roll-forward.
