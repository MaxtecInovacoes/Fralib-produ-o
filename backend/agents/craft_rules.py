"""craft_rules.py — Regras universais de qualidade (Open Design craft/ adaptado)
Anti-slop + tipografia + cor + animação com disciplina.
"""

ANTI_SLOP = """
=== ANTI-AI-SLOP — 7 PECADOS CAPITAIS (BLOQUEANTES) ===

1. PROIBIDO usar #6366f1, #4f46e5, #4338ca, #8b5cf6, #7c3aed como accent (indigo/violet Tailwind = slop de IA)
2. PROIBIDO gradiente purple→blue, blue→cyan, indigo→pink no hero
3. PROIBIDO emojis como ícones (✨🚀🎯⚡🔥💡) em headings, botões ou listas — usar SVG monoline com currentColor
4. PROIBIDO sans-serif em display/h1 quando o design system define serif como font-heading
5. PROIBIDO card com borda colorida à esquerda (o "AI dashboard tile")
6. PROIBIDO métricas inventadas ("10x mais rápido", "99.9% uptime", "500+ clientes") sem dado real do lead
7. PROIBIDO filler copy ("Feature One", "Lorem ipsum", texto placeholder, "Descrição do serviço")

SOFT TELLS (evitar fortemente):
- Sequência Hero→Features→Pricing→FAQ→CTA sem variação de layout
- Imagens externas de stock (unsplash.com, picsum.photos, placehold.co, via.placeholder.com)
- Mais de 12 valores hex fora do :root
- var(--accent) usado 6+ vezes no body
- Blobs/waves SVG decorativos sem propósito funcional
- Layout perfeitamente simétrico sem tensão visual
- Inter ou Roboto como font-heading (são fontes de corpo, não display)
- Gradiente em cada seção de fundo
- Ícone em cada heading h2/h3

REGRA DOS 80/20:
  80% padrões comprovados + 20% escolha distintiva.
  O 20% vive em: uma cor de destaque ousada, microcopy com voz real, uma micro-interação memorável.
=== FIM ANTI-SLOP ===
"""

TYPOGRAPHY_RULES = """
=== REGRAS DE TIPOGRAFIA (obrigatórias) ===

ESCALA FLUIDA (clamp — sem media queries para fonte):
  Display: clamp(3rem, 7vw, 5rem)
  H1:      clamp(2.2rem, 5vw, 3.5rem)
  H2:      clamp(1.5rem, 3vw, 2rem)      ← MÁXIMO text-3xl no Tailwind
  H3:      clamp(1.1rem, 2vw, 1.4rem)    ← MÁXIMO text-2xl no Tailwind
  Body:    clamp(0.95rem, 1.5vw, 1.1rem)
  Caption: 0.75rem

LINE HEIGHT:
  Display/H1 → 1.0–1.15 (tight)
  H2/H3      → 1.2–1.3
  Body       → 1.55–1.65
  Small      → 1.5

LETTER SPACING (regra mais ignorada):
  Body          → 0
  Small/caption → +0.01–0.02em
  Botões/labels → 0.02em
  ALL CAPS      → 0.06–0.1em OBRIGATÓRIO
  H2/H3 32px+   → -0.01 a -0.02em
  Display 48px+ → -0.02 a -0.03em

PESOS (sistema de 3 — nunca mais):
  400 → leitura | 510–550 → ênfase | 590–600 → anúncio
  Peso 700+ raramente necessário — reservar para display único

LINHA DE TEXTO: 50–75 chars | max-width: 65ch como padrão seguro
MÁXIMO 3 tamanhos de fonte acima do fold
NUNCA font-family: system-ui sozinho em heading
=== FIM TIPOGRAFIA ===
"""

COLOR_RULES = """
=== REGRAS DE COR (obrigatórias) ===

6 TOKENS UNIVERSAIS — ÚNICA FONTE DE VERDADE:
  var(--bg)      → fundo da página (70–80% da tela)
  var(--surface) → cards, modais, painéis
  var(--fg)      → texto primário
  var(--muted)   → texto secundário, labels, placeholders
  var(--border)  → divisores, outlines, separadores
  var(--accent)  → 1 cor de destaque — MÁXIMO 2 usos visíveis por tela

REGRA DO ACENTO ÚNICO:
  var(--accent) aparece no máximo 2x por tela visível.
  Links contam. Hover rings contam. Bordas de botão contam.
  Se precisar de mais destaque, use opacidade: color-mix(in oklch, var(--accent) 20%, transparent)

CONTRASTE MÍNIMO (WCAG AA):
  Texto body ≤16px → 4.5:1
  Texto grande >18px → 3:1
  Componentes UI → 3:1

DARK MODE:
  Usar DARK_OVERLAY do design_context — nunca inventar valores
  Background → oklch(12% 0.010 260) — nunca #000
  Foreground → oklch(93% 0.005 0)   — nunca #fff puro
  Bordas → oklch com alpha via color-mix

NOMENCLATURA SEMÂNTICA OBRIGATÓRIA:
  var(--bg), var(--surface), var(--fg), var(--muted), var(--border), var(--accent)
  NUNCA var(--blue-500), var(--indigo-600) — nomear por propósito, não por cor
  NUNCA hardcode hex fora do :root (exceto #000/#fff em sombras)

ANTI-DEFAULTS:
  #6366f1 = tell de IA — proibido como accent
  Gradiente 2 stops purple→blue no hero = proibido
  Gradientes decorativos sem propósito funcional = proibido
=== FIM COR ===
"""

ANIMATION_RULES = """
=== REGRAS DE ANIMAÇÃO COM DISCIPLINA ===

QUANDO ANIMAR (apenas):
  - Reorientação espacial: elementos entrando na viewport (scroll reveal)
  - Feedback de interação: hover, press, toggle, focus
  - Transição de estado: modal abrindo, accordion expandindo
  - Progresso: loading, contador incrementando

NUNCA ANIMAR PARA:
  - Decorar (animação que não comunica nada)
  - Sinalizar "premium" (movimento não é sinônimo de qualidade)
  - Ensinar (o usuário não precisa de tutorial visual)

DURAÇÕES (convergência Material 3 + IBM Carbon + Shopify Polaris):
  50ms  → feedback instantâneo (hover color, toggle, press)
  150ms → confirmação de estado (padrão para micro-interações)
  200–300ms → entrada de UI (modais, dropdowns, tooltips)
  300–500ms → transições entre seções, container morphs
  >500ms → apenas transições cross-screen (nunca em elementos isolados)

CURVAS:
  Opacity/color:          cubic-bezier(0.4, 0.0, 0.2, 1)  ← standard
  Position/scale (enter): cubic-bezier(0.0, 0.0, 0.2, 1)  ← decelerate
  Position/scale (exit):  cubic-bezier(0.4, 0.0, 1, 1)    ← accelerate
  Spring/bounce:          cubic-bezier(0.34, 1.56, 0.64, 1) ← apenas energético

REDUCED MOTION — OBRIGATÓRIO:
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      transition-duration: 0.01ms !important;
    }
  }
  Toda animação com translate/scale/rotate DEVE ter fallback de opacity.

SCROLL REVEAL (padrão):
  Usar IntersectionObserver — NUNCA scroll event listener
  threshold: 0.15 | rootMargin: "0px 0px -50px 0px"
  Classe .reveal → opacity:0 + translateY(24px) → opacity:1 + translateY(0)
  Stagger entre cards: delay incremental via --i CSS custom property

CTA PULSE (obrigatório em botão principal):
  @keyframes pulse-cta {
    0%, 100% { box-shadow: 0 0 0 0 color-mix(in oklch, var(--accent) 40%, transparent); }
    50%       { box-shadow: 0 0 0 8px transparent; }
  }
  animation: pulse-cta 2.5s ease-in-out infinite;
=== FIM ANIMAÇÃO ===
"""

AUTOCRITICA_TEMPLATE = """
=== AUTOCRÍTICA OBRIGATÓRIA (antes de emitir) ===

Avalie o HTML gerado em 5 dimensões. Se qualquer dimensão for < 3, REESCREVA antes de retornar.

1. PHILOSOPHY (1–5): O tom visual bate com o nicho e o brief?
   < 3 = reescrever hero e seção sobre

2. HIERARCHY (1–5): O olho tem um ponto focal claro? H1 domina, depois subtítulo, depois CTA?
   < 3 = ajustar tamanhos e pesos tipográficos

3. EXECUTION (1–5): Tipografia, espaçamento e contraste corretos? Sem cores hardcoded fora do :root?
   < 3 = corrigir CSS vars e espaçamentos

4. SPECIFICITY (1–5): Todo texto é específico ao negócio? Zero lorem ipsum, zero "Feature One"?
   < 3 = substituir todo filler copy por dados reais do brief

5. RESTRAINT (1–5): Apenas 1 cor de destaque, usada no máximo 2x? Sem gradiente em cada fundo?
   < 3 = remover usos extras de --accent e gradientes decorativos

Formato de resposta interna (não incluir no HTML):
SCORES: philosophy=X hierarchy=X execution=X specificity=X restraint=X
ACTION: [nenhuma | reescrever hero | corrigir CSS | substituir copy | remover accent]
=== FIM AUTOCRÍTICA ===
"""




TYPOGRAPHY_HIERARCHY = """
=== HIERARQUIA TIPOGRAFICA - OPEN DESIGN (obrigatoria) ===

CONTRATO: 1 ENTRY POINT DOMINANTE POR TELA
  Cada secao tem exatamente 1 elemento que domina o olho.
  Hero: H1 e o entry point. NUNCA vazio, generico ou menor que o subtitulo.
  H1 NUNCA pode ter menos de 8 palavras.
  H1 DEVE conter: beneficio principal + cidade.
  Exemplo correto: Nutricao esportiva de alta performance em Campina Grande do Sul
  Exemplo ERRADO: Bem-vindo | Nossos Servicos | apenas o nome do negocio

5 VETORES DE HIERARQUIA (use pelo menos 3 por secao):
  1. ESCALA    - diferenca de tamanho entre H1 e H2: minimo 1.5x
  2. PESO      - H1 bold/black, subtitulo regular, body light
  3. ESPACO    - margin-bottom do H1 = 1.5x o margin-bottom do H2
  4. TRACKING  - H1 display: -0.02em | ALL CAPS labels: 0.08em obrigatorio
  5. ALINHAMENTO - quebra de alinhamento cria tensao (ex: H1 left, eyebrow center)

VIOLACOES CONTROLADAS (1 por secao, nao mais):
  - H1 uppercase quando design e brutalist/editorial
  - Subtitulo maior que H2 quando e unica linha de suporte
  - Eyebrow em monospace quando o resto e sans-serif

PROIBIDO:
  - H1 vazio ou com apenas o nome do negocio
  - H1 e H2 com o mesmo tamanho de fonte
  - Mais de 1 elemento dominante por secao
  - Subtitulo mais longo que 2 linhas no desktop
=== FIM HIERARQUIA TIPOGRAFICA ===
"""

LAWS_OF_UX = """
=== LEIS DE UX - OPEN DESIGN (aplicar em todo HTML gerado) ===

GESTALT - AGRUPAMENTO VISUAL:
  Proximidade: elementos relacionados com gap menor que nao relacionados
  Similaridade: cards do mesmo tipo com exatamente o mesmo estilo
  Continuidade: listas e grids com alinhamento consistente - sem itens soltos
  Fechamento: secoes com delimitacao clara (padding, border, ou mudanca de --bg/--surface)

HICK'S LAW - REDUCAO DE OPCOES:
  Maximo 3 CTAs por pagina (hero CTA + 1 secundario + contato)
  Menu de navegacao: maximo 5 itens
  Cards de servicos: maximo 6 por grid
  FAQ: maximo 8 perguntas visiveis (resto em accordion fechado)

FITTS'S LAW - ALVOS TOCAVEIS:
  Botoes CTA: minimo 48px de altura (py-4 no Tailwind)
  Links de texto: padding minimo 8px vertical
  Botao WhatsApp flutuante: minimo 56x56px
  Inputs de formulario: minimo 44px de altura

MILLER'S LAW - CHUNKING:
  Listas de beneficios: maximo 7 itens
  Secao de servicos: agrupar por categoria se mais de 6
  Depoimentos: mostrar 3 por vez

PEAK-END RULE - MOMENTOS MEMORAVEIS:
  Pico = hero (H1 impactante + foto real + CTA claro)
  Final = secao de contato (simples, direta, sem friccao)
  NUNCA terminar com FAQ ou lista de servicos - sempre CTA ou contato

VON RESTORFF - ELEMENTO DISTINTIVO:
  1 elemento por pagina quebra o padrao para chamar atencao (geralmente o CTA principal)
  NUNCA mais de 1 elemento especial - perde o efeito
=== FIM LEIS DE UX ===
"""


TYPOGRAPHY_HIERARCHY = """
=== HIERARQUIA TIPOGRAFICA - OPEN DESIGN (obrigatoria) ===

CONTRATO: 1 ENTRY POINT DOMINANTE POR TELA
  Cada secao tem exatamente 1 elemento que domina o olho.
  Hero: H1 e o entry point. NUNCA vazio, generico ou menor que o subtitulo.
  H1 NUNCA pode ter menos de 8 palavras.
  H1 DEVE conter: beneficio principal + cidade.

5 VETORES DE HIERARQUIA (use pelo menos 3 por secao):
  1. ESCALA    - diferenca de tamanho entre H1 e H2: minimo 1.5x
  2. PESO      - H1 bold/black, subtitulo regular, body light
  3. ESPACO    - margin-bottom do H1 = 1.5x o margin-bottom do H2
  4. TRACKING  - H1 display: -0.02em | ALL CAPS labels: 0.08em obrigatorio
  5. ALINHAMENTO - quebra de alinhamento cria tensao (ex: H1 left, eyebrow center)

PROIBIDO:
  - H1 vazio ou com apenas o nome do negocio
  - H1 e H2 com o mesmo tamanho de fonte
  - Mais de 1 elemento dominante por secao
  - Subtitulo mais longo que 2 linhas no desktop
=== FIM HIERARQUIA TIPOGRAFICA ===
"""

LAWS_OF_UX = """
=== LEIS DE UX - OPEN DESIGN (aplicar em todo HTML gerado) ===

GESTALT - AGRUPAMENTO VISUAL:
  Proximidade: elementos relacionados com gap menor que nao relacionados
  Similaridade: cards do mesmo tipo com exatamente o mesmo estilo
  Continuidade: listas e grids com alinhamento consistente
  Fechamento: secoes com delimitacao clara (padding, border, ou mudanca de --bg/--surface)

HICK'S LAW - REDUCAO DE OPCOES:
  Maximo 3 CTAs por pagina (hero CTA + 1 secundario + contato)
  Cards de servicos: maximo 6 por grid
  FAQ: maximo 8 perguntas visiveis

FITTS'S LAW - ALVOS TOCAVEIS:
  Botoes CTA: minimo 48px de altura (py-4 no Tailwind)
  Botao WhatsApp flutuante: minimo 56x56px
  Inputs de formulario: minimo 44px de altura

MILLER'S LAW - CHUNKING:
  Listas de beneficios: maximo 7 itens
  Depoimentos: mostrar 3 por vez

PEAK-END RULE - MOMENTOS MEMORAVEIS:
  Pico = hero (H1 impactante + foto real + CTA claro)
  Final = secao de contato (simples, direta, sem friccao)
  NUNCA terminar com FAQ - sempre CTA ou contato

VON RESTORFF - ELEMENTO DISTINTIVO:
  1 elemento por pagina quebra o padrao (geralmente o CTA principal)
  NUNCA mais de 1 elemento especial
=== FIM LEIS DE UX ===
"""


def get_craft_rules() -> str:
    return ANTI_SLOP + TYPOGRAPHY_RULES + TYPOGRAPHY_HIERARCHY + COLOR_RULES + ANIMATION_RULES + LAWS_OF_UX


def get_autocritica() -> str:
    return AUTOCRITICA_TEMPLATE


def get_typography_hierarchy() -> str:
    return TYPOGRAPHY_HIERARCHY


def get_laws_of_ux() -> str:
    return LAWS_OF_UX
