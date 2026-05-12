"""
animation_profile.py - Perfis de animacao por nicho para o Liam.
Mapeia segmento -> intensidade, timing, easing e classes CSS especificas.
Baseado nos padroes do Open Design (nexu-io/open-design) e skills ui-animation/motion-designer.
"""


def get_animation_profile(segmento: str) -> dict:
    """
    Retorna perfil de animacao para o segmento.
    Faz matching parcial (ex: 'Clinica Medica' -> 'clinica').
    """
    _PROFILES = {
        # SAUDE & BEM-ESTAR (suave, clean, confianca)
        "clinica": dict(
            intensity="low", duration_base=300, duration_reveal=700, stagger_ms=80,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="gradient-animated", typewriter=False, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.02, hover_lift=True,
            gradient_animated=True, color_vibe="cool",
            description="Suave e profissional. Transmite confianca e cuidado. Animacoes lentas e fluidas."
        ),
        "medico": dict(
            intensity="low", duration_base=300, duration_reveal=700, stagger_ms=80,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="gradient-animated", typewriter=False, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.02, hover_lift=True,
            gradient_animated=True, color_vibe="cool",
            description="Suave e profissional. Transmite confianca e cuidado. Animacoes lentas e fluidas."
        ),
        "dentista": dict(
            intensity="low", duration_base=280, duration_reveal=650, stagger_ms=70,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="gradient-animated", typewriter=False, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.02, hover_lift=True,
            gradient_animated=True, color_vibe="cool",
            description="Clean e moderno. Branco dominante com accent azul/verde. Animacoes discretas."
        ),
        "odontologica": dict(
            intensity="low", duration_base=280, duration_reveal=650, stagger_ms=70,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="gradient-animated", typewriter=False, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.02, hover_lift=True,
            gradient_animated=True, color_vibe="cool",
            description="Clean e moderno. Branco dominante com accent azul/verde. Animacoes discretas."
        ),
        "nutricionista": dict(
            intensity="low", duration_base=300, duration_reveal=700, stagger_ms=80,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.03, hover_lift=True,
            gradient_animated=True, color_vibe="warm",
            description="Acolhedor e saudavel. Tons verdes/terrosos. Typewriter no H1 para engajamento."
        ),
        "psicologia": dict(
            intensity="low", duration_base=350, duration_reveal=800, stagger_ms=100,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="static", typewriter=False, pulse_cta=False,
            scroll_reveal="fade-in", hover_scale=1.01, hover_lift=False,
            gradient_animated=False, color_vibe="warm",
            description="Muito suave e acolhedor. Sem animacoes agressivas. Foco em seguranca emocional."
        ),
        "estetica": dict(
            intensity="medium", duration_base=280, duration_reveal=600, stagger_ms=60,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.32, 0.72, 0, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.04, hover_lift=True,
            gradient_animated=True, color_vibe="warm",
            description="Elegante e sofisticado. Tons rose/dourado. Animacoes fluidas com toque de luxo."
        ),
        "farmacia": dict(
            intensity="low", duration_base=250, duration_reveal=600, stagger_ms=60,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="gradient-animated", typewriter=False, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.02, hover_lift=True,
            gradient_animated=True, color_vibe="cool",
            description="Confiavel e acessivel. Verde farmacia. Animacoes simples e diretas."
        ),

        # FITNESS & ESPORTE (energetico, dinamico)
        "academia": dict(
            intensity="high", duration_base=200, duration_reveal=500, stagger_ms=40,
            easing="cubic-bezier(0.32, 0.72, 0, 1)", easing_spring="cubic-bezier(0.34, 1.56, 0.64, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="slide-left", hover_scale=1.06, hover_lift=True,
            gradient_animated=True, color_vibe="energetic",
            description="Energetico e motivador. Dark mode preferencial. Animacoes rapidas e impactantes."
        ),
        "crossfit": dict(
            intensity="high", duration_base=180, duration_reveal=450, stagger_ms=35,
            easing="cubic-bezier(0.32, 0.72, 0, 1)", easing_spring="cubic-bezier(0.34, 1.56, 0.64, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="slide-left", hover_scale=1.07, hover_lift=True,
            gradient_animated=True, color_vibe="energetic",
            description="Intenso e desafiador. Preto/laranja/vermelho. Animacoes agressivas e rapidas."
        ),
        "fitness": dict(
            intensity="high", duration_base=200, duration_reveal=500, stagger_ms=40,
            easing="cubic-bezier(0.32, 0.72, 0, 1)", easing_spring="cubic-bezier(0.34, 1.56, 0.64, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="slide-left", hover_scale=1.05, hover_lift=True,
            gradient_animated=True, color_vibe="energetic",
            description="Dinamico e motivador. Animacoes rapidas com spring physics."
        ),
        "personal": dict(
            intensity="medium", duration_base=220, duration_reveal=550, stagger_ms=50,
            easing="cubic-bezier(0.32, 0.72, 0, 1)", easing_spring="cubic-bezier(0.34, 1.56, 0.64, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.04, hover_lift=True,
            gradient_animated=True, color_vibe="energetic",
            description="Profissional e motivador. Equilibrio entre energia e credibilidade."
        ),
        # GASTRONOMIA
        "restaurante": dict(
            intensity="medium", duration_base=250, duration_reveal=600, stagger_ms=60,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.05, hover_lift=True,
            gradient_animated=True, color_vibe="warm",
            description="Aconchegante e apetitoso. Tons quentes. Typewriter para criar expectativa."
        ),
        "lanchonete": dict(
            intensity="medium", duration_base=230, duration_reveal=550, stagger_ms=50,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.05, hover_lift=True,
            gradient_animated=True, color_vibe="warm",
            description="Descontraido e convidativo. Animacoes medias com energia positiva."
        ),
        "padaria": dict(
            intensity="low", duration_base=300, duration_reveal=700, stagger_ms=80,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="gradient-animated", typewriter=False, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.03, hover_lift=True,
            gradient_animated=True, color_vibe="warm",
            description="Artesanal e aconchegante. Tons terrosos/dourados. Animacoes suaves e organicas."
        ),
        "confeitaria": dict(
            intensity="medium", duration_base=280, duration_reveal=650, stagger_ms=70,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.32, 0.72, 0, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="scale-in", hover_scale=1.05, hover_lift=True,
            gradient_animated=True, color_vibe="warm",
            description="Delicado e sofisticado. Tons rose/bege. Scale-in para revelar produtos."
        ),
        "cafe": dict(
            intensity="low", duration_base=320, duration_reveal=750, stagger_ms=90,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="gradient-animated", typewriter=False, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.03, hover_lift=True,
            gradient_animated=True, color_vibe="warm",
            description="Aconchegante e artesanal. Marrom/creme. Animacoes lentas e relaxantes."
        ),
        # BELEZA & ESTILO
        "salao": dict(
            intensity="medium", duration_base=270, duration_reveal=620, stagger_ms=65,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.32, 0.72, 0, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.04, hover_lift=True,
            gradient_animated=True, color_vibe="warm",
            description="Elegante e feminino. Tons rose/dourado/preto. Animacoes fluidas e sofisticadas."
        ),
        "barbearia": dict(
            intensity="medium", duration_base=240, duration_reveal=580, stagger_ms=55,
            easing="cubic-bezier(0.32, 0.72, 0, 1)", easing_spring="cubic-bezier(0.34, 1.56, 0.64, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="slide-left", hover_scale=1.04, hover_lift=True,
            gradient_animated=True, color_vibe="neutral",
            description="Masculino e premium. Preto/dourado/cobre. Animacoes com atitude e precisao."
        ),

        # JURIDICO & PROFISSIONAL
        "advocacia": dict(
            intensity="low", duration_base=350, duration_reveal=800, stagger_ms=100,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="static", typewriter=False, pulse_cta=False,
            scroll_reveal="fade-in", hover_scale=1.02, hover_lift=False,
            gradient_animated=False, color_vibe="neutral",
            description="Sobrio e autoritario. Azul marinho/cinza. Animacoes minimas para transmitir seriedade."
        ),
        "contabilidade": dict(
            intensity="low", duration_base=300, duration_reveal=700, stagger_ms=80,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="static", typewriter=False, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.02, hover_lift=True,
            gradient_animated=False, color_vibe="neutral",
            description="Confiavel e preciso. Azul/cinza. Animacoes discretas e profissionais."
        ),
        # IMOVEIS & ARQUITETURA
        "imobiliaria": dict(
            intensity="medium", duration_base=280, duration_reveal=650, stagger_ms=70,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.32, 0.72, 0, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.04, hover_lift=True,
            gradient_animated=True, color_vibe="neutral",
            description="Premium e aspiracional. Branco/dourado/preto. Animacoes elegantes e lentas."
        ),
        "arquitetura": dict(
            intensity="medium", duration_base=300, duration_reveal=700, stagger_ms=80,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.32, 0.72, 0, 1)",
            hero_style="gradient-animated", typewriter=False, pulse_cta=True,
            scroll_reveal="scale-in", hover_scale=1.03, hover_lift=True,
            gradient_animated=True, color_vibe="neutral",
            description="Minimalista e sofisticado. Branco/cinza/preto. Scale-in para revelar projetos."
        ),
        # EDUCACAO
        "escola": dict(
            intensity="medium", duration_base=250, duration_reveal=600, stagger_ms=60,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.04, hover_lift=True,
            gradient_animated=True, color_vibe="cool",
            description="Acessivel e motivador. Azul/verde. Typewriter para engajar. Animacoes medias."
        ),
        "curso": dict(
            intensity="medium", duration_base=250, duration_reveal=600, stagger_ms=60,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.04, hover_lift=True,
            gradient_animated=True, color_vibe="cool",
            description="Acessivel e motivador. Azul/verde. Typewriter para engajar. Animacoes medias."
        ),
        # PET & AUTO
        "pet": dict(
            intensity="medium", duration_base=250, duration_reveal=580, stagger_ms=55,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.05, hover_lift=True,
            gradient_animated=True, color_vibe="warm",
            description="Carinhoso e confiavel. Verde/laranja. Animacoes amigaveis e acolhedoras."
        ),
        "veterinaria": dict(
            intensity="low", duration_base=280, duration_reveal=650, stagger_ms=70,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
            hero_style="gradient-animated", typewriter=False, pulse_cta=True,
            scroll_reveal="fade-up", hover_scale=1.03, hover_lift=True,
            gradient_animated=True, color_vibe="cool",
            description="Confiavel e cuidadoso. Verde/azul. Animacoes suaves transmitindo cuidado."
        ),
        "auto": dict(
            intensity="medium", duration_base=220, duration_reveal=550, stagger_ms=50,
            easing="cubic-bezier(0.32, 0.72, 0, 1)", easing_spring="cubic-bezier(0.34, 1.56, 0.64, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="slide-left", hover_scale=1.04, hover_lift=True,
            gradient_animated=True, color_vibe="neutral",
            description="Tecnico e confiavel. Cinza/azul/laranja. Animacoes com precisao mecanica."
        ),
        "mecanica": dict(
            intensity="medium", duration_base=220, duration_reveal=550, stagger_ms=50,
            easing="cubic-bezier(0.32, 0.72, 0, 1)", easing_spring="cubic-bezier(0.34, 1.56, 0.64, 1)",
            hero_style="gradient-animated", typewriter=True, pulse_cta=True,
            scroll_reveal="slide-left", hover_scale=1.04, hover_lift=True,
            gradient_animated=True, color_vibe="neutral",
            description="Tecnico e confiavel. Cinza/azul/laranja. Animacoes com precisao mecanica."
        ),
        # FOTOGRAFIA & CRIATIVO
        "fotografia": dict(
            intensity="medium", duration_base=300, duration_reveal=700, stagger_ms=80,
            easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.32, 0.72, 0, 1)",
            hero_style="gradient-animated", typewriter=False, pulse_cta=True,
            scroll_reveal="scale-in", hover_scale=1.05, hover_lift=True,
            gradient_animated=True, color_vibe="neutral",
            description="Visual e artistico. Preto/branco com accent. Scale-in para revelar fotos."
        ),
    }

    _DEFAULT = dict(
        intensity="medium", duration_base=260, duration_reveal=620, stagger_ms=65,
        easing="cubic-bezier(0.22, 1, 0.36, 1)", easing_spring="cubic-bezier(0.25, 1, 0.5, 1)",
        hero_style="gradient-animated", typewriter=True, pulse_cta=True,
        scroll_reveal="fade-up", hover_scale=1.04, hover_lift=True,
        gradient_animated=True, color_vibe="neutral",
        description="Profissional e moderno. Animacoes equilibradas para qualquer nicho."
    )

    seg = segmento.lower().strip()
    if seg in _PROFILES:
        return _PROFILES[seg]
    for key, profile in _PROFILES.items():
        if key in seg or seg in key:
            return profile
    return _DEFAULT


def format_animation_context(segmento: str) -> str:
    p = get_animation_profile(segmento)
    return (
        f"=== ANIMATION_PROFILE para {segmento} ===\n"
        f"Intensidade: {p['intensity']} | Vibe: {p['color_vibe']}\n"
        f"Tom: {p['description']}\n\n"
        f"Timing:\n"
        f"  duration_base: {p['duration_base']}ms\n"
        f"  duration_reveal: {p['duration_reveal']}ms\n"
        f"  stagger_ms: {p['stagger_ms']}ms\n\n"
        f"Easing:\n"
        f"  transicoes: {p['easing']}\n"
        f"  spring: {p['easing_spring']}\n\n"
        f"Animacoes ativas:\n"
        f"  hero_style: {p['hero_style']}\n"
        f"  typewriter_h1: {p['typewriter']}\n"
        f"  pulse_cta: {p['pulse_cta']}\n"
        f"  scroll_reveal: {p['scroll_reveal']}\n"
        f"  hover_scale: {p['hover_scale']}\n"
        f"  hover_lift: {p['hover_lift']}\n"
        f"  gradient_animated: {p['gradient_animated']}\n\n"
        f"CSS vars (definidas no wrapper):\n"
        f"  --duration-base: {p['duration_base']}ms\n"
        f"  --duration-reveal: {p['duration_reveal']}ms\n"
        f"  --stagger-ms: {p['stagger_ms']}ms\n"
        f"  --easing: {p['easing']}\n"
        f"  --easing-spring: {p['easing_spring']}\n"
    )
