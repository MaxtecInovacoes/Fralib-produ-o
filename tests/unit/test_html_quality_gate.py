import os
import re
import sys
from types import SimpleNamespace

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from agents.html_quality_gate import (
    HtmlQualityGateError,
    normalize_generated_html_for_publication,
    sanitize_builder_html_for_publication,
    validate_generated_html,
)


PHOTOS = [
    "https://images.unsplash.com/photo-a",
    "https://images.unsplash.com/photo-b",
    "https://images.unsplash.com/photo-c",
    "https://images.unsplash.com/photo-d",
]


def _with_experience_hero(html: str, title: str) -> str:
    """Add the minimum premium hero contract expected from the canonical renderer."""
    hero = f"""
    <!-- SECTION:hero -->
    <section id="hero" class="fralib-deterministic-hero" data-reveal
      style="background-image:linear-gradient(120deg,#030303,#18202a);">
      <div class="fralib-hero-depth" data-parallax></div>
      <h1>{title}</h1>
      <a class="magnetic-btn shadow" href="#contato">Entrar em contato</a>
      <span class="fralib-proof-chip">Presença local</span>
      <span data-reveal></span><span data-reveal></span><span data-reveal></span>
      <span data-reveal></span><span data-reveal></span>
    </section>
    <!-- /SECTION:hero -->
    <script>new IntersectionObserver(() => null);</script>
    """
    return html.replace("<body>", f"<body>{hero}", 1)


def _prd():
    return SimpleNamespace(
        business_name="Aquaflex Jardim Paulista",
        address="Av. Augusto Staben, 1410, Jardim Paulista, Campina Grande do Sul",
        phone="(41) 99984-3014",
        photos=PHOTOS,
        reviews_count=297,
        reviews_rating=4.7,
        animations=[{"name": "fade-in"}],
        sections=[
            {
                "name": "hero",
                "copy": {"h1": "Aquaflex Jardim Paulista"},
            },
            {
                "name": "sobre",
                "copy": {"h2": "Estrutura para natacao"},
            },
            {
                "name": "servicos",
                "copy": {"h2": "Aulas de natacao para sua rotina"},
            },
            {
                "name": "localizacao",
                "copy": {"h2": "Localizacao em Campina Grande do Sul"},
            },
        ],
    )


@pytest.mark.unit
def test_quality_gate_rejects_placeholders_fake_metrics_and_fake_contact():
    html = """<!doctype html><html><head><style>.ph-img{}</style></head><body>
    <h1>Aquaflex</h1>
    <p>[ Piscina da Aquaflex · 16:9 ]</p>
    <p>500+ alunos, 98% melhora, R$ 50 aula experimental</p>
    <footer>Rua Augusta, 1230 · Vila Madalena · contato@aquaflexjp.com.br</footer>
    </body></html>"""

    with pytest.raises(HtmlQualityGateError) as err:
        validate_generated_html(html, _prd())

    msg = str(err.value)
    assert "placeholder" in msg
    assert "email nao confirmado" in msg
    assert "percentual nao confirmado" in msg
    assert "preco nao confirmado" in msg


@pytest.mark.unit
def test_quality_gate_allows_no_media_unless_explicitly_required():
    prd = _prd()
    prd.photos = []
    prd.animations = []
    html = """<!doctype html><html><head>
    <style>@keyframes fade{from{opacity:0}to{opacity:1}}</style>
    </head><body>
    <h1>Aquaflex Jardim Paulista</h1>
    <h2>Estrutura para natacao</h2>
    <h2>Aulas de natacao para sua rotina</h2>
    <h2>Localizacao em Campina Grande do Sul</h2>
    <p>Av. Augusto Staben, 1410, Jardim Paulista, Campina Grande do Sul</p>
    <p>4,7/5 com 297 avaliacoes reais.</p>
    </body></html>"""

    validate_generated_html(normalize_generated_html_for_publication(_with_experience_hero(html, "Aquaflex Jardim Paulista"), prd), prd)


@pytest.mark.unit
def test_publication_normalizer_rewrites_client_root_logo_links():
    prd = _prd()
    html = """<!doctype html><html><body>
    <a class="brand" href="/">Aquaflex</a>
    <a class="home" href='/index.html'>Inicio</a>
    <a href="https://wa.me/5541999999999">WhatsApp</a>
    </body></html>"""

    cleaned = normalize_generated_html_for_publication(html, prd)

    assert 'href="#hero"' in cleaned
    assert 'href="/"' not in cleaned
    assert "href='/index.html'" not in cleaned
    assert 'href="https://wa.me/5541999999999"' in cleaned


@pytest.mark.unit
def test_builder_sanitizer_repairs_media_without_injecting_footer():
    prd = _prd()
    html = """<!doctype html><html><body>
    <a class="brand" href="/">Aquaflex</a>
    <main><section id="hero"><h1>Aquaflex</h1></section></main>
    </body></html>"""

    cleaned = sanitize_builder_html_for_publication(html, prd)

    assert 'href="#hero"' in cleaned
    assert "fralib-photo-narrative" in cleaned
    assert "fralib-map-section" not in cleaned
    assert "<footer" not in cleaned


@pytest.mark.unit
def test_quality_gate_allows_editorial_headings_for_skill_fast_prd():
    prd = SimpleNamespace(
        business_name="Duetto Café Restaurante e Pizzaria",
        address="Rodovia do Caqui, 970, Campina Grande do Sul",
        phone="(41) 99999-0000",
        photos=[],
        animations=[],
        renderer_owns_headings=True,
        heading_preservation_min=1,
        sections=[
            {
                "name": "hero",
                "title": "Duetto Café Restaurante e Pizzaria em Campina Grande do Sul",
                "copy": {"body": "Hero editorial com identidade local."},
            },
            {
                "name": "trust-bar",
                "title": "Sinais reais",
                "items": [{"label": "Cidade", "value": "Campina Grande do Sul"}],
            },
            {
                "name": "sobre",
                "title": "Sobre Duetto Café Restaurante e Pizzaria",
                "copy": {"body": "Resumo factual do negócio."},
            },
            {
                "name": "localizacao",
                "title": "Localização e horários",
                "copy": {"body": "Mapa e endereço real."},
            },
        ],
    )
    html = """<!doctype html><html><head>
    <style>@keyframes fade{from{opacity:0}to{opacity:1}}</style>
    </head><body>
    <h1>Duetto Café Restaurante & Pizzaria</h1>
    <h2>Seu ponto de encontro em Campina Grande do Sul</h2>
    <h2>Sobre Duetto Café Restaurante e Pizzaria</h2>
    <h2>Contato</h2>
    <p>Rodovia do Caqui, 970, Campina Grande do Sul</p>
    </body></html>"""

    validate_generated_html(normalize_generated_html_for_publication(_with_experience_hero(html, "Duetto Café Restaurante e Pizzaria"), prd), prd)


@pytest.mark.unit
def test_quality_gate_respects_explicit_media_requirement():
    prd = _prd()
    prd.minimum_required_media = 2
    html = """<!doctype html><html><head>
    <style>@keyframes fade{from{opacity:0}to{opacity:1}}</style>
    </head><body>
    <h1>Aquaflex Jardim Paulista</h1>
    <h2>Estrutura para natacao</h2>
    <h2>Aulas de natacao para sua rotina</h2>
    <h2>Localizacao em Campina Grande do Sul</h2>
    <p>Av. Augusto Staben, 1410, Jardim Paulista, Campina Grande do Sul</p>
    </body></html>"""

    with pytest.raises(HtmlQualityGateError) as err:
        validate_generated_html(html, prd)

    assert "midias finais" in str(err.value)


@pytest.mark.unit
def test_quality_gate_accepts_real_facts_photos_and_motion():
    prd = _prd()
    prd.animations = []
    html = f"""<!doctype html><html><head>
    <style>@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}</style>
    </head><body>
    <h1>Aquaflex Jardim Paulista</h1>
    <h2>Estrutura para natacao</h2>
    <h2>Aulas de natacao para sua rotina</h2>
    <h2>Localizacao em Campina Grande do Sul</h2>
    <p>Av. Augusto Staben, 1410, Jardim Paulista, Campina Grande do Sul</p>
    <img src="{PHOTOS[0]}" alt="Piscina">
    <img src="{PHOTOS[1]}" alt="Aula de natacao">
    <img src="{PHOTOS[2]}" alt="Treino aquatico">
    <img src="{PHOTOS[3]}" alt="Piscina aquecida">
    <p>4,7/5 com 297 avaliacoes reais.</p>
    </body></html>"""

    validate_generated_html(normalize_generated_html_for_publication(_with_experience_hero(html, "Aquaflex Jardim Paulista"), prd), prd)


@pytest.mark.unit
def test_quality_gate_accepts_niche_media_not_exact_curated_urls():
    prd = _prd()
    prd.animations = []
    html = """<!doctype html><html><head>
    <style>
    @keyframes fade{from{opacity:0}to{opacity:1}}
    .hero{background-image:url("https://cdn.example.com/gym-hero.jpg")}
    </style>
    </head><body>
    <h1>Aquaflex Jardim Paulista</h1>
    <h2>Estrutura para natacao</h2>
    <h2>Aulas de natacao para sua rotina</h2>
    <h2>Localizacao em Campina Grande do Sul</h2>
    <p>Av. Augusto Staben, 1410, Jardim Paulista, Campina Grande do Sul</p>
    <img src="https://cdn.example.com/pool-1.jpg" alt="Aula de natacao">
    <img src="https://cdn.example.com/pool-2.jpg" alt="Treino aquatico">
    <img src="https://cdn.example.com/pool-3.jpg" alt="Piscina">
    </body></html>"""

    validate_generated_html(normalize_generated_html_for_publication(_with_experience_hero(html, "Aquaflex Jardim Paulista"), prd), prd)


@pytest.mark.unit
def test_quality_gate_ignores_unused_placeholder_css():
    prd = _prd()
    prd.animations = []
    html = f"""<!doctype html><html><head>
    <style>.ph-img{{aspect-ratio:16/9}} @keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}</style>
    </head><body>
    <h1>Aquaflex Jardim Paulista</h1>
    <h2>Estrutura para natacao</h2>
    <h2>Aulas de natacao para sua rotina</h2>
    <h2>Localizacao em Campina Grande do Sul</h2>
    <p>Av. Augusto Staben, 1410, Jardim Paulista, Campina Grande do Sul</p>
    <img src="{PHOTOS[0]}" alt="Piscina">
    <img src="{PHOTOS[1]}" alt="Aula de natacao">
    <img src="{PHOTOS[2]}" alt="Treino aquatico">
    <img src="{PHOTOS[3]}" alt="Piscina aquecida">
    </body></html>"""

    validate_generated_html(normalize_generated_html_for_publication(_with_experience_hero(html, "Aquaflex Jardim Paulista"), prd), prd)


@pytest.mark.unit
def test_quality_gate_rejects_empty_prd_contract_and_attribute_services():
    prd = SimpleNamespace(
        business_name="High Fitness Academia",
        phone="(41) 99999-0000",
        photos=[],
        animations=[],
        sections=[
            {"order": 1},
            {"order": 2},
            {"order": 3},
            {"order": 4},
        ],
    )
    html = """<!doctype html><html><body>
    <h1>High Fitness Academia</h1>
    <h2>Nossos Servicos</h2>
    <h3>Banheiro</h3>
    <h3>Cartao de Credito</h3>
    </body></html>"""

    with pytest.raises(HtmlQualityGateError) as err:
        validate_generated_html(html, prd)

    msg = str(err.value)
    assert "secao sem nome/id" in msg
    assert "atributos operacionais" in msg


@pytest.mark.unit
def test_quality_gate_rejects_emoji_internal_policy_and_unconfirmed_services():
    prd = SimpleNamespace(
        business_name="High Fitness Academia",
        phone="(41) 99111-4140",
        photos=PHOTOS,
        animations=[],
        services=[],
        sections=[
            {"name": "hero", "copy": {"h1": "High Fitness Academia"}},
            {"name": "sobre", "copy": {"h2": "Sobre a High Fitness"}},
            {"name": "servicos", "copy": {"h2": "Atividades sob consulta"}},
            {"name": "contato", "copy": {"h2": "Contato"}},
        ],
    )
    html = f"""<!doctype html><html><body>
    <h1>High Fitness Academia</h1>
    <h2>Sobre a High Fitness</h2>
    <h2>Atividades sob consulta</h2>
    <p>Dados capturados indicam que voce deve apresentar sem inventar.</p>
    <p>⭐⭐⭐⭐⭐ Muay Thai</p>
    <h2>Contato</h2>
    <img src="{PHOTOS[0]}" alt="Academia">
    <img src="{PHOTOS[1]}" alt="Treino">
    <img src="{PHOTOS[2]}" alt="Equipe">
    <img src="{PHOTOS[3]}" alt="Espaco">
    </body></html>"""

    with pytest.raises(HtmlQualityGateError) as err:
        validate_generated_html(html, prd)

    msg = str(err.value)
    assert "emoji" in msg
    assert "instrucao interna" in msg
    assert "fallback visual legado" in msg


@pytest.mark.unit
def test_quality_gate_rejects_truth_contract_violations_seen_in_high_fitness():
    prd = SimpleNamespace(
        business_name="High Fitness Academia",
        phone="(41) 99111-4140",
        address="",
        photos=PHOTOS,
        animations=[{"name": "fade-in"}],
        services=[],
        hours={
            "domingo: Fechado": "",
            "segunda-feira: 06:00-22:00": "",
        },
        sections=[
            {"name": "hero", "copy": {"h1": "High Fitness Academia"}},
            {"name": "sobre", "copy": {"h2": "Sobre a High Fitness"}},
            {"name": "servicos", "copy": {"h2": "Atividades sob consulta"}},
            {"name": "contato", "copy": {"h2": "Contato"}},
        ],
    )
    html = f"""<!doctype html><html><head>
    <style>@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}</style>
    </head><body>
    <h1>High Fitness Academia</h1>
    <h2>Sobre a High Fitness</h2>
    <p>Fundada com o propósito de levar saúde para a comunidade, com professores dedicados e estrutura completa.</p>
    <p>Espaço com equipamentos funcionais e instrutores dedicados. Com professores que se preocupam com correção técnica, oferece experiência fitness personalizada.</p>
    <h2>Atividades sob consulta</h2>
    <h3>Aulas Online</h3>
    <h3>Serviços Locais</h3>
    <p>Escolha o melhor plano para suas necessidades.</p>
    <p>Domingo: 8h - 20h</p>
    <h2>Contato</h2>
    <img src="{PHOTOS[0]}" alt="Academia">
    <img src="{PHOTOS[1]}" alt="Treino">
    </body></html>"""

    with pytest.raises(HtmlQualityGateError) as err:
        validate_generated_html(html, prd)

    msg = str(err.value)
    assert "claim publica sem prova" in msg
    assert "horario de domingo" in msg
    assert "copy institucional inventada" in msg
    assert "atributos operacionais" in msg


@pytest.mark.unit
def test_quality_gate_rejects_unconfirmed_claims_in_public_metadata():
    prd = SimpleNamespace(
        business_name="High Fitness Academia",
        phone="(41) 99111-4140",
        address="Rua Real, 123",
        photos=PHOTOS,
        animations=[{"name": "fade-in"}],
        services=[],
        sections=[
            {"name": "hero", "copy": {"h1": "High Fitness Academia"}},
            {"name": "sobre", "copy": {"h2": "Sobre a High Fitness"}},
            {"name": "servicos", "copy": {"h2": "Atividades sob consulta"}},
            {"name": "contato", "copy": {"h2": "Contato"}},
        ],
    )
    html = f"""<!doctype html><html><head>
    <meta name="description" content="Treinos direcionados com profissionais dedicados em Campina Grande do Sul">
    <style>@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}</style>
    </head><body>
    <h1>High Fitness Academia</h1>
    <h2>Sobre a High Fitness</h2>
    <p>Rua Real, 123</p>
    <h2>Atividades sob consulta</h2>
    <h2>Contato</h2>
    <img src="{PHOTOS[0]}" alt="Academia">
    <img src="{PHOTOS[1]}" alt="Treino">
    </body></html>"""

    with pytest.raises(HtmlQualityGateError) as err:
        validate_generated_html(html, prd)

    assert "copy institucional inventada" in str(err.value)


@pytest.mark.unit
def test_publication_normalizer_removes_emoji_and_unconfirmed_service_terms():
    prd = SimpleNamespace(
        business_name="High Fitness Academia",
        phone="(41) 99111-4140",
        photos=PHOTOS,
        animations=[],
        services=[],
        sections=[
            {"name": "hero", "copy": {"h1": "High Fitness Academia"}},
            {"name": "sobre", "copy": {"h2": "Sobre a High Fitness"}},
            {"name": "servicos", "copy": {"h2": "Atividades sob consulta"}},
            {"name": "contato", "copy": {"h2": "Contato"}},
        ],
    )
    html = f"""<!doctype html><html><body>
    <h1>High Fitness Academia ⭐</h1>
    <h2>Sobre a High Fitness</h2>
    <h2>Atividades sob consulta</h2>
    <p>Tem dança, musculação e Muay Thai.</p>
    <h2>Contato</h2>
    <img src="{PHOTOS[0]}" alt="Academia">
    <img src="{PHOTOS[1]}" alt="Treino">
    <img src="{PHOTOS[2]}" alt="Equipe">
    <img src="{PHOTOS[3]}" alt="Espaco">
    </body></html>"""

    cleaned = normalize_generated_html_for_publication(html, prd)

    assert "⭐" not in cleaned
    assert "Atividades sob consulta" not in cleaned
    assert "dança" not in cleaned
    assert "musculação" not in cleaned
    assert "Muay Thai" not in cleaned
    validate_generated_html(_with_experience_hero(cleaned, "High Fitness Academia"), prd)


@pytest.mark.unit
def test_publication_normalizer_keeps_one_canonical_location_map():
    prd = SimpleNamespace(
        business_name="High Fitness Academia",
        address="R. Manoel Jacinto de Oliveira Santos, 29, Campina Grande do Sul",
        phone="(41) 99111-4140",
        photos=[],
        animations=[],
        services=[],
        sections=[
            {"name": "hero", "copy": {"h1": "High Fitness Academia"}},
            {"name": "sobre", "copy": {"h2": "Sobre a High Fitness"}},
            {"name": "localizacao", "copy": {"h2": "Localizacao"}},
            {"name": "contato", "copy": {"h2": "Contato"}},
        ],
    )
    html = """<!doctype html><html><body>
    <h1>High Fitness Academia</h1>
    <h2>Sobre a High Fitness</h2>
    <!-- SECTION:localizacao -->
    <section><h2>Como nos encontrar</h2><iframe src="https://maps.google.com/maps?q=um"></iframe></section>
    <!-- /SECTION:localizacao -->
    <!-- SECTION:localizacao -->
    <section><h2>Localizacao real</h2><iframe src="https://maps.google.com/maps?q=dois"></iframe></section>
    <!-- /SECTION:localizacao -->
    <h2>Contato</h2>
    </body></html>"""

    cleaned = normalize_generated_html_for_publication(html, prd)

    assert cleaned.count("fralib-map-section") == 1
    assert cleaned.count("maps.google") == 1
    assert "Localizacao real" not in cleaned
    validate_generated_html(_with_experience_hero(cleaned, "High Fitness Academia"), prd)


@pytest.mark.unit
def test_quality_gate_rejects_legacy_service_fallback_and_duplicate_maps():
    prd = SimpleNamespace(
        business_name="High Fitness Academia",
        address="Rua Real, 123",
        phone="(41) 99111-4140",
        photos=[],
        animations=[],
        services=[],
        sections=[
            {"name": "hero", "copy": {"h1": "High Fitness Academia"}},
            {"name": "sobre", "copy": {"h2": "Sobre a High Fitness"}},
            {"name": "localizacao", "copy": {"h2": "Localizacao"}},
            {"name": "contato", "copy": {"h2": "Contato"}},
        ],
    )
    html = """<!doctype html><html><body>
    <h1>High Fitness Academia</h1>
    <h2>Sobre a High Fitness</h2>
    <section><h2>Atividades sob consulta</h2></section>
    <section><iframe src="https://maps.google.com/maps?q=um"></iframe></section>
    <section><iframe src="https://maps.google.com/maps?q=dois"></iframe></section>
    <h2>Contato</h2>
    <footer>High Fitness Academia</footer>
    </body></html>"""

    with pytest.raises(HtmlQualityGateError) as err:
        validate_generated_html(html, prd)

    msg = str(err.value)
    assert "fallback visual legado" in msg
    assert "mapa/localizacao duplicado" in msg


@pytest.mark.unit
def test_publication_normalizer_does_not_rewrite_css_or_attrs():
    prd = SimpleNamespace(
        business_name="High Fitness Academia",
        phone="(41) 99111-4140",
        photos=[],
        animations=[],
        services=[],
        sections=[
            {"name": "hero", "copy": {"h1": "High Fitness Academia"}},
            {"name": "sobre", "copy": {"h2": "Sobre a High Fitness"}},
            {"name": "contato", "copy": {"h2": "Contato"}},
            {"name": "footer", "copy": {"h2": "Footer"}},
        ],
    )
    html = """<!doctype html><html><body>
    <style>.x{margin-top:1rem;border-top:1px solid red;top:0}</style>
    <section class="top-card" style="top:0"><h1>High Fitness Academia</h1><p>Equipe top.</p></section>
    <section><h2>Sobre a High Fitness</h2></section>
    <section><h2>Contato</h2></section>
    <footer>High Fitness Academia</footer>
    </body></html>"""

    cleaned = normalize_generated_html_for_publication(html, prd)

    assert "margin-top" in cleaned
    assert "border-top" in cleaned
    assert "style=\"top:0\"" in cleaned
    assert "class=\"top-card\"" in cleaned
    assert "Equipe marcante." in cleaned
    assert "margin-direta" not in cleaned
    assert "border-direta" not in cleaned


@pytest.mark.unit
def test_publication_normalizer_removes_real_failed_html_artifacts():
    prd = SimpleNamespace(
        business_name="High Fitness Academia",
        segmento="negocio local",
        address="R. Manoel Jacinto de Oliveira Santos, 29, Campina Grande do Sul",
        city="Campina Grande do Sul",
        phone="(41) 99111-4140",
        photos=[],
        animations=[],
        services=[],
        sections=[
            {"name": "hero", "copy": {"h1": "High Fitness Academia"}},
            {"name": "sobre", "copy": {"h2": "Sobre a High Fitness"}},
            {"name": "localizacao", "copy": {"h2": "Localizacao"}},
            {"name": "contato", "copy": {"h2": "Contato"}},
        ],
    )
    html = """<!doctype html><html><body>
    <style>.card{margin-top:2rem;border-top:1px solid #ff1f1f;top:0}.legacy{margin-direta:1rem;border-direta:1px solid red}</style>
    <section data-reveal><!-- SECTION:hero --><h1>High Fitness Academia</h1><!-- /SECTION:hero --></section>
    <section data-reveal><h2>Sobre a High Fitness</h2></section>
    <!-- SECTION:depoimentos -->
    <section data-reveal><h2>Nossa reputação</h2><p>O professor Godoy ajuda no Muay Thai e tem dança.</p></section>
    <!-- /SECTION:depoimentos -->
    <!-- SECTION:servicos -->
    <section data-reveal><h2>Atividades sob consulta</h2><p>Modalidades devem ser confirmadas.</p></section>
    <!-- /SECTION:servicos -->
    <!-- SECTION:localizacao -->
    <section data-reveal><h2>Como nos encontrar</h2><iframe src="https://maps.google.com/maps?q=um"></iframe></section>
    <!-- /SECTION:localizacao -->
    <section data-reveal><h2>Contato</h2></section>
    <!-- SECTION:localizacao -->
    <section class="fralib-map-section"><h2>Localização real</h2><iframe src="https://maps.google.com/maps?q=dois"></iframe></section>
    <!-- /SECTION:localizacao -->
    <footer><!-- SECTION:footer -->High Fitness Academia<!-- /SECTION:footer --></footer>
    </body></html>"""

    cleaned = normalize_generated_html_for_publication(html, prd)

    assert "Atividades sob consulta" not in cleaned
    assert "Modalidades devem ser confirmadas" not in cleaned
    assert "Muay Thai" not in cleaned
    assert "professor Godoy" not in cleaned
    assert cleaned.count("fralib-map-section") == 1
    assert cleaned.count("maps.google") == 1
    assert "margin-top" in cleaned
    assert "border-top" in cleaned
    assert "margin-direta" not in cleaned
    assert "border-direta" not in cleaned
    validate_generated_html(_with_experience_hero(cleaned, "High Fitness Academia"), prd)


@pytest.mark.unit
def test_publication_normalizer_removes_fallback_even_when_services_exist():
    prd = SimpleNamespace(
        business_name="High Fitness Academia",
        phone="(41) 99111-4140",
        photos=[],
        animations=[],
        services=["Musculacao"],
        sections=[
            {"name": "hero", "copy": {"h1": "High Fitness Academia"}},
            {"name": "sobre", "copy": {"h2": "Sobre a High Fitness"}},
            {"name": "servicos", "copy": {"h2": "Servicos"}},
            {"name": "contato", "copy": {"h2": "Contato"}},
        ],
    )
    html = """<!doctype html><html><body>
    <h1>High Fitness Academia</h1>
    <h2>Sobre a High Fitness</h2>
    <!-- SECTION:atendimento -->
    <section class="fralib-service-fallback"><h2>Atividades sob consulta</h2></section>
    <!-- /SECTION:atendimento -->
    <h2>Contato</h2>
    <footer>High Fitness Academia</footer>
    </body></html>"""

    cleaned = normalize_generated_html_for_publication(html, prd)

    assert "Atividades sob consulta" not in cleaned
    assert "fralib-service-fallback" not in cleaned


@pytest.mark.unit
def test_publication_normalizer_keeps_single_media_narrative():
    prd = SimpleNamespace(
        business_name="High Fitness Academia",
        phone="(41) 99111-4140",
        photos=PHOTOS,
        animations=[],
        services=[],
        sections=[
            {"name": "hero", "copy": {"h1": "High Fitness Academia"}},
            {"name": "sobre", "copy": {"h2": "Sobre a High Fitness"}},
            {"name": "contato", "copy": {"h2": "Contato"}},
            {"name": "footer", "copy": {"h2": "Footer"}},
        ],
    )
    html = f"""<!doctype html><html><body>
    <h1>High Fitness Academia</h1>
    <h2>Sobre a High Fitness</h2>
    <section class="fralib-photo-narrative"><h2>Direção visual</h2><img src="{PHOTOS[0]}"></section>
    <!-- SECTION:media -->
    <section class="fralib-photo-narrative"><h2>Imagens editoriais do contexto do negócio</h2><img src="{PHOTOS[1]}"><img src="{PHOTOS[2]}"></section>
    <!-- /SECTION:media -->
    <section><h2>Contato</h2></section>
    <footer>High Fitness Academia</footer>
    </body></html>"""

    cleaned = normalize_generated_html_for_publication(html, prd)

    assert cleaned.count("fralib-photo-narrative") == 1
    assert len(re.findall(r"<img\b", cleaned, flags=re.I)) >= 2


@pytest.mark.unit
def test_publication_normalizer_removes_legacy_media_strip_after_footer():
    prd = SimpleNamespace(
        business_name="Duetto Café Restaurante e Pizzaria",
        segmento="pizzaria",
        phone="",
        photos=PHOTOS,
        animations=[],
        services=[],
        sections=[
            {"name": "hero", "copy": {"h1": "Duetto"}},
            {"name": "contato", "copy": {"h2": "Contato"}},
            {"name": "footer", "copy": {"h2": "Footer"}},
        ],
    )
    html = f"""<!doctype html><html><body>
    <h1>Duetto</h1>
    <section class="fralib-photo-narrative"><h2>Imagem, detalhe e presença</h2><img src="{PHOTOS[0]}"><img src="{PHOTOS[1]}"></section>
    <footer>Duetto Café Restaurante e Pizzaria</footer>
    <!-- SECTION:galeria -->
    <section id="galeria" class="fralib-media-strip"><img src="{PHOTOS[2]}"><img src="{PHOTOS[3]}"></section>
    <!-- /SECTION:galeria -->
    </body></html>"""

    cleaned = normalize_generated_html_for_publication(html, prd)

    assert "fralib-photo-narrative" in cleaned
    assert "fralib-media-strip" not in cleaned
    assert cleaned.index("fralib-photo-narrative") < cleaned.index("<footer")


@pytest.mark.unit
def test_builder_sanitizer_repairs_publication_contract_tokens():
    prd = SimpleNamespace(
        business_name="Nutricionista Priscila Botelho",
        segmento="Nutricionista",
        address="R. Pedro Pasa, 1158 - Jardim Paulista, Campina Grande do Sul - PR, 83430-000",
        phone="(41) 99231-3569",
        photos=PHOTOS + ["https://images.unsplash.com/photo-e"],
        animations=[],
        services=[],
        visual_contract={},
        sections=[
            {"name": "hero", "copy": {"h1": "Nutricionista Priscila Botelho"}},
            {"name": "sobre", "copy": {"h2": "Sobre"}},
            {"name": "midia", "copy": {"h2": "Midia"}},
            {"name": "footer", "copy": {"h2": "Footer"}},
        ],
    )
    html = f"""<!doctype html><html lang="pt-BR" data-renderer="builder"><head>
    <link rel="canonical" href="">
    <meta property="og:image" content="{PHOTOS[0]}">
    <title>Referência em nutrição →</title>
    </head><body>
    <header><h1>Nutricionista Priscila Botelho</h1><a href="https://wa.me/5541992313569">WhatsApp</a><img src="{PHOTOS[0]}" alt="Nutrição"></header>
    <section><h2>Sobre</h2><p>Atendimento em Campina Grande do Sul.</p></section>
    <section><h2>Referências visuais</h2>
      {"".join(f'<img src="{url}">' for url in PHOTOS + ["https://images.unsplash.com/photo-e"])}
    </section>
    <section class="fralib-map-section"><h2>Localização</h2><p>R. Pedro Pasa, 1158</p><iframe src="https://maps.google.com/maps?q=R.%20Pedro%20Pasa%2C%201158&output=embed&z=18"></iframe></section>
    <div class="lgpd" id="lgpd"><button>Aceitar</button></div>
    <script>localStorage.setItem('lgpd-priscila','1')</script>
    <footer>Nutricionista Priscila Botelho</footer>
    </body></html>"""

    cleaned = sanitize_builder_html_for_publication(html, prd)

    validate_generated_html(cleaned, prd)
    assert 'meta property="og:url"' in cleaned
    assert "fralib_lgpd_consent_v1" in cleaned
    assert 'meta name="twitter:card"' in cleaned
    assert "data-lgpd-banner" in cleaned
    assert "grid-template-columns:minmax(0,1fr) auto" in cleaned
    assert "max-width:calc(100vw - 32px)" in cleaned
    assert "white-space:nowrap" in cleaned
    assert 'data-builder-hero="true"' in cleaned
    assert 'data-parallax="soft"' in cleaned
    assert "<!-- SECTION:footer -->" in cleaned
    assert "fralib-photo-narrative" in cleaned
    assert "fralib-footer-nav" in cleaned
    assert "fralib-footer-trust" in cleaned
    assert "referência" not in cleaned.lower()
    assert "→" not in cleaned
    assert "★" not in cleaned
    assert prd.address in cleaned
