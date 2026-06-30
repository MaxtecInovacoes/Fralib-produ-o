# DIAGNÓSTICO: Por que todos os sites saem iguais?

## RESUMO DO PROBLEMA

O usuário reportou: **"todos os sites saem iguais"**

---

## SISTEMA DE VARIAÇÃO EXISTENTE

### 1. **VariationSeed** (`backend/services/variation_seed.py`)

Sistema de variação determinística com **4 eixos**:

```python
VariationSeed(
    seed: int,                    # Hash do nome do negócio
    hero_layout: str,              # split | center | asymmetric | fullbleed | video
    motion_style: str,            # sharp | smooth | minimal
    copy_voice: str,              # aggressive | friendly | authoritative
    color_emphasis: str,          # primary_dominant | secondary_dominant | balanced
    section_order_style: str,      # credibility_first | visual_first | offer_first | story_first
    proof_style: str,             # score_wall | quote_spotlight | card_marquee | editorial_case
    surface_style: str,           # glass | solid | outline | soft_tint
    visual_lane: str,             # lane_a | lane_b | ... | lane_h
)
```

**Total de combinações teóricas:** 5 × 3 × 3 × 3 × 4 × 4 × 4 × 8 = **138.240 variações**

### 2. **Studio Archetypes** (`backend/services/studio_archetypes.json`)

6 archetypes visuais:

| Archetype | Segmentos | Descrição Visual |
|-----------|-----------|------------------|
| BOLD_ENERGY | academia, fitness, crossfit | Alto impacto, cores vibrantes |
| WARM_LOCAL | barbearia, salao_beleza | Tons quentes, comunidade |
| ZEN_PURE | clinica, estetica, nutri | Minimalista, limpo |
| LUXURY_ELITE | restaurante, pizzaria | Premium, elegante |
| MODERN_TECH | energia solar, mecanica | Tech, moderno |
| PROFESSIONAL_TRUST | advocacia, contabilidade | Profissional, confiavel |

Cada archetype tem **3 layout_variations**, **3 motion_variations**, **3 copy_variations**.

---

## FLUXO DE VARIAÇÃO

```
[FASE 7] Agente Variação
    │
    ├─► generate_variation() [templates/_system/variation.py]
    │       │
    │       └─►usa counter rotation para evitar repetição
    │
    └─► get_variation() [variation_seed.py]
            │
            └─►usa seed baseado no nome do negócio

    ↓

[FASE 9] Builder (Vite/React)
    │
    ├─► variation_seed.inject() → manifest
    │
    └─► render_vite_react_site()
            │
            ├─► _get_archetype_for_segment()
            │
            ├─► _with_cinematic_variation_defaults()
            │       │
            │       └─►usa variation_seed para pegar variações
            │
            └─► _pick_hero_layout(archetype, seed)
            └─► _select_copy_variation(archetype, seed)
```

---

## POSSÍVEIS CAUSAS DO PROBLEMA

### CAUSA 1: Variation não está sendo gerado corretamente

Verificar se `gerar_variacao()` (Fase 7) está rodando:

```python
# backend/endpoints/pipeline_phase_helpers.py:208
if state.variacao_estrutural is None:
    state.variacao_estrutural = gerar_variacao(...)  # Pode estar falhando silenciosamente
```

### CAUSA 2: Variation não está sendo injetado no Builder

Verificar se o manifest recebe a variação:

```python
# backend/services/builder_worker.py:278-288
manifest["prompt_agent"]["context"]["variation"] = _var_payload
```

### CAUSA 3: Vite/React não está usando a variação

O `render_vite_react_site` pode estar ignorando a variação:

```python
# backend/services/vite_react_renderer.py:4916-4921
if get_variation is not None:
    variation = get_variation(safe_facts)
    safe_facts = apply_variation_to_facts(safe_facts, variation)
```

### CAUSA 4: Counter rotation não está funcionando

O counter rotation é o mecanismo para evitar sites iguais para o mesmo negócio:

```python
# variation_seed.py:258-260
counter_offset = (int(counter) * _GOLDEN_RATIO_PRIME) & 0xFFFFFFFFFFFFFFFF
seed = (base_seed ^ counter_offset) & 0xFFFFFFFFFFFFFFFF
```

Se o `counter` for sempre 0, todos os sites do mesmo negócio serão idênticos.

---

## COMO VERIFICAR

### 1. Verificar logs do Pipeline

```bash
# Procurar logs de variação
grep -r "variacao" logs/ | grep -i "gerar\|variation"

# Verificar se agente_variacao rodou
grep "agente_variacao" logs/
```

### 2. Verificar manifest do Builder

```bash
# Localizar manifests
ls -la logs/builder_manifests/

# Verificar conteúdo de um manifest
cat logs/builder_manifests/<manifest_id>.json | grep -A5 '"variation"'
```

### 3. Verificar variation no HTML gerado

```bash
# Buscar marcadores de variação no HTML
grep -r "hero_layout\|motion_style\|visual_lane" dist/
```

---

## SOLUÇÕES POSSÍVEIS

### SOLUÇÃO 1: Garantir que variation é gerado

Verificar se a Fase 7 está completando corretamente:

```python
# backend/endpoints/pipeline_phase_helpers.py
if not state.variacao_estrutural:
    logger.error("Variação estrutural não foi gerada!")
```

### SOLUÇÃO 2: Garantir que variation é injetado

Verificar se o manifest contém a variação:

```python
# No builder_worker.py, adicionar log:
logger.info(f"[builder] variation injetado: {manifest['prompt_agent']['context'].get('variation')}")
```

### SOLUÇÃO 3: Ativar counter rotation

O counter rotation é controlado pelo `counter` no facts:

```python
# variation_seed.py - counter deve mudar a cada geração
counter = facts.get("__counter") or 0
```

### SOLUÇÃO 4: Usar variação manual

Forçar uma variação específica:

```python
facts["variation"] = {
    "hero_layout": "video",
    "motion_style": "sharp",
    "copy_voice": "aggressive",
    "color_emphasis": "primary_dominant"
}
```

---

## PRÓXIMOS PASSOS

1. **Verificar logs** - confirmar se variação está sendo gerada
2. **Verificar manifest** - confirmar se variação está sendo injetada
3. **Verificar HTML** - confirmar se variação está sendo aplicada
4. **Testar manualmente** - gerar 2 sites do mesmo segmento e comparar

---

## ARQUIVOS CHAVE

| Arquivo | Função |
|---------|--------|
| `variation_seed.py` | Geração determinística de variação |
| `studio_archetypes.json` | 6 archetypes visuais |
| `agente_variacao.py` | Agente que gera variação (Fase 7) |
| `archetype_resolver.py` | Resolve archetype por segmento |
| `vite_react_renderer.py` | Usa variação no Vite/React |
| `builder_worker.py` | Injeta variação no manifest |
