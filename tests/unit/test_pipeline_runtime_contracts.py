def test_variacao_and_site_build_plan_do_not_require_lgpd_section():
    from backend.agents.site_build_plan import build_site_build_plan
    from backend.agents.agente_variacao import VariacaoEstrutural

    variacao = VariacaoEstrutural(
        task_id="t1",
        source_agent="agente_variacao",
        target_agent="arquiteto_mestre",
        status="ok",
        task_summary="ok",
        template_estrutura="editorial",
        template_hero="hero-fullscreen",
        template_prova_social="reviews-grid",
        template_cta="cta-central",
        template_faq="faq-accordion",
        ordem_das_secoes=["hero", "interesse", "desejo", "faq", "acao", "footer"],
        angulo_de_comunicacao="resultado real",
        regra_antirrepeticao="não repetir bloco genérico",
        justificativa="ok",
    )
    setattr(variacao, "required_sections", ["hero", "interesse", "desejo", "acao", "faq", "footer"])

    plan = build_site_build_plan(
        {
            "business_name": "Elite Performance Academia",
            "segmento": "academia",
            "cidade": "Curitiba",
            "variation_blueprint": {
                "ordem_das_secoes": list(variacao.ordem_das_secoes),
                "required_sections": list(getattr(variacao, "required_sections")),
            },
        }
    )

    assert "lgpd" not in plan["information_architecture"]["section_order"]
    assert "lgpd" not in plan["information_architecture"]["required_sections"]


def test_worker_infers_segment_and_city_from_name_and_address():
    import worker

    assert worker._infer_segment_from_name("Elite Performance Academia") == "academia"
    assert worker._infer_segment_from_name("PhD Sports Gym") == "academia"
    assert (
        worker._infer_city_from_address(
            "Rua das Acácias, 420 — Sala 3, Jardim Botânico, Curitiba — PR"
        )
        == "Curitiba"
    )
