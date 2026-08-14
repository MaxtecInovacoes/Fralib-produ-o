import os
import sys

os.environ.setdefault("TESTING", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def test_academia_media_filters_off_niche_office_unsplash(monkeypatch):
    from backend.services.pipeline_media import deterministic_media_bundle

    monkeypatch.setattr(
        "backend.services.pipeline_media.editorial_image_reachable",
        lambda url: True,
    )
    photos, og_image = deterministic_media_bundle(
        "academia",
        [
            "https://images.unsplash.com/photo-1497366754035-f200968a6e72",
            "https://images.unsplash.com/photo-1497366811353-6870744d04b2",
        ],
    )

    assert all("photo-149736" not in url for url in photos)
    assert "photo-1517836357463" in photos[0]
    assert "photo-1517836357463" in og_image


def test_nicho_extracts_json_inside_markdown():
    from backend.agents.agente_nicho import _extract_json_object

    response = """
    ## Briefing
    Conteúdo em markdown.

    ```json
    {
      "nicho": "academia",
      "subnichos": ["musculação"],
      "publico_alvo": ["adultos locais"],
      "usp": ["horário estendido"],
      "diferenciais": ["estacionamento"],
      "objcoes": ["preço"],
      "keywords": ["academia em campina grande do sul"],
      "tom_de_voz": "direto",
      "notas": "usar dados reais",
      "confianca": "media",
      "dados_ausentes": [],
      "competidores": []
    }
    ```
    """

    parsed = _extract_json_object(response)
    assert parsed["nicho"] == "academia"
    assert parsed["keywords"] == ["academia em campina grande do sul"]


def test_site_build_plan_removes_testimonials_without_real_reviews():
    from backend.agents.site_build_plan import build_site_build_plan

    plan = build_site_build_plan(
        {
            "business_name": "Academia Teste",
            "segmento": "academia",
            "cidade": "Campina Grande do Sul",
            "reviews_list": [],
            "variation_blueprint": {
                "ordem_das_secoes": ["hero", "depoimentos", "servicos", "faq", "footer"]
            },
        }
    )

    order = plan["information_architecture"]["section_order"]
    assert "depoimentos" not in order
    assert "social_proof" not in order


def test_openui_prompt_forbids_fake_reviews_phone_and_narrow_cards():
    sys.path.insert(0, os.path.abspath("openui-service-wandb/backend"))
    from openui import generate as module

    prompt = module._build_system_prompt(
        {
            "_render_hint": "section_fragment",
            "business_name": "Academia Teste",
            "segmento": "academia",
            "cidade": "Campina Grande do Sul",
            "phone": "5541985143249",
            "reviews_list": [],
            "sections": [{"name": "footer", "copy_data": {}}],
        }
    )

    assert "5541985143249" in prompt
    assert "(41) 99999-9999" in prompt
    assert "Do NOT invent testimonials" in prompt
    assert "min-w-[280px]" in prompt
    assert "max 3 columns" in prompt


def test_caio_rejects_phd_sports_as_known_network(monkeypatch):
    from backend.agents.caio import qualificar_lead

    monkeypatch.setattr("backend.agents.caio.verificar_whatsapp_ativo", lambda *args, **kwargs: (True, "ok"))
    result = qualificar_lead(
        {
            "nome": "Academia Ph.D Sports Jardim Paulista",
            "cidade": "Campina Grande do Sul",
            "segmento": "academia",
            "telefone": "5541985143249",
            "whatsapp": "5541985143249",
            "rating": 4.8,
            "reviews_count": 9,
            "fotos": ["foto1", "foto2", "foto3", "foto4", "foto5"],
            "website": "",
        }
    )

    assert result.qualificacao == "REJEITADO"
    assert result.tier == "REJEITADO"
    assert "Rede/franquia" in result.motivo


def test_academia_and_bold_force_dark_mode():
    from backend.agents.manager.step_arquiteto import _should_force_dark_mode
    from backend.agents.manager.states import PipelineState

    state = PipelineState(
        tenant_id=2,
        run_id="dark-test",
        lead_id="lead-dark",
        segmento="academia",
        cidade="Campina Grande do Sul",
        creative_direction={"visual_concept": "bold"},
    )

    assert _should_force_dark_mode(state, False) is True


def test_builder_shell_imports_heading_and_body_fonts():
    from backend.agents.builder.agent import _ensure_shell_fonts

    html = (
        "<!DOCTYPE html><html><head>"
        "<link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap\" rel=\"stylesheet\">"
        "</head><body><main id=\"app-shell\"></main></body></html>"
    )
    cleaned = _ensure_shell_fonts(
        html,
        {"typography": {"heading": "Archivo Black", "body": "Inter"}},
    )

    assert "family=Archivo+Black" in cleaned
    assert "family=Inter:wght@400;500;600;700;800;900" in cleaned


def test_builder_normalizes_proprietary_font_aliases_to_web_fonts():
    from backend.agents.builder.agent import _google_fonts_href

    href = _google_fonts_href({"heading": "UberMove", "body": "UberMoveText"})

    assert "family=Archivo+Black" in href
    assert "family=Inter:wght@400;500;600;700;800;900" in href


def test_deploy_flattens_dense_circular_copy_panels():
    from backend.agents.manager.step_deploy import _sanitize_deploy_html

    html = """
    <!DOCTYPE html><html><head></head><body>
    <main>
      <section>
        <div class="rounded-full aspect-square bg-red-500 text-white p-6">
          <h2>Pronto para transformar seu corpo e sua vida?</h2>
          <p>Texto longo demais para ficar dentro de um círculo sem esmagar a leitura, com CTA e contato.</p>
          <a href="https://wa.me/5541999999999">Falar agora</a>
        </div>
      </section>
    </main>
    </body></html>
    """

    sanitized = _sanitize_deploy_html(html)

    assert "rounded-full" not in sanitized
    assert "aspect-square" not in sanitized
    assert 'width:min(100%,32rem)' in sanitized
