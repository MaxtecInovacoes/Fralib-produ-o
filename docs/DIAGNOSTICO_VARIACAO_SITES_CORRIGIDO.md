# DIAGNÓSTICO VARIACAO SITES - CORRIGIDO
## Problema: Sites saiam todos iguais

---

## 🔴 CAUSA RAIZ IDENTIFICADA

### O Bug:
1. `agente_variacao.py` (Fase 7) gerava `VariationSeed` com `get_variation()`
2. MAS **NÃO SALVAVA** o variation completo no `VariacaoEstrutural`
3. Só passava strings simples (`template_hero=_layout_v`)
4. `DesignerPRD` não tinha campo `variation`
5. `pipeline_prompt_agent.py` não copiava `variation` para o PRD
6. `builder_worker.py` não recebia `variation` para injetar no manifest
7. `vite_react_renderer.py` usava `__counter=0` por padrão → CSS idêntico!

### Evidência:
Dois sites de Academia tinham **CSS idêntico**:
```
site-academia-pump-iron/assets/index-Cr5TWGjm.css  ← IGUAL
site-academia/assets/index-Cr5TWGjm.css            ← IGUAL
```

---

## ✅ CORREÇÕES APLICADAS

### 1. `handoff_types.py` - Adicionado campo `variation` ao `VariacaoEstrutural`

```python
class VariacaoEstrutural(HandoffBase):
    # ... campos existentes ...
    # Sprint 16: variation seed completo
    variation: Dict = Field(default_factory=dict)
```

### 2. `agente_variacao.py` - Salvar variation no retorno

```python
return VariacaoEstrutural(
    # ... outros campos ...
    # Sprint 16: salvar variation seed completo
    variation=_variation.to_dict() if _variation else {},
)
```

### 3. `variation_seed.py` - Adicionar `counter` ao VariationSeed

```python
@dataclass(frozen=True)
class VariationSeed:
    seed: int
    counter: int = 0  # Sprint 16: para o renderer usar
    # ... outros campos ...
```

### 4. `pipeline_prompt_agent.py` - Copiar variation para o PRD

```python
_var_estrutural = object_to_dict(getattr(state, "variacao_estrutural", None)) or {}
_variation = _var_estrutural.get("variation") or {}
return SimpleNamespace(
    # ...
    variation=_variation,  # Sprint 16
)
```

---

## FLUXO CORRIGIDO

```
[Fase 7] agente_variacao.py
    │
    ├─► get_variation(facts, counter=N)
    │       │
    │       └─► VariationSeed(seed, counter=N, hero_layout, motion_style, ...)
    │
    └─► VariacaoEstrutural(
            variation=VariationSeed.to_dict()  ← SALVO AGORA!
        )

[Fase 8] Arquiteto
    └─► prd_arquiteto.variation = state.variacao_estrutural.variation

[Fase 9] builder_worker.py
    └─► manifest["prompt_agent"]["context"]["variation"] = variation

[Fase 9] vite_react_renderer.py
    │
    ├─► facts["variation"]["counter"] → __counter
    │
    └─► _seed_for_html = __counter
            │
            └─► _hero_class = _HERO_CLASSES_POOL[__counter % 10]
            └─► CSS único por site!
```

---

## COMO VERIFICAR

### 1. Gerar 2 sites do mesmo segmento

```bash
# Trigger pipeline para 2 leads do mesmo subnicho
```

### 2. Comparar CSS hashes

```bash
# Os CSS devem ser DIFERENTES
ls -la sites/*/assets/*.css
```

### 3. Comparar manifest

```bash
cat logs/builder_manifests/*.json | grep -A5 '"variation"'
```

Deve mostrar:
```json
{
  "variation": {
    "seed": 12345678,
    "counter": 0,  // ou 1 para o segundo
    "hero_layout": "split",
    "motion_style": "smooth",
    ...
  }
}
```

---

## ARQUIVOS MODIFICADOS

| Arquivo | Modificação |
|---------|-------------|
| `handoff_types.py` | Adicionado campo `variation` |
| `agente_variacao.py` | Salvar `variation.to_dict()` no retorno |
| `variation_seed.py` | Adicionar `counter` ao `VariationSeed` |
| `pipeline_prompt_agent.py` | Copiar `variation` para o PRD |

---

## TESTE DE REGRESSÃO

Para garantir que não quebrou nada:

```bash
pytest tests/ -v -k "variacao or variation"
```

---

## NOTAS

1. **Counter rotation**: O `site_generation_counter.get_counter()` retorna `COUNT(*)` de gerações anteriores. Se for a primeira geração, counter=0; segunda=1, etc.

2. **Fallback LLM**: Quando o subnicho não está em `SUB_NICHO_TEMPLATES`, o agente chama Sonnet. Nesse caso, `variation` fica vazio `{}` e o renderer gera variação padrão.

3. **CSS único**: O `vite_react_renderer.py` usa `__counter` para selecionar classes de hero, H1 size, font, etc. Com counter diferente, o CSS compilado será diferente.
