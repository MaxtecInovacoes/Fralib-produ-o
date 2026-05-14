"""
Liam — Gerador de HTML cinematografico para negocios locais
Modulos: liam_models, liam_motion, liam_seo
"""
import sys
import time
import re
import json
sys.path.insert(0, "/root/fralib/backend/agents")

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from llm_direct import call_claude, call_claude_structured
from liam_seo import _get_schema_type  # gerar_seo_tags e gerar_whatsapp_float substituidos por funcoes inline
from open_design_selector import get_open_design_for_liam

# Importar modulos Liam

SYSTEM_LIAM_SINGLE_PASS = """Voce e Liam, desenvolvedor frontend senior da FraLib.
Voce executa EXATAMENTE a instrucao_criativa_para_dev do Arquiteto Mestre.
Sua unica tarefa: gerar as sections internas do site em HTML/Tailwind estatico.

=== REGRAS ESTRUTURAIS ===
1. Retorne APENAS tags <section>. NUNCA inclua DOCTYPE, html, head, body, header, footer ou scripts.
2. INICIO: comece com <section id="hero". Nenhum texto antes.
3. GRID: 60/40 ou 40/60. NUNCA 50/50.
4. H1 OBRIGATORIO: deve conter o nome da cidade. NUNCA H1 generico sem cidade.
5. PRECOS: NUNCA mencione valores. Use: Consulte nossos valores.
6. DADOS REAIS: use APENAS dados fornecidos. NUNCA invente nomes, enderecos, depoimentos ou metricas.
7. FOTOS: Use APENAS as URLs fornecidas no contexto. Hero: loading=eager com object-fit:cover. Demais: loading=lazy com object-fit:cover e aspect-ratio adequado. OBRIGATORIO incluir imagens nas secoes hero, sobre e servicos.
8. DEPOIMENTOS: NUNCA omita esta secao. Se reviews reais fornecidos, use-os. Se nao houver reviews, gere 3 depoimentos ficticios persuasivos com nomes genericos e framework PAS.
9. BOTOES: TODOS com href valido. WhatsApp: href='https://wa.me/{wnum}'. NUNCA href='#' vazio.
10. CONTADORES: NUNCA invente numeros. Use apenas rating e total_avaliacoes reais.

=== 6 TOKENS CSS — UNICA FONTE DE VERDADE ===
O :root JA ESTA DEFINIDO no wrapper HTML com os 6 tokens OKLch do design_context.
Use EXCLUSIVAMENTE estas variaveis CSS — NUNCA hardcode hex fora do :root:
  var(--bg)      → fundo de secoes
  var(--surface) → cards, modais, paineis
  var(--fg)      → texto primario (h1, h2, h3, p, li)
  var(--muted)   → texto secundario, labels, subtitulos
  var(--border)  → divisores, outlines, separadores
  var(--accent)  → destaque — MAXIMO 2 usos visiveis por tela

PROIBIDO: text-white, text-gray-100, text-slate-100, color:#fff em p/span/h1-h6/li.
PROIBIDO: var(--color-primary), var(--color-background) — os tokens sao --bg/--fg/--accent.

=== TIPOGRAFIA ===
  h1: font-size: clamp(2.2rem,5vw,3.5rem); line-height:1.1; letter-spacing:-0.02em
  h2: MAXIMO text-3xl; letter-spacing:-0.01em
  h3: MAXIMO text-2xl
  tracking-widest APENAS em labels text-xs ALL CAPS. NUNCA em h1/h2/h3/p.
  font-heading vem do design_context — NUNCA substituir por Inter ou Roboto.

=== LAYOUTS ===
  hero-split: flex row, texto 60% esquerda, imagem 40% direita
  hero-center: texto centralizado, bg com overlay
  hero-fullscreen: imagem full com overlay gradiente
  hero-diagonal: divisao diagonal texto/imagem
  sobre-grid: 2col texto+fotos
  services-cards: grid 3col com hover elevation
  services-accordion: lista retratil com chevron JS
  reviews-masonry: 3col altura variavel
  location-split: 2col mapa+info
  contact-split: info esquerda, CTA direita

=== ANIMACOES COM DISCIPLINA ===
Usar IntersectionObserver — NUNCA scroll event listener.
Classes obrigatorias (definidas no wrapper CSS):
  .reveal        → opacity:0 + translateY(24px) → opacity:1 + translateY(0)
  .reveal-left   → opacity:0 + translateX(-24px) → opacity:1 + translateX(0)
  .scale-in      → opacity:0 + scale(0.95) → opacity:1 + scale(1)
  .stagger-item  → usa --i para delay incremental (calc(var(--i,0) * stagger_ms))
Duracao e easing vem do animation_profile do design_context — NAO hardcode valores.
CTA principal: class="btn-primary pulse-cta" — o wrapper CSS define o keyframe.
OBRIGATORIO: @media (prefers-reduced-motion) ja esta no wrapper — nao redefinir.

=== ANTI-AI-SLOP (bloqueantes) ===
1. PROIBIDO #6366f1, #4f46e5, #8b5cf6 como accent
2. PROIBIDO gradiente purple→blue no hero
3. PROIBIDO emojis como icones (✨🚀🎯⚡) — usar SVG monoline com currentColor
4. PROIBIDO sans-serif em h1 quando design define serif
5. PROIBIDO card com borda colorida a esquerda
6. PROIBIDO metricas inventadas sem dado real
7. PROIBIDO filler copy (Feature One, Lorem ipsum, Descricao do servico)

=== SEO ===
Keywords nos H2/H3. FAQ accordion se FAQ_DO_NICHO fornecido.

=== ANTI-AI-SLOP (BLOQUEANTES) ===
1. PROIBIDO #6366f1, #4f46e5, #4338ca, #8b5cf6, #7c3aed como accent (indigo/violet Tailwind = slop de IA)
2. PROIBIDO gradiente purple->blue, blue->cyan, indigo->pink no hero
3. PROIBIDO emojis como icones em headings, botoes ou listas — usar SVG ou Phosphor icons
4. PROIBIDO card com borda colorida a esquerda (o "AI dashboard tile")
5. PROIBIDO metricas inventadas sem dado real do lead
6. PROIBIDO filler copy ("Feature One", "Lorem ipsum", texto placeholder)
7. PROIBIDO Inter ou Roboto como font-heading (sao fontes de corpo)
8. PROIBIDO layout simetrico Hero->Features->Pricing->FAQ->CTA sem variacao
9. PROIBIDO var(--accent) usado 6+ vezes no body
10. PROIBIDO blobs/waves SVG decorativos sem proposito funcional

=== REGRA DE COR ===
var(--accent) aparece no MAXIMO 2x por tela visivel.
Links contam. Hover rings contam. Bordas de botao contam.
Se precisar de mais destaque, use opacidade: color-mix(in oklch, var(--accent) 20%, transparent)

=== HIERARQUIA TIPOGRAFICA (obrigatoria) ===
CONTRATO: 1 ENTRY POINT DOMINANTE POR SECAO.
  H1 e o entry point do hero. NUNCA vazio, generico ou menor que o subtitulo.
  H1 DEVE ter 8+ palavras com beneficio + cidade.
  Diferenca de tamanho H1 vs H2: minimo 1.5x.
  H1 bold/black, subtitulo regular, body light.
  PROIBIDO: H1 vazio, H1 = nome do negocio apenas, H1 e H2 mesmo tamanho.

=== LEIS DE UX (aplicar sempre) ===
  GESTALT: cards do mesmo tipo = mesmo estilo. Secoes com delimitacao clara.
  HICK: maximo 3 CTAs por pagina. Cards de servicos: max 6. FAQ: max 8.
  FITTS: botoes CTA min 48px altura (py-4). WhatsApp flutuante min 56x56px.
  MILLER: listas max 7 itens. Depoimentos: 3 por vez.
  PEAK-END: hero = pico emocional. Contato = final. NUNCA terminar com FAQ.
  VON RESTORFF: 1 elemento especial por pagina (CTA principal). Nunca mais de 1.

=== AUTOCRITICA (antes de retornar) ===
Avalie internamente em 5 dimensoes (1-5). Se qualquer uma < 3, corrija antes de retornar:
1. PHILOSOPHY: tom visual bate com o nicho?
2. HIERARCHY: H1 domina com 8+ palavras + cidade? Subtitulo menor? CTA claro?
3. EXECUTION: sem cores hardcoded, sem tokens errados, botoes min 48px?
4. SPECIFICITY: zero filler copy, todos os dados sao reais?
5. RESTRAINT: --accent max 2x? Sem gradiente decorativo? Max 3 CTAs?
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
    """Pos-processador: substitui cores de texto claras hardcoded por CSS vars para compatibilidade com light mode."""
    import re as _re

    def fix_color_white_inline(m):
        full = m.group(0)
        if any(x in full for x in ['btn', 'button', 'badge', 'rounded-full', 'background']):
            return full
        return _re.sub(r'color\s*:\s*#(?:fff|ffffff)\b', 'color:var(--color-text)', full)

    def fix_color_gray_inline(m):
        full = m.group(0)
        if any(x in full for x in ['btn', 'button', 'badge', 'rounded-full', 'background']):
            return full
        return _re.sub(
            r'color\s*:\s*#(?:d1d5db|9ca3af|a0aec0|e2e8f0|cbd5e1|f3f4f6|e5e7eb)\b',
            'color:var(--color-muted)', full
        )

    # Corrigir color:#fff em tags de texto com style inline
    html = _re.sub(
        r'<(?:p|span|li|td|th|label|small|em|strong|h1|h2|h3|h4)[^>]+style="[^"]*color\s*:\s*#(?:fff|ffffff)[^"]*"[^>]*>',
        fix_color_white_inline, html, flags=_re.IGNORECASE
    )
    # Corrigir cinzas claros em tags de texto com style inline
    html = _re.sub(
        r'<(?:p|span|li|td|th|label|small|em|strong|h1|h2|h3|h4)[^>]+style="[^"]*color\s*:\s*#(?:d1d5db|9ca3af|a0aec0|e2e8f0|cbd5e1|f3f4f6|e5e7eb)[^"]*"[^>]*>',
        fix_color_gray_inline, html, flags=_re.IGNORECASE
    )

    # Substituir class text-white em tags de texto dentro de sections com bg claro/neutro
    def fix_section(m):
        section_tag = m.group(1)
        section_body = m.group(2)

        has_dark_bg = any(x in section_tag for x in [
            'var(--color-primary)', 'var(--color-accent)', 'var(--color-footer',
            'linear-gradient', '#1a1a', '#0f0f', '#111', '#000', '#2d2d', '#1f1f', '#0d0d'
        ])
        has_light_bg = any(x in section_tag for x in [
            'var(--color-background)', 'var(--color-surface)', '#f8f8', '#fff', '#faf', '#f0f'
        ])

        if has_dark_bg and not has_light_bg:
            return m.group(0)

        def fix_text_white_tag(tm):
            tag = tm.group(0)
            if any(x in tag for x in ['px-6', 'px-8', 'py-3', 'py-2', 'rounded-full', 'rounded-lg btn', 'cta']):
                return tag
            tag = _re.sub(r'(?<!\w)text-white(?!\w)', 'text-adaptive', tag)
            return tag

        section_body = _re.sub(
            r'<(?:h1|h2|h3|h4|p|span|li|td|th|label)[^>]*class="[^"]*text-white[^"]*"[^>]*>',
            fix_text_white_tag, section_body, flags=_re.IGNORECASE
        )
        return '<section' + section_tag + '>' + section_body + '</section>'

    html = _re.sub(
        r'<section([^>]*)>(.*?)</section>',
        fix_section, html, flags=_re.DOTALL
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
        return f"/tmp/liam_ckpt_{slug}.json"

    def _ckpt_load(slug):
        path = _ckpt_path(slug)
        if _os.path.exists(path):
            try:
                with open(path) as _f:
                    data = _json.load(_f)
                print(f"[Liam] Checkpoint encontrado: {len(data)} secoes ja prontas")
                return data
            except:
                pass
        return {}

    def _ckpt_save(slug, secoes_dict):
        try:
            with open(_ckpt_path(slug), 'w') as _f:
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
    fotos = getattr(prd, "photos", []) or []
    logo = getattr(prd, "logo_url", None)
    telefone = getattr(prd, "phone", "") or ""
    wnum = telefone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    whatsapp_url = "https://wa.me/55" + wnum
    maps_embed = getattr(prd, "google_maps_embed", "") or ""
    nl = chr(10)


    instrucao_diretor = getattr(prd, "instrucao_criativa_para_dev", None) or "Crie um layout moderno e responsivo com Tailwind."

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
        + "CSS variables: --color-primary:" + cores.primary
        + " --color-accent:" + cores.accent
        + " --color-background:" + cores.background
        + " --color-text:" + cores.text
    )

    # Open Design: instrucoes de componentes e layout para o Liam
    try:
        _od_segmento = getattr(prd, "segmento", "") or getattr(prd, "nicho", "") or ""
        _od_nome = prd.business_name or ""
        _od_tier = getattr(prd, "tier", "STANDARD") or "STANDARD"
        _od_ref = get_open_design_for_liam(_od_segmento, _od_nome, _od_tier)
        if _od_ref:
            contexto_global += "\n\n" + _od_ref
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
    _hero_layout = (_dc_tokens.get("hero_style") or {}).get("layout", "hero-split")
    _hero_overlay = (_dc_tokens.get("hero_style") or {}).get("overlay", "rgba(0,0,0,0.45)")
    _hero_img_style = (_dc_tokens.get("hero_style") or {}).get("img_style", "object-fit:cover;")

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

        # Reviews para secao depoimentos — NUNCA omitir
        reviews_instrucao = ""
        if nome_s.lower() in ("depoimentos", "reviews", "testimonials", "avaliacoes"):
            if reviews:
                reviews_instrucao = nl + "REVIEWS REAIS (use exatamente, sem inventar):" + nl + reviews_fmt
            else:
                print("[Liam] Secao depoimentos: sem reviews reais, gerando ficticios PAS")
                reviews_instrucao = nl + "SEM REVIEWS REAIS. Gere EXATAMENTE 3 depoimentos ficticios persuasivos usando framework PAS (Problema-Agitacao-Solucao). Use nomes genericos brasileiros (ex: Maria S., Carlos R., Ana P.). Cada depoimento deve: 1) mencionar uma dor real do nicho, 2) descrever a frustracao antes, 3) elogiar a solucao encontrada neste negocio. Rating 5 estrelas. Maximo 2 frases cada."

        copy_json = _json.dumps(copy_s, ensure_ascii=False)[:500]
        maps_instrucao = ""
        if nome_s == "localizacao" and maps_embed:
            maps_instrucao = nl + "GOOGLE MAPS EMBED (incorpore INTEGRALMENTE dentro da section):" + nl + maps_embed

        # System prompt fixo — cacheado pela Anthropic a partir da 2a chamada (mesmo texto em todas as secoes)
        system_liam = (
            "Voce e Liam, o pedreiro do frontend da FraLib." + nl
            + "Sua unica tarefa e gerar EXCLUSIVAMENTE uma tag HTML <section> completa e fechada." + nl
            + nl
            + "LAYOUTS DISPONIVEIS:" + nl
            + "hero-split=flex row texto 60% esq img 40% dir height:100vh | "
            + "hero-center=texto centralizado overlay escuro height:100vh | "
            + "sobre-timeline=lista vertical linha conectora | "
            + "sobre-grid=grid 2col texto esq mosaico fotos dir | "
            + "services-cards=grid 3col cards sombra hover | "
            + "services-accordion=lista chevron JS vanilla | "
            + "reviews-masonry=grid 3col altura variavel | "
            + "reviews-carousel=scroll horizontal snap | "
            + "location-split=grid 2col mapa esq info dir | "
            + "location-full=mapa full-width info abaixo | "
            + "contact-minimal=form centralizado fundo claro | "
            + "contact-split=info esq CTA dir" + nl
            + nl
            + "REGRAS ABSOLUTAS:" + nl
            + "1. Retorne APENAS o HTML da tag <section id=NOME> inteira e fechada." + nl
            + "2. Comece com <section. Nenhum texto antes. Nenhum markdown (```html)." + nl
            + "3. Use Tailwind CSS. NUNCA cores hardcoded — use var(--bg), var(--fg), var(--accent), var(--surface), var(--muted), var(--border)." + nl
            + "4. NUNCA invente dados, historias ou textos sobre o negocio. Use APENAS informacoes fornecidas no user prompt. Se nao ha dados sobre a historia do negocio, use frases genericas curtas como 'Atendimento de qualidade em [cidade]' — NUNCA crie narrativas ficticias." + nl
            + "5. NUNCA use height fixo exceto hero (height:100vh)." + nl
            + "6. NUNCA crie SVGs inline complexos. PROIBIDO Emojis para design. Para icones use Phosphor Icons CDN (<script src=\"https://unpkg.com/@phosphor-icons/web\"></script>) com classes (ex: <i class=\"ph-fill ph-star\"></i>)." + nl
            + "7. MAPA: Se os dados fornecerem um iframe do Google Maps valido (nao vazio), incorpore-o INTEGRALMENTE. Se nao houver iframe valido, exiba o endereco em texto com icone ph-fill ph-map-pin e um botao CTA linkando para o Google Maps — NUNCA exiba iframe vazio ou quebrado." + nl
            + "8. NUNCA use bolinhas com letras como logo. Se nao houver URL de logo, escreva o nome em texto Bold elegante (font-bold text-2xl)." + nl
            + "9. ANIMACOES OBRIGATORIAS: Hero: H1=.scale-in, subtitulo=.reveal, CTA=.pulse-cta. Sections: divs com .reveal. Cards: .stagger-item style=--i:N para entrada sequencial. Imagens: .reveal-left. Contadores: data-count=VALOR. Botoes: .btn-primary. PARALLAX: hero div background com data-parallax=0.3. MICRO-INTERACOES: Cards com hover:scale-[1.02] hover:shadow-lg transition-all duration-300." + nl
            + "10. OBEDIENCIA VISUAL ABSOLUTA: Sua unica bussola de design e a instrucao_criativa_para_dev acima. Se o Arquiteto mandar usar cores solidas, gradientes, glassmorphism, fotos reais ou texturas, voce DEVE aplicar rigorosamente via Tailwind. Voce nao tem opiniao de design — apenas executa com precisao cirurgica." + nl
            + "11. PRECOS PROIBIDOS: NUNCA mencione valores monetarios, precos, mensalidades ou planos com valores. Se a secao for de planos/precos, use apenas CTA: Consulte nossos valores ou Fale conosco para saber mais." + nl
            + "12. CONTRASTE OBRIGATORIO: Se um elemento tiver background escuro (var(--color-primary), var(--color-accent), cores hex escuras), o texto DENTRO dele deve ser claro (var(--color-text) no dark ou #ffffff). Se o background for claro (var(--color-surface), var(--color-background) no light), o texto deve ser escuro. NUNCA use var(--color-text) dentro de cards com background var(--color-primary) — use color:#ffffff ou color:var(--color-accent) para garantir contraste."
        )

        # User prompt variavel — muda por secao (dados do negocio + copy especifico)
        prompt_secao = (
            "ORDEM DO DIRETOR DE ARTE:" + nl
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

        print("[Liam] Gerando " + nome_s + " (layout: " + tipo_layout + ")...")
        try:
            resposta_secao = call_claude(
                system=system_liam,
                user=prompt_secao,
                model="opus",
                max_tokens=8000,
                temperature=0.4,
                agent_name="liam",
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
                )
                _continua = _continua.replace("```html", "").replace("```", "").strip()
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

    # Executar secoes SEQUENCIALMENTE — gc.collect() entre cada para liberar RAM
    import gc
    print("[Liam] Iniciando geracao SEQUENCIAL de " + str(len(_secoes_fonte)) + " secoes...")
    for _s_seq in _secoes_fonte:
        try:
            _nome_resultado, _html_resultado = _gerar_secao(_s_seq)
        except Exception as _fe:
            print("[Liam] Erro na secao: " + str(_fe)[:80])
        finally:
            gc.collect()

    # Montar html_final na ORDEM ORIGINAL do PRD
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
    return html_final.strip()


# Alias para compatibilidade com pipeline_endpoints.py
def gerar_html_main_single_pass(prd):
    return gerar_html_componentizado(prd)


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
    reviews_count = getattr(prd, "reviews_count", 10) or 10
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
        opening_hours = _ohs if _ohs else [
            {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"], "opens": "08:00", "closes": "18:00"},
        ]
    else:
        opening_hours = [
            {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"], "opens": "08:00", "closes": "18:00"},
            {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Saturday"], "opens": "08:00", "closes": "13:00"},
        ]
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
        "openingHoursSpecification": opening_hours,
        "hasMap": f"https://www.google.com/maps/search/{_re.sub(r'[^a-z0-9]+', '+', nome.lower())}+{_re.sub(r'[^a-z0-9]+', '+', cidade.lower())}",
    }
    if rating and float(rating) > 0:
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
    _easing_std = _anim_profile.get("easing_std", "cubic-bezier(0.4,0.0,0.2,1)")
    _easing_ent = _anim_profile.get("easing_enter","cubic-bezier(0.0,0.0,0.2,1)")
    _stagger    = _anim_profile.get("stagger",    "60ms")
    if logo:
        logo_html = ("<img src=" + q + logo + q + " class=" + q + "h-10 w-auto object-contain" + q
            + " alt=" + q + "Logo " + nome + q + " loading=" + q + "eager" + q + ">")
    else:
        logo_html = ("<div class=" + q + "h-10 w-10 rounded-full flex items-center justify-center font-bold" + q
            + " style=" + q + "background:var(--accent);color:var(--bg)" + q + ">" + nome[0].upper() + "</div>")
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
        + "<link href=" + q + "https://fonts.googleapis.com/css2?family=" + _font_heading.replace(" ","+") + ":wght@400;600;700;800&family=" + _font_body.replace(" ","+") + ":wght@400;500;600&display=swap" + q + " rel=" + q + "stylesheet" + q + ">" + chr(10)
        + "<script src=" + q + "https://cdn.tailwindcss.com" + q + "></script>" + chr(10)
        + "<style id=" + q + "fralib-tokens" + q + ">" + chr(10)
        + ":root {" + chr(10)
        + "  --bg:      " + _bg      + ";" + chr(10)
        + "  --surface: " + _surface + ";" + chr(10)
        + "  --fg:      " + _fg      + ";" + chr(10)
        + "  --muted:   " + _muted   + ";" + chr(10)
        + "  --border:  " + _border  + ";" + chr(10)
        + "  --accent:  " + _accent  + ";" + chr(10)
        + "  /* compat aliases — remover após migração completa */" + chr(10)
        + "  --color-primary:    " + _fg     + ";" + chr(10)
        + "  --color-accent:     " + _accent + ";" + chr(10)
        + "  --color-background: " + _bg     + ";" + chr(10)
        + "  --color-text:       " + _fg     + ";" + chr(10)
        + "  --color-surface:    " + _surface+ ";" + chr(10)
        + "  --color-border:     " + _border + ";" + chr(10)
        + "  --color-muted:      " + _muted  + ";" + chr(10)
        + "  /* animação */" + chr(10)
        + "  --dur-enter:    " + _enter_dur  + ";" + chr(10)
        + "  --dur-feedback: " + _feedback   + ";" + chr(10)
        + "  --ease-std:     " + _easing_std + ";" + chr(10)
        + "  --ease-enter:   " + _easing_ent + ";" + chr(10)
        + "  --stagger:      " + _stagger    + ";" + chr(10)
        + "}" + chr(10)
        + "body { font-family: '" + _font_body + "', sans-serif; background: var(--bg); color: var(--fg); }" + chr(10)
        + "h1,h2,h3,h4 { font-family: '" + _font_heading + "', serif; font-weight: 700; }" + chr(10)
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
        + "</style>" + chr(10)
        + "<script src=" + q + "https://unpkg.com/@phosphor-icons/web@2.1.1" + q + "></script>" + chr(10)
        + "</head>" + chr(10)
        + "<body>" + chr(10)
        + """<style>
:root {
  --bg:      """ + _bg + """;
  --surface: """ + _surface + """;
  --fg:      """ + _fg + """;
  --muted:   """ + _muted + """;
  --border:  """ + _border + """;
  /* compat aliases */
  --color-background: """ + _bg + """;
  --color-text: """ + _fg + """;
  --color-surface: """ + _surface + """;
  --color-border: """ + _border + """;
  --color-muted: """ + _muted + """;
  --color-header-bg: color-mix(in oklch, var(--bg) 92%, transparent);
  --color-header-border: color-mix(in oklch, var(--border) 80%, transparent);
  --color-footer-bg: oklch(13% 0.01 0);
  --color-footer-text: oklch(95% 0.005 0);
  --color-footer-muted: oklch(70% 0.005 0);
  --color-footer-border: oklch(25% 0.01 0);
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
        + "      <span class=" + q + "font-bold text-sm hidden sm:block" + q + " style=" + q + "color:var(--color-text)" + q + ">" + nome + "</span>" + chr(10)
        + "    </a>" + chr(10)
        + "    <nav class=" + q + "hidden md:flex items-center gap-6 text-sm font-medium" + q + " style=" + q + "color:var(--color-muted)" + q + ">" + chr(10)
        + _gerar_nav_links(prd, q)
        + "    </nav>" + chr(10)
        + "    <div class=" + q + "flex items-center gap-3" + q + ">" + chr(10)


        + "      <a href=" + q + whatsapp_url + q + " target=" + q + "_blank" + q + " rel=" + q + "noopener" + q
        + " class=" + q + "px-4 py-2 rounded-xl text-white text-sm font-semibold transition-transform hover:scale-105" + q
        + " style=" + q + "background:var(--color-accent)" + q + ">WhatsApp</a>" + chr(10)
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
        + "<div><h3>Hor&aacute;rios</h3><ul>" + _horas_html + "</ul></div>" + nl
        + "<div><h3>Contato</h3>"
        + ("<p class=" + q + "text-sm mb-2" + q + ">" + endereco + "</p>" if endereco else "")
        + "<a href=" + q + "tel:" + telefone.replace(" ","").replace("(","").replace(")","").replace("-","") + q + " class=" + q + "block text-sm mb-3" + q + ">" + telefone + "</a>"
        + "<a href=" + q + whatsapp_url + q + " target=" + q + "_blank" + q + " rel=" + q + "noopener" + q + " class=" + q + "footer-cta" + q + "><i class=" + q + "ph-fill ph-whatsapp-logo" + q + "></i> Falar no WhatsApp</a>"
        + "<a href=" + q + "/politica-de-privacidade" + q + " class=" + q + "block text-xs mt-4" + q + ">Pol&iacute;tica de Privacidade</a></div>" + nl
        + "</div>" + nl
        + "<div class=" + q + "border-t footer-divider pt-6 flex flex-col md:flex-row items-center justify-between gap-3" + q + ">"
        + "<p class=" + q + "text-xs" + q + ">&copy; " + str(_ano) + " " + nome + " &mdash; Todos os direitos reservados.</p>"
        + "<p class=" + q + "text-xs" + q + ">Site criado por <a href=" + q + "https://fralib.com.br" + q + " target=" + q + "_blank" + q + " rel=" + q + "noopener" + q + ">FraLib</a></p></div>" + nl
        + "</div></footer>" + nl
        + """<script>
(function(){
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
    document.querySelectorAll('.reveal,.reveal-left,.scale-in').forEach(function(el,i){
      el.style.setProperty('--i',i%6);
      io.observe(el);
    });
    // Stagger items
    document.querySelectorAll('.stagger-item').forEach(function(el,i){
      el.style.setProperty('--i',i);
    });
  // Typewriter effect on hero H1 — reveal char by char on page load
  (function(){
    var mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    if(mq.matches) return;
    var h1 = document.querySelector('#hero h1');
    if(!h1) return;
    var text = h1.textContent;
    var dur = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--dur-enter')) || 0.6;
    var delay = dur * 1000;
    h1.textContent = '';
    h1.style.visibility = 'visible';
    var i = 0;
    var interval = delay / Math.max(text.length, 1);
    interval = Math.min(Math.max(interval, 20), 60);
    function tick(){
      if(i < text.length){ h1.textContent += text[i++]; setTimeout(tick, interval); }
    }
    setTimeout(tick, 80);
  })();
  });
})();
</script>""" + nl
        + _gerar_lgpd_banner(prd) + nl
        + "</body></html>" + nl
    )
    return header + "<main id=" + q + "fralib-content" + q + " class=" + q + "w-full overflow-hidden pt-20" + q + ">" + nl + html_main + nl + "</main>" + nl + footer
