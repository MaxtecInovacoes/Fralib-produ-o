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
from memory import salvar_memoria
from liam_seo import gerar_seo_tags, gerar_whatsapp_float

# Importar modulos Liam

SYSTEM_LIAM_SINGLE_PASS = (
    "Voce e Liam, desenvolvedor frontend senior especializado em HTML/Tailwind CSS estatico. "
    "Voce e CEGO PARA DESIGN PROPRIO — nao tem opiniao sobre cores, layout ou estetica. "
    "Voce executa EXATAMENTE a instrucao_criativa_para_dev fornecida pelo Arquiteto Mestre. "
    "Sua unica tarefa: gerar as sections internas do site dentro do main. "
    "REGRAS ABSOLUTAS: "
    "1. Retorne APENAS tags section. NUNCA inclua DOCTYPE, html, head, body, header, footer ou scripts. "
    "2. Use Tailwind CSS via CDN (ja incluido na pagina). "
    "3. CORES: NUNCA use cores hardcoded. SEMPRE use CSS variables: var(--color-primary), var(--color-accent), var(--color-background), var(--color-text), var(--color-surface). "
    "4. PROIBIDO usar o atributo style para definir cores. Use classes Tailwind ou CSS variables. "
    "5. SECOES crescem livremente. NUNCA use height fixo (exceto hero: height:100vh). "
    "6. TIPOGRAFIA REGRA ABSOLUTA: h1 usa clamp(1.8rem,4vw,3rem) via style. h2 MAXIMO text-3xl — NUNCA use font-size inline em h2 (nem clamp, nem rem, nem px). h3 MAXIMO text-2xl — NUNCA use font-size inline em h3. Corpo usa text-base ou text-lg. PROIBIDO em h1/h2/h3/p: text-4xl, text-5xl, text-6xl, text-7xl, text-8xl e qualquer font-size inline maior que 2rem. Icones (i, svg) e contadores decorativos (span numerico) podem usar text-4xl max. tracking-widest APENAS em labels com text-xs. NUNCA tracking-widest em h1, h2, h3, p. leading-relaxed maximo. "
    "7. DADOS: use APENAS os dados fornecidos. NUNCA invente nomes, enderecos ou depoimentos. "
    "8. TEMA DIA/NOITE: NUNCA use rgba(241,245,249,...) ou rgba(255,255,255,...) como cor de texto. SEMPRE use var(--color-text) para texto principal e var(--color-muted) para texto secundario. O site tem toggle dia/noite — cores hardcoded brancas ficam invisiveis no modo claro. "
    "8b. DEPOIMENTOS: se reviews_list vazio, retorne section vazia: <section id=\"depoimentos\"></section>. NUNCA invente depoimentos, nomes ou avaliacoes. NUNCA use fotos de pessoas em depoimentos — use div com inicial. NUNCA coloque depoimentos em outras secoes (hero, sobre, servicos). "
    "9. FOTOS: Use APENAS as URLs de fotos fornecidas nos dados. NUNCA use URLs do Unsplash, Pexels, Pixabay ou qualquer outro site externo. Se nao houver fotos fornecidas, use div colorido com icone Phosphor — NUNCA busque imagens externas. Hero usa loading=eager. Demais loading=lazy. REGRA DE FERRO: ZERO faces humanas — NUNCA use crop=face, NUNCA foto de pessoa real. Para depoimentos, use div.w-12.h-12.rounded-full com inicial do nome. "
    "10. H1: deve conter nome do negocio E cidade. "
    "11. PRECOS: NUNCA mencione valores. Use CTA: Consulte nossos valores. "
    "12. ANIMACOES: classes reveal, reveal-left, scale-in, card-3d, stagger-reveal nas tags. "
    "13. WHATSAPP: use exatamente a URL fornecida. "
    "14. GRID: proporcao 60/40 ou 40/60. NUNCA 50/50. "
    "15. AVATAR DEPOIMENTOS: div.w-12.h-12.rounded-full com inicial + style=background:var(--color-primary). NUNCA foto de pessoa. "
    "16. LAYOUT_TYPE: o PRD informa o layout desejado para cada secao (ex: hero-split, services-cards). "
    "    Voce DEVE usar Tailwind para criar a estrutura visual exata solicitada: "
    "    hero-split = flex row, texto 60% esquerda, imagem 40% direita. "
    "    hero-center = texto centralizado, overlay escuro sobre imagem de fundo. "
    "    sobre-timeline = lista vertical com linha conectora e pontos. "
    "    sobre-grid = grid 2 colunas, texto esquerda, mosaico de fotos direita. "
    "    services-cards = grid 3 colunas, cards com sombra e hover elevado. "
    "    services-accordion = lista com chevron, expande ao clicar (JS vanilla). "
    "    reviews-masonry = grid 3 colunas com cards de altura variavel. "
    "    reviews-carousel = scroll horizontal com snap. "
    "    location-split = grid 2 colunas, mapa esquerda, info direita. "
    "    location-full = mapa full-width, info centralizada abaixo. "
    "    contact-minimal = formulario centralizado, fundo claro. "
    "    contact-split = info de contato esquerda, CTA whatsapp direita. "
    "    Seja criativo na construcao do DOM para honrar o layout_type. "
    "17. INICIO: comece diretamente com <section id=hero. Nenhum texto antes. "
    "18. BOTOES FUNCIONAIS OBRIGATORIO: TODOS os botoes e links devem ter href valido. "
    "CTAs de contato/whatsapp/agendar/falar/ligar devem usar href='https://wa.me/{wnum}' (wnum sera substituido). "
    "CTAs de navegacao interna (Saiba mais, Ver servicos, Conheca, Ver planos) devem usar href='#{id_secao}' "
    "(ex: href='#sobre', href='#servicos', href='#planos', href='#contato'). "
    "NUNCA use href='#' vazio ou href='javascript:void(0)'. "
    "Botao de hero CTA principal sempre aponta para whatsapp. Botao secundario aponta para #sobre ou #servicos."
)



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

def _sanitizar_unsplash(html):
    """Remove fotos externas (Unsplash/Pexels) com faces e substitui por avatar com inicial."""
    import re as _re

    def fix_img_face(m):
        full = m.group(0)
        src = m.group(1)
        alt = _re.search(r'alt="([^"]*)"', full)
        alt_text = alt.group(1) if alt else ""
        # Extrair inicial do nome do alt (ex: "Foto de Carlos M." -> "C")
        nome_match = _re.search(r'(?:Foto de |de )([A-Za-zÀ-ú]+)', alt_text)
        inicial = nome_match.group(1)[0].upper() if nome_match else "C"
        # Substituir por div avatar
        return (
            f'<div class="w-10 h-10 rounded-full flex items-center justify-center '
            f'font-bold text-white text-sm flex-shrink-0" '
            f'style="background:var(--color-primary)">{inicial}</div>'
        )

    # Remover <img> com URLs externas (unsplash, pexels, pixabay, googleusercontent com crop=face)
    html = _re.sub(
        r'<img[^>]+src="(https?://(?:images\.unsplash\.com|source\.unsplash\.com|images\.pexels\.com|[^"]*crop=face)[^"]*)"[^>]*>',
        fix_img_face, html
    )
    return html


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
    html = _re.sub(r"<a[^>]+href=[^>]*>[^<]{0,80}</a>", fix_href, html, flags=_re.DOTALL)

    return html


def gerar_html_componentizado(prd):
    """
    Arquitetura Diretor-Operario: uma chamada de API por secao.
    O Arquiteto Mestre (Diretor) define a instrucao criativa.
    O Liam (Operario) executa secao por secao com payloads leves.
    Evita Erro 529 do proxy mantendo cada chamada em ~50-100 linhas de HTML.
    """
    import json as _json
    import re as _re_sp
    import os as _os
    from llm_direct import call_claude

    # ===== CHECKPOINT HELPERS =====
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
    fotos = getattr(prd, "photos", []) or []
    logo = getattr(prd, "logo_url", None)
    telefone = getattr(prd, "phone", "") or ""
    wnum = telefone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    whatsapp_url = "https://wa.me/55" + wnum
    maps_embed = getattr(prd, "google_maps_embed", "") or ""
    nl = chr(10)

    # Instrucao criativa do Diretor de Arte (ArquitetoMestre)
    instrucao_diretor = getattr(prd, "instrucao_criativa_para_dev", None) or "Crie um layout moderno e responsivo com Tailwind."

    # Contexto global compartilhado por todas as secoes
    contexto_global = (
        "Negocio: " + prd.business_name + nl
        + "Telefone: " + telefone + nl
        + "WhatsApp: " + whatsapp_url + nl
        + "Rating: " + str(prd.reviews_rating) + "/5 (" + str(prd.reviews_count) + " avaliacoes)" + nl
        + "Logo: " + (logo or "nao disponivel") + nl
        + "Maps embed: " + (maps_embed or "nao disponivel") + nl
        + "Fotos: " + (nl.join(fotos[:6]) if fotos else "Nenhuma - use Unsplash para o segmento") + nl
        + "CSS variables: --color-primary:" + cores.primary
        + " --color-accent:" + cores.accent
        + " --color-background:" + cores.background
        + " --color-text:" + cores.text
    )

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

    # ===== CHECKPOINT: carregar secoes ja geradas =====
    _ckpt_slug_val = _ckpt_slug(prd.business_name)
    _secoes_prontas = _ckpt_load(_ckpt_slug_val)

    print("[Liam] Iniciando geracao componente por componente para " + prd.business_name + "...")
    print("[Liam] Instrucao do Diretor: " + instrucao_diretor[:80] + "...")
    if _secoes_prontas:
        print("[Liam] Retomando de checkpoint: " + str(list(_secoes_prontas.keys())))

    # Reconstruir html_final com secoes ja prontas (ordem do PRD)
    for _s_prev in _secoes_fonte:
        _sd = _s_prev.dict() if hasattr(_s_prev, "dict") else (_s_prev if isinstance(_s_prev, dict) else {})
        _n = _sd.get("name", "")
        if _n and _n in _secoes_prontas:
            html_final += _secoes_prontas[_n]
            secoes_processadas += 1

    for s in _secoes_fonte:
        s_dict = s.dict() if hasattr(s, "dict") else (s if isinstance(s, dict) else {})
        nome_s = s_dict.get("name", "")
        tipo_layout = s_dict.get("layout_type", "padrao")
        copy_s = s_dict.get("copy", {}) or {}
        omitir_s = s_dict.get("omitir", False)

        if not nome_s or omitir_s or nome_s.lower() == "footer":
            if omitir_s and nome_s:
                print("[Liam] Omitindo secao: " + nome_s)
            if nome_s == "footer":
                print("[Liam] Secao footer omitida — rodape gerado pelo template")
            continue

        # Pular secoes ja no checkpoint
        if nome_s in _secoes_prontas:
            print("[Liam] " + nome_s + ": ja no checkpoint, pulando")
            continue

        # Reviews apenas para secao depoimentos
        reviews_instrucao = ""
        if nome_s.lower() in ("depoimentos", "reviews", "testimonials", "avaliacoes"):
            if not reviews:
                print("[Liam] Secao depoimentos: sem reviews reais, omitindo")
                continue
            reviews_instrucao = nl + "REVIEWS REAIS (use exatamente, sem inventar):" + nl + reviews_fmt

        copy_json = _json.dumps(copy_s, ensure_ascii=False)[:500]
        # Fix 3: injetar Google Maps embed explicitamente na secao localizacao
        maps_instrucao = ""
        if nome_s == "localizacao" and maps_embed:
            maps_instrucao = nl + "GOOGLE MAPS EMBED (incorpore INTEGRALMENTE dentro da section):" + nl + maps_embed

        prompt_secao = (
            "Voce e Liam, o pedreiro do frontend." + nl
            + "Sua unica tarefa e gerar EXCLUSIVAMENTE a tag HTML <section id=\"" + nome_s + "\">." + nl
            + nl
            + "ORDEM DO DIRETOR DE ARTE:" + nl
            + instrucao_diretor + nl
            + nl
            + "LAYOUT ESCOLHIDO PELO DIRETOR: " + tipo_layout + nl
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
            + "DADOS DO NEGOCIO:" + nl + contexto_global + nl
            + nl
            + "COPY DESTA SECAO (use exatamente):" + nl + copy_json
            + reviews_instrucao + nl
            + nl
            + "REGRAS ABSOLUTAS:" + nl
            + "1. Retorne APENAS o HTML da tag <section id=\"" + nome_s + "\"> inteira e fechada." + nl
            + "2. Comece com <section. Nenhum texto antes. Nenhum markdown (```html)." + nl
            + "3. Use Tailwind CSS. NUNCA cores hardcoded — use var(--color-primary), var(--color-accent) etc." + nl
            + "4. NUNCA invente dados — use apenas os fornecidos acima." + nl
            + "5. NUNCA use height fixo exceto hero (height:100vh)." + nl
            + "6. NUNCA crie SVGs inline complexos. PROIBIDO Emojis para design. Para icones use Phosphor Icons CDN (<script src=\"https://unpkg.com/@phosphor-icons/web\"></script>) com classes (ex: <i class=\"ph-fill ph-star\"></i>)." + nl
            + "7. MAPA: Se os dados fornecerem um iframe do Google Maps valido (nao vazio), incorpore-o INTEGRALMENTE. Se nao houver iframe valido, exiba o endereco em texto com icone ph-fill ph-map-pin e um botao CTA linkando para o Google Maps — NUNCA exiba iframe vazio ou quebrado." + nl
            + "8. NUNCA use bolinhas com letras como logo. Se nao houver URL de logo, escreva o nome em texto Bold elegante (font-bold text-2xl)." + nl
            + "9. Use atributos data-aos='fade-up' nas divs principais para animacao de scroll (AOS ja esta carregado no footer)." + nl
            + "10. OBEDIENCIA VISUAL ABSOLUTA: Sua unica bussola de design e a instrucao_criativa_para_dev acima. Se o Arquiteto mandar usar cores solidas, gradientes, glassmorphism, dark mode, fotos reais ou texturas, voce DEVE aplicar rigorosamente via Tailwind. Voce nao tem opiniao de design — apenas executa com precisao cirurgica." + nl
            + "11. PRECOS PROIBIDOS: NUNCA mencione valores monetarios, precos, mensalidades ou planos com valores. Se a secao for de planos/precos, use apenas CTA: Consulte nossos valores ou Fale conosco para saber mais." + nl
            + "12. CONTRASTE OBRIGATORIO: Se um elemento tiver background escuro (var(--color-primary), var(--color-accent), cores hex escuras), o texto DENTRO dele deve ser claro (var(--color-text) no dark ou #ffffff). Se o background for claro (var(--color-surface), var(--color-background) no light), o texto deve ser escuro. NUNCA use var(--color-text) dentro de cards com background var(--color-primary) — use color:#ffffff ou color:var(--color-accent) para garantir contraste."
        )

        print("[Liam] Gerando " + nome_s + " (layout: " + tipo_layout + ")...")
        try:
            if maps_instrucao:
                prompt_secao += maps_instrucao
            resposta_secao = call_claude(
                system="Voce e um gerador rigoroso de codigo HTML estruturado com Tailwind. Retorne APENAS a tag section solicitada. SEMPRE feche com </section>.",
                user=prompt_secao,
                model="sonnet",
                max_tokens=8000,
                temperature=0.4,
            )
            # Auto-Continue: se secao truncada, continuar de onde parou
            _auto_continue = 0
            while "</section>" not in resposta_secao[-500:].lower() and _auto_continue < 2:
                _auto_continue += 1
                print("[Liam] " + nome_s + ": truncada — auto-continue " + str(_auto_continue) + "/2")
                _continua = call_claude(
                    system="Voce e um gerador de codigo HTML continuo. Continue EXATAMENTE de onde o codigo anterior parou.",
                    user="O codigo HTML foi cortado no meio. Continue escrevendo EXATAMENTE de onde parou. Nao repita codigo anterior. Nao adicione saudacoes ou markdown. Apenas continue o HTML ate fechar </section>.",
                    model="sonnet",
                    max_tokens=4000,
                    temperature=0.1,
                )
                _continua = _continua.replace("```html", "").replace("```", "").strip()
                resposta_secao += nl + _continua
            # Limpeza do raw text
            resposta_secao = resposta_secao.replace("```html", "").replace("```", "").strip()
            # Remover lixo antes do <section
            _fs = resposta_secao.lower().find("<section")
            if _fs > 0:
                resposta_secao = resposta_secao[_fs:]
            # Garantir que termina no </section>
            _ls = resposta_secao.lower().rfind("</section>")
            if _ls > 0:
                resposta_secao = resposta_secao[:_ls + len("</section>")]
            # Remover tags de documento
            resposta_secao = _re_sp.sub(r"(?i)<!DOCTYPE[^>]*>", "", resposta_secao)
            resposta_secao = _re_sp.sub(r"(?i)<html[^>]*>|</html>", "", resposta_secao)
            resposta_secao = _re_sp.sub(r"(?i)<head[^>]*>.*?</head>", "", resposta_secao, flags=_re_sp.DOTALL)
            resposta_secao = _re_sp.sub(r"(?i)<body[^>]*>|</body>", "", resposta_secao)
            resposta_secao = resposta_secao.strip()

            if resposta_secao and len(resposta_secao) > 50:
                # Garantir fechamento da tag section
                if not resposta_secao.lower().rstrip().endswith("</section>"):
                    print("[Liam] " + nome_s + ": secao nao fechada — forcando </section>")
                    resposta_secao = resposta_secao.rstrip() + nl + "</section>"
                # Envolver com comentarios SECTION para a Liz editar cirurgicamente
                _bloco_html = ("<!-- SECTION:" + nome_s + " -->" + nl
                    + resposta_secao + nl
                    + "<!-- /SECTION:" + nome_s + " -->" + nl + nl)
                # Nao duplicar se ja veio do checkpoint
                if nome_s not in _secoes_prontas:
                    html_final += _bloco_html
                    secoes_processadas += 1
                    _secoes_prontas[nome_s] = _bloco_html
                    _ckpt_save(_ckpt_slug_val, _secoes_prontas)
                print("[Liam] " + nome_s + ": " + str(len(resposta_secao)) + " chars OK")
            else:
                print("[Liam] " + nome_s + ": resposta vazia, pulando")
        except Exception as _e:
            print("[Liam] Erro " + nome_s + ": " + str(_e)[:80])

    print("[Liam] Componentizado: " + str(secoes_processadas) + " secoes, " + str(len(html_final)) + " chars total")
    html_final = _sanitizar_fontes(html_final)
    print("[Liam] Fontes sanitizadas")
    html_final = _sanitizar_cores_light(html_final)
    print("[Liam] Cores light sanitizadas")
    html_final = _sanitizar_unsplash(html_final)
    print("[Liam] Fotos externas sanitizadas")
    html_final = _sanitizar_botoes(html_final, wnum)
    print("[Liam] Botoes sanitizados")
    _ckpt_clear(_ckpt_slug_val)  # Limpar checkpoint apos conclusao bem-sucedida
    return html_final.strip()


# Alias para compatibilidade com pipeline_endpoints.py
def gerar_html_main_single_pass(prd):
    return gerar_html_componentizado(prd)



def _gerar_seo_inline(prd) -> str:
    """Gera meta tags SEO determinísticas a partir do PRD."""
    import unicodedata as _ud, re as _re
    nome = getattr(prd, "business_name", "") or ""
    cidade = getattr(prd, "cidade", "") or ""
    segmento = getattr(prd, "segmento", "") or ""
    telefone = getattr(prd, "phone", "") or ""
    rating = getattr(prd, "rating", 0) or 0
    fotos = getattr(prd, "photos", []) or []
    image_url = fotos[0] if fotos else ""
    desc = f"{segmento.capitalize()} em {cidade}. Atendimento personalizado e resultados reais."
    slug = _re.sub(r"[^a-z0-9]+", "-", _ud.normalize("NFKD", nome.lower()).encode("ascii", "ignore").decode()).strip("-")[:50]
    canonical = f"https://seunegociofralib.site/sites/{slug}/"
    wnum = telefone.replace(" ","").replace("-","").replace("(","").replace(")","")
    schema = (
        '{"@context":"https://schema.org","@type":"LocalBusiness",'
        f'"name":"{nome}","description":"{desc}",'
        f'"address":{{"@type":"PostalAddress","addressLocality":"{cidade}"}},'
        f'"telephone":"{telefone}",'
        f'"aggregateRating":{{"@type":"AggregateRating","ratingValue":"{rating}","reviewCount":"10"}}}}'
    )
    return (
        f'''<link rel="icon" type="image/x-icon" href="https://fralib.com.br/favicon.ico">
<meta name="description" content="{desc}">
<meta name="robots" content="index, follow">
<meta property="og:title" content="{nome}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{image_url}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{canonical}">
<script type="application/ld+json">{schema}</script>'''
    )


def _gerar_lgpd_banner(prd) -> str:
    """Banner LGPD com consentimento de cookies — determinístico."""
    return """<div id="lgpd-banner" style="display:none;position:fixed;bottom:0;left:0;right:0;z-index:9999;background:#1a1a2e;border-top:1px solid rgba(255,255,255,0.1);padding:16px 24px;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;">
  <p style="margin:0;font-size:0.8rem;color:#94a3b8;max-width:700px;">
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

def montar_template_python(html_main, prd):
    cores = prd.color_palette
    telefone = getattr(prd, "phone", "") or ""
    wnum = telefone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    whatsapp_url = "https://wa.me/55" + wnum
    logo = getattr(prd, "logo_url", None)
    nome = prd.business_name
    endereco = getattr(prd, "address", "") or ""
    secondary = getattr(cores, "secondary", "#f9fafb") or "#f9fafb"
    q = chr(34)
    if logo:
        logo_html = ("<img src=" + q + logo + q + " class=" + q + "h-10 w-auto object-contain" + q
            + " alt=" + q + "Logo " + nome + q + " loading=" + q + "eager" + q + ">")
    else:
        logo_html = ("<div class=" + q + "h-10 w-10 rounded-full flex items-center justify-center text-white font-bold" + q
            + " style=" + q + "background:var(--color-primary)" + q + ">" + nome[0].upper() + "</div>")
    header = (
        "<!DOCTYPE html>" + chr(10)
        + "<html lang=" + q + "pt-BR" + q + ">" + chr(10)
        + "<head>" + chr(10)
        + "<meta charset=" + q + "UTF-8" + q + ">" + chr(10)
        + "<meta name=" + q + "viewport" + q + " content=" + q + "width=device-width, initial-scale=1.0" + q + ">" + chr(10)
        + "<title>" + nome + "</title>" + chr(10)
        + _gerar_seo_inline(prd) + chr(10)
        + "<link href=" + q + "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@700;800;900&family=Inter:wght@400;500;600&display=swap" + q + " rel=" + q + "stylesheet" + q + ">" + chr(10)
        + "<script src=" + q + "https://cdn.tailwindcss.com" + q + "></script>" + chr(10)
        + "<style id=" + q + "fralib-colors" + q + ">" + chr(10)
        + ":root {" + chr(10)
        + "  --color-primary: " + cores.primary + ";" + chr(10)
        + "  --color-secondary: " + secondary + ";" + chr(10)
        + "  --color-accent: " + cores.accent + ";" + chr(10)
        + "  --color-background: " + cores.background + ";" + chr(10)
        + "  --color-text: " + cores.text + ";" + chr(10)
        + "  --color-surface: #f9fafb;" + chr(10)
        + "  --color-border: #e5e7eb;" + chr(10)
        + "  --color-muted: #6b7280;" + chr(10)
        + "}" + chr(10)
        + "body { font-family: Inter, sans-serif; background: var(--color-background); color: var(--color-text); }" + chr(10)
        + "h1,h2,h3 { font-family: " + q + "Plus Jakarta Sans" + q + ", sans-serif; font-weight: 800; }" + chr(10)
        + "</style>" + chr(10)
        + "<link rel=" + q + "stylesheet" + q + " href=" + q + "https://unpkg.com/aos@2.3.4/dist/aos.css" + q + ">" + chr(10)
        + "<script src=" + q + "https://unpkg.com/@phosphor-icons/web@2.1.1" + q + "></script>" + chr(10)
        + "</head>" + chr(10)
        + "<body data-theme=" + q + "dark" + q + ">" + chr(10)
        + """<style>
/* Toggle dia/noite — adapta TODAS as CSS vars automaticamente */
[data-theme="dark"] {
  --color-background: """ + cores.background + """;
  --color-text: #f1f5f9;
  --color-surface: #111111;
  --color-border: rgba(255,255,255,0.08);
  --color-muted: rgba(240,240,245,0.45);
  --color-header-bg: rgba(10,10,10,0.92);
  --color-header-border: rgba(255,255,255,0.07);
  --color-footer-bg: #0d0d0d;
}
[data-theme="light"] {
  --color-background: #f8f8f8;
  --color-text: #111111;
  --color-surface: #ffffff;
  --color-primary: """ + cores.accent + """;
  --color-secondary: """ + cores.secondary + """;
  --color-border: rgba(0,0,0,0.08);
  --color-muted: #6b7280;
  --color-header-bg: rgba(255,255,255,0.95);
  --color-header-border: rgba(0,0,0,0.07);
  --color-footer-bg: #1a1a2e;
}
body { background: var(--color-background); color: var(--color-text); transition: background 0.3s, color 0.3s; }
#fralib-header { background: var(--color-header-bg); border-bottom: 1px solid var(--color-header-border); }
#theme-toggle { cursor:pointer; background:none; border:1px solid var(--color-border); border-radius:999px; padding:6px 12px; color:var(--color-text); font-size:0.8rem; display:flex; align-items:center; gap:6px; transition:all 0.2s; }
#theme-toggle:hover { border-color: var(--color-accent); }
</style>
""" + chr(10)
        + "<header id=" + q + "fralib-header" + q + " class=" + q + "fixed top-0 left-0 right-0 z-50 backdrop-blur-md shadow-sm transition-all duration-300" + q + ">" + chr(10)
        + "  <div class=" + q + "max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4" + q + ">" + chr(10)
        + "    <a href=" + q + "#hero" + q + " class=" + q + "flex items-center gap-3 no-underline" + q + ">" + chr(10)
        + "      " + logo_html + chr(10)
        + "      <span class=" + q + "font-bold text-sm hidden sm:block" + q + " style=" + q + "color:var(--color-text)" + q + ">" + nome + "</span>" + chr(10)
        + "    </a>" + chr(10)
        + "    <nav class=" + q + "hidden md:flex items-center gap-6 text-sm font-medium" + q + " style=" + q + "color:var(--color-muted)" + q + ">" + chr(10)
        + "      <a href=" + q + "#sobre" + q + " class=" + q + "hover:text-current transition-colors" + q + " style=" + q + "color:var(--color-muted)" + q + ">Sobre</a>" + chr(10)
        + "      <a href=" + q + "#servicos" + q + " class=" + q + "hover:text-current transition-colors" + q + " style=" + q + "color:var(--color-muted)" + q + ">Serviços</a>" + chr(10)
        + "      <a href=" + q + "#depoimentos" + q + " class=" + q + "hover:text-current transition-colors" + q + " style=" + q + "color:var(--color-muted)" + q + ">Depoimentos</a>" + chr(10)
        + "      <a href=" + q + "#localizacao" + q + " class=" + q + "hover:text-current transition-colors" + q + " style=" + q + "color:var(--color-muted)" + q + ">Localização</a>" + chr(10)
        + "    </nav>" + chr(10)
        + "    <div class=" + q + "flex items-center gap-3" + q + ">" + chr(10)
        + "      <button id=" + q + "theme-toggle" + q + " aria-label=" + q + "Alternar tema" + q + " onclick=" + q + "toggleTheme()" + q + ">" + chr(10)
        + "        <span id=" + q + "theme-icon" + q + ">☀️</span><span id=" + q + "theme-label" + q + ">Dia</span>" + chr(10)
        + "      </button>" + chr(10)
        + "      <a href=" + q + whatsapp_url + q + " target=" + q + "_blank" + q + " rel=" + q + "noopener" + q
        + " class=" + q + "px-4 py-2 rounded-xl text-white text-sm font-semibold transition-transform hover:scale-105" + q
        + " style=" + q + "background:var(--color-accent)" + q + ">WhatsApp</a>" + chr(10)
        + "    </div>" + chr(10)
        + "  </div>" + chr(10)
        + "</header>" + chr(10)
        + "<script>function toggleTheme(){var b=document.body;var t=b.getAttribute('data-theme')==='dark'?'light':'dark';b.setAttribute('data-theme',t);document.getElementById('theme-icon').textContent=t==='dark'?'☀️':'🌙';document.getElementById('theme-label').textContent=t==='dark'?'Dia':'Noite';localStorage.setItem('fralib-theme',t);}(function(){var s=localStorage.getItem('fralib-theme');if(s){document.body.setAttribute('data-theme',s);document.getElementById('theme-icon').textContent=s==='dark'?'☀️':'🌙';document.getElementById('theme-label').textContent=s==='dark'?'Dia':'Noite';}})();</script>" + chr(10)
    )
    footer = (
        "<footer style=" + q + "background:var(--color-footer-bg);color:var(--color-text);border-top:1px solid var(--color-border);" + q + ">" + chr(10)
        + "  <div class=" + q + "max-w-7xl mx-auto px-6 py-16 grid grid-cols-1 md:grid-cols-3 gap-10" + q + ">" + chr(10)
        + "    <div>" + chr(10)
        + "      " + logo_html + chr(10)
        + "      <p class=" + q + "mt-4 text-sm leading-relaxed" + q + " style=" + q + "color:var(--color-muted)" + q + ">" + nome + " — " + (prd.segmento if hasattr(prd, 'segmento') else 'Academia') + " em " + (prd.cidade if hasattr(prd, 'cidade') else '') + "</p>" + chr(10)
        + "    </div>" + chr(10)
        + "    <div>" + chr(10)
        + "      <p class=" + q + "font-semibold mb-4 text-sm tracking-widest uppercase" + q + " style=" + q + "color:var(--color-accent)" + q + ">Contato</p>" + chr(10)
        + "      <p class=" + q + "text-sm mb-2" + q + " style=" + q + "color:var(--color-muted)" + q + ">" + (endereco or "Campina Grande do Sul, PR") + "</p>" + chr(10)
        + "      <a href=" + q + "tel:" + telefone.replace(" ","").replace("(","").replace(")","").replace("-","") + q + " class=" + q + "text-sm block mb-2 hover:underline" + q + " style=" + q + "color:var(--color-muted)" + q + ">" + telefone + "</a>" + chr(10)
        + "      <a href=" + q + whatsapp_url + q + " target=" + q + "_blank" + q + " class=" + q + "text-sm font-semibold hover:underline" + q + " style=" + q + "color:var(--color-accent)" + q + ">Falar no WhatsApp</a>" + chr(10)
        + "    </div>" + chr(10)
        + "    <div>" + chr(10)
        + "      <p class=" + q + "font-semibold mb-4 text-sm tracking-widest uppercase" + q + " style=" + q + "color:var(--color-accent)" + q + ">Links</p>" + chr(10)
        + "      <a href=" + q + "#sobre" + q + " class=" + q + "block text-sm mb-2 hover:underline" + q + " style=" + q + "color:var(--color-muted)" + q + ">Sobre nós</a>" + chr(10)
        + "      <a href=" + q + "#servicos" + q + " class=" + q + "block text-sm mb-2 hover:underline" + q + " style=" + q + "color:var(--color-muted)" + q + ">Serviços</a>" + chr(10)
        + "      <a href=" + q + "#contato" + q + " class=" + q + "block text-sm mb-2 hover:underline" + q + " style=" + q + "color:var(--color-muted)" + q + ">Contato</a>" + chr(10)
        + "      <a href=" + q + "/politica-de-privacidade" + q + " class=" + q + "block text-sm hover:underline" + q + " style=" + q + "color:var(--color-muted)" + q + ">Política de Privacidade</a>" + chr(10)
        + "    </div>" + chr(10)
        + "  </div>" + chr(10)
        + "  <div class=" + q + "border-t text-center py-6 text-xs" + q + " style=" + q + "border-color:var(--color-border);color:var(--color-muted)" + q + ">" + chr(10)
        + "    &copy; " + nome + " &mdash; Todos os direitos reservados" + chr(10)
        + "  </div>" + chr(10)
        + "</footer>" + chr(10)
        + "<script src=" + q + "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js" + q + " defer></script>" + chr(10)
        + "<script src=" + q + "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js" + q + " defer></script>" + chr(10)
        + "<script src=" + q + "https://unpkg.com/aos@2.3.4/dist/aos.js" + q + " defer></script>" + chr(10)
        + "<script>document.addEventListener('DOMContentLoaded',function(){if(typeof AOS!=='undefined')AOS.init({duration:700,once:true,offset:80});});</script>" + chr(10)
        + _gerar_lgpd_banner(prd) + chr(10)
        + _gerar_wpp_float(prd) + chr(10)
        + "</body>" + chr(10)
        + "</html>" + chr(10)
    )
    return header + "<main id=" + q + "fralib-content" + q + " class=" + q + "w-full overflow-hidden pt-20" + q + ">" + chr(10) + html_main + chr(10) + "</main>" + chr(10) + footer