def _html(*, accent="#ff1f1f", hero_class="hero-full", font="Bebas Neue", image="https://img.example/hero.jpg"):
    copy = " ".join(["Conteúdo local real com proposta, prova social e conversão."] * 35)
    return f"""
    <!doctype html>
    <html>
      <head>
        <style>
          :root{{--accent:{accent};--bg:#050505;--fg:#ffffff}}
          body{{font-family:{font}}}
        </style>
      </head>
      <body>
        <main>
          <section id="hero" class="{hero_class} max-w-7xl rounded-3xl" style="background:{accent}">
            <h1 style="font-family:{font}">Treino real</h1>
            <img src="{image}">
            <p>{copy}</p>
          </section>
          <section id="faq" class="grid rounded-3xl"><h2>FAQ</h2><p>{copy}</p></section>
          <section id="contato" class="flex border"><h2>Contato</h2><p>{copy}</p></section>
        </main>
      </body>
    </html>
    """


def test_visual_fingerprint_similarity_detects_same_visual_pattern():
    from backend.agents.visual_fingerprint import build_visual_fingerprint, fingerprint_similarity

    prd = {"variation_blueprint": {"ordem_das_secoes": ["hero", "faq", "contato"]}}
    first = build_visual_fingerprint(_html(), prd)
    second = build_visual_fingerprint(_html(), prd)
    different = build_visual_fingerprint(_html(accent="#00aa88", hero_class="hero-centered", font="Inter"), {})

    assert fingerprint_similarity(first, second) == 1.0
    assert fingerprint_similarity(first, different) < 1.0
    assert first["section_order"] == ["hero", "faq", "contato"]
    assert first["media_count"] == 1


def test_quality_gate_records_fingerprint_and_passes_good_html(monkeypatch):
    from backend.agents.manager import step_quality_gate as qg
    from backend.agents.manager.states import PipelineState, STATE_PUBLISHING, STATE_VALIDATING

    monkeypatch.setattr(qg, "_load_prior_fingerprint_comparisons", lambda state, fingerprint: [])

    state = PipelineState(
        tenant_id=2,
        lead_id="lead-1",
        run_id="run-1",
        current_state=STATE_VALIDATING,
        build_output={"html": _html()},
        design_output={
            "creative_direction": {
                "hard_constraints": {
                    "palette": {"--accent": "#ff1f1f"},
                    "typography": {"heading": "Bebas Neue"},
                }
            },
            "variation_blueprint": {"ordem_das_secoes": ["hero", "faq", "contato"]},
            "media_plan": [
                {
                    "url": "https://img.example/hero.jpg",
                    "role": "hero",
                    "section": "hero",
                    "required": True,
                }
            ],
        },
    )

    state = qg.step_quality_gate(state)

    assert state.current_state == STATE_PUBLISHING
    assert state.visual_fingerprint["hero"] in {"hero-full", "section-hero", "full-bleed"}
    assert state.build_output["gates"]["passed"] is True
    assert state.build_output["qa_v2"]["vision_passed"] is True


def test_quality_gate_rejects_missing_required_media(monkeypatch):
    from backend.agents.manager import step_quality_gate as qg
    from backend.agents.manager.states import PipelineState, STATE_FAILED, STATE_VALIDATING

    monkeypatch.setattr(qg, "_load_prior_fingerprint_comparisons", lambda state, fingerprint: [])

    state = PipelineState(
        tenant_id=2,
        lead_id="lead-1",
        run_id="run-1",
        current_state=STATE_VALIDATING,
        build_output={"html": _html(image="https://img.example/other.jpg")},
        design_output={
            "media_plan": [
                {
                    "url": "https://img.example/hero.jpg",
                    "role": "hero",
                    "section": "hero",
                    "required": True,
                }
            ],
        },
    )

    state = qg.step_quality_gate(state)

    assert state.current_state == STATE_FAILED
    assert "mídia obrigatória ausente" in state.error


def test_quality_gate_rejects_too_similar_prior_fingerprint(monkeypatch):
    from backend.agents.manager import step_quality_gate as qg
    from backend.agents.manager.states import PipelineState, STATE_FAILED, STATE_VALIDATING

    monkeypatch.setattr(
        qg,
        "_load_prior_fingerprint_comparisons",
        lambda state, fingerprint: [{"lead_id": "older-lead", "segmento": "academia", "similarity": 0.99}],
    )

    state = PipelineState(
        tenant_id=2,
        lead_id="lead-2",
        run_id="run-2",
        current_state=STATE_VALIDATING,
        build_output={"html": _html()},
        design_output={"variation_blueprint": {"ordem_das_secoes": ["hero", "faq", "contato"]}},
    )

    state = qg.step_quality_gate(state)

    assert state.current_state == STATE_FAILED
    assert "Visual Diversity Gate" in state.error


def test_technical_gate_allows_low_nonzero_opacity():
    from backend.agents.manager import step_quality_gate as qg

    html = _html() + '<div style="background:var(--accent);opacity:0.08;"></div>'

    result = qg._technical_gate(html)

    assert result["passed"] is True
    assert not any("invisível" in issue for issue in result["issues"])


def test_technical_gate_allows_reveal_with_safe_visibility_release():
    from backend.agents.manager import step_quality_gate as qg

    html = """
    <!doctype html>
    <html>
      <head>
        <style>
          .reveal { opacity: 0; transform: translateY(24px); }
          .reveal.visible { opacity: 1; transform: translateY(0); }
          html.no-js .reveal { opacity: 1 !important; transform: none !important; }
        </style>
      </head>
      <body>
        <main>
          <section class="reveal"><h1>Treino real em Campina Grande do Sul</h1><p>Conteúdo visível por fallback, com contexto local, benefícios claros, proposta comercial válida e texto suficiente para passar pelo gate técnico.</p><div>Benefícios</div><div>Estrutura</div><div>Contato</div></section>
          <section><h2>Bloco 2</h2><p>Texto suficiente com detalhes de serviços, localização, diferenciais, ritmo visual e proposta de valor para uma academia local orientada a resultado.</p><div>Card 1</div><div>Card 2</div></section>
          <section><h2>Bloco 3</h2><p>Mais texto suficiente com perguntas frequentes, CTA, endereço real, contexto editorial, SEO local e elementos de fechamento institucional coerentes.</p><div>FAQ</div><div>CTA</div></section>
        </main>
        <script>document.querySelector('.reveal').classList.add('visible');</script>
      </body>
    </html>
    """

    result = qg._technical_gate(html)

    assert result["passed"] is True
    assert not any("invisível" in issue for issue in result["issues"])


def test_section_completeness_gate_passes_with_required_contracts():
    from backend.agents.manager import step_quality_gate as qg
    from backend.agents.manager.states import PipelineState

    html = """
    <!doctype html>
    <html><body><main>
      <section id="hero">
        <h1>Treino real em Campina Grande do Sul</h1>
        <p>Academia local com proposta clara e contexto da cidade.</p>
        <img src="https://img.example/hero.jpg">
        <div>Benefícios</div><div>Provas</div><a href="#contato">Agende agora</a>
      </section>
      <section id="faq">
        <h2>FAQ</h2>
        <details><summary>Pergunta 1</summary><p>Resposta 1</p></details>
        <details><summary>Pergunta 2</summary><p>Resposta 2</p></details>
        <details><summary>Pergunta 3</summary><p>Resposta 3</p></details>
      </section>
      <section id="contato">
        <h2>Contato</h2>
        <p>Fale conosco em Campina Grande do Sul para conhecer planos, estrutura e aula experimental.</p>
        <p>(41) 98514-3249</p>
        <div>WhatsApp</div><a href="https://wa.me/5541985143249">Chamar</a>
      </section>
      <section id="footer">
        <h2>Footer</h2>
        <p>Campina Grande do Sul</p>
        <p>(41) 98514-3249</p>
        <div>Rua Teste, 123</div><div>Links legais</div><div>Marca</div>
        <p>Academia local com atendimento real, rota clara de contato e fechamento institucional consistente.</p>
      </section>
    </main></body></html>
    """

    state = PipelineState(
        tenant_id=2,
        lead_id="lead-1",
        run_id="run-1",
        design_output={
            "phone": "5541985143249",
            "address": "Rua Teste, 123",
            "section_contracts": [
                {"name": "hero", "required_media_count": 1, "media_plan": [{"url": "https://img.example/hero.jpg", "required": True}], "minimum_requirements": {"minimum_content_blocks": 4}},
                {"name": "faq", "required_media_count": 0, "media_plan": [], "minimum_requirements": {"minimum_content_blocks": 3}},
                {"name": "contato", "required_media_count": 0, "media_plan": [], "minimum_requirements": {"minimum_content_blocks": 3}},
                {"name": "footer", "required_media_count": 0, "media_plan": [], "minimum_requirements": {"minimum_content_blocks": 3}},
            ],
            "reviews_list": [],
        },
        cidade="Campina Grande do Sul",
    )

    result = qg._section_completeness_gate(state, html)

    assert result["passed"] is True
    assert result["issues"] == []


def test_section_completeness_gate_rejects_missing_faq_and_placeholder_phone():
    from backend.agents.manager import step_quality_gate as qg
    from backend.agents.manager.states import PipelineState

    html = """
    <!doctype html>
    <html><body><main>
      <section id="hero">
        <h1>Treino real</h1>
        <p>Sem cidade.</p>
        <div>Bloco</div><div>Bloco</div><a href="#contato">Fale</a>
      </section>
      <section id="faq">
        <h2>FAQ</h2>
        <details><summary>Pergunta 1</summary><p>Resposta 1</p></details>
      </section>
      <section id="contato">
        <h2>Contato</h2>
        <p>(41) 99999-9999</p>
      </section>
    </main></body></html>
    """

    state = PipelineState(
        tenant_id=2,
        lead_id="lead-2",
        run_id="run-2",
        design_output={
            "phone": "5541985143249",
            "address": "Rua Teste, 123",
            "section_contracts": [
                {"name": "hero", "required_media_count": 1, "media_plan": [{"url": "https://img.example/hero.jpg", "required": True}], "minimum_requirements": {"minimum_content_blocks": 4, "must_not": []}},
                {"name": "faq", "required_media_count": 0, "media_plan": [], "minimum_requirements": {"minimum_content_blocks": 3, "must_not": []}},
                {"name": "contato", "required_media_count": 0, "media_plan": [], "minimum_requirements": {"minimum_content_blocks": 3, "must_not": ["fake contact data"]}},
                {"name": "footer", "required_media_count": 0, "media_plan": [], "minimum_requirements": {"minimum_content_blocks": 3, "must_not": ["fake contact data"]}},
            ],
            "reviews_list": [],
        },
        cidade="Campina Grande do Sul",
    )

    result = qg._section_completeness_gate(state, html)

    assert result["passed"] is False
    assert any("FAQ com menos de 3" in issue for issue in result["issues"])
    assert any("telefone placeholder" in issue for issue in result["issues"])
