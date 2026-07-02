# Sistema de Polos e Nichos — Arquitetura Técnica

> Documento técnico de arquitetura. Última atualização: Sprint 12.x (Etapas 1-5).

## Princípio Central

**`backend/config/nicho_registry.py` é a fonte única de verdade para tudo que é nicho-específico.**

Este é o axioma do sistema: `nicho_registry.py` é a única fonte de verdade. Qualquer adição de nicho, lane, copy, schema.org, polo ou sub-nicho override **deve** ser feita primeiro no registry. Os outros módulos consomem via `get_nicho_config(nicho)` / `get_schema_type(nicho)` / `resolve_polo_for_lead(nicho, subnicho)`.

## Camadas de arquitetura

```
┌────────────────────────────────────────────────────────────────────┐
│ 1. CONSTITUIÇÃO (fonte única)                                       │
│    backend/config/nicho_registry.py                                │
│    - NICHO_CONFIG: dict com 13 nichos canônicos                    │
│    - NichoConfig: dataclass frozen com                            │
│        schema_type, polo_sugerido, lanes, modal_config,            │
│        faq, hero_headlines, copy_defaults, design_logic,           │
│        seo_keywords                                                │
│    - ALIASES: 50+ aliases para segmentos variantes                 │
│    - SUB_NICHO_POLO_OVERRIDES: 43 regras de override por subnicho  │
│    - get_nicho_config(nicho) / get_schema_type / get_modal_config  │
│    - resolve_polo_for_lead(nicho, subnicho, inferido)              │
└────────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼──────────────────────┐
        ▼                     ▼                      ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ 2. COPY       │    │ 3. VISUAL        │    │ 4. PROMPTS       │
│              │    │                  │    │                  │
│ copywriting/ │    │ services/        │    │ agents/          │
│ - copy_angles │    │ vite_liquid_     │    │ - bloco_copy     │
│ - polo_voice  │    │   components     │    │ - bloco_estrutura│
│ - seo_templates│    │ vite_visual_     │    │ - polo_prompts   │
│              │    │   lanes          │    │ - prompts_        │
│ 8 frameworks │    │ vite_templates   │    │   arquiteto      │
│ 4 polos voice│    │ vite_react_      │    │                  │
│ 56 SEO tpls  │    │   renderer       │    │                  │
└──────────────┘    └──────────────────┘    └──────────────────┘
```

## Os 4 Polos Estéticos

| Polo | Nichos principais | Visual | Copy voice |
|---|---|---|---|
| **SOFT** | nutri, estetica, pet_shop, salao, restaurante, barbearia | 30-50px radius, serif, warm, respiro | acolhedor, sensorial, ritual |
| **BOLD** | academia, oficina, eventos | 0px radius, Anton italic uppercase, text-stroke | agressivo, confrontativo, identidade tribal |
| **CLASSIC** | advogado, clinica, dentista, contabilidade | 4-8px radius, Inter Medium, grid limpo | autoridade, técnica, sigilo, método |
| **TECH** | energia_solar, SaaS, arquitetura, startups | 12px radius, Space Grotesk, glassmorphism | dados, ROI, monitoramento, especificidade |

**Override por subnicho** (43 regras):
- `nutricionista + atleta/performance` → BOLD
- `academia + yoga/pilates/alongamento` → SOFT
- `advogado + empresarial/tributario/compliance` → TECH
- `restaurante + fast_food/hamburgueria/pizzaria` → BOLD

## 13 Nichos Canônicos

```
academia, advogado, barbearia, clinica, dentista, energia_solar,
estetica, imobiliaria, nutricionista, oficina, pet_shop, restaurante,
salao
+ default (fallback)
```

Cada nicho tem: `schema_type`, `polo_sugerido`, `lanes`, `modal_config`, `faq`, `hero_headlines`, `copy_defaults`, `design_logic`, `seo_keywords`.

Total de **38 lanes** mapeadas (2-4 por nicho) com paleta, variants e copy enrichments próprios.

## Aliases e Compatibilidade

Módulos legados que mantemos apenas para compatibilidade:

| Módulo | Constante legacy | Status |
|---|---|---|
| `vite_prompts.py` | `NICHO_MODAL_CONFIG` | DEPRECATED — fallback apenas |
| `seo_context.py` | `SEO_NICHOS` | DEPRECATED — registry primeiro |
| `vite_visual_lanes.py` | `_FAMILY_COPY_DEFAULTS` | DEPRECATED — registry primeiro |

**Regra**: código NOVO nunca deve ler essas constantes legacy. Use os helpers do registry.

## Fluxo de Dados

```
Lead chega
  ↓
agente_nicho / agente_variacao → segmento + subnicho
  ↓
nicho_registry.resolve_polo_for_lead(segmento, subnicho)
  ↓ polo: SOFT | BOLD | CLASSIC | TECH
  ↓
bloco_estrutura → _montar_prompt_bloco1
  - injetar POLO block (tokens + DesignLogic)
  ↓
bloco_copy → _montar_prompt_bloco2
  - injetar POLO block (CopyDefaults)
  - injetar COPY ANGLE (framework + hook + body + cta)
  - injetar VOICE CHECK (vocab + avoid + triggers)
  - injetar SEO templates
  ↓
LLM gera site com polo + copy + voice corretos
  ↓
vite_react_renderer → build_vite_project
  - data-pole="X" no <html>
  - design-system-tokens.css linkado
  - Layout Mode (hero/services/gallery) por polo
  ↓
vite_templates._facts_json_ld → schema.org @type dinâmico
  - advogado → LegalService
  - restaurante → Restaurant
  - etc.
  ↓
Site publicado com polo + nicho + copy + SEO corretos
```

## Adicionar um Nicho Novo (checklist)

1. Adicionar entrada em `NICHO_CONFIG` (nicho_registry.py)
2. Escolher `polo_sugerido` (SOFT/BOLD/CLASSIC/TECH)
3. Adicionar aliases em `ALIASES` (se houver variações)
4. Adicionar sub-nicho overrides em `SUB_NICHO_POLO_OVERRIDES` (se houver)
5. Adicionar lanes em `lanes` (criar 2-4 lanes com paleta/variants/copy próprios)
6. Adicionar `seo_keywords` (3-6 keywords com placeholder {cidade})
7. Definir `CopyDefaults` (tone, voice, cta_primary)
8. Definir `DesignLogic` (radius/spacing multipliers + allow_overlap/skew)
9. Definir `hero_headlines` por polo (SOFT/BOLD/CLASSIC/TECH)
10. Definir `faq` (5 perguntas)
11. Definir `modal_config` (title, cta, fields, submit_action)
12. Se nicho for sub-nicho de outro (ex: nutri+atleta), adicionar override
13. Escrever testes em `tests/test_nicho_config.py` + `test_design_logic.py`

## Onde encontrar cada coisa

| O que | Onde |
|---|---|
| Configuração canônica de nicho | `backend/config/nicho_registry.py` |
| Frameworks de copy (8) | `backend/copywriting/copy_angles.py` |
| Voz por polo (4) | `backend/copywriting/polo_voice.py` |
| SEO templates (56) | `backend/copywriting/seo_templates.py` |
| Hero/Services/Gallery Layout Modes | `backend/services/vite_liquid_components.py` |
| Lanes (38) | `backend/services/vite_visual_lanes.py::_LANES` |
| Polos para system prompts LLM | `backend/agents/polo_prompts.py` |
| Polos no núcleo de render | `backend/services/vite_react_renderer.py` |
| Polos no schema.org JSON-LD | `backend/services/vite_templates.py::_facts_json_ld` |
| Aliases lane (barber-* → barbearia-*) | `backend/services/vite_visual_lanes.py::_LANE_ID_ALIASES` |

## Decisões de Design Importantes

1. **Por que nich_registry e não classes separadas?**
   - Registry é a única estrutura que sobrevive a 13 nichos × 12+ campos
   - Permite lookup O(1) por nome canônico
   - Dataclass frozen garante imutabilidade

2. **Por que 4 polos e não 5 ou 6?**
   - Testado empiricamente que cobre 95%+ dos casos
   - Mais que isso vira "todos os sites são diferentes" (paradoxo da escolha)
   - Menos que isso vira "tudo é igual" (perda de identidade)

3. **Por que DEPRECATED e não remoção?**
   - Código de produção usa registry desde Sprint 12.x
   - Mas imports externos (testes legados, integrações) ainda dependem
   - Marcar DEPRECATED deixa claro a direção sem quebrar o sistema

4. **Por que sub_nicho overrides?**
   - 1 mesmo nicho pode ter públicos muito diferentes (nutri vs nutri+atleta)
   - Override simples: nutri padrão = SOFT, mas com atleta vira BOLD
   - Sem precisar de 2 nichos separados

## Histórico de Etapas (Sprint 12.x)

| Etapa | Foco | Resultado |
|---|---|---|
| 1.3 | Schema.org dinâmico | 4 arquivos migrados, 38 testes, 13 schemas corretos |
| 1.5 | Polo em system prompts | polo_prompts.py criado, 26 testes |
| 2 | CVA Layout Modes | Services + Gallery modes, 33 testes |
| 3 | Lanes dedicados (38) | 22 lanes adicionadas, aliases, 11 testes |
| 4 | Copy + SEO por polo | 3 módulos copywriting, 37 lanes reescritas, 28 testes |
| 5 | Unificação | LEGACY marcado DEPRECATED, registry é fonte única |
