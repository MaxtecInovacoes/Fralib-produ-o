     1|# REFATORACAO PIPELINE v5.0 — DOCUMENTAÇÃO COMPLETA
     2|**Data:** 09/05/2026
     3|**Status:** Implementado. Aguardando Etapa 4 (teste isolado).
     4|**Autor:** Kiro
     5|
     6|---
     7|
     8|## VISÃO GERAL DO PIPELINE
     9|
    10|O pipeline FraLib gera sites para negócios locais de forma 100% automática.
    11|Fluxo: Hunter → Caio → Unsplash + paleta_nicho → Theo → ArquitetoMestre → Liam → Deploy → Liz → Franz
    12|
    13|Agentes que NÃO foram alterados nesta refatoração:
    14|  Hunter, Caio, Unsplash, paleta_nicho, Theo, Deploy, Franz
    15|
    16|Agentes alterados: ArquitetoMestre, Liam
    17|Arquivos novos/refatorados: design_context.py, craft_rules.py (seo_context.py inalterado)
    18|
    19|---
    20|
    21|## ARQUIVO: design_context.py
    22|**Localização:** /root/fralib/backend/agents/design_context.py
    23|**Linhas:** 272
    24|
    25|### O que faz
    26|Sistema de design determinístico por nicho. Define EXATAMENTE como cada site deve parecer
    27|antes do LLM ser chamado. Inspirado no Open Design (nexu-io/open-design).
    28|
    29|### Estrutura
    30|
    31|DIRECOES_VISUAIS — 5 direções com 6 tokens OKLch cada:
    32|  editorial       → Playfair Display + Inter, animação elegante
    33|  modern_minimal  → Plus Jakarta Sans + Inter, animação elegante
    34|  warm_soft       → Lora + Source Sans 3, animação vibrante
    35|  tech_utility    → Outfit + Inter, animação energetico
    36|  brutalist       → Bebas Neue + IBM Plex Mono, animação energetico
    37|
    38|Os 6 tokens universais (mesmos nomes em todos os nichos):
    39|  --bg      → fundo da página (70-80% da tela)
    40|  --surface → cards, modais, painéis
    41|  --fg      → texto primário
    42|  --muted   → texto secundário, labels
    43|  --border  → divisores, outlines
    44|  --accent  → 1 cor de destaque — MÁXIMO 2 usos visíveis por tela
    45|
    46|DARK_OVERLAY — sobrepõe os 5 tokens neutros para dark mode:
    47|  --bg:      oklch(12% 0.010 260)
    48|  --surface: oklch(17% 0.012 260)
    49|  --fg:      oklch(93% 0.005 0)
    50|  --muted:   oklch(65% 0.010 260)
    51|  --border:  oklch(28% 0.015 260)
    52|  (--accent não muda no dark mode)
    53|
    54|ANIMATION_PROFILES — 3 perfis com durações convergidas (Material 3 + IBM Carbon + Shopify Polaris):
    55|  elegante:   enter=300ms, feedback=150ms, easing decelerate, stagger=80ms
    56|              hero_type=fade-up, card_type=fade-up
    57|              nichos: clínica, advocacia, estética, barbearia, odontologia
    58|  vibrante:   enter=250ms, feedback=100ms, easing standard, stagger=60ms
    59|              hero_type=slide-up, card_type=slide-left
    60|              nichos: restaurante, pizzaria, lanchonete, pet_shop, escola
    61|  energetico: enter=200ms, feedback=80ms, easing spring bounce, stagger=40ms
    62|              hero_type=scale-in, card_type=scale-in
    63|              nichos: academia, crossfit, auto_pecas, farmacia, contabilidade
    64|
    65|NICHOS — 15 nichos mapeados com:
    66|  dir: direção visual (chave de DIRECOES_VISUAIS)
    67|  components: componentes obrigatórios da página
    68|  tom: tom de voz para o copy
    69|  seo: regras de H1, schema.org e FAQ
    70|  anti: anti-patterns específicos do nicho
    71|
    72|ALIASES — 20+ aliases para variações de nome de segmento
    73|
    74|TIER_DIRECAO — mapeamento tier → direções permitidas:
    75|  PREMIUM:  editorial, modern_minimal
    76|  STANDARD: warm_soft, tech_utility
    77|  BASIC:    tech_utility
    78|  ATENÇÃO: a direção do nicho tem prioridade absoluta sobre o tier.
    79|  Academia sempre usa brutalist, independente do tier.
    80|
    81|### Funções exportadas
    82|
    83|get_design_context(segmento, tier, dark_mode) → dict
    84|  Retorna dict com: dir_key, dir_nome, tokens (6 OKLch), font_heading, font_body,
    85|  vibe, animation, animation_profile, components, tom, seo, anti, segmento, tier
    86|  Usado pelo ArquitetoMestre para extrair valores programaticamente.
    87|
    88|get_design_context_prompt(segmento, tier, dark_mode) → str
    89|  Retorna string formatada para injetar em prompts LLM.
    90|  Inclui: tokens, tipografia, perfil de animação, componentes, tom, SEO, anti-patterns.
    91|
    92|---
    93|
    94|## ARQUIVO: craft_rules.py
    95|**Localização:** /root/fralib/backend/agents/craft_rules.py
    96|**Linhas:** 190
    97|
    98|### O que faz
    99|Regras universais de qualidade de design. Injetadas no prompt do ArquitetoMestre
   100|E diretamente no SYSTEM_LIAM. Inspirado nos arquivos craft/ do Open Design.
   101|
   102|### Seções
   103|
   104|ANTI_SLOP — 7 pecados capitais bloqueantes:
   105|  1. PROIBIDO #6366f1, #4f46e5, #8b5cf6 como accent (indigo/violet Tailwind = slop de IA)
   106|  2. PROIBIDO gradiente purple→blue no hero
   107|  3. PROIBIDO emojis como ícones (✨🚀🎯⚡) — usar SVG monoline com currentColor
   108|  4. PROIBIDO sans-serif em h1 quando design define serif
   109|  5. PROIBIDO card com borda colorida à esquerda
   110|  6. PROIBIDO métricas inventadas sem dado real do lead
   111|  7. PROIBIDO filler copy (Feature One, Lorem ipsum, placeholder)
   112|  + 9 soft tells (evitar fortemente)
   113|  + Regra dos 80/20
   114|
   115|TYPOGRAPHY_RULES — escala fluida com clamp(), line-height, letter-spacing, pesos
   116|
   117|COLOR_RULES — 6 tokens universais, regra do acento único, WCAG AA, dark mode, nomenclatura semântica
   118|
   119|ANIMATION_RULES — quando animar, durações convergidas, curvas por tipo, reduced motion,
   120|  scroll reveal com IntersectionObserver, CTA pulse com color-mix oklch
   121|
   122|AUTOCRITICA_TEMPLATE — 5 dimensões (Philosophy, Hierarchy, Execution, Specificity, Restraint)
   123|  Qualquer dimensão < 3 obriga reescrita antes de retornar
   124|
   125|### Funções exportadas
   126|  get_craft_rules() → str  (ANTI_SLOP + TYPOGRAPHY_RULES + COLOR_RULES + ANIMATION_RULES)
   127|  get_autocritica() → str  (AUTOCRITICA_TEMPLATE)
   128|
   129|---
   130|
   131|## ARQUIVO: seo_context.py
   132|**Localização:** /root/fralib/backend/agents/seo_context.py
   133|**Linhas:** 62
   134|**Status:** NÃO ALTERADO na v5.0
   135|
   136|### O que faz
   137|Framework SEO local por nicho. Injetado no prompt do ArquitetoMestre.
   138|  - Schema.org específico por nicho (BarberShop, Restaurant, Dentist, etc.)
   139|  - H1 template com cidade e nome obrigatório
   140|  - Keywords primárias e cauda longa por nicho
   141|  - FAQ pré-definido por nicho
   142|  - Intenção de busca mapeada (transacional vs comercial)
   143|
   144|### Função exportada
   145|  get_seo_context(segmento, cidade, nome) → str
   146|
   147|---
   148|
   149|## ARQUIVO: arquiteto_mestre.py
   150|**Localização:** /root/fralib/backend/agents/arquiteto_mestre.py
   151|**Linhas:** 531
   152|
   153|### O que faz
   154|Agente central. Recebe dados brutos (Hunter, Caio, Theo, Jina) e retorna DesignerPRD
   155|com copy completa, paleta, tipografia, animações e seções para o Liam.
   156|
   157|### Fluxo interno (ordem de execução)
   158|
   159|1. Google Suggest — busca termos reais do nicho/cidade
   160|2. Extrai dados estruturados da Jina (FAQ, keywords, value_props)
   161|3. _design_dict = get_design_context(segmento, tier, dark_mode)
   162|   CRÍTICO: definido ANTES do bloco do Alex para que o fallback de accent use OKLch
   163|4. Normaliza paleta do Alex (hint apenas — tokens OKLch têm prioridade)
   164|   Fallback de accent: _design_dict["tokens"]["--accent"] (nunca #6366f1)
   165|5. Monta 4 contextos para o prompt:
   166|   _brief_estruturado  → dados reais organizados (surface, audience, tone, brand, scale)
   167|   _design_ctx         → get_design_context_prompt() — tokens + tipografia + animação
   168|   _craft_ctx          → get_craft_rules() — anti-slop + tipografia + cor + animação
   169|   _seo_ctx            → get_seo_context() — schema + H1 + keywords
   170|   _autocritica_ctx    → get_autocritica() — 5 dimensões
   171|6. Chama Claude Sonnet com o prompt completo (max_tokens=12000, temperature=0.3)
   172|7. Fallback: segunda chamada com prompt enxuto se JSON inválido
   173|8. Pós-processamento:
   174|   color_palette → tokens_oklch com os 6 valores OKLch intactos
   175|   typography    → heading/body do _design_dict (nunca fallback hardcoded)
   176|   seo_keywords  → Jina + base + Google Suggest
   177|   dark_mode     → propagado para o Liam
   178|
   179|### O que o prompt instrui o LLM a fazer
   180|  - Gerar JSON com sections, copy específica, layout_type, animações
   181|  - Usar os 6 tokens OKLch exatos no :root
   182|  - Usar a tipografia do nicho
   183|  - Terminar instrucao_criativa_para_dev com "CSS VARS CONFIRMADAS: --bg:X --surface:X ..."
   184|  - Autocrítica em 5 dimensões antes de retornar
   185|
   186|### Função exportada
   187|  gerar_arquiteto_mestre_prd(dados_hunter, cidade, segmento, jina_insights,
   188|                              alex_colors, caio_tier, caio_score, caio_motivo,
   189|                              briefing_theo, dark_mode) → DesignerPRD
   190|
   191|
---

## ARQUIVO: liam.py
**Localização:** /root/fralib/backend/agents/liam.py
**Linhas:** 1218

### O que faz
Gerador de HTML. Recebe o DesignerPRD do ArquitetoMestre e retorna HTML completo
autocontido (CSS inline, JS inline, zero dependências externas).

### SYSTEM_LIAM_SINGLE_PASS (system prompt)
Injetado em cada chamada LLM. Contém:

REGRAS ESTRUTURAIS (10 regras):
  - Retornar apenas tags <section> — sem DOCTYPE, html, head, body
  - H1 obrigatório com nome da cidade
  - Grid 60/40 ou 40/60 — nunca 50/50
  - Dados reais apenas — nunca inventar
  - Fotos apenas das URLs fornecidas
  - Botões com href válido — nunca href="#" vazio

6 TOKENS CSS — ÚNICA FONTE DE VERDADE:
  O :root já está definido no wrapper com os 6 tokens OKLch.
  O Liam usa EXCLUSIVAMENTE: var(--bg), var(--surface), var(--fg),
  var(--muted), var(--border), var(--accent)
  PROIBIDO: var(--color-primary), var(--color-background) (nomes antigos)
  PROIBIDO: text-white, text-gray-100, color:#fff em elementos de texto

TIPOGRAFIA:
  h1: clamp(2.2rem,5vw,3.5rem), line-height:1.1, letter-spacing:-0.02em
  h2: máximo text-3xl, letter-spacing:-0.01em
  h3: máximo text-2xl
  font-heading vem do design_context — nunca substituir por Inter ou Roboto

LAYOUTS (10 tipos definidos):
  hero-split, hero-center, hero-fullscreen, hero-diagonal
  sobre-grid, services-cards, services-accordion
  reviews-masonry, location-split, contact-split

ANIMAÇÕES COM DISCIPLINA:
  IntersectionObserver — nunca scroll event listener
  Classes: .reveal, .reveal-left, .scale-in, .stagger-item
  Duração e easing via var(--dur-enter) e var(--ease-std) — nunca hardcode
  CTA principal: class="btn-primary pulse-cta"
  @media (prefers-reduced-motion) já está no wrapper — não redefinir

ANTI-AI-SLOP (7 bloqueantes diretamente no Liam):
  Mesmos 7 pecados do craft_rules — o Liam não depende do ArquitetoMestre repassar

AUTOCRÍTICA (5 dimensões antes de retornar):
  Philosophy, Hierarchy, Execution, Specificity, Restraint
  Qualquer dimensão < 3 → corrigir antes de retornar

### montar_template_python(html_main, prd) — wrapper HTML

Monta o HTML completo em torno das sections geradas pelo LLM.

Extração de tokens (ordem de prioridade):
  1. color_palette.tokens_oklch (dict com 6 tokens OKLch — caminho feliz)
  2. Fallback para campos hex legados (background, text, accent) se tokens_oklch ausente

Extração de tipografia:
  prd.typography["heading"] e prd.typography["body"]
  Definidos pelo ArquitetoMestre a partir do design_context — nunca hardcoded

Extração de animação:
  _enter_dur, _feedback, _easing_std, _easing_ent, _stagger
  Vindos do animation_profile do design_context via tokens_oklch["_animation_profile"]

O que o :root contém:
  6 tokens OKLch: --bg, --surface, --fg, --muted, --border, --accent
  Aliases de compatibilidade: --color-primary, --color-accent, --color-background,
    --color-text, --color-surface, --color-border, --color-muted
  Variáveis de animação: --dur-enter, --dur-feedback, --ease-std, --ease-enter, --stagger

CSS de reveal (definido no wrapper, usado pelo Liam):
  .reveal        → opacity:0 + translateY(24px) → .visible → opacity:1 + translateY(0)
  .reveal-left   → opacity:0 + translateX(-24px) → .visible → opacity:1 + translateX(0)
  .scale-in      → opacity:0 + scale(0.95) → .visible → opacity:1 + scale(1)
  .stagger-item  → delay via calc(var(--i,0) * var(--stagger))
  .pulse-cta     → @keyframes pulse-cta com color-mix oklch
  @media (prefers-reduced-motion) → desativa tudo globalmente

Google Fonts:
  Carrega as fontes corretas do nicho dinamicamente
  Ex: barbearia → Playfair Display + Inter
      restaurante → Lora + Source Sans 3
      academia → Bebas Neue + IBM Plex Mono

Dark/light mode:
  [data-theme="dark"] → DARK_OVERLAY OKLch (não mais _escurecer_cor hex)
  [data-theme="light"] → tokens do design_context
  Toggle via toggleTheme() JS inline

JS de animação:
  IntersectionObserver nativo — threshold=0.15, rootMargin=-50px
  Atribui --i incremental para stagger
  REMOVIDOS: AOS (unpkg), GSAP (cdnjs) — zero CDNs externos de animação

---

## ARQUIVO: liz.py
**Localização:** /root/fralib/backend/agents/liz.py
**Linhas:** 546
**Status:** NÃO ALTERADO na v5.0 (alterado na v4.0)

### O que faz
Auditora de qualidade. Avalia o HTML gerado pelo Liam em 5 dimensões.

Dimensões de auditoria:
  Técnica: DOCTYPE, Tailwind, WhatsApp, estrutura HTML
  Semântica (3 novas da v4.0):
    Especificidade: o site parece feito para ESTE negócio?
    Contenção: sem contadores zerados, seções vazias, texto placeholder?
    Consistência de nicho: WhatsApp CTA, Schema.org, H1 com cidade?

Poder de rejeição (v4.0):
  Tentativa 1: reprovado → status "rejeitar_regenerar" + instruções cirúrgicas para o Liam
  Tentativa 2: ainda reprovado → status "revisao_manual" + publica o melhor dos dois
  Nunca trava o pipeline — sempre publica algo

Score mínimo: 70

---

## FLUXO DE DADOS COMPLETO (v5.0)

Hunter coleta dados do negócio (nome, telefone, endereço, fotos, reviews, rating)
  ↓
Caio qualifica o lead → tier (PREMIUM/STANDARD/BASIC) + score
  ↓
Unsplash + paleta_nicho → fotos e paleta base (hint apenas)
  ↓
Theo → briefing estratégico
  ↓
ArquitetoMestre:
  1. get_design_context(segmento, tier) → _design_dict com 6 tokens OKLch
  2. Monta prompt com brief + design_ctx + craft_rules + seo_ctx + autocritica
  3. Claude Sonnet gera JSON com sections, copy, layout_type
  4. color_palette.tokens_oklch = 6 tokens OKLch intactos
  5. typography = {heading: fonte_do_nicho, body: fonte_do_nicho}
  → DesignerPRD
  ↓
Liam:
  1. Recebe DesignerPRD
  2. Extrai tokens_oklch → monta :root com OKLch
  3. Extrai typography → carrega Google Fonts corretas
  4. Chama LLM com SYSTEM_LIAM (anti-slop + 6 tokens + autocrítica)
  5. LLM gera sections HTML usando var(--bg), var(--fg), var(--accent)
  6. montar_template_python() envolve com header + :root + CSS reveal + footer
  → HTML completo autocontido
  ↓
Deploy → publica em /var/www/fralib/sites/{slug}/index.html
  ↓
Liz → audita em 5 dimensões → aprova ou pede regeneração
  ↓
Franz → notifica o lead

---

## BUGS CONHECIDOS (pendentes)

B2: toggle cores hardcoded — alguns elementos ainda usam hex fixo no toggle dark/light
    (os aliases de compatibilidade no :root mitigam mas não eliminam)
B4: H1 sem cidade — o Liam às vezes gera H1 genérico sem cidade
    (regra está no SYSTEM_LIAM mas o LLM pode ignorar)

---

## INCONSISTÊNCIAS CONHECIDAS (pendentes)

I1: paleta_nicho.py ainda gera hex — não foi migrada para OKLch
    (não é crítico pois o ArquitetoMestre usa design_context como fonte de verdade)
I2: instrucao_criativa_para_dev pode ficar desconectada dos CSS vars
    (mitigado pelo "CSS VARS CONFIRMADAS" obrigatório no final)

---

## ETAPA PENDENTE — TESTE ISOLADO (gate obrigatório)

Rodar pipeline completo com 3 nichos e validar:

1. Barbearia PREMIUM em Curitiba
   Esperado: Editorial Monocle, Playfair Display, animação elegante
   Tokens: --bg oklch(97% 0.008 80), --accent oklch(55% 0.18 45)

2. Restaurante STANDARD em São Paulo
   Esperado: Warm Soft, Lora + Source Sans 3, animação vibrante
   Tokens: --bg oklch(96% 0.020 80), --accent oklch(60% 0.15 35)

3. Academia STANDARD em Belo Horizonte
   Esperado: Brutalist, Bebas Neue + IBM Plex Mono, animação energetico
   Tokens: --bg oklch(98% 0.000 0), --accent oklch(65% 0.30 110)

Checklist por site gerado:
  [ ] PRD.color_palette.tokens_oklch tem os 6 tokens com oklch()
  [ ] PRD.typography.heading bate com a direção do nicho
  [ ] HTML :root contém oklch() (não hex)
  [ ] HTML não usa var(--color-primary) ou var(--color-background)
  [ ] HTML usa var(--dur-enter) e var(--ease-std) nas animações
  [ ] Nenhum CDN de AOS ou GSAP no HTML
  [ ] Google Fonts carrega a fonte correta do nicho
  [ ] Score Liz >= 70

Só avançar para produção em escala após os 3 nichos passarem.

---

## PRÓXIMOS PASSOS SUGERIDOS (pós-teste)

P1: Migrar paleta_nicho.py para OKLch (baixa prioridade — design_context tem prioridade)
P2: Seed template HTML base por direção visual (elimina variância residual do Liam)
P3: Banco de blocos HTML por layout_type (layouts.md equivalente)
P4: Corrigir B2 (toggle cores hardcoded) e B4 (H1 sem cidade)
