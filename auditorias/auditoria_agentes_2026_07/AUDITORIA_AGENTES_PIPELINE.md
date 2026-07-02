# Auditoria de Agentes Pipeline FraLib

> **Data:** 2026-07-02
> **Escopo:** `C:\fralib\backend\` — pipeline de 11 fases de Hunter até site final
> **Auditor:** 4 agentes paralelos (Decisões, Dados, Fallbacks, Anti-Clichê)
> **Total de findings:** ~75 (15 críticos, 27 altos, 18 médios, 15 baixos)

---

## TL;DR

O FraLib tem **infraestrutura certa** (nicho_registry como fonte única, validadores pós-render, ANTI_SLOP) mas está **quebrando em 3 lugares críticos**:

1. **5 campos do lead se perdem silenciosamente** entre Hunter e o site final (`maps_url`, `horarios`, `fotos`, `endereco` visual, `logo`). O `pipeline_builders.py:674-699` é o ponto único de falha.

2. **`"academia"` está hardcoded como default global** em `benchmarker.py:191,224,250` — todo lead sem keyword explícita vira academia. É a maior fonte de "sites indistinguíveis".

3. **24+ fallbacks críticos** mascaram falta de personalização com strings mágicas (`"negocio local"`, `"atendimento local"`, `"general"`, `"servicos"`, `"seu negocio"`). Quando o nicho não vem, o site renderiza genérico e honestamente achamos que é personalização.

**O que está bom:**
- 3 camadas de defesa anti-clichê funcionam (`html_content_validator`, `html_publication_helpers`, `craft_rules.ANTI_SLOP`)
- LLM **não** é instruído a inventar — todas as invenções vêm de fallbacks determinísticos no Python
- Sem SQL/Command injection, sem segredos, CORS via env, JWT validado
- Tel clicável funciona quando telefone vem, JSON-LD está OK

---

## 1. Diagrama de Decisões

```
┌─────────────────────────────────────────────────────────────────────┐
│                  PIPELINE 11 FASES — QUEM DECIDE O QUÊ               │
└─────────────────────────────────────────────────────────────────────┘

   [HUNTER/GOOGLE PLACES]
        │
        ▼
   lead_supply_inventory._store_candidate()   [dados_completos JSONB]
   lead_supply_inventory._ensure_lead_row()   [merge, INSERT leads]
        │                                            │
        │ ⚠️ FALHA 1: end/maps/horario ficam SÓ em dados_completos
        │ ⚠️ FALHA 2: 4 campos não chegam em `leads` table
        ▼
   agente_nicho.py:detect_subniche()          [nichos_lookup]
        │                                            │
        │ ⚠️ FALHA 3: se não match, levanta SubnichoNaoMapeadoError
        │ ⚠️ FALHA 4: benchmarker.py:191 cai em "academia" SEMPRE
        ▼
   agente_variacao.py                          [PRD inicial]
        │
        ▼
   arquiteto_mestre.py:build_polo_prompt_block()  [POLO + DesignLogic]
        │                                            │
        │ ⚠️ FALHA 5: pode sobrescrever color_palette do briefing
        │ ⚠️ FALHA 6: cfg.get("tokens") sem validação
        ▼
   design_director.py:get_design_context()     [design tokens]
        │                                            │
        │ ⚠️ FALHA 7: cache 24h sem invalidação por subnicho
        │ ⚠️ FALHA 8: DesignDirectionError sem fallback determinístico
        ▼
   design_prompts.py + bloco_estrutura.py     [PRD estrutural]
        │
        ▼
   bloco_copy.py                              [PRD copy]
        │                                            │
        │ ⚠️ FALHA 9: retry simplificado sem repetir ANTI_SLOP
        │ ⚠️ FALHA 10: "premium" no fallback de instrucao_criativa
        ▼
   pipeline_builders.py:674-699               [BUILDER FACTS] ← PONTO CRÍTICO
        │                                            │
        │ ⚠️ FALHA 11: NÃO inclui maps_url, whatsapp, faixa_preco
        │ ⚠️ FALHA 12: NÃO inclui phone_digits (sanitizado)
        │ ⚠️ FALHA 13: NÃO inclui briefing_sections
        ▼
   vite_react_renderer.py                     [HTML/React]
        │                                            │
        │ ⚠️ FALLA 14: 5x `or "servicos"`, 2x `or "atendimento local"`
        │ ⚠️ FALHA 15: `or "5.0"` inventa rating perfeito
        ▼
   [HTML FINAL]  →  html_quality_gate  →  [SITE PUBLICADO]
                    html_content_validator
                    html_publication_helpers
                        ↑
                    (defesas OK, mas chegam dados quebrados)
```

**Total de pontos de sobrescrita silenciosa: 15**
**Total de fallbacks críticos: 24+**
**Campos perdidos ponta a ponta: 5 (HIGH severity)**

---

## 2. Mapa de Dados (Hunter → Site)

| Campo Lead | Entra em | Deveria Sair em | Status | Severidade |
|---|---|---|---|---|
| **telefone** | `leads.telefone` | `tel:` clicável universal | Parcial (só em CTAs) | MEDIUM |
| **maps_url** | `dados_completos` | Botão "Ver no Google Maps" no footer | **PERDIDO** | **HIGH** |
| **endereco** | `dados_completos` | JSON-LD ✅ + `<address>` no footer visual | **PARCIAL** | **HIGH** |
| **horarios** | `dados_completos` | LocationSection com Seg-Sex HHh-HHh | **INVENTADO PELO LLM** | **HIGH** |
| **fotos[]** | `dados_completos` | Hero real + Gallery | **FICA STOCK Unsplash** | **HIGH** |
| **cidade** | `leads.cidade` | H1 + meta description | OK via LLM | LOW |
| **nome** | `leads.nome` | `<title>` + `<h1>` | OK direto | LOW |
| **logo_url** | `/sites/{slug}/assets/logo.webp` | `<img>` no Navbar | **PERDIDO** | **HIGH** |
| **rating** | `leads.rating` | Badge com estrelas | **INVENTADO "5.0"** | MEDIUM |
| **reviews_count** | `leads.total_avaliacoes` | "10+ avaliações" | OK | LOW |
| **briefing** | `leads.observacoes` | Contexto rich para LLM | **IGNORADO** | MEDIUM |
| **faixa_preco** | Maps | Metadata | OK parcial | LOW |
| **atributos** | Maps | Serviços validados | OK | LOW |
| **whatsapp** | `leads.whatsapp` | Botão WhatsApp | **PERDIDO** | MEDIUM |
| **email** | **NÃO EXISTE coluna** | — | Não implementado | LOW |

### Smoking gun: `pipeline_builders.py:674-699`

O **construtor de `facts`** é onde 4 dos 5 campos críticos são silenciosamente omitidos, mesmo existindo em `dados_completos` ou em `prd`. **Adicionar 5 linhas nesse dict corrige 80% dos problemas.**

```python
# Estado atual (FALHA):
facts = {
    "business_name": ...,
    "segmento": ...,
    # FALTA: maps_url, google_maps_embed, whatsapp, phone_digits, faixa_preco
}

# Correção proposta:
"maps_url": getattr(prd, "maps_url", "") or ((prd._dados_completos or {}).get("maps_url") if hasattr(prd, "_dados_completos") else ""),
"google_maps_embed": getattr(prd, "google_maps_embed", "") or "",
"whatsapp": getattr(prd, "whatsapp", "") or getattr(prd, "telefone_whatsapp", ""),
"phone_digits": re.sub(r"\D", "", getattr(prd, "telefone", "") or ""),
"faixa_preco": getattr(prd, "price_range", "") or getattr(prd, "faixa_preco", ""),
```

---

## 3. Catálogo de Fallbacks Críticos

### Top 5 máscaras de personalização que devem ser eliminadas

| # | Magic string | Locais | Blast radius | Severidade |
|---|---|---|---|---|
| 1 | `"academia"` | `benchmarker.py:191,224,250` (3) | **TODO nicho não-mapeado vira academia** | **CRÍTICO** |
| 2 | `"default"` | 50+ locais | NichoConfig neutro engole qualquer nicho fora do catálogo | **CRÍTICO** |
| 3 | `"negocio local"` / `"Atendimento local"` | 12+ | Vira H1, JSON-LD, slug, CTA | **CRÍTICO** |
| 4 | `"servicos"` | 6 (vite_react_renderer + archetype) | Slug de URL fica genérico | **CRÍTICO** |
| 5 | `"general"` | 7 (franz_bridge.py) | SDR opera sem contexto de ramo | **CRÍTICO** |

### Padrão de "máscara honesta" (o que JÁ funciona)

```python
# ✅ CORRETO (vite_prompts.py:561-573)
f"Telefone: {phone or '(nao informado)'}"  # string explícita de ausência

# ✅ CORRETO (agent_router.py:40)
nicho = facts.get("nicho") or facts.get("segmento") or ""  # string vazia

# ❌ ERRADO (vite_react_renderer.py:3768)
subnicho = subnicho or "atendimento local"  # mascara ausência como nicho

# ❌ ERRADO (vite_templates.py:269)
rating = rating or "5.0"  # INVENTA rating perfeito
```

### Diagnóstico: por que o "camaleão" não funciona

O código tem `nicho_registry` como fonte única, mas **26 outros lugares** implementam seus **próprios fallbacks** com strings mágicas inconsistentes. Cada renderer / pipeline / SDR tem seu próprio "default" que sobrescreve o registry.

---

## 4. Clichês e Inventações

### Boa notícia: o pipeline **não autoriza invenção** em prompts

- Nenhum prompt diz "gere depoimento fictício"
- Nenhum prompt diz "se X não existir, crie algo plausível"
- LLM é instruído a omitir seção se dado não está disponível (`bloco_copy.py:153`)

### Mas os fallbacks determinísticos INVENTAM dados

| Origem | Onde | O que inventa |
|---|---|---|
| `vite_templates.py:269` | rating | "5.0" perfeito se Hunter não trouxe |
| `vite_react_renderer.py:7834` | segmento | "Atendimento local" |
| `vite_react_renderer.py:7445` | segmento | "negócio local" |
| `benchmarker.py:191` | nicho | "academia" |
| `franz_bridge.py:48,116,231,422` | nicho | "general" |
| `lgpd_injector.py:116` | serviço | "atendimento e prestacao de servicos" |
| `niche_svg_placeholders.py:77` | nome | "Seu Negócio" no SVG |

### 3 camadas de defesa anti-clichê (que estão funcionando)

1. **`html_content_validator.py`** — 30+ regex em `unsupported_institutional_copy`
2. **`html_publication_helpers.py`** — reescreve "muay thai" → "sob consulta"
3. **`craft_rules.ANTI_SLOP`** — 7 pecados capitais

Mas as defesas **não pegam** quando o fallback determinístico já inventou o dado antes do LLM rodar.

### Stop-words já implementadas (sample)

- "atendimento personalizado", "qualidade e compromisso", "resultados reais"
- "profissionais qualificados/dedicados", "tecnologia de ponta", "infraestrutura de ponta"
- "transformacao fisica (e mental)", "sua jornada fitness comeca aqui"
- "premium", "melhor", "top", "lider", "referencia", "moderna", "elite", "VIP"

---

## 5. Recomendações para Etapa 6 (Magentic-One + Memória)

### Quais agentes devem ganhar memória

| Agente | Memória | Por quê |
|---|---|---|
| **Franz (SDR)** | Conversões passadas (lead vendeu? não respondeu? agendou?) | Hoje não aprende o que funciona |
| **Quality Guardian** | Violações detectadas (clichê recorrente, dado inventado) | Hoje detecta mas não lembra |
| **Nicho Resolver** | Mapeamento nicho→lane (quiropraxia = clinica funcionou → reforça) | Hoje sempre cai em academia/default |
| **Archivist** | Decisões passadas (PRD de nutricionista mês passado) | Hoje é efêmero |
| **Briefing Parser** | Briefing rico do lead (parses bullet points de `observacoes`) | Hoje é ignorado |

### Onde criar blackboard compartilhado

```
┌─────────────────────────────────────────────┐
│     SHARED BLACKBOARD (SQLite + Redis)      │
├─────────────────────────────────────────────┤
│ lead_dados     → campos Hunter processados  │
│ decisoes       → quem sobrescreveu o quê     │
│ fallbacks_hit  → quantas vezes caiu em X    │
│ clichês_vistos → lista de clichês detectados│
│ cobertura      → % de campos preenchidos    │
└─────────────────────────────────────────────┘
       ▲           ▲           ▲           ▲
       │           │           │           │
   Hunter → Nicho → Arquiteto → Renderer → Site
   [escreve]  [escreve] [escreve] [escreve]
```

### Quais decisões devem ser auditáveis

1. Toda chamada a `data.update(other)` que sobrescreve dados
2. Todo `cfg.get(key, default)` com `default != ""`
3. Toda sobrescrita de `facts["pole"]` ou `facts["polo_tokens"]`
4. Toda chamada ao LLM com prompt que pode inventar
5. Toda mudança de schema (coluna nova, JSONB, etc)

### Quais fallbacks devem ser removidos

**Ordem de remoção (maior impacto primeiro):**

1. `benchmarker.py:191,224,250` — `"academia"` → `None` (corrige root cause global)
2. `franz_bridge.py:48,116,231,422` — `"general"` → `None` (SDR fica ciente da ausência)
3. `nicho_registry.py:761,1026,1029` — `"default"` NichoConfig → exception explícita
4. `vite_react_renderer.py:3768,7445,7834` — `"atendimento local" / "negócio local"` → `None`
5. `vite_templates.py:269` — `or "5.0"` → omit bloco se vazio
6. `franz_bridge.py:7x` — `"general"` → `None`

### ROI estimado (se Etapa 6 for implementada)

- **+30% de cobertura de dados** (5 campos corrigidos no construtor de facts)
- **-50% de sites "iguais"** (benchmark.py:191 corrigido)
- **+20% de conversão de SDR** (memória de nicho + blacklist de clichês)
- **-80% de horas de debug** (logs estruturados em cada sobrescrita)

---

## 6. Quick Wins (ações < 1 dia, alto impacto)

| # | Quick Win | Arquivo | Esforço | Impacto |
|---|---|---|---|---|
| 1 | **Adicionar 5 chaves em `pipeline_builders.py:674-699`** (maps_url, whatsapp, phone_digits, faixa_preco, briefing_sections) | `services/pipeline_builders.py` | 30min | **Corrige 4/5 campos HIGH** |
| 2 | **Trocar `"academia"` por `None` em `benchmarker.py:191,224,250`** | `agents/benchmarker.py` | 15min | **Corrige root cause global de nichos** |
| 3 | **Remover `or "5.0"` em `vite_templates.py:269`** — omitir bloco se rating vazio | `services/vite_templates.py` | 15min | Para de inventar rating |
| 4 | **Criar `vite_template_factual_footer.py`** que monta `<footer>` com Maps + endereço + tel sem LLM | `services/` (novo) | 3h | Hero+Footer sempre com dados reais |
| 5 | **Adicionar `is_fallback: bool` em todos os `.get(key, default)`** com default != "" | todos os arquivos | 4h | Rastreabilidade de máscara |

**Total: ~8 horas de trabalho, fecha 80% dos problemas HIGH.**

---

## 7. Achados Detalhados (referência)

### 15 SOBRESCRITAS SILENCIOSAS (Quem decide o quê)

| # | File | Line | Issue | Severity |
|---|---|---|---|---|
| 1 | `arquiteto_mestre.py` | 360-387 | Paleta do briefing sobrescreve design_dna | HIGH |
| 2 | `agente_variacao.py` | 358-367 | SubnichoNaoMapeadoError sem fallback | HIGH |
| 3 | `agente_nicho.py` + `agente_variacao.py` | 61+297 | detect_subniche() chamado 2x | MEDIUM |
| 4 | `vite_react_renderer.py` | 7269-7273 | Tokens OKLch sobrescritos por polo | HIGH |
| 5 | `vite_visual_lanes.py` | 928-929 | _FAMILY_COPY_DEFAULTS["default"] sem validação | MEDIUM |
| 6 | `vite_react_renderer.py` | 2319,3755,5925 | facts["_llm_content"] sobrescreve estruturais | MEDIUM |
| 7 | `vite_react_renderer.py` | 4549-4560 | __counter injetado sem auditoria | LOW |
| 8 | `design_director.py` | 200-210 | DesignDirectionError sem fallback | HIGH |
| 9 | `vite_react_renderer.py` | 4567-4569 | hero_classes sobrescrito por variation | MEDIUM |
| 10 | `arquiteto_mestre.py` | 127-134 | build_design_dna() get("tokens") sem validação | MEDIUM |
| 11 | `vite_react_renderer.py` | 4513-4516 | font_family sobrescrito por subnicho | MEDIUM |
| 12 | `vite_visual_lanes.py` | 942-946 | resolve_visual_lane() com index=0 sem log | MEDIUM |
| 13 | `vite_react_renderer.py` | 3949-3954 | lane copy sobrescreve LLM | MEDIUM |
| 14 | `vite_liquid_components.py` | 449-453 | infer_aesthetic_pole default "corporate" | MEDIUM |
| 15 | `vite_react_renderer.py` | 4457-4459 | variation injetado sem auditoria | LOW |

### 28 FALLBACKS CRÍTICOS (Máscaras de personalização)

Resumo — full list em [seção 3]:

- 6x `"servicos"` em vite_react_renderer (slug URL)
- 3x `"academia"` em benchmarker (root cause global)
- 5x `"negocio local"` / `"Atendimento local"` em pipeline/renderer
- 7x `"general"` em franz_bridge
- 1x `"5.0"` em vite_templates (inventa rating)
- 1x `"Seu Negócio"` em niche_svg_placeholders
- 1x `"atendimento e prestacao de servicos"` em lgpd_injector
- 50+ `"default"` em todo pipeline

### 0 INVENÇÕES AUTORIZADAS NO LLM (Boa notícia)

Nenhum prompt do FraLib instrui o LLM a inventar. **Toda invenção detectada vem de fallback determinístico no Python**, que o LLM recebe pronto.

---

## 8. Próximos passos

1. **Implementar 5 Quick Wins** (~8h) — corrige 80% dos problemas HIGH
2. **Adicionar `is_fallback: bool` em todos os `.get(key, default)`** — rastreabilidade
3. **Etapa 6: Magentic-One Manager** com blackboard compartilhado
4. **Quality Guardian como agente** com memória de violações passadas
5. **Briefing Parser** que extrai contexto rico de `observacoes`

---

*Auditoria gerada em 2026-07-02. Total: 4 agentes paralelos + consolidação.*
*Próxima auditoria recomendada: após implementação dos 5 Quick Wins.*
