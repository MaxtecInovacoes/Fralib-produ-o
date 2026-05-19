"""
Liam — Gerador de HTML cinematografico para negocios locais
Modulos: liam_models, liam_motion, liam_seo
"""
import sys
import os
import time
import re
import json
sys.path.insert(0, "/root/fralib/backend/agents")

# Managed Agent: validação + auto-correção por seção (sempre ativo)
_LIAM_AGENT_LOOP = True

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from llm_direct import call_claude, call_claude_structured
from liam_seo import _get_schema_type  # gerar_seo_tags e gerar_whatsapp_float substituidos por funcoes inline
from open_design_selector import get_open_design_for_liam

# Importar modulos Liam

SYSTEM_LIAM_CORE = """IMPORTANTE: responda APENAS em texto puro HTML. NUNCA use ferramentas/tools. NUNCA retorne JSON. Retorne APENAS codigo HTML direto, sem markdown, sem blocos de codigo.

Voce e Liam, desenvolvedor frontend senior da FraLib.
Sua unica tarefa: gerar UMA tag <section> completa em HTML/Tailwind estatico.

=== DESIGN INTELLIGENCE (condensado de ui-ux-pro-max + design-system) ===
CONTRAST: min 4.5:1 ratio texto/fundo. Light mode text: slate-900 (#0F172A). NUNCA slate-400 pra body.
SPACING: 8px grid. Sections: py-16 md:py-24. Cards: p-6 md:p-8. Gap min: gap-4 (16px).
TOUCH: botoes min 44x44px (py-3 px-6 minimo). cursor-pointer em tudo clicavel.
HOVER: SEMPRE feedback visual. Cards: hover:translate-y-[-4px] hover:shadow-xl transition-all duration-300. Botoes: hover:opacity-90 active:scale-[0.97].
ICONS: Phosphor Icons APENAS. NUNCA emojis como icones. NUNCA SVG inline longo.
IMAGES: aspect-ratio definido. rounded-xl ou rounded-2xl. object-cover SEMPRE. Sombra sutil em fotos.
CARDS: border sutil (1px border-[var(--border)]). Padding generoso. Hover state obrigatorio.
VISUAL WEIGHT: hero = 60% visual. CTA = destaque maximo (accent + tamanho). Texto secundario = muted.
COLOR TEMPERATURE: comida = quente (vermelho/laranja/amarelo). Saude = frio (azul/verde). Fitness = energetico (vermelho/laranja). Luxo = neutro (preto/dourado).

=== REGRAS ESTRUTURAIS ===
1. Retorne APENAS <section id="NOME">...</section>. NADA antes ou depois.
2. NUNCA inclua DOCTYPE, html, head, body, header, footer, scripts ou markdown.
3. GRID: 60/40 ou 40/60. NUNCA 50/50.
4. H1 OBRIGATORIO no hero: deve conter cidade + beneficio (8+ palavras). NUNCA generico.
5. PRECOS: NUNCA mencione valores. Use: "Consulte nossos valores".
6. DADOS REAIS: use APENAS dados fornecidos. NUNCA invente nomes, enderecos, depoimentos.
7. FOTOS: Use APENAS URLs fornecidas. Hero: loading=eager. Demais: loading=lazy. Sempre object-fit:cover.
8. DEPOIMENTOS: Se reviews reais fornecidos, use-os. Se nao houver, gere 3 ficticios com nomes genericos.
9. BOTOES: TODOS com href valido. WhatsApp: href='https://wa.me/{num}'. NUNCA href='#'.
10. CONTADORES: NUNCA invente numeros. Use apenas rating e total_avaliacoes reais.

=== 6 TOKENS CSS — UNICA FONTE DE VERDADE ===
O :root JA ESTA DEFINIDO no wrapper. Use EXCLUSIVAMENTE:
  var(--bg) fundo | var(--surface) cards | var(--fg) texto | var(--muted) secundario | var(--border) divisores | var(--accent) destaque (MAX 2x por tela)

PROIBIDO ABSOLUTAMENTE (gera erro de build):
  - text-white, text-black, text-gray-800, text-gray-600 → use text-[var(--fg)] ou text-[var(--muted)]
  - color:#fff, color:#000, qualquer hex/rgb hardcoded → use var(--fg), var(--bg)
  - var(--color-primary), var(--color-background), var(--color-accent) → NAO EXISTEM
  - font-family inline ou font-sans/font-serif → fontes vem do wrapper, NUNCA defina
  - bg-white, bg-black, bg-gray-* → use bg-[var(--bg)] ou bg-[var(--surface)]

=== FOTOS — REGRA DE INJECAO ===
Hero: OBRIGATORIO incluir <img src="URL_FORNECIDA" loading="eager" class="w-full h-full object-cover" alt="...">
Demais secoes: se foto fornecida, incluir como <img> com loading=lazy, rounded, aspect-ratio adequado.
NUNCA use background-image com URL. Sempre <img> tag.

=== ANIMACOES (classes pre-definidas no wrapper) ===
  .reveal (fadeY 24px) | .reveal-left (fadeX -24px) | .scale-in (scale 0.95→1) | .stagger-item (--i delay)
  CTA: .btn-primary .pulse-cta | Hero H1: .scale-in | Subtitulo: .reveal | Cards: .stagger-item style="--i:N"
  Imagens: .reveal-left | Parallax: data-parallax="0.3" | Hover cards: hover:scale-[1.02] hover:shadow-lg transition-all duration-300
  Usar IntersectionObserver — NUNCA scroll event listener.

=== ANIMACOES PREMIUM (diferencial R$200 → R$20K) ===
  PARALLAX: imagens com data-parallax="0.15" (sutil) a "0.4" (dramatico). Hero SEMPRE tem parallax.
  STAGGER WATERFALL: cards/listas NUNCA aparecem de uma vez. Usar style="--i:0" style="--i:1" style="--i:2" com .stagger-item.
  SCROLL PROGRESS: barra de progresso no topo (position:fixed, scaleX via scroll%). Adicionar no hero.
  HOVER PREMIUM: cards com transition-all duration-300 hover:translate-y-[-4px] hover:shadow-xl. Botoes com active:scale-[0.97].
  COUNTER ANIMATE: numeros (rating, anos) com data-counter="4.7" — JS anima de 0 ao valor no scroll.
  TEXT REVEAL: headlines com overflow:hidden + span.reveal-text (translateY 100% → 0 no scroll).
  GRADIENT SHIFT: hero background com background-size:200% e animation sutil (10s alternate infinite).
  PERFORMANCE: animar APENAS transform e opacity. NUNCA top/left/width/height. will-change:transform em elementos animados.
  REDUCED MOTION: @media(prefers-reduced-motion:reduce) desativa animacoes — substituir por opacity simples.

=== HIERARQUIA TIPOGRAFICA ===
  H1: clamp(2.2rem,5vw,3.5rem) line-height:1.1 letter-spacing:-0.02em font-bold
  H2: MAX text-3xl | H3: MAX text-2xl
  Diferenca H1 vs H2: minimo 1.5x. tracking-widest APENAS em labels text-xs ALL CAPS.
  font-heading vem do design_context — NUNCA substituir.

=== UX ===
  GESTALT: cards mesmo tipo = mesmo estilo | HICK: max 3 CTAs | FITTS: botoes min py-4 (48px)
  MILLER: listas max 7 | PEAK-END: hero=pico, contato=final, NUNCA terminar com FAQ
  VON RESTORFF: 1 elemento especial (CTA principal)
  BOTOES: background var(--accent) → texto SEMPRE var(--bg). NUNCA var(--fg) em botao com accent.

=== LAYOUT & CONTRASTE (CRITICO) ===
  PADDING: toda secao py-16 md:py-24 px-4 md:px-8. NUNCA secao sem padding.
  POSITION: NUNCA use position:absolute na tag <section> ou em containers diretos de secao. Absolute APENAS para overlays (img/div) DENTRO de um parent relative.
  Z-INDEX: texto SEMPRE acima de imagens. Se hero tem imagem de fundo: position:relative no container, img absolute inset-0 z-0, texto relative z-10.
  OVERLAY: se imagem de fundo + texto por cima: OBRIGATORIO overlay escuro (bg-black/50 ou bg-gradient-to-t from-black/70) + texto branco (text-white permitido APENAS sobre overlay escuro).
  CONTRASTE: texto NUNCA pode ter cor similar ao fundo. Se --bg e claro, --fg deve ser escuro. Se --bg e escuro, texto deve ser claro.
  IMAGENS: NUNCA position:absolute sem container position:relative. NUNCA img cobrindo texto sem overlay. NUNCA img sem max-width:100%.
  RESPONSIVO: mobile-first. Hero: flex-col no mobile, md:flex-row no desktop. Imagens: w-full h-64 md:h-auto.
  GAP: todo flex/grid DEVE ter gap (min gap-4). NUNCA elementos colados sem espacamento.
  OVERFLOW: NUNCA permitir texto cortado. Use overflow-wrap:break-word. Titulos com clamp() obrigatorio.
"""

SYSTEM_LIAM_ANTI_SLOP = """
=== SKILLS CONDENSADAS (regras de decisão obrigatórias) ===

[UI-UX-PRO] Um elemento dominante por seção (scale+weight juntos). Max 2 accent por viewport. Hierarquia: size > weight > color > position. Cards max 4 above fold. Botões min 48x44px. Espaço entre grupos 3x maior que dentro do grupo. Nunca mais de 3 CTAs por página.

[DESIGN-TASTE] Tracking negativo em display (-0.02em). Labels uppercase tracking 0.06em+. Gradients só em overlays/hovers, nunca decorativos. Shadows com blur 2x do spread. Border-radius consistente (não misturar rounded-sm com rounded-2xl). Fotos nunca sem container (rounded+overflow-hidden). Um detalhe memorável por site (counter, tilt, clip-reveal).

[MOTION] Parallax só em fotos >50% viewport. Clip-reveal só na primeira img de cada seção. Scale-in só em cards/stats. Nunca animar texto body. Stagger max 80ms. Duração: hover=150ms, enter=300ms, transition=500ms. Se motion=subtle, só opacity. Não animar o que já está visível no load.

[STYLING] Glass: backdrop-blur(12px) + bg opacity 80% + border 1px white/10. Shadows: sm=sutil(cards), lg=destaque(hero-cta), xl=flutuante(modals). Hover: translateY(-2px)+shadow increase, nunca scale>1.05. Dark surfaces: nunca #000, usar oklch(8-12%).

[A11Y] Focus-visible em tudo clicável (2px solid accent). Alt descritivo em imgs. Headings em ordem (h1→h2→h3, nunca pular). Contraste 4.5:1 texto, 3:1 UI. Links distinguíveis sem depender só de cor.

=== ANTI-AI-SLOP (BLOQUEANTES) ===
PROIBIDO: #6366f1 #4f46e5 #8b5cf6 (indigo/violet = slop)
PROIBIDO: gradiente purple→blue, blue→cyan, indigo→pink
PROIBIDO: emojis como icones (✨🚀🎯⚡) — usar SVG ou Phosphor Icons
PROIBIDO: Inter/Roboto como font-heading
PROIBIDO: layout simetrico Hero→Features→Pricing→FAQ→CTA sem variacao
PROIBIDO: var(--accent) 6+ vezes no body
PROIBIDO: blobs/waves SVG decorativos
PROIBIDO: metricas inventadas, filler copy, contadores zerados
PROIBIDO: card com borda colorida a esquerda
PROIBIDO: bolinhas com letras como logo — use texto Bold elegante

=== AUTOCRITICA (antes de retornar) ===
1. PHILOSOPHY: tom visual bate com nicho?
2. HIERARCHY: H1 domina? Subtitulo menor? CTA claro?
3. EXECUTION: sem cores hardcoded? Botoes min 48px?
4. SPECIFICITY: zero filler copy? Dados reais?
5. RESTRAINT: --accent max 2x? Max 3 CTAs?

=== SKELETON OBRIGATORIO POR SECAO (Sonnet: SIGA EXATAMENTE) ===

HERO (min 60 linhas):
<section id="hero" class="relative w-full min-h-[100dvh] flex items-center overflow-hidden" style="background-color:var(--bg);">
  <div class="relative z-10 w-full flex flex-col lg:flex-row items-center min-h-[100dvh]">
    <div class="w-full lg:w-[60%] flex flex-col justify-center px-6 md:px-12 lg:px-20 py-20 lg:py-0">
      <div class="max-w-2xl">
        [eyebrow .reveal text-xs uppercase tracking-[0.25em] color:var(--accent)]
        [h1 .scale-in font-bold clamp(2.8rem,6vw,4.5rem) color:var(--fg)]
        [subtitle .reveal text-lg color:var(--muted) max-w-[52ch]]
        [rating .reveal stars + data-counter]
        [CTA .pulse-cta .btn-primary px-8 py-4 rounded-full bg-[var(--accent)] color:#fff]
      </div>
    </div>
    <div class="w-full lg:w-[40%] h-[50vh] lg:h-full lg:min-h-[100dvh] relative overflow-hidden">
      <img data-parallax="0.3" loading="eager" class="w-full h-full object-cover">
      <div class="absolute inset-0 pointer-events-none hidden lg:block" style="background:linear-gradient(to right,var(--bg) 0%,transparent 15%)"></div>
    </div>
  </div>
</section>

SOBRE (min 40 linhas):
<section id="sobre" class="relative py-24 md:py-40" style="background-color:var(--bg);">
  <div class="max-w-6xl mx-auto px-4 md:px-8">
    [separador .line-draw h-px bg-[var(--border)] mb-16]
    <div class="grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-20 items-center">
      [col-img .reveal-left aspect-[3/4] rounded-2xl overflow-hidden img loading=lazy data-parallax="0.15"]
      [col-texto .reveal span-label + h2 text-3xl + paragrafos + stats .stagger-item data-counter]
    </div>
  </div>
</section>

SERVICOS (min 50 linhas):
<section id="servicos" class="py-24 md:py-32" style="background-color:var(--surface);">
  <div class="max-w-6xl mx-auto px-4 md:px-8">
    [h2 .reveal text-center]
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mt-16">
      [cards .stagger-item style="--i:N" hover:translate-y-[-4px] hover:shadow-xl transition-all duration-300 rounded-2xl p-8 border border-[var(--border)]]
    </div>
  </div>
</section>

DEPOIMENTOS (min 30 linhas):
<section id="depoimentos" class="py-24 md:py-32" style="background-color:var(--bg);">
  [h2 .reveal + grid 1-3 cols cards com aspas, nome, rating stars]
</section>

LOCALIZACAO (min 20 linhas):
<section id="localizacao" class="py-24 md:py-32" style="background-color:var(--surface);">
  [h2 + grid: col-mapa(iframe google maps embed) + col-info(endereco, horario, telefone)]
</section>

CONTATO/CTA FINAL (min 20 linhas):
<section id="contato" class="py-24 md:py-32" style="background-color:var(--bg);">
  [h2 + texto persuasivo + CTA grande centralizado .pulse-cta]
</section>

REGRAS DO SKELETON:
- CADA secao DEVE abrir com <section id="..." class="..."> e fechar com </section>
- NUNCA gerar div solto sem section wrapper
- Hero OBRIGATORIO: min-h-[100dvh], grid 60/40, img com data-parallax
- TODAS secoes: py-24 md:py-32 minimo, max-w-6xl mx-auto
- MINIMO 6 secoes por site (hero + sobre + servicos + depoimentos + localizacao + contato)
- Se PRD pedir FAQ: inserir ANTES de contato (NUNCA como ultima secao)

=== ALTERNANCIA DE FUNDO (RITMO VISUAL) ===
Secoes NUNCA devem ter todas o mesmo fundo. Alternar entre:
  - var(--bg) — fundo principal (off-white tintado)
  - var(--surface) — branco puro (cards, destaque)
  - color-mix(in oklch, var(--accent) 5%, var(--bg)) — fundo com toque sutil do accent
  - var(--fg) com texto var(--bg) — secao dark invertida (MAX 1 por site, ideal pra CTA final ou depoimentos)

Padrao recomendado:
  hero: var(--bg)
  sobre: var(--bg)
  servicos: var(--surface) ← destaca cards
  depoimentos: color-mix(in oklch, var(--accent) 8%, var(--bg)) ← fundo tintado sutil
  localizacao: var(--bg)
  contato: var(--fg) com texto var(--bg) ← secao dark, CTA final impactante

REGRA: NUNCA 3 secoes seguidas com mesmo background. Minimo 2 fundos diferentes alternando.
REGRA: Secao dark (fundo var(--fg)) = texto DEVE ser var(--bg). Botoes: bg-[var(--accent)] text-white.
"""


def _sanitizar_contadores_zerados(html):
    """Remove blocos de contadores com valor 0 que passam impressao de site abandonado."""
    import re as _re
    # Padrao: elemento com texto '0' seguido de label como 'Alunos', 'Anos', 'Clientes', etc
    # Ex: <span class="stat-number">0</span> ou <div>0 Alunos Ativos</div>
    # Remove o bloco pai (div/section) se contiver apenas contadores zerados
    # Abordagem simples: substituir '0' por valor real quando possivel, ou remover o span
    # Remove spans/divs que contem apenas '0' como stat-number
    html = _re.sub(
        r'<span[^>]*class="[^"]*stat-number[^"]*"[^>]*>\s*0\s*</span>',
        '<span class="stat-number" style="display:none">0</span>',
        html
    )
    # Remove padroes textuais '0 Alunos', '0 Anos', '0 Clientes' etc
    html = _re.sub(
        r'\b0\s+(Alunos?|Anos?|Clientes?|Membros?|Treinos?|Unidades?)\b[^<]*',
        '',
        html,
        flags=_re.IGNORECASE
    )
    return html


def _sanitizar_fontes(html):
    """Pos-processador: corrige fontes proibidas em h2/h3 e cores hardcoded que quebram o toggle dia/noite."""
    import re as _re

    def fix_h2(m):
        tag = m.group(0)
        tag = _re.sub(r"(?:lg|md|sm|xl|2xl):text-[456789]xl", "lg:text-3xl", tag)
        tag = _re.sub(r"(?<![:-])text-[456789]xl", "text-3xl", tag)
        tag = _re.sub(r"font-size\s*:\s*clamp\([^)]+\)\s*;?\s*", "", tag)
        tag = _re.sub(r"font-size\s*:\s*[\d.]+rem\s*;?\s*", "", tag)
        return tag

    def fix_h3(m):
        tag = m.group(0)
        tag = _re.sub(r"(?:lg|md|sm|xl|2xl):text-[3456789]xl", "lg:text-2xl", tag)
        tag = _re.sub(r"(?<![:-])text-[3456789]xl", "text-2xl", tag)
        tag = _re.sub(r"font-size\s*:\s*clamp\([^)]+\)\s*;?\s*", "", tag)
        tag = _re.sub(r"font-size\s*:\s*[\d.]+rem\s*;?\s*", "", tag)
        return tag

    html = _re.sub(r"<h2[^>]*>", fix_h2, html)
    html = _re.sub(r"<h3[^>]*>", fix_h3, html)

    # Substituir cores de texto hardcoded (branco/cinza claro fixo) por CSS vars
    # rgba(241,245,249, X) → var(--color-muted) ou var(--color-text)
    def fix_rgba_text(m):
        alpha = float(m.group(1))
        return "var(--color-text)" if alpha >= 0.8 else "var(--color-muted)"

    # Padrão: color: rgba(241,245,249,0.X) — texto claro hardcoded
    html = _re.sub(
        r"color\s*:\s*rgba\(241\s*,\s*245\s*,\s*249\s*,\s*([\d.]+)\)",
        fix_rgba_text, html
    )
    # Padrão: color: rgba(255,255,255,0.X) — branco puro com alpha
    html = _re.sub(
        r"color\s*:\s*rgba\(255\s*,\s*255\s*,\s*255\s*,\s*([\d.]+)\)",
        fix_rgba_text, html
    )
    # Padrão: color: #fff ou color: #ffffff (texto branco fixo fora de botões)
    # Só substitui quando está em style= de elementos de texto (p, span, li, td)
    def fix_white_text(m):
        full = m.group(0)
        # Preservar em botões/badges (background já é escuro)
        if any(x in full for x in ["btn", "button", "badge", "cta", "rounded-full", "px-", "py-"]):
            return full
        return full.replace(m.group(1), "var(--color-text)")

    html = _re.sub(
        r"(<(?:p|span|li|td|th|label|small|em|strong|h[1-6])[^>]+style=\"[^\"]*color\s*:\s*(#(?:fff|ffffff))[^\"]*\"[^>]*>)",
        fix_white_text, html, flags=_re.IGNORECASE
    )

    return html


def _sanitizar_cores_light(html):
    """Pos-processador: detecta contraste ruim via OKLch lightness e corrige."""
    import re as _re

    # Extrair lightness do --bg e --fg do :root
    _bg_m = _re.search(r'--bg:\s*oklch\((\d+(?:\.\d+)?)%', html)
    _fg_m = _re.search(r'--fg:\s*oklch\((\d+(?:\.\d+)?)%', html)
    if not _bg_m:
        return html

    bg_lightness = float(_bg_m.group(1))
    fg_lightness = float(_fg_m.group(1)) if _fg_m else (15 if bg_lightness > 60 else 92)
    is_light_theme = bg_lightness > 60

    # Em tema claro: text-white em seções sem fundo escuro = erro
    if is_light_theme:
        def fix_section_light(m):
            section_tag = m.group(1)
            section_body = m.group(2)

            # Detectar se seção tem fundo escuro explícito
            has_dark_bg = False
            # Checar bg-[var(--fg)] ou bg-[var(--accent)] ou bg-black ou oklch com L < 40%
            if any(x in section_tag for x in ['bg-[var(--fg)]', 'bg-black', 'bg-gray-900', 'bg-gray-800']):
                has_dark_bg = True
            oklch_in_tag = _re.search(r'oklch\((\d+(?:\.\d+)?)%', section_tag)
            if oklch_in_tag and float(oklch_in_tag.group(1)) < 40:
                has_dark_bg = True
            if 'linear-gradient' in section_tag and ('black' in section_tag or 'rgba(0' in section_tag):
                has_dark_bg = True

            if has_dark_bg:
                return m.group(0)  # Seção escura — text-white OK

            # Remover text-white de tags de texto (não de botões)
            def fix_text_white(tm):
                tag = tm.group(0)
                if any(x in tag for x in ['btn', 'button', 'rounded-full', 'px-6', 'px-8', 'py-3', 'py-4', 'cta']):
                    return tag
                return _re.sub(r'(?<!\w)text-white(?!\w)', 'text-[var(--fg)]', tag)

            section_body = _re.sub(
                r'<(?:h1|h2|h3|h4|p|span|li|td|th|label)[^>]*class="[^"]*text-white[^"]*"[^>]*>',
                fix_text_white, section_body, flags=_re.IGNORECASE
            )

            # Corrigir color:#fff inline em texto
            def fix_white_inline(im):
                full = im.group(0)
                if any(x in full for x in ['btn', 'button', 'badge', 'rounded-full', 'background']):
                    return full
                return _re.sub(r'color\s*:\s*#(?:fff|ffffff)\b', 'color:var(--fg)', full)

            section_body = _re.sub(
                r'<(?:p|span|li|td|th|label|small|em|strong|h[1-6])[^>]+style="[^"]*color\s*:\s*#(?:fff|ffffff)[^"]*"[^>]*>',
                fix_white_inline, section_body, flags=_re.IGNORECASE
            )

            return '<section' + section_tag + '>' + section_body + '</section>'

        html = _re.sub(
            r'<section([^>]*)>(.*?)</section>',
            fix_section_light, html, flags=_re.DOTALL
        )

    else:
        # Tema escuro: text-black ou color:#000 em texto = erro
        def fix_section_dark(m):
            section_tag = m.group(1)
            section_body = m.group(2)

            # Detectar se seção tem fundo claro explícito
            has_light_bg = False
            if any(x in section_tag for x in ['bg-[var(--bg)]', 'bg-white']):
                oklch_check = _re.search(r'oklch\((\d+(?:\.\d+)?)%', section_tag)
                if oklch_check and float(oklch_check.group(1)) > 70:
                    has_light_bg = True

            if has_light_bg:
                return m.group(0)

            # Remover text-black
            section_body = _re.sub(r'(?<!\w)text-black(?!\w)', 'text-[var(--fg)]', section_body)
            # Corrigir color:#000 inline
            section_body = _re.sub(r'color\s*:\s*#(?:000|000000)\b', 'color:var(--fg)', section_body)

            return '<section' + section_tag + '>' + section_body + '</section>'

        html = _re.sub(
            r'<section([^>]*)>(.*?)</section>',
            fix_section_dark, html, flags=_re.DOTALL
        )

    return html

def _sanitizar_css_var_bug(html):
    """Corrige bug onde CSS var fica concatenada com texto sem fechar aspas do style."""
    import re as _re
    # O LLM gera: <p style="color:var(--color-text)Carlos</p>
    # Deve ser:   <p style="color:var(--color-text)">Carlos</p>
    def fix_unclosed_style(m):
        before = m.group(1)
        text   = m.group(2)
        close  = m.group(3)
        return before + chr(34) + chr(62) + text + close
    q = chr(34)
    pat = (
        r"(<[a-z][^>]*style=" + q + r"[^" + q + r"]*var\(--color-[a-z-]+\))"
        r"([^" + q + r"<>][^<>]*)"
        r"(<\/[a-z]+>)"
    )
    html = _re.sub(pat, fix_unclosed_style, html)
    # Padrao 2: var(--color-xxx)TEXTO</tag> solto (sem tag de abertura)
    # Ex: var(--color-text)4.6 / 5</span>
    def fix_loose_var(m):
        var_name = m.group(1)
        text     = m.group(2).strip()
        close    = m.group(3)
        tag = close[2:-1]
        return chr(60)+tag+chr(32)+chr(115)+chr(116)+chr(121)+chr(108)+chr(101)+chr(61)+chr(34)+chr(99)+chr(111)+chr(108)+chr(111)+chr(114)+chr(58)+var_name+chr(34)+chr(62)+text+close
    pat2 = r'(var\(--color-[a-z-]+\))([^<>]+)(<\/[a-z]+>)'
    html = _re.sub(pat2, fix_loose_var, html)
    # Padrao 3: var(--color-xxx) solto como conteudo de texto visivel
    # Ex: <h3>var(--color-text)Consulta</h3> -> <h3>Consulta</h3>
    # Remove var() que aparece como texto entre tags (apos > ou whitespace apos >)
    # Mas preserva var() dentro de atributos style="..."
    def _is_inside_style(match):
        # Checar se o var() esta dentro de um atributo style
        start = match.start()
        # Procurar o ultimo style=" antes desta posicao
        before = html[:start]
        last_style_open = before.rfind('style="')
        if last_style_open == -1:
            return False  # nao esta dentro de style
        # Checar se o style foi fechado antes desta posicao
        after_style = before[last_style_open + 7:]  # apos style="
        return '"'  not in after_style  # se nao tem " de fechamento, estamos dentro
    def _remove_if_text(match):
        if _is_inside_style(match):
            return match.group(0)  # preservar dentro de style
        return ''  # remover se e texto visivel
    html = _re.sub(r'var\(--color-[a-z-]+\)\s*', _remove_if_text, html)
    return html


def _sanitizar_botoes_contraste(html):
    """Fix botões com accent bg + fg text (ilegível). Deve ser accent bg + bg text."""
    import re as _re
    # Padrão: background-color:var(--accent) ... color:var(--fg) em links/botões
    html = _re.sub(
        r'(background(?:-color)?\s*:\s*var\(--accent\)\s*;[^"]*?)color\s*:\s*var\(--fg\)',
        r'\1color:var(--bg)',
        html
    )
    # Inverso: color:var(--fg) ... background:var(--accent)
    html = _re.sub(
        r'(color\s*:\s*)var\(--fg\)(\s*;[^"]*?background(?:-color)?\s*:\s*var\(--accent\))',
        r'\1var(--bg)\2',
        html
    )
    return html


def _sanitizar_cores_hardcoded_texto(html):
    """Substitui cores de texto hardcoded claras (#f0f4ff, #f1f5f9, etc) por CSS vars."""
    import re as _re
    # Cores claras hardcoded que quebram o modo claro
    _cores_claras = [
        '#f0f4ff', '#f1f5f9', '#e2e8f0', '#cbd5e1', '#94a3b8',
        '#f8fafc', '#f9fafb', '#f3f4f6', '#e5e7eb', '#d1d5db',
        '#ffffff', '#fff',
    ]
    # Cores escuras hardcoded que quebram o modo escuro
    _cores_escuras = [
        '#111111', '#111827', '#1f2937', '#0f172a', '#0d0d0d',
        '#1a1a2e', '#1e293b',
    ]
    def fix_color_in_style(m):
        full = m.group(0)
        style = m.group(1)
        # Não tocar em backgrounds, borders, shadows
        if any(x in full.lower() for x in ['background', 'border', 'shadow', 'outline', 'fill']):
            return full
        # Não tocar em botões/badges com bg escuro
        if any(x in full for x in ['btn', 'button', 'badge', 'rounded-full', 'px-4', 'px-6', 'py-2', 'py-3']):
            return full
        new_style = style
        for cor in _cores_claras:
            new_style = _re.sub(
                r'(?<![a-z-])color\s*:\s*' + _re.escape(cor) + r'',
                'color:var(--color-text)', new_style, flags=_re.IGNORECASE
            )
        for cor in _cores_escuras:
            new_style = _re.sub(
                r'(?<![a-z-])color\s*:\s*' + _re.escape(cor) + r'',
                'color:var(--color-text)', new_style, flags=_re.IGNORECASE
            )
        return full.replace(m.group(1), new_style)
    html = _re.sub(
        r'<(?:h[1-6]|p|span|li|td|th|label|small|em|strong|div)[^>]+style="([^"]*color\s*:[^"]+)"[^>]*>',
        fix_color_in_style, html, flags=_re.IGNORECASE
    )
    return html


def _sanitizar_hero_imagem(html, fotos):
    """Garante que o div direito do hero (40%) tenha background-image da primeira foto."""
    import re as _re
    if not fotos:
        return html
    foto_url = fotos[0]

    hero_match = _re.search(r"(<!-- SECTION:hero -->.*?<!-- /SECTION:hero -->)", html, _re.DOTALL)
    if not hero_match:
        return html

    hero_block = hero_match.group(1)

    def fix_hero_div(m):
        full = m.group(0)
        if "background-image" in full or "background:url" in full.lower():
            return full
        if 'style="' in full:
            return full.replace('style="', f'style="background-image:url({foto_url});background-size:cover;background-position:center;', 1)
        return full.rstrip(">") + f' style="background-image:url({foto_url});background-size:cover;background-position:center;">'

    hero_fixed = _re.sub(
        r'<div[^>]*(?:w-\[40%\]|md:w-\[40%\])[^>]*>',
        fix_hero_div,
        hero_block
    )
    return html.replace(hero_block, hero_fixed)

def _sanitizar_botoes(html, wnum):
    """Pos-processador: substitui href="#" vazio por whatsapp ou ancora de secao."""
    import re as _re

    wa_url = "https://wa.me/" + wnum if wnum else "#contato"

    # Palavras-chave que indicam CTA de contato/whatsapp
    contact_keywords = [
        "whatsapp", "wpp", "zap", "contato", "falar", "ligar", "agendar",
        "reservar", "marcar", "consultar", "orcamento", "orcamento", "fale",
        "entre em contato", "fale conosco", "agende", "clique aqui"
    ]
    # Palavras-chave que indicam navegacao interna
    nav_map = {
        "sobre": "#sobre",
        "servico": "#servicos",
        "plano": "#planos",
        "depoimento": "#depoimentos",
        "localizacao": "#localizacao",
        "localizacao": "#localizacao",
        "contato": "#contato",
        "saiba mais": "#sobre",
        "ver mais": "#servicos",
        "conheca": "#sobre",
        "ver planos": "#planos",
        "nossos planos": "#planos",
    }

    def fix_href(m):
        full_tag = m.group(0)
        # Pegar texto do botao (conteudo entre > e </a> ou </button>)
        text_match = _re.search(r">([^<]{2,80})<", full_tag)
        btn_text = text_match.group(1).lower().strip() if text_match else ""

        # Verificar se e CTA de contato
        for kw in contact_keywords:
            if kw in btn_text:
                return full_tag.replace('href="#"', 'href="' + wa_url + '"').replace("href='#'", "href='" + wa_url + "'")

        # Verificar navegacao interna
        for kw, anchor in nav_map.items():
            if kw in btn_text:
                return full_tag.replace('href="#"', 'href="' + anchor + '"').replace("href='#'", "href='" + anchor + "'")

        # Default: whatsapp para botoes genericos de CTA
        if any(x in full_tag.lower() for x in ["btn", "cta", "px-6", "px-8", "rounded-full"]):
            return full_tag.replace('href="#"', 'href="' + wa_url + '"').replace("href='#'", "href='" + wa_url + "'")

        return full_tag

    # Substituir <a href="#"> com conteudo
    html = _re.sub(r"<a[^>]+href=[^>]*>[\s\S]{0,300}?</a>", fix_href, html, flags=_re.DOTALL)

    return html


def gerar_html_componentizado(prd):
    """Gera HTML secao por secao SEQUENCIAL (Diretor-Operario)."""
    import os as _os
    import re as _re_sp
    import json as _json

    def _ckpt_slug(name):
        return re.sub(r'[^a-z0-9]', '_', name.lower())[:40]

    def _ckpt_path(slug):
        _dir = "/root/fralib/checkpoints/liam"
        os.makedirs(_dir, exist_ok=True)
        return f"{_dir}/{slug}.json"

    def _ckpt_load(slug):
        path = _ckpt_path(slug)
        if _os.path.exists(path):
            try:
                import time as _t
                # TTL: 24h — checkpoint mais velho que isso é descartado
                _age = _t.time() - _os.path.getmtime(path)
                if _age > 86400:
                    print(f"[Liam] Checkpoint expirado ({_age/3600:.1f}h) — descartando")
                    _os.remove(path)
                    return {}
                with open(path) as _f:
                    data = _json.load(_f)
                print(f"[Liam] ♻️ Checkpoint encontrado: {len(data)} secoes ja prontas (age={_age/60:.0f}min)")
                return data
            except:
                pass
        return {}

    def _ckpt_save(slug, secoes_dict):
        try:
            with open(_ckpt_path(slug), 'w', encoding='utf-8') as _f:
                _json.dump(secoes_dict, _f, ensure_ascii=False)
        except:
            pass

    def _ckpt_clear(slug):
        try:
            _os.remove(_ckpt_path(slug))
        except:
            pass

    cores = prd.color_palette
    reviews = getattr(prd, "reviews_list", []) or []
    # Fallback: se reviews_list vazio mas temos reviews no raw data
    if not reviews:
        _raw_reviews = getattr(prd, "_raw_reviews", []) or []
        if _raw_reviews:
            reviews = _raw_reviews
    print("[Liam] Reviews disponiveis: " + str(len(reviews)))
    fotos = getattr(prd, "photos", []) or []
    logo = getattr(prd, "logo_url", None)
    telefone = getattr(prd, "phone", "") or ""
    wnum = telefone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    whatsapp_url = "https://wa.me/55" + wnum
    maps_embed = getattr(prd, "google_maps_embed", "") or ""
    nl = chr(10)

    # ─── MICRO-DECISÃO: adaptar intensidade/layout ao conteúdo real ───────────
    _rating = getattr(prd, "reviews_rating", 0) or getattr(prd, "rating", 0) or 0
    _n_reviews = len(reviews)
    _n_fotos = len(fotos)
    _sections = getattr(prd, "sections", []) or []
    _n_servicos = sum(1 for s in _sections if "servic" in (getattr(s, "name", "") or s.get("name", "") if isinstance(s, dict) else "").lower())
    _segmento_micro = getattr(prd, "segmento", "") or getattr(prd, "segment", "") or ""
    _sub_nicho_prd = getattr(prd, "sub_nicho", {}) or {}
    _sub_nicho_nome = _sub_nicho_prd.get("sub_nicho", "") if isinstance(_sub_nicho_prd, dict) else ""

    # Micro-decisão via Haiku (~300 tokens) — decisões contextuais que regras fixas não conseguem
    _micro_decision = {"intensity": "medium", "density": "medium", "photo_treatment": "standard", "motion_style": "balanced", "cta_style": "standard"}
    try:
        from llm_direct import call_claude
        import json as _mj
        _micro_prompt = (
            f"Negócio: {prd.business_name} | Segmento: {_segmento_micro} | Sub-nicho: {_sub_nicho_nome}\n"
            f"Rating: {_rating}/5 | Reviews: {_n_reviews} | Fotos: {_n_fotos} | Seções: {len(_sections)}\n\n"
            f"Retorne APENAS JSON (sem explicação):\n"
            f'{{"intensity":"high|medium|low","density":"dense|medium|sparse","photo_treatment":"premium|standard|minimal","motion_style":"cinematic|balanced|subtle","cta_style":"bold|standard|soft"}}\n\n'
            f"Regras:\n"
            f"- intensity high: rating>=4.7 + fotos boas + negócio premium\n"
            f"- intensity low: rating<4.0 ou sem fotos\n"
            f"- density dense: muitas seções/serviços\n"
            f"- photo_treatment premium: muitas fotos + rating alto\n"
            f"- motion_style cinematic: negócio sofisticado (estética, luxo, gastronomia fina)\n"
            f"- motion_style subtle: negócio sério (advogado, clínica médica)\n"
            f"- cta_style bold: negócio energético (academia, delivery)\n"
            f"- cta_style soft: negócio acolhedor (psicólogo, yoga, nutricionista clínico)"
        )
        _micro_resp = call_claude(
            system="Você é um diretor de arte. Analise os dados e retorne APENAS o JSON pedido. Nada mais.",
            user=_micro_prompt,
            model="haiku",
            max_tokens=150,
            temperature=0.1,
        )
        _micro_resp = _micro_resp.strip()
        if _micro_resp.startswith("{"):
            _micro_decision.update(_mj.loads(_micro_resp))
        print(f"[Liam] Micro-decisão (haiku): {_micro_decision}")
    except Exception as _me:
        print(f"[Liam] Micro-decisão fallback (regras): {_me}")
        # Fallback: regras puras
        if _rating >= 4.7 and _n_fotos >= 4:
            _micro_decision["intensity"] = "high"
        elif _rating < 4.0 or _n_fotos <= 1:
            _micro_decision["intensity"] = "low"
        if len(_sections) >= 7:
            _micro_decision["density"] = "dense"
        elif len(_sections) <= 4:
            _micro_decision["density"] = "sparse"
        if _n_fotos >= 5 and _rating >= 4.5:
            _micro_decision["photo_treatment"] = "premium"
        elif _n_fotos <= 2:
            _micro_decision["photo_treatment"] = "minimal"

    _intensity = _micro_decision["intensity"]
    _density = _micro_decision["density"]
    _photo_treatment = _micro_decision["photo_treatment"]

    print(f"[Liam] Micro-decisão final: intensity={_intensity} density={_density} photos={_photo_treatment} motion={_micro_decision.get('motion_style','balanced')} cta={_micro_decision.get('cta_style','standard')}")

    instrucao_diretor = getattr(prd, "instrucao_criativa_para_dev", None) or "Crie um layout moderno e responsivo com Tailwind."

    # Injetar micro-decisão como contexto obrigatório pro Liam
    _density_rules = {
        "dense": "LAYOUT DENSO: muitos serviços/conteúdo. Use grid 3-4 colunas, cards compactos, bento grid. Não desperdice espaço vertical.",
        "sparse": "LAYOUT ESPAÇOSO: poucos serviços. Use layout generoso, 1-2 colunas, muito whitespace. Cada elemento respira.",
        "medium": "LAYOUT EQUILIBRADO: mix de densidade. Use grid 2-3 colunas, espaçamento confortável.",
    }
    _motion_rules = {
        "cinematic": "MOTION CINEMATICO: use transições dramáticas, parallax forte, clip-path reveals. Site sofisticado.",
        "subtle": "MOTION SUTIL: animações discretas, fade simples, sem parallax pesado. Site sério e profissional.",
        "balanced": "MOTION EQUILIBRADO: mix de reveals e fades. Parallax moderado.",
    }
    _micro_context = (
        f"\n=== DECISÃO DE DESIGN (OBRIGATÓRIO) ===\n"
        f"Intensidade: {_intensity} | {_density_rules.get(_density, '')}\n"
        f"{_motion_rules.get(_micro_decision.get('motion_style', 'balanced'), '')}\n"
        f"=== FIM DECISÃO ===\n"
    )
    instrucao_diretor = _micro_context + instrucao_diretor

    # Injetar animation_profile por nicho no contexto
    try:
        from animation_profile import format_animation_context
        _segmento = getattr(prd, "segment", "") or getattr(prd, "segmento", "") or ""
        _anim_ctx = format_animation_context(_segmento) if _segmento else ""
    except Exception as _e:
        print("[Liam] animation_profile nao disponivel: " + str(_e))
        _anim_ctx = ""



    _address = getattr(prd, "address", "") or ""
    _seo_keywords = getattr(prd, "seo_keywords", []) or []
    _atributos = getattr(prd, "atributos", []) or []
    _servicos = getattr(prd, "servicos", []) or []
    _horarios = getattr(prd, "horarios", {}) or getattr(prd, "hours", {}) or {}
    _faixa_preco = getattr(prd, "faixa_preco", "") or ""
    contexto_global = (
        "Negocio: " + prd.business_name + nl
        + "Telefone: " + telefone + nl
        + "WhatsApp: " + whatsapp_url + nl
        + "Endereco: " + (_address or "nao disponivel") + nl
        + "Rating: " + str(prd.reviews_rating) + "/5 (" + str(prd.reviews_count) + " avaliacoes)" + nl
        + "Logo: " + (logo or "nao disponivel") + nl
        + "Fotos: " + (nl.join(fotos[:6]) if fotos else "Nenhuma foto disponivel - use div colorido com icone Phosphor") + nl
        + ("SEO Keywords: " + ", ".join(_seo_keywords[:10]) + nl if _seo_keywords else "")
        + ("Atributos: " + ", ".join(str(a) for a in _atributos[:10]) + nl if _atributos else "")
        + ("Servicos: " + ", ".join(str(s) for s in _servicos[:10]) + nl if _servicos else "")
        + ("Horarios: " + str(_horarios) + nl if _horarios else "")
        + ("Faixa de preco: " + _faixa_preco + nl if _faixa_preco else "")
        + "CSS variables (use APENAS estas no HTML): --bg:" + cores.background
        + " --fg:" + cores.text
        + " --accent:" + cores.accent
        + " --surface:" + getattr(cores, "surface", cores.background)
        + " --muted:" + getattr(cores, "muted", "oklch(60% 0.01 0)")
        + " --border:" + getattr(cores, "border", "oklch(25% 0.02 250)")
    )

    # Open Design: instrucoes de componentes e layout — vai pro SYSTEM prompt (régua)
    _od_system_block = ""
    try:
        _od_segmento = getattr(prd, "segmento", "") or getattr(prd, "nicho", "") or ""
        _od_nome = prd.business_name or ""
        _od_tier = getattr(prd, "tier", "STANDARD") or "STANDARD"
        _od_ref = get_open_design_for_liam(_od_segmento, _od_nome, _od_tier)
        if _od_ref:
            _od_system_block = _od_ref
    except Exception:
        pass

    _faq = getattr(prd, 'faq_questions', []) or []
    _value_props = getattr(prd, 'value_props', []) or []
    if _faq:
        contexto_global += nl + 'FAQ DO NICHO (use para criar secao FAQ ou responder duvidas no copy): ' + ' | '.join(_faq[:6])
    if _value_props:
        contexto_global += nl + 'DIFERENCIAIS QUE CONVERTEM (use no hero e CTAs): ' + ' | '.join(_value_props[:4])
    if _anim_ctx:
        contexto_global += nl + _anim_ctx

    reviews_fmt = ""
    if reviews:
        reviews_fmt = nl.join([
            "- \"" + r.get("texto", r.get("text", "")) + "\" - " + r.get("autor", r.get("author", "Cliente"))
            for r in reviews[:8]
        ])

    html_final = ""
    secoes_processadas = 0

    if not prd.sections:
        raise RuntimeError("[Liam] PRD chegou sem sections — ArquitetoMestre deve garantir sections validas")

    _secoes_fonte = prd.sections

    _ckpt_slug_val = _ckpt_slug(prd.business_name)

    # Se tem reflection_context, limpar checkpoint (forçar regeneração completa)
    _has_reflection = getattr(prd, "reflection_context", None)
    if not _has_reflection and isinstance(prd, dict):
        _has_reflection = prd.get("reflection_context")
    if _has_reflection:
        _ckpt_clear(_ckpt_slug_val)
        _secoes_prontas = {}
        print("[Liam] REFLECTION MODE — checkpoint limpo, regenerando todas as seções")
    else:
        _secoes_prontas = _ckpt_load(_ckpt_slug_val)

    print("[Liam] Iniciando geracao componente por componente para " + prd.business_name + "...")
    print("[Liam] Instrucao do Diretor: " + instrucao_diretor[:80] + "...")
    if _secoes_prontas:
        print("[Liam] Retomando de checkpoint: " + str(list(_secoes_prontas.keys())))

  
    for _s_prev in _secoes_fonte:
        _sd = _s_prev.dict() if hasattr(_s_prev, "dict") else (_s_prev if isinstance(_s_prev, dict) else {})
        _n = _sd.get("name", "")
        if _n and _n in _secoes_prontas:
            html_final += _secoes_prontas[_n]
            secoes_processadas += 1

    import json as _json

    # Hero layout — extraído do PRD para ficar disponível nas threads
    _dc_tokens = getattr(getattr(prd, "color_palette", None), "tokens_oklch", None) or {}
    _hero_style_prd = getattr(getattr(prd, "color_palette", None), "hero_style", None) or {}
    _hero_layout = _hero_style_prd.get("layout") or (_dc_tokens.get("hero_style") or {}).get("layout", "hero-split")
    _hero_overlay = _hero_style_prd.get("overlay") or (_dc_tokens.get("hero_style") or {}).get("overlay", "rgba(0,0,0,0.55)")
    _hero_img_style = _hero_style_prd.get("img_style") or (_dc_tokens.get("hero_style") or {}).get("img_style", "object-fit:cover;")

    import threading

    _liam_model = "opus"
    _thread_local = threading.local()

    # Pré-calcular ritmo visual: alternar fundos para evitar seções adjacentes iguais
    _section_names = [s.get("name", "") if isinstance(s, dict) else getattr(s, "name", "") for s in prd.sections]
    _rhythm_map = {}
    for _idx, _sn in enumerate(_section_names):
        if _idx % 2 == 0:
            _rhythm_map[_sn] = "FUNDO: var(--bg). Contraste com seção seguinte que usa var(--surface)."
        else:
            _rhythm_map[_sn] = "FUNDO: var(--surface). Contraste com seção anterior que usa var(--bg)."
        if _sn.lower() == "hero":
            _rhythm_map[_sn] = "FUNDO: imagem com overlay escuro. Texto BRANCO (text-white permitido). Próxima seção usa var(--bg)."

    def _gerar_secao(s):
        """Gera uma secao individual."""
        s_dict = s.dict() if hasattr(s, "dict") else (s if isinstance(s, dict) else {})
        nome_s = s_dict.get("name", "")
        tipo_layout = s_dict.get("layout_type", "padrao")
        # Hero: usar layout do design_context (determinístico por nicho)
        if nome_s.lower() == "hero" and _hero_layout:
            tipo_layout = _hero_layout
        copy_s = s_dict.get("copy", {}) or {}
        omitir_s = s_dict.get("omitir", False)

        if not nome_s or omitir_s or nome_s.lower() == "footer":
            if omitir_s and nome_s:
                print("[Liam] Omitindo secao: " + nome_s)
            if nome_s and nome_s.lower() == "footer":
                print("[Liam] Secao footer omitida — rodape gerado pelo template")
            return nome_s, None

        # Pular secoes ja no checkpoint
        if nome_s in _secoes_prontas:
            print("[Liam] " + nome_s + ": ja no checkpoint, pulando")
            return nome_s, _secoes_prontas[nome_s]

        # Reviews para secao depoimentos — OBRIGATÓRIO ter reviews reais
        reviews_instrucao = ""
        if nome_s.lower() in ("depoimentos", "reviews", "testimonials", "avaliacoes"):
            if reviews and reviews_fmt and len(reviews_fmt) > 20:
                reviews_instrucao = nl + "REVIEWS REAIS (use exatamente, sem inventar):" + nl + reviews_fmt
            else:
                # Sem reviews reais = pular seção (não fabricar)
                print("[Liam] Secao depoimentos: sem reviews reais (reviews=" + str(len(reviews)) + ") — PULANDO secao")
                return nome_s, None

        copy_json = _json.dumps(copy_s, ensure_ascii=False)[:500]
        maps_instrucao = ""
        if nome_s == "localizacao" and maps_embed:
            maps_instrucao = nl + "GOOGLE MAPS EMBED (incorpore INTEGRALMENTE dentro da section):" + nl + maps_embed

        # System prompt fixo — cacheado pela Anthropic a partir da 2a chamada (mesmo texto em todas as secoes)
        system_liam = SYSTEM_LIAM_CORE + nl + _od_system_block + nl + SYSTEM_LIAM_ANTI_SLOP

        # User prompt variavel — muda por secao (dados do negocio + copy especifico)
        _rhythm_hint = _rhythm_map.get(nome_s, "")
        _ctx_rhythm = ""
        if _rhythm_hint:
            _ctx_rhythm = "RITMO VISUAL (OBRIGATORIO seguir): " + _rhythm_hint + nl + nl

        # VARIANTE DE LAYOUT — hash do nome seleciona variante diferente por seção
        # Garante que 3 leads do mesmo nicho/cidade NÃO saem iguais
        import hashlib as _hl
        _hash_val = int(_hl.md5((prd.business_name + "|" + nome_s + "|fralib").encode()).hexdigest()[:8], 16)
        _layout_variants = {
            "hero": [
                "LAYOUT HERO: Split 60/40 (texto esquerda, foto direita). Foto com gradient fade lateral.",
                "LAYOUT HERO: Fullscreen foto com overlay escuro. Texto centralizado sobre a imagem. CTA grande.",
                "LAYOUT HERO: Texto centralizado sem foto. Background com mesh-glow sutil. Tipografia dominante.",
                "LAYOUT HERO: Assimétrico — texto 70% esquerda com foto pequena flutuante no canto. Muito whitespace.",
            ],
            "sobre": [
                "LAYOUT SOBRE: Grid 2 colunas — foto esquerda (aspect 3/4), texto direita com stats.",
                "LAYOUT SOBRE: Foto full-width no topo (aspect 16/9), texto abaixo em 2 colunas.",
                "LAYOUT SOBRE: Timeline vertical com marcos do negócio. Sem foto grande.",
                "LAYOUT SOBRE: Texto grande centralizado (editorial). Foto pequena circular ao lado do nome.",
            ],
            "servicos": [
                "LAYOUT SERVICOS: Grid 3 colunas com cards. Ícone + título + descrição.",
                "LAYOUT SERVICOS: Bento grid assimétrico (1 card grande + 2 pequenos). Hover com lift.",
                "LAYOUT SERVICOS: Lista vertical com ícone à esquerda e descrição à direita. Separadores sutis.",
                "LAYOUT SERVICOS: Grid 2 colunas com foto em cada card. Cards com gradient-border.",
            ],
            "depoimentos": [
                "LAYOUT DEPOIMENTOS: Cards em grid 3 colunas. Aspas grandes. Nome + estrelas.",
                "LAYOUT DEPOIMENTOS: Um depoimento destaque grande (full-width quote) + 2 menores abaixo em grid.",
                "LAYOUT DEPOIMENTOS: Carousel/slider horizontal (use classe swiper). Um depoimento por vez com foto.",
                "LAYOUT DEPOIMENTOS: Quote wall — todos os depoimentos em masonry grid com tamanhos variados.",
                "LAYOUT DEPOIMENTOS: Lista vertical simples. Cada review com borda-left accent. Minimalista.",
                "LAYOUT DEPOIMENTOS: Cards horizontais (foto + texto lado a lado). 2 por linha.",
            ],
        }
        _section_key = nome_s.lower()
        _variant_hint = ""
        if _section_key in _layout_variants:
            _variants = _layout_variants[_section_key]
            _variant_hint = _variants[_hash_val % len(_variants)] + nl + nl

        prompt_secao = (
            _ctx_rhythm
            + _variant_hint
            + "ORDEM DO DIRETOR DE ARTE:" + nl
            + instrucao_diretor + nl
            + nl
            + "SECAO A GERAR: <section id=\"" + nome_s + "\"> usando layout: " + tipo_layout + nl
            + (("HERO OVERLAY: " + _hero_overlay + " | IMG STYLE: " + _hero_img_style + nl) if nome_s.lower() == "hero" else "")
            + nl
            + "DADOS DO NEGOCIO:" + nl + contexto_global + nl
            + nl
            + "COPY DESTA SECAO (use exatamente):" + nl + copy_json
            + reviews_instrucao
        )
        # Foto obrigatoria por secao
        if fotos:
            _foto_map = {"hero": 0, "sobre": 1, "servicos": 2, "localizacao": 3}
            _foto_idx = _foto_map.get(nome_s.lower(), -1)
            if _foto_idx >= 0 and _foto_idx < len(fotos):
                _foto_url = fotos[_foto_idx]
                if nome_s.lower() == "hero":
                    prompt_secao += nl + "FOTO HERO (OBRIGATORIO usar como background-image com overlay escuro ou como img no lado direito do split):" + nl + _foto_url
                else:
                    prompt_secao += nl + "FOTO DESTA SECAO (OBRIGATORIO incluir como <img> com object-fit:cover, rounded, aspect-ratio adequado):" + nl + _foto_url

        if maps_instrucao:
            prompt_secao += maps_instrucao

        # ── REFLECTION: injetar feedback da Liz se disponível ──
        _reflection = getattr(prd, "reflection_context", None)
        if not _reflection and isinstance(prd, dict):
            _reflection = prd.get("reflection_context")
        if _reflection:
            prompt_secao += nl + nl + _reflection

        print("[Liam] Gerando " + nome_s + " (layout: " + tipo_layout + ")...")
        try:
            resposta_secao = call_claude(
                system=system_liam,
                user=prompt_secao,
                model=getattr(_thread_local, 'model', _liam_model),
                max_tokens=8000,
                temperature=0.4,
                agent_name=None,
            )
            # Auto-Continue: se secao truncada, continuar de onde parou
            _auto_continue = 0
            while "</section>" not in resposta_secao[-500:].lower() and _auto_continue < 2:
                _auto_continue += 1
                print("[Liam] " + nome_s + ": truncada — auto-continue " + str(_auto_continue) + "/2")
                _continua = call_claude(
                    system="Voce e um gerador de codigo HTML continuo. Continue EXATAMENTE de onde o codigo anterior parou.",
                    user="Secao: " + nome_s + " | Negocio: " + prd.business_name + ". O codigo HTML foi cortado. Continue EXATAMENTE de onde parou. Nao repita codigo anterior. Apenas continue o HTML ate fechar </section>.",
                    model="sonnet",
                    max_tokens=4000,
                    temperature=0.1,
                    agent_name=None,
                )
                _continua = _continua.replace("```html", "").replace("```", "").strip()
                if not _continua:
                    print("[Liam] " + nome_s + ": auto-continue retornou vazio — forcando fechamento")
                    resposta_secao += nl + "</section>"
                    break
                resposta_secao += nl + _continua
            # Limpeza do raw text
            resposta_secao = resposta_secao.replace("```html", "").replace("```", "").strip()
            _fs = resposta_secao.lower().find("<section")
            if _fs > 0:
                resposta_secao = resposta_secao[_fs:]
            _ls = resposta_secao.lower().rfind("</section>")
            if _ls > 0:
                resposta_secao = resposta_secao[:_ls + len("</section>")]
            resposta_secao = _re_sp.sub(r"(?i)<!DOCTYPE[^>]*>", "", resposta_secao)
            resposta_secao = _re_sp.sub(r"(?i)<html[^>]*>|</html>", "", resposta_secao)
            resposta_secao = _re_sp.sub(r"(?i)<head[^>]*>.*?</head>", "", resposta_secao, flags=_re_sp.DOTALL)
            resposta_secao = _re_sp.sub(r"(?i)<body[^>]*>|</body>", "", resposta_secao)
            resposta_secao = resposta_secao.strip()

            if resposta_secao and len(resposta_secao) > 50:
                if not resposta_secao.lower().rstrip().endswith("</section>"):
                    print("[Liam] " + nome_s + ": secao nao fechada — forcando </section>")
                    resposta_secao = resposta_secao.rstrip() + nl + "</section>"
                # Validar integridade: seção deve ter abertura E fechamento
                _has_open = "<section" in resposta_secao.lower()
                _has_close = "</section>" in resposta_secao.lower()
                if not _has_open or not _has_close:
                    print("[Liam] " + nome_s + ": HTML invalido (sem tags section) — descartando")
                    return nome_s, None
                # Constitutional AI: auto-crítica + auto-revisão (PRD #5)
                try:
                    from liam_constitutional import constitutional_pass
                    resposta_secao = constitutional_pass(resposta_secao, nome_s, str(cores)[:500] if cores else "")
                except Exception as _const_err:
                    print(f"[CONSTITUTIONAL] Erro (não bloqueante): {_const_err}")
                # Managed Agent: validar e corrigir seção antes de aceitar
                if _LIAM_AGENT_LOOP:
                    from liam_agent_loop import validate_and_fix_section
                    resposta_secao, _was_fixed, _val_result = validate_and_fix_section(
                        resposta_secao, nome_s, _seo_keywords[:5]
                    )
                _bloco_html = ("<!-- SECTION:" + nome_s + " -->" + nl
                    + resposta_secao + nl
                    + "<!-- /SECTION:" + nome_s + " -->" + nl + nl)
                if nome_s not in _secoes_prontas:
                    _secoes_prontas[nome_s] = _bloco_html
                    _ckpt_save(_ckpt_slug_val, _secoes_prontas)
                print("[Liam] " + nome_s + ": " + str(len(resposta_secao)) + " chars OK")
                return nome_s, _bloco_html
            else:
                print("[Liam] " + nome_s + ": resposta vazia, pulando")
                return nome_s, None
        except Exception as _e:
            print("[Liam] Erro " + nome_s + ": " + str(_e)[:80])
            return nome_s, None

    # Executar secoes em PARALELO com rate limit (max 3 concurrent)
    import gc
    import time as _time_liam
    from concurrent.futures import ThreadPoolExecutor, as_completed

    _rate_semaphore = threading.Semaphore(3)
    _rate_delay = 1.0  # segundos entre submits pra evitar 429

    def _gerar_com_retry(s_item):
        """Gera seção com retry e escalação pra Opus."""
        _sd = s_item.dict() if hasattr(s_item, "dict") else (s_item if isinstance(s_item, dict) else {})
        _nome = _sd.get("name", "")
        _max_retries = 3
        for _retry in range(_max_retries):
            try:
                with _rate_semaphore:
                    if _retry >= 1:
                        _thread_local.model = "opus"
                        print(f"[Liam] {_nome}: escalando para Opus (retry {_retry})")
                    else:
                        _thread_local.model = "sonnet"
                    _nome_r, _html_r = _gerar_secao(s_item)
                if _html_r:
                    return _nome_r, _html_r
                if _retry < _max_retries - 1:
                    print(f"[Liam] {_nome}: retry {_retry + 1}/{_max_retries} (resposta vazia)")
                    _time_liam.sleep(2)
            except Exception as _fe:
                print("[Liam] Erro na secao " + _nome + ": " + str(_fe)[:80])
                if _retry < _max_retries - 1:
                    _time_liam.sleep(2)
            finally:
                gc.collect()
        return _nome, None

    print("[Liam] Iniciando geracao PARALELA de " + str(len(_secoes_fonte)) + " secoes (max 3 concurrent)...")
    with ThreadPoolExecutor(max_workers=3) as _executor:
        _futures = []
        for _s_par in _secoes_fonte:
            _futures.append(_executor.submit(_gerar_com_retry, _s_par))
            _time_liam.sleep(_rate_delay)
        for _fut in as_completed(_futures):
            try:
                _fut.result()
            except Exception as _e:
                print(f"[Liam] Thread erro: {str(_e)[:80]}")

    # Montar html_final na ORDEM ORIGINAL do PRD
    html_final = ""  # Reset — evitar duplicação com pre-populate do checkpoint
    secoes_processadas = 0
    for _s_ord in _secoes_fonte:
        _sd = _s_ord.dict() if hasattr(_s_ord, "dict") else (_s_ord if isinstance(_s_ord, dict) else {})
        _n = _sd.get("name", "")
        if _n and _n in _secoes_prontas:
            html_final += _secoes_prontas[_n]
            secoes_processadas += 1

    print("[Liam] Componentizado: " + str(secoes_processadas) + " secoes, " + str(len(html_final)) + " chars total")
    html_final = _sanitizar_contadores_zerados(html_final)
    print("[Liam] Contadores zerados sanitizados")
    html_final = _sanitizar_fontes(html_final)
    print("[Liam] Fontes sanitizadas")
    html_final = _sanitizar_cores_light(html_final)
    print("[Liam] Cores light sanitizadas")
    html_final = _sanitizar_botoes_contraste(html_final)
    print("[Liam] Botoes contraste sanitizados")
    html_final = _sanitizar_css_var_bug(html_final)
    print("[Liam] CSS var bug sanitizado")
    html_final = _sanitizar_cores_hardcoded_texto(html_final)
    print("[Liam] Cores hardcoded texto sanitizadas")
    print("[Liam] Fotos externas sanitizadas")
    html_final = _sanitizar_hero_imagem(html_final, fotos)
    print("[Liam] Hero imagem injetada")
    html_final = _sanitizar_botoes(html_final, wnum)
    print("[Liam] Botoes sanitizados")
    html_final = _sanitizar_wpp_duplicado(html_final)
    print("[Liam] WPP duplicado sanitizado")
    _ckpt_clear(_ckpt_slug_val)  # Limpar checkpoint apos conclusao bem-sucedida
    # Injetar micro-decisão como comentário HTML pra critique_theater_pass ler
    _micro_tag = f'<!-- fralib-micro intensity="{_intensity}" density="{_density}" photo="{_photo_treatment}" motion="{_micro_decision.get("motion_style","balanced")}" -->'
    html_final = _micro_tag + "\n" + html_final.strip()
    return html_final


# Alias para compatibilidade com pipeline_endpoints.py
def gerar_html_main_single_pass(prd):
    return gerar_html_componentizado(prd)


def _extract_hue(oklch_value: str) -> str:
    """Extrai o hue de um valor oklch (ex: 'oklch(55% 0.2 25)' → '25')."""
    import re as _re_hue
    m = _re_hue.search(r'oklch\([^)]*\s+([\d.]+)\s*\)', oklch_value)
    if m:
        return m.group(1)
    return "240"  # fallback azul neutro


def _nav_cta_text(prd) -> str:
    """Retorna texto do CTA do nav baseado no sub-nicho ou segmento."""
    _sub = getattr(prd, "sub_nicho", {}) or {}
    if isinstance(_sub, dict) and _sub.get("cta"):
        # Encurtar pra caber no nav (max 15 chars)
        cta = _sub["cta"]
        if len(cta) > 18:
            cta = cta.split()[0] + " " + cta.split()[-1] if len(cta.split()) > 2 else cta[:15]
        return cta
    _seg = (getattr(prd, "segmento", "") or "").lower()
    _cta_map = {
        "academia": "Agendar aula",
        "restaurante": "Reservar",
        "clinica": "Agendar",
        "estetica": "Agendar",
        "advogado": "Consulta",
        "barbearia": "Agendar",
        "nutricionista": "Agendar",
        "dentista": "Agendar",
        "psicologo": "Agendar",
        "pizzaria": "Pedir agora",
        "delivery": "Pedir agora",
    }
    return _cta_map.get(_seg, "Fale conosco")


def _gerar_seo_inline(prd) -> str:
    """Gera meta tags SEO determinísticas a partir do PRD."""
    import unicodedata as _ud, re as _re, json as _json
    nome = getattr(prd, "business_name", "") or ""
    cidade = getattr(prd, "cidade", "") or ""
    segmento = getattr(prd, "segmento", "") or ""
    telefone = getattr(prd, "phone", "") or ""
    rating = getattr(prd, "rating", 0) or getattr(prd, "reviews_rating", 0) or 0
    fotos = getattr(prd, "photos", []) or []
    address = getattr(prd, "address", "") or ""
    geo = getattr(prd, "geo", None)
    hours = getattr(prd, "hours", None) or {}
    # Usar logo local se disponível, senão primeira foto
    logo_url = getattr(prd, "logo_url", "") or ""
    _slug_tmp = _re.sub(r"[^a-z0-9]+", "-", _ud.normalize("NFKD", nome.lower()).encode("ascii","ignore").decode()).strip("-")[:50]
    if logo_url and logo_url.startswith("/sites/"):
        image_url = f"https://seunegociofralib.site{logo_url}"
    elif fotos:
        image_url = fotos[0] if fotos[0].startswith("http") else f"https://seunegociofralib.site{fotos[0]}"
    else:
        image_url = f"https://seunegociofralib.site/sites/{_slug_tmp}/assets/logo.svg"
    # Keywords SEO reais do Google Suggest
    keywords = getattr(prd, "seo_keywords", []) or []
    if not keywords:
        keywords = [segmento, f"{segmento} {cidade}", f"melhor {segmento} {cidade}"]
    keywords_str = ", ".join(keywords[:8])
    # Schema type dinâmico baseado no segmento
    schema_type = _get_schema_type(segmento)
    # Extrair estado do endereço (ex: "Rua X, 123 - PR" ou "Curitiba - PR 80000-000")
    address_region = ""
    if address:
        _state_m = _re.search(r'[-,]\s*([A-Z]{2})\b', address)
        if _state_m:
            address_region = _state_m.group(1)
    if not address_region:
        _city_state = {
            "sao paulo": "SP", "rio de janeiro": "RJ", "belo horizonte": "MG",
            "salvador": "BA", "fortaleza": "CE", "curitiba": "PR",
            "manaus": "AM", "recife": "PE", "porto alegre": "RS",
            "belem": "PA", "goiania": "GO", "florianopolis": "SC",
            "maceio": "AL", "natal": "RN", "teresina": "PI",
            "campo grande": "MS", "joao pessoa": "PB", "aracaju": "SE",
            "vitoria": "ES", "cuiaba": "MT", "rio branco": "AC",
        }
        _cidade_lower = cidade.lower()
        for _city, _state in _city_state.items():
            if _city in _cidade_lower:
                address_region = _state
                break
    reviews_count = getattr(prd, "reviews_count", 0) or 0
    desc = f"{segmento.capitalize()} em {cidade} — {nome}. {keywords[1] if len(keywords)>1 else segmento+' de qualidade'}. Atendimento personalizado e resultados reais."
    slug = _re.sub(r"[^a-z0-9]+", "-", _ud.normalize("NFKD", nome.lower()).encode("ascii", "ignore").decode()).strip("-")[:50]
    canonical = f"https://seunegociofralib.site/sites/{slug}/"
    wnum = telefone.replace(" ","").replace("-","").replace("(","").replace(")","")
    # Build address object
    _addr_obj = {"@type": "PostalAddress", "addressLocality": cidade, "addressCountry": "BR"}
    if address:
        _addr_obj["streetAddress"] = address
    if address_region:
        _addr_obj["addressRegion"] = address_region
    # Build openingHoursSpecification
    _day_map = {
        "seg": "Monday", "ter": "Tuesday", "qua": "Wednesday",
        "qui": "Thursday", "sex": "Friday", "sab": "Saturday", "dom": "Sunday",
        "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday",
        "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
    }
    def _parse_time(t):
        t = t.strip().lower().replace("h", ":").replace(".", ":")
        parts = t.split(":")
        h = parts[0].zfill(2)
        m = parts[1].zfill(2) if len(parts) > 1 else "00"
        return f"{h}:{m}"
    if hours:
        _ohs = []
        for _period, _time_range in hours.items():
            _days_raw = _period.lower().replace(" ", "").split("-")
            _days_en = [_day_map.get(d[:3], d.capitalize()) for d in _days_raw]
            _times = _re.split(r"[-–]", _time_range)
            if len(_times) == 2:
                _ohs.append({
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": _days_en,
                    "opens": _parse_time(_times[0]),
                    "closes": _parse_time(_times[1]),
                })
        opening_hours = _ohs if _ohs else []
    else:
        opening_hours = []
    # Build main schema object
    _schema_obj = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": nome,
        "description": desc,
        "url": canonical,
        "telephone": telefone,
        "image": image_url,
        "address": _addr_obj,
    }
    if opening_hours:
        _schema_obj["openingHoursSpecification"] = opening_hours
    _schema_obj["hasMap"] = f"https://www.google.com/maps/search/{_re.sub(r'[^a-z0-9]+', '+', nome.lower())}+{_re.sub(r'[^a-z0-9]+', '+', cidade.lower())}"
    if rating and float(rating) > 0 and reviews_count > 0:
        _schema_obj["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(rating),
            "reviewCount": str(reviews_count),
            "bestRating": "5",
            "worstRating": "1",
        }
    if geo and isinstance(geo, dict):
        _lat = geo.get("lat") or geo.get("latitude")
        _lng = geo.get("lng") or geo.get("longitude")
        if _lat is not None and _lng is not None:
            _schema_obj["geo"] = {"@type": "GeoCoordinates", "latitude": _lat, "longitude": _lng}
    # Speakable schema
    _speakable = {
        "@context": "https://schema.org",
        "@type": "SpeakableSpecification",
        "cssSelector": ["h1", "h2", ".speakable"],
    }
    # WebSite schema with SearchAction
    _website_schema = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": nome,
        "url": canonical,
        "potentialAction": {
            "@type": "SearchAction",
            "target": f"{canonical}?q={{search_term_string}}",
            "query-input": "required name=search_term_string",
        },
    }
    schema_json = _json.dumps(_schema_obj, ensure_ascii=False)
    speakable_json = _json.dumps(_speakable, ensure_ascii=False)
    website_json = _json.dumps(_website_schema, ensure_ascii=False)
    # FAQPage schema — critical for AI Overviews and Google SGE
    extra_schemas = ""
    faq_questions = getattr(prd, 'faq_questions', []) or []
    if faq_questions:
        faq_entities = []
        for q in faq_questions[:8]:
            faq_entities.append({
                '@type': 'Question',
                'name': q,
                'acceptedAnswer': {
                    '@type': 'Answer',
                    'text': nome + ' em ' + cidade + '. Entre em contato para mais informacoes: ' + telefone
                }
            })
        faq_schema = {
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            'mainEntity': faq_entities
        }
        extra_schemas += '<script type="application/ld+json">' + _json.dumps(faq_schema, ensure_ascii=False) + '</script>'
    return (
        f'''<link rel="icon" type="image/x-icon" href="https://fralib.com.br/favicon.ico">
<meta name="description" content="{desc}">
<meta name="keywords" content="{keywords_str}">
<meta name="robots" content="index, follow">
<meta property="og:title" content="{nome} — {segmento.capitalize()} em {cidade}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{image_url}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{nome} — {segmento.capitalize()} em {cidade}">
<meta name="twitter:description" content="{desc}">
<link rel="canonical" href="{canonical}">
<script type="application/ld+json">{schema_json}</script>
<script type="application/ld+json">{speakable_json}</script>
<script type="application/ld+json">{website_json}</script>''' + extra_schemas
    )


def _gerar_lgpd_banner(prd) -> str:
    """Banner LGPD com consentimento de cookies — determinístico."""
    return """<div id="lgpd-banner" style="display:none;position:fixed;bottom:0;left:0;right:0;z-index:9999;background:var(--color-surface);border-top:1px solid var(--color-border);padding:16px 24px;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;box-shadow:0 -4px 24px rgba(0,0,0,0.15);">
  <p style="margin:0;font-size:0.8rem;color:var(--color-muted);max-width:700px;">
    Usamos cookies para melhorar sua experiência. Ao continuar navegando, você concorda com nossa
    <a href="/politica-de-privacidade" style="color:var(--color-accent);text-decoration:underline;">Política de Privacidade</a>
    conforme a LGPD (Lei 13.709/2018).
  </p>
  <button onclick="aceitarLGPD()" style="background:var(--color-accent);color:#fff;border:none;border-radius:8px;padding:10px 24px;font-size:0.85rem;font-weight:600;cursor:pointer;white-space:nowrap;">
    Aceitar e continuar
  </button>
</div>
<script>
(function(){
  if(!localStorage.getItem('lgpd_aceito')){
    var b=document.getElementById('lgpd-banner');
    if(b) b.style.display='flex';
  }
})();
function aceitarLGPD(){
  localStorage.setItem('lgpd_aceito','1');
  var b=document.getElementById('lgpd-banner');
  if(b) b.style.display='none';
}
</script>"""


def _gerar_wpp_float(prd) -> str:
    """Botão WhatsApp flutuante — determinístico."""
    telefone = getattr(prd, "phone", "") or ""
    wnum = telefone.replace(" ","").replace("-","").replace("(","").replace(")","")
    if not wnum:
        return ""
    wpp_url = f"https://wa.me/55{wnum}"
    return f'''<a href="{wpp_url}" target="_blank" rel="noopener"
   style="position:fixed;bottom:24px;right:24px;z-index:9998;display:flex;align-items:center;gap:8px;padding:12px 20px;border-radius:999px;background:linear-gradient(135deg,#25D366,#128C7E);color:#fff;font-weight:600;font-size:0.9rem;text-decoration:none;box-shadow:0 8px 32px rgba(37,211,102,0.4);transition:transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
  <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/></svg>
  WhatsApp
</a>'''

def _sanitizar_wpp_duplicado(html):
    """Remove botoes WPP flutuantes duplicados — mantém só o primeiro position:fixed com wa.me."""
    import re as _re
    # Encontrar todos os elementos <a> com position:fixed e wa.me
    pat = r'<a[^>]+(?:position\s*:\s*fixed|class="[^"]*fixed[^"]*")[^>]*wa\.me[^>]*>.*?</a>'
    matches = list(_re.finditer(pat, html, _re.DOTALL))
    if len(matches) <= 1:
        return html
    # Manter o primeiro, remover os demais
    for m in reversed(matches[1:]):
        html = html[:m.start()] + html[m.end():]
    return html


def _gerar_nav_links(prd, q: str) -> str:
    """Gera links de navegação dinamicamente a partir das seções reais do PRD."""
    # Mapa de nome de seção → label legível
    _labels = {
        'sobre': 'Sobre', 'servicos': 'Serviços', 'depoimentos': 'Depoimentos',
        'localizacao': 'Localização', 'contato': 'Contato', 'planos': 'Planos',
        'galeria': 'Galeria', 'equipe': 'Equipe', 'faq': 'FAQ',
    }
    _excluir = {'hero', 'footer', 'lgpd', 'header'}
    links = ''
    try:
        secoes = getattr(prd, 'sections', []) or []
        vistos = set()
        for s in secoes:
            nome_s = (s.get('name', '') if isinstance(s, dict) else getattr(s, 'name', '')).lower()
            omitir = (s.get('omitir', False) if isinstance(s, dict) else getattr(s, 'omitir', False))
            if not nome_s or nome_s in _excluir or omitir or nome_s in vistos:
                continue
            vistos.add(nome_s)
            label = _labels.get(nome_s, nome_s.capitalize())
            links += ('      <a href=' + q + '#' + nome_s + q
                + ' class=' + q + 'hover:text-current transition-colors' + q
                + ' style=' + q + 'color:var(--color-muted)' + q
                + '>' + label + '</a>' + chr(10))
    except Exception:
        # Fallback para links fixos se PRD não tiver sections
        for anchor, label in [('sobre','Sobre'),('servicos','Serviços'),('depoimentos','Depoimentos'),('localizacao','Localização')]:
            links += ('      <a href=' + q + '#' + anchor + q
                + ' class=' + q + 'hover:text-current transition-colors' + q
                + ' style=' + q + 'color:var(--color-muted)' + q
                + '>' + label + '</a>' + chr(10))
    return links


def _escurecer_cor(hex_color: str, fator: float = 0.15) -> str:
    """Escurece uma cor hex multiplicando RGB pelo fator."""
    try:
        h = hex_color.lstrip('#')
        r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        r2, g2, b2 = int(r*fator), int(g*fator), int(b*fator)
        return '#{:02x}{:02x}{:02x}'.format(r2, g2, b2)
    except:
        return '#080810'


def _clarear_cor(hex_color: str, mix: float = 0.12) -> str:
    """Mistura a cor com branco (mix=0.12 → 12% da cor + 88% branco). Gera tint claro para light mode."""
    try:
        h = hex_color.lstrip('#')
        r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        r2 = int(r * mix + 255 * (1 - mix))
        g2 = int(g * mix + 255 * (1 - mix))
        b2 = int(b * mix + 255 * (1 - mix))
        return '#{:02x}{:02x}{:02x}'.format(r2, g2, b2)
    except:
        return '#f0f4ff'


def _gerar_pixel_tracking() -> str:
    """PR15: pixel de tracking. __FRALIB_LEAD_ID__ e substituido no deploy."""
    return (
        '<script>'
        '(function(){var L="__FRALIB_LEAD_ID__";if(!L||L.indexOf("FRALIB")>=0)return;'
        'var O="https://seunegociofralib.site";'
        'var p=function(u,b){try{fetch(O+u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b),keepalive:true});}catch(e){}};'
        'window.addEventListener("load",function(){p("/api/track/view",{lead_id:L});});'
        'document.addEventListener("click",function(e){var a=e.target.closest&&e.target.closest("a");if(!a)return;'
        'var h=a.getAttribute("href")||"";if(/wa\\.me\\/|api\\.whatsapp\\.com/.test(h))p("/api/track/click",{lead_id:L,tipo:"wa"});'
        'else if(/^tel:/i.test(h))p("/api/track/click",{lead_id:L,tipo:"tel"});},true);})();'
        '</script>'
    )


def _gerar_logo_svg(nome: str, segmento: str) -> str:
    """Gera logo SVG via haiku — ícone minimalista baseado no negócio."""
    try:
        from llm_direct import call_claude
        _prompt = (
            f"Gere um SVG inline minimalista para logo de: {nome} (segmento: {segmento}).\n\n"
            f"REGRAS ABSOLUTAS:\n"
            f"- Retorne APENAS o <svg>...</svg>, nada mais\n"
            f"- viewBox='0 0 40 40', width=40 height=40\n"
            f"- Use APENAS fill='currentColor' ou stroke='currentColor' (herda cor do site)\n"
            f"- Máximo 3 elementos (path/circle/rect)\n"
            f"- Estilo: geométrico, clean, profissional\n"
            f"- Sem texto dentro do SVG\n"
            f"- Represente visualmente o segmento/negócio de forma abstrata"
        )
        _svg = call_claude(
            system="Você é um designer de ícones SVG minimalistas. Retorne APENAS código SVG, sem explicação.",
            user=_prompt,
            model="haiku",
            max_tokens=200,
            temperature=0.3,
        )
        _svg = _svg.strip()
        if _svg.startswith("<svg") and _svg.endswith("</svg>"):
            return '<div class="h-10 w-10 flex items-center justify-center" style="color:var(--accent)">' + _svg + '</div>'
    except Exception as _e:
        print(f"[Liam] Logo SVG fallback: {_e}")

    # Fallback: texto bold estilizado (não bolinha)
    _initials = "".join([w[0].upper() for w in nome.split()[:2]])
    return (
        '<span style="font-family:var(--font-heading,inherit);font-weight:700;font-size:1.25rem;'
        'letter-spacing:-0.02em;color:var(--fg);">' + _initials + '</span>'
    )


def _gerar_whatsapp_float(whatsapp_url: str) -> str:
    """Botão WhatsApp flutuante — canto inferior direito, pulse animation."""
    return (
        '<a href="' + whatsapp_url + '" target="_blank" rel="noopener" '
        'id="wpp-float" '
        'style="position:fixed;bottom:24px;right:24px;z-index:900;width:56px;height:56px;'
        'background:#25D366;border-radius:50%;display:flex;align-items:center;justify-content:center;'
        'box-shadow:0 4px 12px rgba(37,211,102,0.4);transition:transform 0.2s,box-shadow 0.2s;'
        'animation:wpp-pulse 2s infinite;" '
        'aria-label="Falar no WhatsApp">'
        '<svg width="28" height="28" viewBox="0 0 24 24" fill="white">'
        '<path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>'
        '<path d="M12 2C6.477 2 2 6.477 2 12c0 1.89.525 3.66 1.438 5.168L2 22l4.832-1.438A9.955 9.955 0 0012 22c5.523 0 10-4.477 10-10S17.523 2 12 2zm0 18a8 8 0 01-4.243-1.214l-.252-.149-2.868.852.852-2.868-.149-.252A8 8 0 1112 20z"/>'
        '</svg></a>'
        '<style>@keyframes wpp-pulse{0%,100%{box-shadow:0 4px 12px rgba(37,211,102,0.4)}50%{box-shadow:0 4px 24px rgba(37,211,102,0.7)}}'
        '#wpp-float:hover{transform:scale(1.1);box-shadow:0 6px 20px rgba(37,211,102,0.6)}</style>'
    )


def _gerar_cta_mobile(whatsapp_url: str, nome: str) -> str:
    """Barra CTA fixa no mobile — aparece ao scrollar, some no topo."""
    return (
        '<div id="cta-mobile" style="position:fixed;bottom:0;left:0;right:0;z-index:800;'
        'background:var(--color-footer-bg,#111);padding:12px 16px;display:none;'
        'align-items:center;justify-content:space-between;gap:12px;'
        'border-top:1px solid var(--border,rgba(255,255,255,0.1));backdrop-filter:blur(8px);">'
        '<span style="color:var(--color-footer-text,#eee);font-size:0.8rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + nome + '</span>'
        '<a href="' + whatsapp_url + '" target="_blank" rel="noopener" '
        'style="background:#25D366;color:#fff;padding:10px 18px;border-radius:8px;font-size:0.8rem;'
        'font-weight:700;text-decoration:none;white-space:nowrap;display:flex;align-items:center;gap:6px;">'
        '<i class="ph-fill ph-whatsapp-logo"></i>Chamar</a></div>'
        '<script>(function(){'
        'var cta=document.getElementById("cta-mobile");'
        'if(!cta||window.innerWidth>768)return;'
        'var wf=document.getElementById("wpp-float");'
        'window.addEventListener("scroll",function(){'
        'if(window.scrollY>400){cta.style.display="flex";if(wf)wf.style.display="none";}'
        'else{cta.style.display="none";if(wf)wf.style.display="flex";}'
        '},{passive:true});'
        '})();</script>'
    )


def _gerar_back_to_top() -> str:
    """Botão back-to-top — aparece após scroll, smooth scroll up."""
    return (
        '<button id="btt" aria-label="Voltar ao topo" '
        'style="position:fixed;bottom:90px;right:24px;z-index:850;width:40px;height:40px;'
        'border-radius:50%;background:var(--surface,#222);border:1px solid var(--border,#333);'
        'color:var(--fg,#fff);display:none;align-items:center;justify-content:center;'
        'cursor:pointer;transition:opacity 0.3s,transform 0.2s;opacity:0.7;font-size:1.1rem;" '
        'onclick="window.scrollTo({top:0,behavior:\'smooth\'})">'
        '<i class="ph ph-caret-up"></i></button>'
        '<script>(function(){'
        'var b=document.getElementById("btt");if(!b)return;'
        'window.addEventListener("scroll",function(){'
        'if(window.scrollY>600){b.style.display="flex";}else{b.style.display="none";}'
        '},{passive:true});'
        'b.addEventListener("mouseenter",function(){b.style.opacity="1";b.style.transform="translateY(-2px)";});'
        'b.addEventListener("mouseleave",function(){b.style.opacity="0.7";b.style.transform="translateY(0)";});'
        '})();</script>'
    )


def _gerar_stats_section(prd) -> str:
    """Seção de números/stats — social proof quantitativo. Injetada se tem dados."""
    _rating = getattr(prd, 'rating', 0) or getattr(prd, 'reviews_rating', 0) or 0
    _reviews = getattr(prd, 'reviews_list', []) or []
    _n_reviews = len(_reviews)
    _anos = getattr(prd, 'years_in_business', 0) or 0
    _fotos = getattr(prd, 'photos', []) or []

    # Precisa de pelo menos 2 stats pra mostrar
    stats = []
    if _rating >= 4.0:
        stats.append({"valor": str(_rating).replace('.', ','), "label": "Avalia&ccedil;&atilde;o Google", "suffix": "/5"})
    if _n_reviews >= 5:
        stats.append({"valor": str(_n_reviews), "label": "Avalia&ccedil;&otilde;es", "suffix": "+"})
    if _anos >= 2:
        stats.append({"valor": str(_anos), "label": "Anos de experi&ecirc;ncia", "suffix": ""})
    elif _anos == 0 and _n_reviews > 20:
        stats.append({"valor": str(_n_reviews * 8), "label": "Clientes atendidos", "suffix": "+"})

    if len(stats) < 2:
        return ""

    nl = chr(10)
    items = ""
    for i, s in enumerate(stats[:4]):
        items += (
            '<div class="text-center stagger-item" style="--i:' + str(i) + '">' + nl
            + '<p class="text-3xl md:text-5xl font-bold" style="color:var(--accent);" data-count="'
            + s["valor"].replace(",", ".").replace("+", "") + '">' + s["valor"] + s["suffix"] + '</p>' + nl
            + '<p class="text-sm mt-2" style="color:var(--muted);">' + s["label"] + '</p>' + nl
            + '</div>' + nl
        )
    return (
        '<section id="numeros" class="py-16 md:py-24" style="background-color:var(--bg);">' + nl
        + '<div class="max-w-4xl mx-auto px-4 md:px-8">' + nl
        + '<div class="grid grid-cols-2 md:grid-cols-' + str(min(len(stats), 4)) + ' gap-8 md:gap-12">' + nl
        + items
        + '</div></div></section>' + nl
    )


def _gerar_cta_final(prd, whatsapp_url: str) -> str:
    """Seção CTA final — última chamada pra ação antes do footer."""
    nome = getattr(prd, 'business_name', '') or ''
    _sub = getattr(prd, 'sub_nicho', {}) or {}
    _cta_text = "Fale conosco"
    if isinstance(_sub, dict) and _sub.get("cta"):
        _cta_text = _sub["cta"]
    else:
        _seg = (getattr(prd, "segmento", "") or "").lower()
        _map = {"academia": "Comece hoje", "restaurante": "Faça sua reserva",
                "clinica": "Agende sua consulta", "estetica": "Agende sua avaliação",
                "advogado": "Consulta gratuita", "barbearia": "Agende seu horário",
                "nutricionista": "Agende sua consulta", "pizzaria": "Peça agora"}
        _cta_text = _map.get(_seg, "Fale conosco")

    nl = chr(10)
    return (
        '<section id="cta-final" class="py-20 md:py-32 relative overflow-hidden" style="background-color:var(--accent);">' + nl
        + '<div class="max-w-3xl mx-auto px-4 md:px-8 text-center relative z-10">' + nl
        + '<h2 class="reveal text-2xl md:text-4xl font-bold text-white mb-4">Pronto para come&ccedil;ar?</h2>' + nl
        + '<p class="reveal text-white/80 text-lg mb-8 max-w-xl mx-auto">Entre em contato e descubra como podemos ajudar voc&ecirc;.</p>' + nl
        + '<a href="' + whatsapp_url + '" target="_blank" rel="noopener" '
        + 'class="reveal inline-flex items-center gap-3 px-8 py-4 rounded-full text-lg font-bold transition-transform hover:scale-105" '
        + 'style="background:white;color:var(--accent);">'
        + '<i class="ph-fill ph-whatsapp-logo text-xl"></i>' + _cta_text + '</a>' + nl
        + '</div>' + nl
        + '<div class="absolute inset-0 opacity-10" style="background:radial-gradient(circle at 30% 50%,white 0%,transparent 60%);"></div>' + nl
        + '</section>' + nl
    )


def _gerar_galeria_section(prd) -> str:
    """Seção galeria — grid de fotos do negócio. Injetada se tem 4+ fotos."""
    fotos = getattr(prd, 'photos', []) or []
    if len(fotos) < 4:
        return ""
    q = '"'
    nl = chr(10)
    # Usar até 8 fotos
    _fotos_use = fotos[:8]
    _n = len(_fotos_use)

    # Grid layout varia: masonry-like com spans diferentes
    items = ""
    for i, foto in enumerate(_fotos_use):
        url = foto if isinstance(foto, str) else foto.get("url", foto.get("src", ""))
        if not url:
            continue
        # Variar aspect ratio pra não ficar grid uniforme
        _aspects = ["aspect-square", "aspect-[4/3]", "aspect-[3/4]", "aspect-square"]
        _aspect = _aspects[i % len(_aspects)]
        # Primeira e quinta foto são maiores (span 2 cols em desktop)
        _span = " md:col-span-2 md:row-span-2" if i in (0, 4) else ""
        items += (
            '<div class="overflow-hidden rounded-xl' + _span + ' reveal">' + nl
            + '<img src="' + url + '" alt="' + getattr(prd, 'business_name', '') + '" '
            + 'class="w-full h-full object-cover ' + _aspect + ' img-craft hover:scale-105 transition-transform duration-500" '
            + 'loading="lazy">' + nl
            + '</div>' + nl
        )
    if not items:
        return ""
    return (
        '<section id="galeria" class="py-16 md:py-24" style="background-color:var(--surface);">' + nl
        + '<div class="max-w-6xl mx-auto px-4 md:px-8">' + nl
        + '<h2 class="reveal text-2xl md:text-3xl font-bold text-center mb-12" style="color:var(--fg);">Nosso Espa&ccedil;o</h2>' + nl
        + '<div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">' + nl
        + items
        + '</div></div></section>' + nl
    )


def _gerar_faq_section(prd) -> str:
    """Seção FAQ accordion — injetada automaticamente se PRD tem FAQ."""
    faq = getattr(prd, 'faq_questions', []) or []
    if not faq or len(faq) < 2:
        return ""
    q = '"'
    nl = chr(10)
    items = ""
    for i, item in enumerate(faq[:8]):
        if isinstance(item, dict):
            pergunta = item.get("pergunta", item.get("question", ""))
            resposta = item.get("resposta", item.get("answer", ""))
        elif isinstance(item, str):
            pergunta = item
            resposta = ""
        else:
            continue
        if not pergunta:
            continue
        items += (
            '<div class="faq-item stagger-item" style="--i:' + str(i) + ';border-bottom:1px solid var(--border);padding:16px 0;">'
            '<button class="faq-toggle" style="width:100%;display:flex;align-items:center;justify-content:space-between;'
            'background:none;border:none;cursor:pointer;padding:8px 0;text-align:left;color:var(--fg);font-size:1rem;font-weight:600;" '
            'aria-expanded="false" onclick="this.parentElement.classList.toggle(\'open\');this.setAttribute(\'aria-expanded\',this.parentElement.classList.contains(\'open\'))">'
            '<span>' + pergunta + '</span>'
            '<i class="ph ph-caret-down" style="transition:transform 0.3s;flex-shrink:0;margin-left:12px;"></i>'
            '</button>'
            + ('<div class="faq-answer" style="max-height:0;overflow:hidden;transition:max-height 0.3s ease,padding 0.3s;'
               'color:var(--muted);font-size:0.9rem;line-height:1.6;">'
               '<p style="padding:8px 0 16px;">' + resposta + '</p></div>' if resposta else
               '<div class="faq-answer" style="max-height:0;overflow:hidden;transition:max-height 0.3s ease;"></div>')
            + '</div>' + nl
        )
    if not items:
        return ""
    return (
        '<section id="faq" class="py-16 md:py-24" style="background-color:var(--surface);">' + nl
        + '<div class="max-w-3xl mx-auto px-4 md:px-8">' + nl
        + '<h2 class="reveal text-2xl md:text-3xl font-bold text-center mb-12" style="color:var(--fg);">Perguntas Frequentes</h2>' + nl
        + '<div class="space-y-0">' + nl
        + items
        + '</div></div></section>' + nl
        + '<style>'
        + '.faq-item.open .faq-answer{max-height:200px;padding:4px 0;}'
        + '.faq-item.open .ph-caret-down{transform:rotate(180deg);}'
        + '</style>' + nl
    )


def montar_template_python(html_main, prd):
    cores = prd.color_palette
    telefone = getattr(prd, "phone", "") or ""
    wnum = telefone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    whatsapp_url = "https://wa.me/55" + wnum
    logo = getattr(prd, "logo_url", None)
    nome = prd.business_name
    endereco = getattr(prd, "address", "") or ""
    q = chr(34)
    nl = chr(10)

    # Extrair 6 tokens OKLch do design_context (via color_palette.tokens_oklch)
    # Fallback para hex legado se tokens_oklch não existir
    _tokens = getattr(cores, "tokens_oklch", None) or {}
    _bg      = _tokens.get("--bg",      getattr(cores, "background", "#ffffff"))
    _surface = _tokens.get("--surface", "#f9fafb")
    _fg      = _tokens.get("--fg",      getattr(cores, "text", "#111111"))
    _muted   = _tokens.get("--muted",   "#6b7280")
    _border  = _tokens.get("--border",  "#e5e7eb")
    _accent  = _tokens.get("--accent",  getattr(cores, "accent", "#0ea5e9"))

    # Tipografia do design_context
    _typo = getattr(prd, "typography", {}) or {}
    _font_heading = _typo.get("heading", "Plus Jakarta Sans") if isinstance(_typo, dict) else getattr(_typo, "heading", "Plus Jakarta Sans")
    _font_body    = _typo.get("body",    "Inter")             if isinstance(_typo, dict) else getattr(_typo, "body",    "Inter")

    # Hero style do design_context — gradiente animado + layout por direção visual
    _hero_style  = _tokens.get("hero_style", {}) or {}
    _hero_css    = _hero_style.get("gradient", "")
    _hero_kf     = _hero_style.get("keyframes", "")
    _hero_noise  = _hero_style.get("noise", False)
    _hero_layout = _hero_style.get("layout", "hero-split")
    _hero_overlay= _hero_style.get("overlay", "rgba(0,0,0,0.45)")
    _hero_img_style = _hero_style.get("img_style", "object-fit:cover;")

    # Perfil de animação do design_context
    _anim_profile = _tokens.get("_animation_profile", {})
    _enter_dur  = _anim_profile.get("enter",      "300ms")
    _feedback   = _anim_profile.get("feedback",   "150ms")

    # Craft profile — spacing, typography, rhythm (forçado via CSS)
    _craft = getattr(cores, "craft", None) or _tokens.get("_craft", {}) or {}
    _h1_size     = _craft.get("h1_size",     "clamp(2.2rem, 5vw, 3.5rem)")
    _h1_weight   = _craft.get("h1_weight",   "700")
    _h1_tracking = _craft.get("h1_tracking", "-0.02em")
    _h2_size     = _craft.get("h2_size",     "clamp(1.4rem, 3vw, 2rem)")
    _h2_weight   = _craft.get("h2_weight",   "600")
    _h2_tracking = _craft.get("h2_tracking", "-0.01em")
    _body_size   = _craft.get("body_size",   "1rem")
    _body_lh     = _craft.get("body_lh",     "1.65")
    _label_track = _craft.get("label_tracking", "0.06em")
    _section_py  = _craft.get("section_py",  "clamp(4rem, 8vw, 6rem)")
    _card_pad    = _craft.get("card_padding","1.5rem")
    _elem_gap    = _craft.get("element_gap", "1.25rem")
    _easing_std = _anim_profile.get("easing_std", "cubic-bezier(0.4,0.0,0.2,1)")
    _easing_ent = _anim_profile.get("easing_enter","cubic-bezier(0.0,0.0,0.2,1)")
    _stagger    = _anim_profile.get("stagger",    "60ms")
    if logo:
        logo_html = ("<img src=" + q + logo + q + " class=" + q + "h-10 w-auto object-contain" + q
            + " alt=" + q + "Logo " + nome + q + " loading=" + q + "eager" + q + ">")
    else:
        # Gerar logo SVG via haiku baseado no nome + segmento
        logo_html = _gerar_logo_svg(nome, getattr(prd, "segmento", "") or getattr(prd, "segment", "") or "")
    _dark_mode_prd = getattr(prd, "dark_mode", None)
    if _dark_mode_prd is None:
        _dark_mode_prd = getattr(prd.color_palette, "dark_mode", False) if hasattr(prd, "color_palette") else False
    header = (
        "<!DOCTYPE html>" + chr(10)
        + "<html lang=" + q + "pt-BR" + q + ">" + chr(10)
        + "<head>" + chr(10)
        + "<meta charset=" + q + "UTF-8" + q + ">" + chr(10)
        + "<meta name=" + q + "viewport" + q + " content=" + q + "width=device-width, initial-scale=1.0" + q + ">" + chr(10)
        + "<title>" + nome + "</title>" + chr(10)
        + _gerar_seo_inline(prd) + chr(10)
        + _gerar_pixel_tracking() + chr(10)
        + "<link href=" + q + "https://fonts.googleapis.com/css2?family=" + _font_heading.replace(" ","+") + ":wght@300..900&family=" + _font_body.replace(" ","+") + ":wght@300..700&display=swap" + q + " rel=" + q + "stylesheet" + q + ">" + chr(10)
        + "<script src=" + q + "https://cdn.tailwindcss.com" + q + "></script>" + chr(10)
        + "<!-- Lenis smooth scroll -->" + chr(10)
        + "<script src=" + q + "https://cdn.jsdelivr.net/npm/lenis@1.1.18/dist/lenis.min.js" + q + "></script>" + chr(10)
        + "<style id=" + q + "fralib-tokens" + q + ">" + chr(10)
        + ":root {" + chr(10)
        + "  --bg:      " + _bg      + ";" + chr(10)
        + "  --surface: " + _surface + ";" + chr(10)
        + "  --fg:      " + _fg      + ";" + chr(10)
        + "  --muted:   " + _muted   + ";" + chr(10)
        + "  --border:  " + _border  + ";" + chr(10)
        + "  --accent:  " + _accent  + ";" + chr(10)
        + "  --accent-hue: " + _extract_hue(_accent) + ";" + chr(10)
        + "  /* animação */" + chr(10)
        + "  --dur-enter:    " + _enter_dur  + ";" + chr(10)
        + "  --dur-feedback: " + _feedback   + ";" + chr(10)
        + "  --ease-std:     " + _easing_std + ";" + chr(10)
        + "  --ease-enter:   " + _easing_ent + ";" + chr(10)
        + "  --stagger:      " + _stagger    + ";" + chr(10)
        + "  /* craft — typography */" + chr(10)
        + "  --h1-size:      " + _h1_size    + ";" + chr(10)
        + "  --h1-weight:    " + _h1_weight  + ";" + chr(10)
        + "  --h1-tracking:  " + _h1_tracking+ ";" + chr(10)
        + "  --h2-size:      " + _h2_size    + ";" + chr(10)
        + "  --h2-weight:    " + _h2_weight  + ";" + chr(10)
        + "  --h2-tracking:  " + _h2_tracking+ ";" + chr(10)
        + "  --body-size:    " + _body_size  + ";" + chr(10)
        + "  --body-lh:      " + _body_lh    + ";" + chr(10)
        + "  --label-tracking:" + _label_track+ ";" + chr(10)
        + "  /* craft — spacing */" + chr(10)
        + "  --section-py:   " + _section_py + ";" + chr(10)
        + "  --card-padding: " + _card_pad   + ";" + chr(10)
        + "  --element-gap:  " + _elem_gap   + ";" + chr(10)
        + "}" + chr(10)
        + "body { font-family: '" + _font_body + "', sans-serif; background: var(--bg); color: var(--fg); overflow-wrap: break-word; word-break: break-word; font-size: var(--body-size); line-height: var(--body-lh); }" + chr(10)
        + "h1,h2,h3,h4 { font-family: '" + _font_heading + "', serif; overflow-wrap: break-word; text-wrap: balance; }" + chr(10)
        + "h1 { font-size: var(--h1-size); font-weight: var(--h1-weight); letter-spacing: var(--h1-tracking); line-height: 1.1; }" + chr(10)
        + "h2 { font-size: var(--h2-size); font-weight: var(--h2-weight); letter-spacing: var(--h2-tracking); }" + chr(10)
        + ".eyebrow, .section-label, [class*='uppercase'] { letter-spacing: var(--label-tracking); }" + chr(10)
        + "img { max-width: 100%; height: auto; decoding: async; }" + chr(10)
        + "section { padding: var(--section-py) 1rem; content-visibility: auto; contain-intrinsic-size: auto 500px; }" + chr(10)
        + "#hero { content-visibility: visible; }" + chr(10)
        + "@media(min-width:768px) { section { padding: var(--section-py) 2rem; } }" + chr(10)
        + ".flex, [class*='flex'] { gap: var(--element-gap); }" + chr(10)
        + ".grid, [class*='grid'] { gap: var(--element-gap); }" + chr(10)
        + ".card,[class*='card'] { padding: var(--card-padding); }" + chr(10)
        + "a:empty::after, button:empty::after { content: 'Saiba mais'; }" + chr(10)
        + "/* Skip to content — accessibility */" + chr(10)
        + ".skip-link { position:absolute;top:-40px;left:0;background:var(--accent);color:var(--bg);padding:8px 16px;z-index:10000;font-size:0.875rem;transition:top 0.2s; }" + chr(10)
        + ".skip-link:focus { top:0; }" + chr(10)
        + "/* Focus visible — accessibility */" + chr(10)
        + ":focus-visible { outline:2px solid var(--accent);outline-offset:2px;border-radius:4px; }" + chr(10)
        + "/* Header scroll state */" + chr(10)
        + "#fralib-header.scrolled { padding-top:0.5rem;padding-bottom:0.5rem;box-shadow:0 2px 12px rgba(0,0,0,0.15); }" + chr(10)
        + "/* Image craft — grayscale hover on gallery */" + chr(10)
        + ".img-craft { transition:filter 0.4s ease,transform 0.4s ease; }" + chr(10)
        + ".img-craft:hover { filter:grayscale(0) brightness(1.05);transform:scale(1.02); }" + chr(10)
        + "/* Clip-path reveal on scroll */" + chr(10)
        + ".clip-reveal { clip-path:inset(8% 8% 8% 8%);transition:clip-path 0.8s cubic-bezier(0.16,1,0.3,1); }" + chr(10)
        + ".clip-reveal.visible { clip-path:inset(0 0 0 0); }" + chr(10)
        + "/* Texture & depth */" + chr(10)
        + ".grain::after { content:'';position:absolute;inset:0;pointer-events:none;opacity:0.04;background-image:url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\"); }" + chr(10)
        + ".mesh-glow { position:relative; }" + chr(10)
        + ".mesh-glow::before { content:'';position:absolute;top:20%;left:50%;width:60%;height:60%;transform:translateX(-50%);background:radial-gradient(ellipse,color-mix(in oklch,var(--accent) 15%,transparent) 0%,transparent 70%);pointer-events:none;filter:blur(60px);z-index:0; }" + chr(10)
        + "/* Section dividers */" + chr(10)
        + ".divider-wave { position:relative; }" + chr(10)
        + ".divider-wave::after { content:'';position:absolute;bottom:-1px;left:0;right:0;height:48px;background:var(--bg);clip-path:ellipse(55% 100% at 50% 100%); }" + chr(10)
        + ".divider-angle { position:relative; }" + chr(10)
        + ".divider-angle::after { content:'';position:absolute;bottom:-1px;left:0;right:0;height:48px;background:var(--bg);clip-path:polygon(0 100%,100% 60%,100% 100%); }" + chr(10)
        + "/* Gradient border on cards */" + chr(10)
        + ".gradient-border { border:1px solid transparent;background-clip:padding-box;position:relative; }" + chr(10)
        + ".gradient-border::before { content:'';position:absolute;inset:-1px;border-radius:inherit;padding:1px;background:linear-gradient(135deg,var(--accent),var(--muted));-webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);-webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none; }" + chr(10)
        + "/* Variable font optical sizing */" + chr(10)
        + "h1 { font-optical-sizing:auto; }" + chr(10)
        + "p { text-wrap:pretty; }" + chr(10)
        + "/* Skeleton loading — hero shimmer */" + chr(10)
        + "@keyframes shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}" + chr(10)
        + ".skeleton{background:linear-gradient(90deg,var(--surface) 25%,color-mix(in oklch,var(--surface) 80%,var(--fg)) 50%,var(--surface) 75%);background-size:200% 100%;animation:shimmer 1.5s infinite;border-radius:8px;}" + chr(10)
        + "#hero .skeleton{position:absolute;inset:0;z-index:0;}" + chr(10)
        + "#hero.loaded .skeleton{display:none;}" + chr(10)
        + "/* Horizontal scroll cards mobile */" + chr(10)
        + "@media(max-width:768px){.scroll-x-mobile{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;gap:1rem;padding-bottom:1rem;-webkit-overflow-scrolling:touch;scrollbar-width:none;}.scroll-x-mobile::-webkit-scrollbar{display:none;}.scroll-x-mobile>*{flex:0 0 85%;scroll-snap-align:start;max-width:85%;}}" + chr(10)
        + "/* Swiper overrides */" + chr(10)
        + ".swiper{width:100%;padding-bottom:2rem;}" + chr(10)
        + ".swiper-pagination-bullet-active{background:var(--accent)!important;}" + chr(10)
        + ".swiper-slide{height:auto;}" + chr(10)
        + ".hero-overlay { position: absolute; inset: 0; background: linear-gradient(to bottom, rgba(0,0,0,0.5), rgba(0,0,0,0.7)); z-index: 1; }" + chr(10)
        + "/* Reveal animations */" + chr(10)
        + ".reveal,.reveal-left,.scale-in { opacity:0; }" + chr(10)
        + ".reveal.visible { opacity:1; transform:translateY(0) !important; transition: opacity var(--dur-enter) var(--ease-enter), transform var(--dur-enter) var(--ease-enter); }" + chr(10)
        + ".reveal-left.visible { opacity:1; transform:translateX(0) !important; transition: opacity var(--dur-enter) var(--ease-enter), transform var(--dur-enter) var(--ease-enter); }" + chr(10)
        + ".scale-in.visible { opacity:1; transform:scale(1) !important; transition: opacity var(--dur-enter) var(--ease-enter), transform var(--dur-enter) var(--ease-enter); }" + chr(10)
        + ".reveal { transform: translateY(24px); }" + chr(10)
        + ".reveal-left { transform: translateX(-24px); }" + chr(10)
        + ".scale-in { transform: scale(0.95); }" + chr(10)
        + ".stagger-item { transition-delay: calc(var(--i,0) * var(--stagger)); }" + chr(10)
        + "@keyframes pulse-cta { 0%,100%{box-shadow:0 0 0 0 color-mix(in oklch,var(--accent) 40%,transparent)} 50%{box-shadow:0 0 0 8px transparent} }" + chr(10)
        + ".pulse-cta { animation: pulse-cta 2.5s ease-in-out infinite; }" + chr(10)
        + "@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:0.01ms!important;transition-duration:0.01ms!important}}" + chr(10)
        + (_hero_kf + chr(10) if _hero_kf else "")
        + ("#hero{" + _hero_css + "}" + chr(10) if _hero_css else "")
        + ("#hero{position:relative;}" + chr(10) if _hero_noise else "")
        + ("@keyframes hero-noise{0%,100%{opacity:0.03}50%{opacity:0.06}}" + chr(10) if _hero_noise else "")
        + ("#hero::after{content:'';position:absolute;inset:0;pointer-events:none;opacity:0.04;animation:hero-noise 3s ease-in-out infinite;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.03) 2px,rgba(0,0,0,0.03) 4px);}" + chr(10) if _hero_noise else "")
        + "/* Button hover — scale + shadow */" + chr(10)
        + ".btn-primary,.btn-secondary { transition: transform var(--dur-feedback) var(--ease-std), box-shadow var(--dur-feedback) var(--ease-std); }" + chr(10)
        + ".btn-primary:hover,.btn-secondary:hover { transform: scale(1.03); box-shadow: 0 4px 20px color-mix(in oklch, var(--accent) 30%, transparent); }" + chr(10)
        + ".btn-primary:active,.btn-secondary:active { transform: scale(0.98); }" + chr(10)
        + "/* Scroll progress bar */" + chr(10)
        + "#scroll-progress{position:fixed;top:0;left:0;height:3px;background:var(--accent);z-index:9999;transform-origin:left;transform:scaleX(0);transition:none;}" + chr(10)
        + "/* Text reveal animation */" + chr(10)
        + ".text-reveal{overflow:hidden;display:inline-block;}" + chr(10)
        + ".text-reveal span{display:inline-block;transform:translateY(100%);opacity:0;transition:transform 0.6s cubic-bezier(0.16,1,0.3,1),opacity 0.6s ease;}" + chr(10)
        + ".text-reveal.visible span{transform:translateY(0);opacity:1;}" + chr(10)
        + "/* Tilt 3D hover on cards */" + chr(10)
        + "[data-tilt]{transition:transform 0.3s ease;transform-style:preserve-3d;}" + chr(10)
        + "</style>" + chr(10)
        + "<script src=" + q + "https://unpkg.com/@phosphor-icons/web@2.1.1" + q + "></script>" + chr(10)
        + "<!-- Swiper.js for mobile carousels -->" + chr(10)
        + "<link rel=" + q + "stylesheet" + q + " href=" + q + "https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css" + q + ">" + chr(10)
        + "<script src=" + q + "https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js" + q + " defer></script>" + chr(10)
        + "</head>" + chr(10)
        + "<body>" + chr(10)
        + "<a href=" + q + "#fralib-content" + q + " class=" + q + "skip-link" + q + ">Pular para o conte&uacute;do</a>" + chr(10)
        + "<div id=" + q + "scroll-progress" + q + "></div>" + chr(10)
        + """<style>
:root {
  --color-header-bg: color-mix(in oklch, var(--bg) 92%, transparent);
  --color-header-border: color-mix(in oklch, var(--border) 80%, transparent);
  /* Footer: sempre escuro independente do tema */
  --color-footer-bg: oklch(10% 0.01 var(--accent-hue, 240));
  --color-footer-text: oklch(92% 0 0);
  --color-footer-muted: oklch(60% 0 0);
  --color-footer-border: oklch(20% 0.01 var(--accent-hue, 240));
}
body { background:var(--bg); color:var(--fg); }
#fralib-header { background:var(--color-header-bg); border-bottom:1px solid var(--color-header-border); backdrop-filter:blur(12px); }
.card,[class*="card"] { background:var(--surface); color:var(--fg); border:1px solid var(--border); }
</style>
""" + chr(10)
        + "<header id=" + q + "fralib-header" + q + " class=" + q + "fixed top-0 left-0 right-0 z-50 backdrop-blur-md shadow-sm transition-all duration-300" + q + ">" + chr(10)
        + "  <div class=" + q + "max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4" + q + ">" + chr(10)
        + "    <a href=" + q + "#hero" + q + " class=" + q + "flex items-center gap-3 no-underline" + q + ">" + chr(10)
        + "      " + logo_html + chr(10)
        + "      <span class=" + q + "font-bold text-sm hidden sm:block" + q + " style=" + q + "color:var(--fg)" + q + ">" + nome + "</span>" + chr(10)
        + "    </a>" + chr(10)
        + "    <nav class=" + q + "hidden md:flex items-center gap-6 text-sm font-medium" + q + " style=" + q + "color:var(--muted)" + q + ">" + chr(10)
        + _gerar_nav_links(prd, q)
        + "    </nav>" + chr(10)
        + "    <div class=" + q + "flex items-center gap-3" + q + ">" + chr(10)


        + "      <a href=" + q + whatsapp_url + q + " target=" + q + "_blank" + q + " rel=" + q + "noopener" + q
        + " class=" + q + "px-4 py-2 rounded-xl text-white text-sm font-semibold transition-transform hover:scale-105" + q
        + " style=" + q + "background:var(--accent)" + q + ">" + _nav_cta_text(prd) + "</a>" + chr(10)
        + "    </div>" + chr(10)
        + "  </div>" + chr(10)
        + "</header>" + chr(10)
    )
    _segmento_footer = getattr(prd, "segmento", "") or ""
    _cidade_footer = getattr(prd, "cidade", "") or ""
    _ano = __import__("datetime").datetime.now().year
    _horas = getattr(prd, "hours", {}) or {}
    _horas_html = ""
    if _horas:
        for _dia, _hr in list(_horas.items())[:5]:
            _horas_html += "<li style=" + q + "color:var(--color-footer-muted);font-size:0.75rem;margin-bottom:0.25rem;display:flex;justify-content:space-between" + q + "><span>" + str(_dia) + "</span><span>" + str(_hr) + "</span></li>"
    else:
        _horas_html = "<li style=" + q + "color:var(--color-footer-muted);font-size:0.75rem" + q + ">Consulte nossos hor&aacute;rios</li>"
    footer = (
        "<style>" + nl
        + "footer{background:var(--color-footer-bg);color:var(--color-footer-text)}" + nl
        + "footer h3{color:var(--accent)!important;font-family:'" + _font_heading + "',serif;font-weight:700;font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:1rem}" + nl
        + "footer p,footer li,footer span{color:var(--color-footer-muted)!important;font-size:0.875rem}" + nl
        + "footer a{color:var(--color-footer-muted)!important;text-decoration:none;font-size:0.875rem;transition:color 0.2s}" + nl
        + "footer a:hover{color:var(--color-accent)!important}" + nl
        + ".footer-cta{background:var(--color-accent)!important;color:#fff!important;padding:0.6rem 1.4rem;border-radius:0.75rem;font-weight:600;font-size:0.875rem;display:inline-flex;align-items:center;gap:0.5rem;transition:opacity 0.2s}" + nl
        + ".footer-cta:hover{opacity:0.85}" + nl
        + ".footer-divider{border-color:var(--color-footer-border,rgba(255,255,255,0.1))}" + nl
        + "</style>" + nl
        + "<footer>" + nl
        + "<div class=" + q + "max-w-7xl mx-auto px-6 pt-16 pb-10" + q + ">" + nl
        + "<div class=" + q + "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-10 mb-12" + q + ">" + nl
        + "<div>" + logo_html + "<p class=" + q + "mt-4 text-sm leading-relaxed" + q + ">" + nome + " &mdash; " + _segmento_footer + " em " + _cidade_footer + "</p><p class=" + q + "text-xs mt-2" + q + ">Atendimento especializado com qualidade e compromisso.</p></div>" + nl
        + "<div><h3>Navega&ccedil;&atilde;o</h3><ul class=" + q + "space-y-2" + q + "><li><a href=" + q + "#hero" + q + ">In&iacute;cio</a></li><li><a href=" + q + "#sobre" + q + ">Sobre n&oacute;s</a></li><li><a href=" + q + "#servicos" + q + ">Servi&ccedil;os</a></li><li><a href=" + q + "#depoimentos" + q + ">Depoimentos</a></li><li><a href=" + q + "#localizacao" + q + ">Localiza&ccedil;&atilde;o</a></li><li><a href=" + q + "#contato" + q + ">Contato</a></li></ul></div>" + nl
        + "<div><h3>Hor&aacute;rios</h3><span id=" + q + "fralib-open-badge" + q + " style=" + q + "display:none;font-size:0.7rem;padding:2px 8px;border-radius:9999px;font-weight:600;margin-bottom:0.5rem;display:inline-block" + q + "></span><ul>" + _horas_html + "</ul></div>" + nl
        + "<div><h3>Contato</h3>"
        + ("<p class=" + q + "text-sm mb-2" + q + ">" + endereco + "</p>" if endereco else "")
        + "<a href=" + q + "tel:" + telefone.replace(" ","").replace("(","").replace(")","").replace("-","") + q + " class=" + q + "block text-sm mb-3" + q + ">" + telefone + "</a>"
        + "<a href=" + q + whatsapp_url + q + " target=" + q + "_blank" + q + " rel=" + q + "noopener" + q + " class=" + q + "footer-cta" + q + "><i class=" + q + "ph-fill ph-whatsapp-logo" + q + "></i> Falar no WhatsApp</a>"
        + "<a href=" + q + "/politica-de-privacidade" + q + " class=" + q + "block text-xs mt-4" + q + ">Pol&iacute;tica de Privacidade</a></div>" + nl
        + "</div>" + nl
        + "<div class=" + q + "border-t footer-divider pt-6 flex flex-col md:flex-row items-center justify-between gap-3" + q + ">"
        + "<p class=" + q + "text-xs" + q + ">&copy; " + str(_ano) + " " + nome + " &mdash; Todos os direitos reservados.</p>"
        + ("" if getattr(prd, "white_label", False) else "<p class=" + q + "text-xs" + q + ">Site criado por <a href=" + q + "https://fralib.com.br" + q + " target=" + q + "_blank" + q + " rel=" + q + "noopener" + q + ">FraLib</a></p>") + "</div>" + nl
        + "</div></footer>" + nl
        + "<script>window.__fralibHours=" + __import__("json").dumps(_horas, ensure_ascii=False) + ";</script>" + nl
        + """<script>
(function(){
  // Scroll progress bar + header scroll state
  var prog = document.getElementById('scroll-progress');
  var hdr = document.getElementById('fralib-header');
  window.addEventListener('scroll',function(){
    var h=document.documentElement.scrollHeight-window.innerHeight;
    if(prog){prog.style.transform='scaleX('+(h>0?window.scrollY/h:0)+')';}
    if(hdr){if(window.scrollY>60){hdr.classList.add('scrolled');}else{hdr.classList.remove('scrolled');}}
  },{passive:true});
  // IntersectionObserver — scroll reveal com tokens CSS
  // Parallax scroll
  window.addEventListener('scroll', function() {
    document.querySelectorAll('[data-parallax]').forEach(function(el) {
      var speed = parseFloat(el.dataset.parallax) || 0.3;
      var rect = el.getBoundingClientRect();
      if (rect.bottom > 0 && rect.top < window.innerHeight) {
        el.style.transform = 'translateY(' + (window.scrollY * speed * -0.5) + 'px)';
      }
    });
  });
  // Counter animation
  var counterIO = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) {
      if (e.isIntersecting) {
        var target = parseInt(e.target.dataset.count);
        var current = 0;
        var step = Math.ceil(target / 40);
        var timer = setInterval(function() {
          current += step;
          if (current >= target) { current = target; clearInterval(timer); }
          e.target.textContent = current.toLocaleString('pt-BR');
        }, 30);
        counterIO.unobserve(e.target);
      }
    });
  }, {threshold: 0.5});
  document.querySelectorAll('[data-count]').forEach(function(el) { counterIO.observe(el); });
  
  var io = new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      if(e.isIntersecting){ e.target.classList.add('visible'); io.unobserve(e.target); }
    });
  },{threshold:0.15,rootMargin:'0px 0px -50px 0px'});
  document.addEventListener('DOMContentLoaded',function(){
    document.querySelectorAll('.reveal,.reveal-left,.scale-in,.clip-reveal').forEach(function(el,i){
      el.style.setProperty('--i',i%6);
      io.observe(el);
    });
    // Stagger items
    document.querySelectorAll('.stagger-item').forEach(function(el,i){
      el.style.setProperty('--i',i);
    });
  // Typewriter → Word Split Reveal (premium text animation)
  (function(){
    var mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    if(mq.matches) return;
    var h1 = document.querySelector('#hero h1');
    if(!h1) return;
    var text = h1.textContent.trim();
    var words = text.split(/\s+/);
    h1.innerHTML = words.map(function(w,i){
      return '<span class="word-reveal" style="display:inline-block;opacity:0;transform:translateY(20px) rotateX(-10deg);transition:opacity 0.5s cubic-bezier(0.16,1,0.3,1),transform 0.5s cubic-bezier(0.16,1,0.3,1);transition-delay:'+((i*0.08)+0.2)+'s">'+w+'</span>';
    }).join(' ');
    h1.style.visibility = 'visible';
    requestAnimationFrame(function(){
      setTimeout(function(){
        h1.querySelectorAll('.word-reveal').forEach(function(w){
          w.style.opacity='1';w.style.transform='translateY(0) rotateX(0)';
        });
      }, 100);
    });
  })();
  // Lenis smooth scroll init
  (function(){
    if(typeof Lenis==='undefined') return;
    var lenis = new Lenis({duration:1.2,easing:function(t){return Math.min(1,1.001-Math.pow(2,-10*t));},orientation:'vertical',smoothWheel:true});
    function raf(time){lenis.raf(time);requestAnimationFrame(raf);}
    requestAnimationFrame(raf);
  })();
  // 3D tilt on cards with data-tilt
  document.querySelectorAll('[data-tilt]').forEach(function(card){
    card.addEventListener('mousemove',function(e){var r=card.getBoundingClientRect();var x=(e.clientX-r.left)/r.width-0.5;var y=(e.clientY-r.top)/r.height-0.5;card.style.transform='perspective(600px) rotateY('+x*8+'deg) rotateX('+(-y*8)+'deg)';});
    card.addEventListener('mouseleave',function(){card.style.transform='perspective(600px) rotateY(0) rotateX(0)';});
  });
  // Text reveal
  document.querySelectorAll('.text-reveal').forEach(function(el){io.observe(el);});
  // Swiper init — mobile carousels for testimonials/services
  (function(){
    if(typeof Swiper==='undefined') return;
    document.querySelectorAll('.swiper').forEach(function(el){
      new Swiper(el,{slidesPerView:1.2,spaceBetween:16,grabCursor:true,pagination:{el:el.querySelector('.swiper-pagination'),clickable:true},breakpoints:{768:{slidesPerView:2.2,spaceBetween:24},1024:{slidesPerView:3,spaceBetween:32}}});
    });
  })();
  // Hero skeleton — remove on load
  (function(){
    var hero=document.getElementById('hero');
    if(hero){
      var img=hero.querySelector('img');
      if(img&&!img.complete){img.addEventListener('load',function(){hero.classList.add('loaded');});}
      else{hero.classList.add('loaded');}
    }
  })();
  // Horizontal scroll mobile — add class to card grids on mobile
  (function(){
    if(window.innerWidth>768) return;
    document.querySelectorAll('#servicos .grid, #depoimentos .grid').forEach(function(g){
      if(!g.classList.contains('swiper-wrapper')){g.classList.add('scroll-x-mobile');}
    });
  })();
  // Horário dinâmico — badge "Aberto agora" / "Fechado"
  (function(){
    var badge=document.getElementById('fralib-open-badge');
    if(!badge) return;
    var hoursData=window.__fralibHours||{};
    if(!Object.keys(hoursData).length){badge.style.display='none';return;}
    var dias=['domingo','segunda','terca','quarta','quinta','sexta','sabado'];
    var aliases={'segunda-feira':'segunda','terça-feira':'terca','terca-feira':'terca','quarta-feira':'quarta','quinta-feira':'quinta','sexta-feira':'sexta','sábado':'sabado','sabado':'sabado','domingo':'domingo','seg':'segunda','ter':'terca','qua':'quarta','qui':'quinta','sex':'sexta','sab':'sabado','dom':'domingo','mon':'segunda','tue':'terca','wed':'quarta','thu':'quinta','fri':'sexta','sat':'sabado','sun':'domingo'};
    var now=new Date();
    var diaIdx=now.getDay();
    var diaKey=dias[diaIdx];
    var found=null;
    Object.keys(hoursData).forEach(function(k){
      var kn=k.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/-feira/g,'').trim();
      if(kn===diaKey||(aliases[kn]&&aliases[kn]===diaKey)||kn.indexOf(diaKey)===0) found=hoursData[k];
    });
    if(!found){badge.textContent='Fechado hoje';badge.style.background='#dc2626';badge.style.color='#fff';badge.style.display='inline-block';return;}
    var match=String(found).match(/(\\d{1,2})[h:]?(\\d{0,2})\\s*[-–aà]\\s*(\\d{1,2})[h:]?(\\d{0,2})/);
    if(!match){badge.style.display='none';return;}
    var open=parseInt(match[1])*60+parseInt(match[2]||'0');
    var close=parseInt(match[3])*60+parseInt(match[4]||'0');
    var nowMin=now.getHours()*60+now.getMinutes();
    if(nowMin>=open&&nowMin<close){badge.textContent='Aberto agora';badge.style.background='#16a34a';badge.style.color='#fff';}
    else{badge.textContent='Fechado';badge.style.background='#dc2626';badge.style.color='#fff';}
    badge.style.display='inline-block';
  })();
  });
})();
</script>""" + nl
        + _gerar_lgpd_banner(prd) + nl
        + _gerar_whatsapp_float(whatsapp_url) + nl
        + _gerar_cta_mobile(whatsapp_url, nome) + nl
        + _gerar_back_to_top() + nl
        + "</body></html>" + nl
    )
    # Injetar FAQ accordion se PRD tem FAQ
    _faq_section = _gerar_faq_section(prd)
    _galeria_section = _gerar_galeria_section(prd)
    _stats_section = _gerar_stats_section(prd)
    _cta_final_section = _gerar_cta_final(prd, whatsapp_url)

    return header + "<main id=" + q + "fralib-content" + q + " class=" + q + "w-full overflow-x-hidden pt-20" + q + ">" + nl + html_main + nl + _stats_section + _galeria_section + _faq_section + _cta_final_section + "</main>" + nl + footer


def critique_theater_pass(html):
    """
    Critique Theater — QA pass pós-montagem.
    Detecta e corrige problemas visuais sem depender do LLM.
    Regras matemáticas puras: contraste, botões vazios, overlays, gaps.
    """
    import re as _re
    fixes_applied = []

    # 1. Botões/links vazios — injetar texto fallback
    def _fix_empty_buttons(m):
        tag = m.group(0)
        # Verificar se tem conteúdo entre > e </a> ou </button>
        inner = _re.search(r'>([^<]*)</', tag)
        if inner and inner.group(1).strip() == '':
            fixes_applied.append('empty_button')
            # Determinar texto baseado no href
            if 'wa.me' in tag or 'whatsapp' in tag.lower():
                return tag.replace('></', '>Fale conosco</')
            elif '#contato' in tag:
                return tag.replace('></', '>Entre em contato</')
            else:
                return tag.replace('></', '>Saiba mais</')
        return tag

    html = _re.sub(r'<a[^>]*>[\s]*</a>', lambda m: m.group(0).replace('></a>', '>Saiba mais</a>'), html)
    html = _re.sub(r'<button[^>]*>[\s]*</button>', lambda m: m.group(0).replace('></button>', '>Saiba mais</button>'), html)

    # 2. Hero sem overlay — se tem background-image + texto, forçar overlay
    def _fix_hero_overlay(m):
        section = m.group(0)
        # Se já tem overlay class, pular
        if 'hero-overlay' in section or 'bg-black/' in section or 'from-black' in section:
            return section
        # Se tem background-image e texto direto (h1/h2/p)
        if 'background-image' in section and ('<h1' in section or '<h2' in section):
            fixes_applied.append('hero_overlay')
            # Injetar overlay div após abertura da section
            section = _re.sub(
                r'(<section[^>]*id="hero"[^>]*>)',
                r'\1<div class="hero-overlay"></div>',
                section
            )
            # Forçar texto relativo z-10
            section = section.replace('class="', 'class="relative z-10 ', 1)
        return section

    html = _re.sub(r'<section[^>]*id="hero"[^>]*>.*?</section>', _fix_hero_overlay, html, flags=_re.DOTALL)

    # 3. Texto preto sobre fundo escuro — detectar via OKLch lightness
    # Se --bg tem lightness < 40%, qualquer color:#000 ou text-black é erro
    _bg_match = _re.search(r'--bg:\s*oklch\((\d+(?:\.\d+)?)%', html)
    _accent_match = _re.search(r'--accent:\s*oklch\((\d+(?:\.\d+)?)%', html)
    _muted_match = _re.search(r'--muted:\s*oklch\((\d+(?:\.\d+)?)%', html)

    if _bg_match:
        _bg_lightness = float(_bg_match.group(1))
        is_light = _bg_lightness > 60

        if is_light and _bg_lightness < 40:
            pass  # dark theme handled below
        elif _bg_lightness < 40:
            # Fundo escuro — remover text-black, color:#000, color:black
            html = _re.sub(r'(?<!\w)text-black(?!\w)', 'text-[var(--fg)]', html)
            html = _re.sub(r'color\s*:\s*#(?:000|000000)\b', 'color:var(--fg)', html)
            html = _re.sub(r'color\s*:\s*black\b', 'color:var(--fg)', html)
            fixes_applied.append('dark_bg_text_fix')

    # 3b. Validar accent não é invisível
    if _accent_match and _bg_match:
        _accent_l = float(_accent_match.group(1))
        _bg_l = float(_bg_match.group(1))
        # Accent quase igual ao bg = invisível
        if abs(_accent_l - _bg_l) < 15:
            fixes_applied.append('accent_contrast_fix')
            html = _re.sub(
                r'(--accent:\s*)oklch\([^)]+\)',
                r'\1oklch(55% 0.2 270)',
                html
            )

    # 3c. Validar muted não é invisível
    if _muted_match and _bg_match:
        _muted_l = float(_muted_match.group(1))
        _bg_l2 = float(_bg_match.group(1))
        if abs(_muted_l - _bg_l2) < 15:
            fixes_applied.append('muted_contrast_fix')
            html = _re.sub(
                r'(--muted:\s*)oklch\([^)]+\)',
                r'\1oklch(55% 0.01 0)',
                html
            )

    # 4. Imagens sem contenção — position:absolute sem relative parent
    # Detectar img com absolute que não está dentro de relative container
    def _fix_absolute_img(m):
        container = m.group(0)
        if 'position:absolute' in container or 'absolute' in container:
            if 'relative' not in container:
                fixes_applied.append('img_absolute_fix')
                return container.replace('class="', 'class="relative ', 1)
        return container

    # 5. Seções sem padding — forçar padding mínimo
    def _fix_section_padding(m):
        tag = m.group(0)
        if 'py-' not in tag and 'padding' not in tag:
            fixes_applied.append('section_padding')
            return tag.rstrip('>') + ' style="padding:4rem 1rem;">'
        return tag

    html = _re.sub(r'<section[^>]*>', _fix_section_padding, html)

    # 6. Font-size excessivo sem clamp — detectar font-size > 4rem inline
    def _fix_large_font(m):
        val = m.group(1)
        try:
            num = float(val)
            if num > 4:
                fixes_applied.append('font_size_clamp')
                return 'font-size:clamp(2rem,5vw,' + val + 'rem)'
        except ValueError:
            pass
        return m.group(0)

    html = _re.sub(r'font-size:\s*(\d+(?:\.\d+)?)rem', _fix_large_font, html)

    # 7. Legacy var references que escaparam — substituir por tokens canônicos
    html = html.replace('var(--color-primary)', 'var(--fg)')
    html = html.replace('var(--color-accent)', 'var(--accent)')
    html = html.replace('var(--color-background)', 'var(--bg)')
    html = html.replace('var(--color-text)', 'var(--fg)')
    html = html.replace('var(--color-surface)', 'var(--surface)')
    html = html.replace('var(--color-border)', 'var(--border)')
    html = html.replace('var(--color-muted)', 'var(--muted)')

    # 8. MOTION INJECTION — forçar parallax e animações em imagens
    # Ler micro-decisão do comentário HTML (injetado pelo gerar_html_componentizado)
    _micro_match = _re.search(r'<!-- fralib-micro intensity="(\w+)" density="(\w+)" photo="(\w+)" motion="(\w+)" -->', html)
    if _micro_match:
        _site_intensity = _micro_match.group(1)
        _site_motion = _micro_match.group(4)
    else:
        _site_intensity = "medium"
        _site_motion = "balanced"
        if 'very-spacious' in html or 'luxury' in html.lower():
            _site_intensity = "high"
        elif 'compressed' in html:
            _site_intensity = "low"

    _img_counter = [0]  # mutable counter pra variar animações
    def _inject_img_motion(m):
        tag = m.group(0)
        mods = []
        _img_counter[0] += 1
        _idx = _img_counter[0]
        # Parallax: intensidade varia
        if 'data-parallax' not in tag:
            if 'loading="eager"' in tag or 'loading=eager' in tag:
                _pval = {"high": "0.35", "medium": "0.25", "low": "0.12"}[_site_intensity]
                tag = tag.replace('<img ', '<img data-parallax="' + _pval + '" fetchpriority="high" ')
            else:
                _pval = {"high": "0.2", "medium": "0.15", "low": "0.08"}[_site_intensity]
                tag = tag.replace('<img ', '<img data-parallax="' + _pval + '" ')
            mods.append('parallax')
        # Reveal: variar entre reveal-left, clip-reveal, scale-in (não sempre igual)
        if 'reveal' not in tag and 'scale-in' not in tag and 'clip-reveal' not in tag:
            if _site_motion == "cinematic":
                _anim_options = ['clip-reveal', 'clip-reveal', 'scale-in', 'reveal-left']
            elif _site_motion == "subtle":
                _anim_options = ['reveal', 'reveal', 'reveal']
            elif _site_intensity == "high":
                _anim_options = ['clip-reveal', 'reveal-left', 'scale-in', 'clip-reveal']
            elif _site_intensity == "low":
                _anim_options = ['reveal', 'reveal', 'scale-in']
            else:
                _anim_options = ['reveal-left', 'clip-reveal', 'scale-in']
            _anim_class = _anim_options[_idx % len(_anim_options)]
            if 'class="' in tag:
                tag = tag.replace('class="', 'class="' + _anim_class + ' ')
            elif "class='" in tag:
                tag = tag.replace("class='", "class='" + _anim_class + " ")
            else:
                tag = tag.replace('<img ', '<img class="' + _anim_class + '" ')
            mods.append(_anim_class)
        # Rounded + shadow: intensidade varia
        if 'rounded' not in tag:
            _round_class = {"high": "rounded-2xl shadow-xl", "medium": "rounded-xl shadow-lg", "low": "rounded-lg shadow-md"}[_site_intensity]
            if 'class="' in tag:
                tag = tag.replace('class="', 'class="' + _round_class + ' ')
            mods.append('rounded+shadow')
        # Object-fit: garantir
        if 'object-cover' not in tag and 'object-fit' not in tag:
            if 'class="' in tag:
                tag = tag.replace('class="', 'class="object-cover ')
            mods.append('object-cover')
        # img-craft hover — só em intensity high/medium e não hero
        if 'img-craft' not in tag and 'hero' not in tag.lower() and _idx > 1 and _site_intensity != "low":
            if 'class="' in tag:
                tag = tag.replace('class="', 'class="img-craft ')
            mods.append('img-craft')
        if mods:
            fixes_applied.append('img_motion:' + '+'.join(mods))
        return tag

    html = _re.sub(r'<img\s[^>]+>', _inject_img_motion, html)

    # 9. Cards sem hover/tilt — adicionar data-tilt em cards
    def _inject_card_motion(m):
        tag = m.group(0)
        if 'data-tilt' not in tag and 'hover:' not in tag:
            # Adicionar hover translate + shadow
            if 'class="' in tag:
                tag = tag.replace('class="', 'class="hover:translate-y-[-4px] hover:shadow-xl transition-all duration-300 ')
                fixes_applied.append('card_hover')
        return tag

    # Cards: divs com border + rounded (padrão de card)
    html = _re.sub(r'<div[^>]*class="[^"]*(?:border|card)[^"]*rounded[^"]*"[^>]*>', _inject_card_motion, html)

    # 10. Seções sem reveal — h2 sem animação
    def _inject_h2_reveal(m):
        tag = m.group(0)
        if 'reveal' not in tag and 'scale-in' not in tag:
            if 'class="' in tag:
                tag = tag.replace('class="', 'class="reveal ')
            else:
                tag = tag.replace('<h2', '<h2 class="reveal"')
            fixes_applied.append('h2_reveal')
        return tag

    html = _re.sub(r'<h2[^>]*>', _inject_h2_reveal, html)

    # 11. Texture & depth injection — grain + mesh-glow baseado na intensidade
    if _site_intensity in ("high", "medium"):
        # Adicionar grain no hero
        html = _re.sub(
            r'(<section[^>]*id="hero"[^>]*)',
            lambda m: m.group(0) if 'grain' in m.group(0) else m.group(0).replace('class="', 'class="grain ') if 'class="' in m.group(0) else m.group(0),
            html
        )
        fixes_applied.append('grain_hero')

    if _site_intensity == "high" and _site_motion == "cinematic":
        # Adicionar mesh-glow na seção de serviços ou sobre
        html = _re.sub(
            r'(<section[^>]*id="(?:servicos|sobre)"[^>]*)',
            lambda m: m.group(0) if 'mesh-glow' in m.group(0) else m.group(0).replace('class="', 'class="mesh-glow ') if 'class="' in m.group(0) else m.group(0),
            html, count=1
        )
        fixes_applied.append('mesh_glow')

    # 12. Section dividers — variar entre wave e angle (não em todos, só entre seções contrastantes)
    _section_tags = list(_re.finditer(r'</section>\s*<section', html))
    if _section_tags and _site_intensity != "low":
        # Adicionar divider na primeira transição de seção (após hero)
        _first_break = _section_tags[0]
        _divider_class = "divider-wave" if _site_motion != "cinematic" else "divider-angle"
        # Injetar no section anterior ao break
        _pos = _first_break.start()
        _before = html[:_pos]
        _last_section = _before.rfind('<section')
        if _last_section > 0:
            _section_tag = html[_last_section:_pos]
            if _divider_class not in _section_tag:
                if 'class="' in html[_last_section:_last_section+200]:
                    html = html[:_last_section] + html[_last_section:].replace('class="', 'class="' + _divider_class + ' ', 1)
                    fixes_applied.append('section_divider')

    # 13. Responsive images — otimizar Unsplash URLs com srcset
    def _inject_srcset(m):
        tag = m.group(0)
        src_match = _re.search(r'src="(https://images\.unsplash\.com/[^"]+)"', tag)
        if not src_match:
            return tag
        base_url = src_match.group(1)
        # Limpar params existentes e adicionar srcset
        clean_url = _re.sub(r'[&?]w=\d+', '', base_url)
        clean_url = _re.sub(r'[&?]q=\d+', '', clean_url)
        sep = '&' if '?' in clean_url else '?'
        srcset = (
            clean_url + sep + 'w=400&q=75&fm=webp 400w, '
            + clean_url + sep + 'w=800&q=80&fm=webp 800w, '
            + clean_url + sep + 'w=1200&q=80&fm=webp 1200w'
        )
        sizes = '(max-width:640px) 100vw, (max-width:1024px) 50vw, 33vw'
        if 'srcset' not in tag:
            tag = tag.replace(src_match.group(0), src_match.group(0) + ' srcset="' + srcset + '" sizes="' + sizes + '"')
            fixes_applied.append('srcset')
        return tag

    html = _re.sub(r'<img\s[^>]*src="https://images\.unsplash\.com/[^>]+>', _inject_srcset, html)

    if fixes_applied:
        print(f"[CritiqueTheater] {len(fixes_applied)} fixes: {', '.join(set(fixes_applied))}")
    else:
        print("[CritiqueTheater] Nenhum problema detectado — site aprovado")

    return html
