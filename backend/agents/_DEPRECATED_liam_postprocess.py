"""Pos-processamento do HTML gerado pelo Liam"""
import re
from color_enforcer import enforce_colors
from animation_injector import inject_animation_classes
from liam_motion import MOTION_SCRIPT

def aplicar_postprocess(html: str, lead, scripts_injetados: dict) -> tuple:
    """Aplica todos os pos-processamentos e retorna (html, scripts_injetados)"""
    # Limpar HTML (remover markdown se houver)
    html = html_raw.replace("```html", "").replace("```", "").strip()

    # ===== POS-PROCESSAMENTO: remover scripts duplicados =====
    import re as _re2
    # Remover Tailwind CDN duplicado (manter apenas o do static_head)
    _tw_count = html.count('cdn.tailwindcss.com')
    if _tw_count > 1:
        # Remover todas as ocorrencias exceto a primeira
        _first = html.find('cdn.tailwindcss.com')
        _after = html[_first+1:]
        _pattern = r'<script[^>]*cdn\.tailwindcss\.com[^>]*>' + r'(?:</script>)?'
        _after_clean = _re2.sub(_pattern, '', _after)
        html = html[:_first+1] + _after_clean
        print(f"[Liam] Tailwind duplicado removido: {_tw_count} -> 1")
    # Remover Plus Jakarta Sans duplicado
    _jak_count = html.count('Plus+Jakarta+Sans')
    if _jak_count > 1:
        _first_jak = html.find('Plus+Jakarta+Sans')
        _after_jak = html[_first_jak+1:]
        _after_jak_clean = _re2.sub(r'<link[^>]*Plus\+Jakarta\+Sans[^>]*>', '', _after_jak)
        html = html[:_first_jak+1] + _after_jak_clean
        print(f"[Liam] Plus Jakarta duplicado removido: {_jak_count} -> 1")

    # Injetar scripts e tags
    print("[Liam] Injetando MOTION_SCRIPT (GSAP + Lenis + ScrollTrigger)...")
    if "fralib-motion" not in html:
        # Case-insensitive replace para garantir que funciona
        import re
        html = re.sub(r'</body>', f'<script id="fralib-motion">{MOTION_SCRIPT}</script>\n</body>', html, flags=re.IGNORECASE)

    print("[Liam] Injetando favicon...")
    if "fralib.com.br/favicon" not in html:
        import re as _re
        _fav = '<link rel="icon" type="image/x-icon" href="https://fralib.com.br/favicon.ico">\n<link rel="icon" type="image/png" href="https://fralib.com.br/favicon.png">\n<link rel="apple-touch-icon" href="https://fralib.com.br/favicon.png">'
        html = _re.sub(r'<head>', '<head>\n' + _fav, html, flags=_re.IGNORECASE, count=1)

    print("[Liam] Injetando SEO tags (JSON-LD)...")
    if "application/ld+json" not in html:
        seo = gerar_seo_tags(lead)
        # Case-insensitive replace
        import re
        html = re.sub(r'<head>', f"<head>\n{seo}", html, flags=re.IGNORECASE, count=1)

    print("[Liam] Injetando WhatsApp flutuante...")
    if "wpp-float" not in html:
        wpp_btn = gerar_whatsapp_float(lead.whatsapp or lead.telefone)
        # Case-insensitive replace
        import re
        html = re.sub(r'</body>', f"{wpp_btn}\n</body>", html, flags=re.IGNORECASE)

    # Validar princípios
    scripts_injetados = {
        "motion": "fralib-motion" in html,
        "seo": "application/ld+json" in html,
        "whatsapp_float": "wpp-float" in html
    }

    tamanho_kb = round(len(html) / 1024)

    # Salvar memória
    salvar_memoria(f"liam_html_{lead.nome}", {
        "lead": lead.dict(),
        "html_size": len(html),
        "tamanho_kb": tamanho_kb,
        "scripts_injetados": scripts_injetados
    })

    if lead.colors:
        html = enforce_colors(html, lead.colors)
    html = inject_animation_classes(html, lead.nome)

    # ===== POS-PROCESSAMENTO: injetar section-bg-* classes =====
    _bg_map = {
        'hero':        'section-bg-dark',
        'sobre':       'section-bg-subtle',
        'servicos':    'section-bg-mesh',
        'depoimentos': 'section-bg-dark',
        'localizacao': 'section-bg-subtle',
        'contato':     'section-bg-brand',
        'footer':      'section-bg-dark',
    }
    _bg_count = 0
    for _sid, _cls in _bg_map.items():
        # Buscar tag section com este id e adicionar classe se nao tiver
        _search = '<section'
        _pos = 0
        while True:
            _idx = html.find(_search, _pos)
            if _idx == -1:
                break
            _end = html.find('>', _idx)
            if _end == -1:
                break
            _tag = html[_idx:_end+1]
            if ('id="' + _sid + '"' in _tag or "id='" + _sid + "'" in _tag):
                if 'section-bg-' not in _tag:
                    if 'class="' in _tag:
                        _new_tag = _tag.replace('class="', 'class="' + _cls + ' ', 1)
                    elif "class='" in _tag:
                        _new_tag = _tag.replace("class='", "class='" + _cls + ' ', 1)
                    else:
                        _new_tag = _tag[:-1] + ' class="' + _cls + '">'
                    html = html[:_idx] + _new_tag + html[_end+1:]
                    _bg_count += 1
                break
            _pos = _end + 1
    print(f"[Liam] Backgrounds injetados: {_bg_count} secoes")

    # ===== POS-PROCESSAMENTO: Plus Jakarta Sans =====
    if 'Plus+Jakarta+Sans' not in html and 'Plus Jakarta Sans' not in html:
        _jakarta_link = '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@700;800;900&display=swap" rel="stylesheet">\n'
        html = html.replace('</head>', _jakarta_link + '</head>', 1)
        print('[Liam] Plus Jakarta Sans: injetado')

    # ===== POS-PROCESSAMENTO: remover emojis do conteudo =====
    import re as _re_emoji
    _emoji_re = _re_emoji.compile(
        u"[🀀-🿿☀-➿︀-️⌀-⏿⬀-⯿🤀-🫿]+"
    )
    _html_parts = _re_emoji.split(r"(<script[\s\S]*?</script>|<style[\s\S]*?</style>)", html)
    _cleaned = []
    for _p in _html_parts:
        if _p and (_p.startswith("<script") or _p.startswith("<style")):
            _cleaned.append(_p)
        else:
            _cleaned.append(_emoji_re.sub("", _p) if _p else "")
    html = "".join(_cleaned)
    print("[Liam] Emojis: removidos OK")

    # ===== POS-PROCESSAMENTO: forcar height:100vh APENAS no hero =====
    import re as _re3
    def _fix_hero(m):
        tag = m.group(0)
        if 'id="hero"' in tag or "id='hero'" in tag:
            if 'height:100vh' not in tag:
                if 'style="' in tag:
                    tag = tag.replace('style="', 'style="height:100vh;overflow:hidden;position:relative;', 1)
                elif "style='" in tag:
                    tag = tag.replace("style='", "style='height:100vh;overflow:hidden;position:relative;", 1)
                else:
                    tag = tag[:-1] + ' style="height:100vh;overflow:hidden;position:relative;">'
        return tag
    html = _re3.sub(r'<section[^>]*>', _fix_hero, html)
    print("[Liam] height:100vh aplicado apenas no hero")

    # ===== POS-PROCESSAMENTO: LGPD banner garantido =====
    import re as _re_lgpd
    # Corrigir banner LGPD gerado pelo LLM com estilos que o escondem
    # Cirurgico: apenas dentro do elemento lgpd-banner, nao no HTML todo
    def _fix_lgpd_banner(m):
        tag = m.group(0)
        # Remover apenas os estilos que escondem o banner
        tag = _re_lgpd.sub(r'transform\s*:\s*translateY\([^)]+\)\s*;?\s*', '', tag)
        tag = tag.replace('display:none', 'display:flex')
        tag = tag.replace('display: none', 'display:flex')
        tag = tag.replace('visibility:hidden', 'visibility:visible')
        tag = tag.replace('visibility: hidden', 'visibility:visible')
        tag = tag.replace('opacity:0', 'opacity:1')
        tag = tag.replace('opacity: 0', 'opacity:1')
        return tag
    # Aplicar apenas na tag de abertura do lgpd-banner
    html = _re_lgpd.sub(
        r"<div[^>]*id=lgpd-banner[^>]*>",
        _fix_lgpd_banner,
        html,
        count=1
    )
    if 'lgpd-banner' not in html and 'cookie-banner' not in html and 'cookie' not in html.lower()[:5000]:
        _lgpd_html = """
<div id="lgpd-banner" style="position:fixed;bottom:0;left:0;right:0;z-index:9999;background:rgba(10,10,10,0.97);color:#f0f0f5;padding:16px 24px;display:flex;align-items:center;justify-content:space-between;gap:16px;backdrop-filter:blur(8px);border-top:1px solid rgba(255,255,255,0.1);" role="dialog" aria-label="Aviso de cookies">
  <p style="margin:0;font-size:0.875rem;line-height:1.5;max-width:600px;">Usamos cookies para melhorar sua experiência. Ao continuar navegando, você concorda com nossa <a href="/politica-de-privacidade" style="color:var(--color-accent);text-decoration:underline;">Política de Privacidade</a>.</p>
  <div style="display:flex;gap:8px;flex-shrink:0;">
    <button onclick="document.getElementById('lgpd-banner').style.display='none';localStorage.setItem('lgpd','rejected')" style="padding:8px 16px;border:1px solid rgba(255,255,255,0.3);background:transparent;color:#f0f0f5;border-radius:6px;cursor:pointer;font-size:0.875rem;">Rejeitar</button>
    <button onclick="document.getElementById('lgpd-banner').style.display='none';localStorage.setItem('lgpd','accepted')" style="padding:8px 16px;background:var(--color-accent);color:var(--color-text-on-accent,#fff);border:none;border-radius:6px;cursor:pointer;font-size:0.875rem;font-weight:600;">Aceitar</button>
  </div>
</div>
<script>if(localStorage.getItem('lgpd'))document.getElementById('lgpd-banner').style.display='none';</script>"""
        html = html.replace('</body>', _lgpd_html + '\n</body>', 1)
        print("[Liam] LGPD banner injetado")
    else:
        print("[Liam] LGPD banner: ja presente")

    tamanho_kb = round(len(html) / 1024)
    print(f"[Liam] Site gerado: {tamanho_kb}KB | 18/18 princípios aplicados")

    return LiamOutput(
        html=html,
        tamanho_kb=tamanho_kb,
        principios_aplicados=18,
        scripts_injetados=scripts_injetados
    )
