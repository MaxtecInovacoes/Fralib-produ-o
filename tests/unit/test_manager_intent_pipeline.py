from types import SimpleNamespace


def test_pipeline_intent_steps_feed_arquiteto(monkeypatch):
    from backend.agents.handoff_types import NichoBriefing, VariacaoEstrutural
    from backend.agents.manager import agent as manager
    from backend.agents.manager.states import (
        PipelineState,
        STATE_BUILDING,
        STATE_DIRECTING,
        STATE_NICHE_BRIEFING,
        STATE_VARIATING,
    )

    received_by_arquiteto = {}

    monkeypatch.setattr(
        "backend.agents.agente_nicho.gerar_briefing",
        lambda **kwargs: NichoBriefing(
            task_id=kwargs["task_id"],
            nicho="academia",
            cidade=kwargs["cidade"],
            publico_alvo=["adultos que treinam sério"],
            usp=["estrutura robusta"],
            keywords=["academia em campina grande do sul"],
            tom_de_voz="energético",
        ),
    )
    monkeypatch.setattr(
        "backend.agents.design_director.gerar_direcao_criativa",
        lambda **kwargs: {
            "direcao_visual": {
                "estilo": "industrial-bold",
                "paleta_primaria": "#050505",
                "paleta_secundaria": "#111111",
                "paleta_acento": "#ff1f1f",
                "fonte_titulo": "Bebas Neue",
                "fonte_corpo": "Inter",
            },
            "motion_style": {"intensidade": "alta", "efeito_principal": "kinetic"},
            "tom_de_voz": {"registro": "direto"},
            "estrutura_unica": {
                "ordem_secoes": ["hero", "prova", "servicos", "faq", "contato", "footer"],
                "template_hero": "hero-full-bleed",
                "cta_principal": "Agendar aula experimental",
            },
            "anti_repeticao": {"evitar": ["layout genérico"]},
            "design_tokens": {
                "tokens": {"--bg": "#050505", "--fg": "#ffffff", "--accent": "#ff1f1f"},
                "font_heading": "Bebas Neue",
                "font_body": "Inter",
            },
        },
    )
    monkeypatch.setattr(
        "backend.agents.agente_variacao.gerar_variacao",
        lambda **kwargs: VariacaoEstrutural(
            task_id=kwargs["task_id"],
            template_estrutura="campaign-bold",
            template_hero="hero-full-bleed",
            ordem_das_secoes=["hero", "prova", "servicos", "faq", "contato", "footer"],
            regra_antirrepeticao="não repetir academia anterior",
        ),
    )

    def fake_arquiteto(**kwargs):
        received_by_arquiteto.update(kwargs)
        return SimpleNamespace(
            business_name="High Fitness",
            sections=[{"name": "hero"}, {"name": "faq"}, {"name": "footer"}],
            color_palette={"primary": "#050505"},
            typography={"heading": "Bebas Neue", "body": "Inter"},
            visual_dna={"archetype": "industrial-bold"},
        )

    monkeypatch.setattr(
        "backend.agents.arquiteto_agent_loop.gerar_arquiteto_mestre_prd_agent",
        fake_arquiteto,
    )
    monkeypatch.setattr(
        "backend.agents.keyword_research.pesquisar_keywords_nicho",
        lambda **kwargs: "academia campina grande do sul",
    )
    monkeypatch.setattr(
        "backend.agents.manager.step_arquiteto.journal_record",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "backend.agents.pipeline_checkpoint.salvar_checkpoint",
        lambda *args, **kwargs: None,
    )

    state = PipelineState(
        tenant_id=2,
        run_id="run-intent-test",
        lead_id="lead-12345678",
        segmento="academia",
        cidade="Campina Grande do Sul",
        lead_data={"nome": "High Fitness", "rating": 4.6, "reviews": []},
        caio_output=SimpleNamespace(tier="STANDARD", score=80, dark_mode=True),
        current_state=STATE_NICHE_BRIEFING,
    )

    state = manager.step_nicho(state)
    assert state.current_state == STATE_DIRECTING
    assert state.niche_brief["nicho"] == "academia"

    state = manager.step_design_director(state)
    assert state.current_state == STATE_VARIATING
    assert state.creative_direction["hard_constraints"]["visual_concept"] == "industrial-bold"

    state = manager.step_variacao(state)
    assert state.current_state == "designing"
    assert state.variation_blueprint["ordem_das_secoes"][0] == "hero"

    state = manager.step_arquiteto(state)
    assert state.current_state == STATE_BUILDING
    assert received_by_arquiteto["niche_brief"]["nicho"] == "academia"
    assert received_by_arquiteto["creative_direction"]["visual_concept"] == "industrial-bold"
    assert received_by_arquiteto["variation_blueprint"]["template_hero"] == "hero-full-bleed"
    assert state.designer_prd["creative_direction"]["visual_concept"] == "industrial-bold"
    assert [record["stage"] for record in state.visual_custody] == [
        "niche_brief",
        "creative_direction",
        "variation_blueprint",
        "designer_prd",
    ]


def test_pipeline_steps_include_intent_chain_before_arquiteto():
    from backend.agents.manager.agent import PIPELINE_STEPS

    step_names = [step.__name__ for step in PIPELINE_STEPS]
    assert step_names.index("step_nicho") < step_names.index("step_design_director")
    assert step_names.index("step_design_director") < step_names.index("step_variacao")
    assert step_names.index("step_variacao") < step_names.index("step_arquiteto")
