# MOTOR DE GERAÇÃO - AUDITORIA TÉCNICA

## 🔍 MOTOR ATUAL: OpenUI (PADRÃO)

### Como funciona:

```
┌─────────────────────────────────────────────────────────────┐
│                    OPENUI RENDERER                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Recebe builder_prompt + facts (dados do lead)         │
│     ↓                                                        │
│  2. Monta system prompt com 7 CONTRATOS:                    │
│     ├─ SEO Framework                                        │
│     ├─ Design System                                        │
│     ├─ Motion Contract (12 sistemas de animação)            │
│     ├─ A11y Contract                                       │
│     ├─ Factual Contract                                     │
│     ├─ LGPD personalizado                                   │
│     └─ Deploy Rules                                         │
│     ↓                                                        │
│  3. Chama LLM (Sonnet primário → Opus fallback)            │
│     ↓                                                        │
│  4. Extrai HTML do response                                 │
│     ↓                                                        │
│  5. Aplica 46 PATCHES (Twitter, OG, A11y, SEO, etc)       │
│     ↓                                                        │
│  6. Quality Gate (loop ≤ 3 retries)                         │
│     ↓                                                        │
│  7. HTML FINAL                                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Contratos Injetados (openui_contracts.py):

| # | Contrato | Função |
|---|----------|--------|
| 1 | SEO Framework | h1, keywords, FAQ, schema.org por nicho |
| 2 | Design System | Paleta, tipografia, motion do nicho |
| 3 | Motion Contract | 12 sistemas (parallax, reveal, marquee, magnetic, 3D tilt, counter) |
| 4 | A11y Contract | Skip link, main, contraste AA |
| 5 | Factual Contract | JSON-LD + dados confirmados |
| 6 | LGPD | Banner personalizado por segmento |
| 7 | Deploy Rules | Tailwind CDN, wa.me/tel: |

### 46 Patches Aplicados:

| Categoria | Qtd | O que faz |
|-----------|-----|-----------|
| Twitter Cards | 4 | title, card, description, image |
| Open Graph | 4 | title, description, image, locale |
| Title | 1 | Título correto da aba |
| Acessibilidade | 5 | skip link, LGPD, apple-touch-icon |
| SEO Técnico | 7 | robots, hreflang, theme-color, canonical, schemas |
| Performance | 7 | Preload LCP, srcset, fetchpriority, lazy, WebP |
| Motion Awwwards | 12 | parallax, reveal, marquee, magnetic, 3D tilt, counter, GSAP |
| CSS Moderno | 5 | :has(), color-mix(), @container, subgrid, prefers-reduced-motion |

---

## ⚠️ MOTOR LEGADO: Vite/React

### Status: **PROIBIDO** (mantido para compatibilidade)

O Vite/React era o engine padrão antes do Sprint 12.9. Agora está
bloqueado e só pode rodar via `FRALIB_BUILDER_ENGINE=vite_react` (modo compatibilidade).

### Arquivos Vite (14 arquivos):

```
backend/services/
├── vite_react_renderer.py      # ⚠️ LEGADO
├── vite_config.py              # ⚠️ LEGADO
├── vite_config_helpers.py     # ⚠️ LEGADO
├── vite_facts.py              # ⚠️ LEGADO
├── vite_file_extractor.py     # ⚠️ LEGADO
├── vite_modules.py            # ⚠️ LEGADO
├── vite_renderer_models.py    # ⚠️ LEGADO
├── vite_validator.py          # ⚠️ LEGADO
├── vite_templates.py          # ⚠️ LEGADO
├── vite_prompts.py           # ⚠️ LEGADO
├── vite_build_executor.py     # ⚠️ LEGADO
├── vite_block_registry.py    # ⚠️ LEGADO
├── vite_visual_lanes.py      # ⚠️ LEGADO
└── vite_theme_guard.py       # ⚠️ LEGADO
```

### Testes Vite (6 arquivos):

```
tests/unit/
├── test_vite_config.py           # ❌ ÓRFÃO
├── test_vite_config_helpers.py    # ❌ ÓRFÃO
├── test_vite_facts.py            # ❌ ÓRFÃO
├── test_vite_file_extractor.py   # ❌ ÓRFÃO
├── test_vite_renderer_models.py  # ❌ ÓRFÃO
└── test_vite_validator.py        # ❌ ÓRFÃO
```

### Scripts Vite (2 arquivos):

```
scripts/
├── test_build_only.py        # ❌ ÓRFÃO
└── test_builder_llm_only.py  # ❌ ÓRFÃO
```

---

## 🆕 NOVO: Templates (Sprint 6+)

### Como funciona:

```
┌─────────────────────────────────────────────────────────────┐
│                  TEMPLATE RENDERER                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Recebe lead_id + segmento                              │
│     ↓                                                        │
│  2. generate_variation() → {estetica, theme, motion}       │
│     (determinístico: mesmo input → mesmo output)           │
│     ↓                                                        │
│  3. load_template(estetica) → HTML canônico               │
│     ↓                                                        │
│  4. render_with_variation() → HTML final                  │
│     (placeholders + CSS vars + motion)                      │
│     ↓                                                        │
│  5. HTML FINAL (zero LLM, zero custo)                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Ativar:
```bash
FRALIB_USE_TEMPLATES=1
```

---

## 📊 COMPARATIVO DE MOTORES

| Aspecto | OpenUI | Vite/React | Templates |
|---------|--------|------------| ----------|
| **Status** | ✅ PADRÃO | ⚠️ LEGADO | 🆕 ATIVO |
| **Custo LLM** | ~$0.025/site | ~$0.10/site | $0 |
| **Latência** | 10-30s | 30-60s | <1s |
| **Qualidade** | Alta | Alta | Média-Alta |
| **Manutenção** | Baixa | ALTA (legado) | Baixa |
| **Testes** | 46 patches | 6 unitários órfãos | Verificando |

---

## 🔒 QUALITY GATE (html_quality_gate.py)

### O que valida:

| Verificação | O que bloqueia |
|-------------|----------------|
| Contract | PRD sem seções estruturadas |
| Emoji | HTML com emoji visível |
| Placeholder | Placeholder visual em vez de mídia |
| Mídia mínima | Menos imagens do que o mínimo exigido |
| Endereço | Endereço real não aparece |
| E-mail | E-mail não confirmado |
| Dados falsos | Dados fake inventados |
| Métricas | Métricas não suportadas |
| Claims públicos | Afirmações não verificáveis |
| Motion | Animação faltando quando exigida |
| Hero | Hero sem mídia/CTA/H1 |
| Footer | Footer ausente |

### Loop de Retry:

```
Tentativa 1 (Sonnet) → Falha → 
Tentativa 2 (Sonnet) → Falha →
Tentativa 3 (Opus) → Falha → BLOQUEIA
```

---

## 🎯 SUB-NICHOS MAPEADOS (8 templates)

| Subnicho | Template | Hero |
|----------|----------|------|
| nutricionista_esportiva | organic | hero-fullscreen |
| nutricionista_clinica | editorial | hero-split |
| clinica_estetica | minimal | hero-center |
| barbearia_premium | brutalist | hero-diagonal |
| academia_crossfit | brutalist | hero-fullscreen |
| restaurante_familiar | organic | hero-split |
| advocacia_trabalhista | corporate | hero-split |
| default | corporate | hero-split |

---

## ⚡ MOTION CONTRACT (12 sistemas)

1. `data-parallax="0.1..0.5"` - Movimento vertical ao scroll
2. `data-reveal="up|down|left|right|scale|fade"` - Fade+slide ao entrar viewport
3. `data-marquee="left|right"` - Trilhas infinitas
4. `data-magnetic="0.2..0.5"` - Botões que seguem cursor
5. `data-3d-tilt="10..20"` - Cards 3D ao mover mouse
6. `data-text-scramble` - Efeito de digitação
7. `data-horizontal-scroll` - Scroll horizontal pinned
8. `data-counter="1234"` - Contador animado
9. `data-stagger` - Parent para stagger
10. Group hover effects
11. motion-safe:animate-*
12. GSAP + ScrollTrigger + Lenis (CDN)

---

## 🚨 PROBLEMAS IDENTIFICADOS

### 1. Motor Vite/React LEGADO
- 14 arquivos sem uso no pipeline atual
- 6 testes órfãos
- 2 scripts órfãos
- **Ação**: Avaliar remoção ou arquivamento

### 2. Divergência de UI
- `dashboard.html` legada vs `admin.html` canônico
- **Ação**: Garantir redirecionamento

### 3. Cache Global
- 6 caches sem escopo tenant
- **Ação**: Corrigir para multi-tenant

### 4. 74 "agentes"? MITO!
- São 11 módulos reais
- **Ação**: Documentar melhor

---

## ✅ RECOMENDAÇÕES

### PRIORIDADE ALTA:
1. Manter OpenUI como padrão (funcionando)
2. Manter Quality Gate (bloqueia publish ruim)
3. Manter 46 patches aplicados
4. Avaliar remoção de arquivos Vite órfãos

### PRIORIDADE MÉDIA:
1. Ativar Templates para custo zero
2. Corrigir caches globais
3. Consolidar UI (admin vs dashboard)

### PRIORIDADE BAIXA:
1. Limpar testes órfãos
2. Documentar agentes melhor
