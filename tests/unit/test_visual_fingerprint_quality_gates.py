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
