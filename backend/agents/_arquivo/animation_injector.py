import re
import hashlib

ANIMATION_PROFILES = {
    0: {'name': 'cinematic',  'ease': 'power4.out',      'duration': '1.2'},
    1: {'name': 'energetic',  'ease': 'back.out(1.7)',   'duration': '0.8'},
    2: {'name': 'elegant',    'ease': 'power2.inOut',    'duration': '1.4'},
    3: {'name': 'playful',    'ease': 'elastic.out(1,0.5)', 'duration': '1.0'},
}

def get_animation_profile(nome: str) -> dict:
    seed = int(hashlib.md5(nome.encode()).hexdigest()[:8], 16)
    return ANIMATION_PROFILES[seed % 4]

def inject_animation_classes(html: str, nome: str) -> str:
    profile = get_animation_profile(nome)
    print(f"[AnimationInjector] Perfil: {profile['name']} para {nome}")

    # h2 sem classe de animacao -> reveal
    def add_reveal_h2(match):
        tag = match.group(0)
        if 'reveal' not in tag and 'stagger' not in tag and 'scale-in' not in tag:
            if 'class="' in tag:
                tag = re.sub(r'class="', 'class="reveal ', tag, count=1)
            else:
                tag = tag.replace('<h2', '<h2 class="reveal"', 1)
        return tag
    html = re.sub(r'<h2[^>]*>', add_reveal_h2, html)

    # h3 sem classe -> reveal-left
    def add_reveal_h3(match):
        tag = match.group(0)
        if 'reveal' not in tag and 'stagger' not in tag:
            if 'class="' in tag:
                tag = re.sub(r'class="', 'class="reveal-left ', tag, count=1)
            else:
                tag = tag.replace('<h3', '<h3 class="reveal-left"', 1)
        return tag
    html = re.sub(r'<h3[^>]*>', add_reveal_h3, html)

    # divs com "card" na classe -> card-3d
    def add_card_3d(match):
        tag = match.group(0)
        if 'card-3d' not in tag and 'no-anim' not in tag:
            tag = re.sub(r'class="', 'class="card-3d ', tag, count=1)
        return tag
    html = re.sub(r'<div[^>]*class="[^"]*\bcard\b[^"]*"[^>]*>', add_card_3d, html)

    # imagens lazy fora do hero -> image-zoom
    def add_image_zoom(match):
        tag = match.group(0)
        if 'image-zoom' not in tag and 'logo' not in tag.lower():
            if 'class="' in tag:
                tag = re.sub(r'class="', 'class="image-zoom ', tag, count=1)
            else:
                tag = tag.replace('<img', '<img class="image-zoom"', 1)
        return tag
    html = re.sub(r'<img[^>]*loading="lazy"[^>]*>', add_image_zoom, html)

    # links WhatsApp -> magnetic
    def add_magnetic(match):
        tag = match.group(0)
        if 'magnetic' not in tag and 'wpp-float' not in tag:
            if 'class="' in tag:
                tag = re.sub(r'class="', 'class="magnetic ', tag, count=1)
            else:
                tag = tag.replace('<a', '<a class="magnetic"', 1)
        return tag
    html = re.sub(r'<a[^>]*href="https://wa\.me[^"]*"[^>]*>', add_magnetic, html)

    # primeiros 3 grids/flex containers -> stagger-reveal
    count = [0]
    def add_stagger(match):
        if count[0] >= 3:
            return match.group(0)
        tag = match.group(0)
        if 'stagger-reveal' not in tag:
            tag = re.sub(r'class="', 'class="stagger-reveal ', tag, count=1)
            count[0] += 1
        return tag
    html = re.sub(r'<div[^>]*class="[^"]*(?:grid|flex)[^"]*(?:gap|cols)[^"]*"[^>]*>', add_stagger, html)

    n_reveal  = html.count('reveal')
    n_card3d  = html.count('card-3d')
    n_mag     = html.count('magnetic')
    print(f"[AnimationInjector] Injetado: {n_reveal} reveals, {n_card3d} card-3d, {n_mag} magnetic")
    return html
