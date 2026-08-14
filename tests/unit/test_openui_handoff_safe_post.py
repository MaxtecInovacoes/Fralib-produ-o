from types import SimpleNamespace


def test_prd_to_spec_carries_media_plan_and_protected_payload():
    from backend.agents.builder.agent import _prd_to_spec
    from backend.agents.designer_prd import ColorPalette, DesignerPRD, SectionSpec

    prd = DesignerPRD(
        business_name="Nova Império Gym",
        cidade="Campina Grande do Sul",
        segmento="academia",
        sections=[
            SectionSpec(name="hero", title="Treino real"),
            SectionSpec(name="faq", title="Dúvidas frequentes"),
        ],
        color_palette=ColorPalette(primary="#050505", accent="#ff1f1f"),
        typography={"heading": "Bebas Neue", "body": "Inter"},
        creative_direction={
            "visual_concept": "industrial-bold",
            "hard_constraints": {
                "palette": {"--bg": "#050505", "--fg": "#ffffff", "--accent": "#ff1f1f"},
                "typography": {"heading": "Bebas Neue", "body": "Inter"},
                "hero_strategy": "hero-full-bleed",
            },
        },
        variation_blueprint={
            "template_hero": "hero-full-bleed",
            "ordem_das_secoes": ["hero", "faq", "contato", "footer"],
        },
        media_plan=[
            {
                "url": "https://images.example.com/gym.jpg",
                "role": "hero",
                "section": "hero",
                "required": True,
            }
        ],
    )

    spec = _prd_to_spec(prd)

    assert spec["media_plan"][0]["url"] == "https://images.example.com/gym.jpg"
    assert spec["openui_payload"]["creative_direction"]["visual_concept"] == "industrial-bold"
    assert spec["openui_payload"]["variation_blueprint"]["template_hero"] == "hero-full-bleed"
    assert spec["openui_payload"]["media_plan"][0]["required"] is True
    assert spec["openui_payload"]["technical_requirements"]["hard_constraints"]["hero_strategy"] == "hero-full-bleed"


def test_site_build_plan_uses_variation_blueprint_as_authority():
    from backend.agents.site_build_plan import build_site_build_plan

    plan = build_site_build_plan(
        {
            "business_name": "Nova Império Gym",
            "segmento": "academia",
            "cidade": "Campina Grande do Sul",
            "variation_blueprint": {
                "ordem_das_secoes": ["hero", "prova", "servicos", "faq", "contato", "footer"]
            },
        }
    )

    assert plan["information_architecture"]["section_order"] == [
        "hero",
        "prova",
        "servicos",
        "faq",
        "contato",
        "footer",
    ]
    assert plan["information_architecture"]["section_order_source"] == "variation_blueprint"


def test_cinematic_post_processor_safe_only_preserves_visual_decisions():
    from backend.agents.cinematic_post_processor import process

    html = """
    <html>
      <head><style>.hero{background:#050505;color:#fff;border-radius:32px}</style></head>
      <body>
        <main>
          <section class="hero" style="background:#050505; padding:96px; border-radius:32px">
            <h1 style="font-family:'Bebas Neue'">Treino real</h1>
            <img src="https://images.example.com/gym.jpg">
          </section>
        </main>
      </body>
    </html>
    """

    processed = process(html, safe_only=True)

    assert "background:#050505" in processed
    assert "padding:96px" in processed
    assert "border-radius:32px" in processed
    assert "Bebas Neue" in processed
    assert "https://images.example.com/gym.jpg" in processed
    assert "section:nth-child" not in processed


def test_get_og_image_from_prd_prefers_real_media_plan_image():
    from backend.agents.html_publication_helpers import get_og_image_from_prd

    prd = {
        "segmento": "academia",
        "media_plan": [
            {
                "url": "https://images.example.com/hero-real.jpg",
                "role": "hero",
                "section": "hero",
                "required": True,
            },
            {
                "url": "https://images.example.com/gallery.jpg",
                "role": "gallery",
                "section": "sobre",
                "required": False,
            },
        ]
    }

    assert get_og_image_from_prd(prd) == "https://images.example.com/hero-real.jpg"


def test_ensure_minimum_footer_adds_contact_and_lgpd_actions():
    from backend.agents.html_publication_helpers import ensure_minimum_footer

    html = "<html><body><main><section id='hero'><h1>Treino real</h1></section></main></body></html>"
    prd = {
        "business_name": "Elite Performance Academia",
        "phone": "(41) 98888-7777",
        "city": "Campina Grande do Sul",
        "address": "Rua Exemplo, 123",
    }

    processed = ensure_minimum_footer(html, prd)

    assert "Falar no WhatsApp" in processed
    assert "Ver política e consentimento" in processed
    assert "Rua Exemplo, 123" in processed
    assert "Campina Grande do Sul" in processed


def test_repair_builder_publication_contract_uses_theme_aware_lgpd_banner(monkeypatch):
    import backend.agents.html_builder_repair as builder_repair

    html = '<html><head></head><body data-renderer="builder"><main><section id="hero"><h1>Treino real</h1></section></main></body></html>'
    monkeypatch.setattr(
        builder_repair,
        "_ensure_builder_seo_schema_contract",
        lambda cleaned, prd: cleaned,
    )
    processed = builder_repair.repair_builder_publication_contract(html, {"segmento": "academia"})

    assert "data-lgpd-banner" in processed
    assert "data-lgpd-accept" in processed
    assert "var(--surface,#111827)" in processed
    assert "var(--accent,#e85d4a)" in processed
