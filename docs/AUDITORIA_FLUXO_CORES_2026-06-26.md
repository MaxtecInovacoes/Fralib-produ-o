# AUDITORIA: Fluxo de Dados e Visuais Exclusivos

**Data:** 2026-06-26  
**Escopo:** Formulário → agente_nicho → designer_prd/arquiteto_mestre → vite_react_renderer → Site final

---

## MAPA COMPLETO DO FLUXO

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FORMULÁRIO (Frontend)                                                       │
│ - Campo: briefing (texto livre)                                            │
│ - Exemplo: "Site para academia feminina, cores roxo e branco"             │
└────────────────────────────┬────────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ backend/core/database.py (leads.briefing_json)                              │
│ - Armazena briefing como JSON no banco                                     │
│ - Campo: user_id (multi-tenant)                                            │
└────────────────────────────┬────────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ backend/agents/agente_nicho.py                                             │
│ - parse_colors_from_briefing_text(): Extrai cores do texto livre          │
│ - NOMINAL_COLOR_MAP: 40+ cores nominais (roxo=#800080, branco=#FFFFFF)   │
│ - Output: NichoBriefing.paleta_cores = {"primary": "#800080", ...}       │
│ ⚠️ Usa: dados_lead.get("briefing", "")                                   │
└────────────────────────────┬────────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ backend/agents/handoff_types.py                                           │
│ - NichoBriefing.paleta_cores: Dict[str, str] = Field(default_factory=dict)│
└────────────────────────────┬────────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ backend/agents/arquiteto_mestre.py ⚠️ PROBLEMA CRÍTICO                     │
│ - NÃO USA paleta_cores do NichoBriefing                                    │
│ - Gera color_palette a partir de design_dna.tokens (determinístico)        │
│ - Ignora completamente o briefing de cores do usuário                       │
└────────────────────────────┬────────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ backend/agents/designer_prd.py                                             │
│ - DesignerPRD.paleta_cores: existe mas NUNCA é populado                   │
│ - gerar_prd(): não recebe nicho_briefing como parâmetro                   │
│ - Campo fica como {} vazio sempre                                          │
└────────────────────────────┬────────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ backend/services/builder_worker.py                                         │
│ - Tenta injetar paleta_cores no manifest                                   │
│ - Procura em: prd_or_facts.paleta_cores, nicho_briefing.paleta_cores     │
│ - Log: "[builder_worker] paleta_cores injetado" se encontrar              │
└────────────────────────────┬────────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ backend/services/vite_react_renderer.py                                    │
│ - _generate_cinematic_studio_files(): Tem lógica para usar paleta_cores   │
│ - Prioridade:                                                            │
│   1. color_palette do DesignerPRD (LLM generated)                          │
│   2. paleta_cores do NichoBriefing (extraído do briefing livre)            │
│   3. design_dna.tokens (fallback determinístico)                           │
│   4. archetype fixo (último fallback)                                      │
└────────────────────────────┬────────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ backend/services/studio_archetypes.json                                    │
│ - 6 archetypes fixos: BOLD_ENERGY, WARM_LOCAL, ZEN_PURE, LUXURY_ELITE,    │
│   MODERN_TECH, PROFESSIONAL_TRUST                                         │
│ - Seleção por segmento (determinística)                                    │
│ - Variações: 3 layouts × 3 motions × 3 copy voices = 27 combinações      │
└────────────────────────────┬────────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ SITE FINAL (Vite React + Tailwind)                                         │
│ - Archetype palette aplicada nos CSS                                        │
│ - Cores do usuário podem ou não ser aplicadas (depende da priorização)     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## PROBLEMAS CRÍTICOS IDENTIFICADOS

### 1. PALETA_CORES IGNORADA PELO ARQUITETO MESTRE
**Severidade:** 🔴 CRÍTICO  
**Arquivo:** `backend/agents/arquiteto_mestre.py`  
**Linha:** ~343-363

**Problema:** O `arquiteto_mestre.py` recebe `NichoBriefing` com `paleta_cores` extraída do briefing livre, mas **NÃO USA** essa paleta. Ele gera `color_palette` a partir de `design_dna.tokens`.

```python
# Linha 353-363 (arquiteto_mestre.py)
dados["color_palette"] = {
    "primary": _tokens.get("--fg", ""),  # ← Ignora paleta_cores do usuário
    "secondary": _tokens.get("--surface", ""),
    ...
}
```

**Impacto:** Se o usuário pede "cores roxo e branco", o site pode sair com as cores do archetype (ex: verde para academia), não as solicitadas.

**Recomendação:** Modificar `build_skill_prd()` ou `build_skill_fast_prd()` para injetar `paleta_cores` do nicho_briefing antes de gerar o PRD.

---

### 2. DESIGNER_PRD.PALETA_CORES NUNCA É POPULADO
**Severidade:** 🔴 CRÍTICO  
**Arquivo:** `backend/agents/designer_prd.py`

**Problema:** O campo `paleta_cores` existe no modelo `DesignerPRD` mas nunca é passado no construtor ou gerado pelo LLM.

```python
# Linha 263 (designer_prd.py)
paleta_cores: Dict[str, str] = Field(default_factory=dict)  # ← Sempre vazio {}

# gerar_prd() não recebe nicho_briefing como parâmetro
def gerar_prd(briefing_theo, dados_hunter, cidade, segmento):
    # paleta_cores nunca é populado
```

**Impacto:** A tentativa do `builder_worker.py` de injetar `paleta_cores` falha silenciosamente.

**Recomendação:** Adicionar parâmetro `nicho_briefing: NichoBriefing` ao `gerar_prd()` e injetar `paleta_cores` no output.

---

### 3. CORES NÃO INJETADAS NO PROMPT DO VITE PROMPTS
**Severidade:** 🟡 MÉDIO  
**Arquivo:** `backend/services/vite_prompts.py`

**Problema:** `_build_lead_briefing_block()` não inclui `paleta_cores` no prompt final.

```python
# Linha 323-441 (vite_prompts.py)
def _build_lead_briefing_block(facts):
    # ...
    # NÃO inclui:
    # - paleta_cores
    # - Cores solicitadas pelo usuário
```

**Impacto:** Mesmo que as cores cheguem no `facts`, o LLM Vite/React não é instruído a usá-las.

**Recomendação:** Adicionar bloco de cores no `_build_lead_briefing_block()`:
```python
# Adicionar após services_block
colors_block = ""
if facts.get("paleta_cores"):
    _c = facts["paleta_cores"]
    colors_block = f"""
CORES SOLICITADAS PELO USUÁRIO (OBRIGATÓRIO USAR):
- Primary: {_c.get('primary', '')}
- Secondary: {_c.get('secondary', '')}
- Accent: {_c.get('accent', '')}
"""
```

---

## PROBLEMAS SECUNDÁRIOS

### 4. INCONSISTÊNCIA DE NOMES DE CHAVES
**Severidade:** 🟡 MÉDIO  
**Arquivos:** Múltiplos

**Problema:** O sistema usa três formas diferentes para a paleta de cores:
- `paleta_cores` (NichoBriefing, BuilderWorker)
- `color_palette` (DesignerPRD, ArquitetoMestre)
- `primary`/`secondary`/`accent` (studio_archetypes)

**Impacto:** Confusão na depuração e potencial falha de fallback.

**Recomendação:** Padronizar para `color_palette` em todo o fluxo.

---

### 5. FALLBACK PARA ARCHETYPE PODE GERAR SITES IGUAIS
**Severidade:** 🟢 BAIXO  
**Arquivo:** `backend/services/studio_archetypes.json`

**Problema:** Quando `paleta_cores` não existe, o sistema usa archetype fixo. Dois tenants do mesmo nicho (ex: duas academias) podem gerar sites visualmente idênticos.

**Recomendação:** O counter rotation já implementado em `_generate_cinematic_studio_files` é bom, mas poderia usar mais variação.

---

## FLUXO IDEAL (CORRIGIDO)

```
Formulário: "cores roxo e branco"
    │
    ▼
agente_nicho.py: parse_colors_from_briefing_text("cores roxo e branco")
    → {"primary": "#800080", "secondary": "#FFFFFF"}
    │
    ▼
NichoBriefing.paleta_cores = {"primary": "#800080", "secondary": "#FFFFFF"}
    │
    ├──────────────────┬──────────────────┐
    ▼                  ▼                  ▼
arquiteto_mestre    builder_worker    vite_prompts
    │                  │                  │
    ▼                  ▼                  ▼
DesignerPRD          manifest          SYSTEM PROMPT
.color_palette =      context           com bloco de
  {"primary":          {                 cores:
   "#800080",          "paleta_cores":    "CORES: primary
   "secondary":         {...},            #800080, secondary
   "#FFFFFF"}          ...                #FFFFFF"
  (sobrescreve        │                  │
  design_dna)          ▼                  ▼
    │              vite_react_renderer.py
    │                  │
    └──────────────────┼──────────────────┘
                       ▼
                  SITE COM CORES
                  ROXO E BRANCO ✅
```

---

## TESTES EXISTENTES

O projeto já tem testes para a extração de cores:

- `tests/integration/test_color_pipeline_integration.py`
  - ✅ `test_parse_colors_comprehensive`
  - ✅ `test_nominal_color_map_coverage`
  - ✅ `test_hex_normalization`

**Falta:** Teste de ponta-a-ponta que verifique se as cores chegam ao site final.

---

## RECOMENDAÇÕES DE CORREÇÃO (PRIORIDADE)

### 🔴 PRIORIDADE 1: Corrigir arquiteto_mestre.py
Modificar `build_skill_prd()` para injetar `paleta_cores` do NichoBriefing:

```python
# Em build_skill_prd() ou build_skill_fast_prd():
if nicho_briefing and nicho_briefing.paleta_cores:
    dados["color_palette"] = nicho_briefing.paleta_cores  # ← SOBRESCREVE design_dna
```

### 🔴 PRIORIDADE 2: Corrigir designer_prd.py
Adicionar parâmetro `nicho_briefing` ao `gerar_prd()`:

```python
def gerar_prd(briefing_theo, dados_hunter, cidade, segmento, nicho_briefing=None):
    # ...
    if nicho_briefing and nicho_briefing.paleta_cores:
        output.color_palette = ColorPalette(**nicho_briefing.paleta_cores)
```

### 🟡 PRIORIDADE 3: Adicionar cores no vite_prompts.py
```python
def _build_lead_briefing_block(facts):
    # ... código existente ...
    
    # Sprint 14.x: Cores do briefing do usuário
    _paleta = facts.get("paleta_cores") or facts.get("color_palette") or {}
    if _paleta and _paleta.get("primary"):
        colors_block = f"""
CORES SOLICITADAS PELO USUÁRIO (APLICAR OBRIGATORIAMENTE):
Primary: {_paleta.get('primary')}
Secondary: {_paleta.get('secondary', '')}
Accent: {_paleta.get('accent', '')}
"""
    else:
        colors_block = ""
    
    return f"""...
{colors_block}
...
"""
```

### 🟢 PRIORIDADE 4: Adicionar teste E2E
```python
def test_colors_from_briefing_reaches_site():
    """Verifica que 'cores roxo e branco' resulta em site com roxo."""
    # 1. Gerar site com briefing "cores roxo e branco"
    # 2. Verificar CSS do site final
    # 3. Assert: primary color contém #800080
```

---

## ARQUIVOS ANALISADOS

| Arquivo | Responsabilidade | Status |
|---------|------------------|--------|
| `backend/agents/agente_nicho.py` | Extrai cores do briefing | ✅ OK |
| `backend/agents/handoff_types.py` | Modelo NichoBriefing | ✅ OK |
| `backend/agents/arquiteto_mestre.py` | Gera PRD | 🔴 IGNORA paleta_cores |
| `backend/agents/designer_prd.py` | Modelo DesignerPRD | 🔴 paleta_cores nunca usado |
| `backend/services/builder_worker.py` | Injeta paleta no manifest | ✅ OK (tenta) |
| `backend/services/vite_prompts.py` | System prompt Vite | 🟡 Não inclui cores |
| `backend/services/vite_react_renderer.py` | Gera site Vite | ✅ OK (lógica existe) |
| `backend/services/studio_archetypes.json` | 6 archetypes fixos | ✅ OK (fallback) |

---

## CONCLUSÃO

**O fluxo de cores está PARCIALMENTE implementado:**

1. ✅ **Extração funciona:** `parse_colors_from_briefing_text()` extrai cores corretamente
2. ✅ **Modelo existe:** `NichoBriefing.paleta_cores` está definido
3. ✅ **Renderer suporta:** `vite_react_renderer.py` tem lógica para usar cores
4. 🔴 **Arquiteto ignora:** `arquiteto_mestre.py` não usa `paleta_cores`
5. 🔴 **DesignerPRD vazio:** `paleta_cores` nunca é populado
6. 🟡 **Prompt incompleto:** `vite_prompts.py` não instrui o LLM a usar cores

**Resultado:** O sistema pode gerar sites com cores solicitadas pelo usuário **APENAS** se o `vite_react_renderer.py` encontrar `paleta_cores` diretamente no `facts` (o que pode acontecer se o `builder_worker` injetar corretamente do `nicho_briefing`).

---

*Gerado automaticamente pela Auditoria de Fluxo de Dados e Visuais Exclusivos - 2026-06-26*
