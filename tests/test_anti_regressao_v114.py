"""Testes anti-regressao v1.14 - Sprint 12.12 (caroco enriquecido com briefing real).

Sprint 12.12 fecha 3 gaps do Vite/React caroço:

Gap 1: _summarize_builder_facts so pegava name/segment/city/phone (no renderer.py).
       Agora pega services, hours, differentials, target_audience, keywords SEO,
       fotos reais. LLM recebe o briefing REAL do lead, nao inventa.

Gap 2: vite_prompts.py tinha _build_nicho_modal_block com NameError em f-string
       (linha com `import { useState } from 'react'` nao tinha escape).
       Quebrava o modulo inteiro (import de vite_prompts.py falhava).
       Agora esta corrigido com `{{ useState }}`.

Gap 3: VITE_REACT_SYSTEM_PROMPT nao tinha GSAP codigo real nem briefing do lead.
       Agora tem:
       - _build_gsap_code_block(): snippets executaveis (useGSAP, ScrollTrigger, MagneticCTA)
       - _build_lead_briefing_block(facts): dados REAIS + JSON-LD + fotos aprovadas
       - _build_caroço_block(facts): agrega TUDO num unico bloco
       - _build_vite_react_system_prompt_with_facts(facts): prompt final com briefing

Valida:
- _build_nicho_modal_block nao quebra (f-string escape correto)
- _build_caroço_block agrega todos os blocos
- _build_lead_briefing_block injeta dados reais
- _build_gsap_code_block tem codigo real de useGSAP/ScrollTrigger
- _summarize_builder_facts agora inclui services, hours, keywords, fotos
- VITE_REACT_SYSTEM_PROMPT contem briefing, GSAP, shadcn, modal, blocos
- Backward-compat: VITE_REACT_SYSTEM_PROMPT sem facts continua funcionando
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))


# ════════════════════════════════════════════════════════════════════
# Facts de teste (simulam o lead Codex Barbearia Tenant 2)
# ════════════════════════════════════════════════════════════════════

LEAD_TEST_FACTS = {
    "business": {
        "name": "Barbearia Fio Nobre Pinhais",
        "segment": "barbearia",
        "subniche": "barbearia_premium",
        "city": "Pinhais",
        "cidade": "Pinhais",
        "phone": "4100000000",
        "whatsapp": "41999990000",
        "address": "Centro, Pinhais - PR",
        "endereco": "Centro, Pinhais - PR",
        "rating": "4.8",
        "total_avaliacoes": "127",
        "services": ["Corte Masculino", "Barba", "Sobrancelha", "Pigmentacao"],
        "servicos": ["Corte Masculino", "Barba", "Sobrancelha", "Pigmentacao"],
        "hours": "Seg-Sex 9h-20h, Sab 9h-14h",
        "horarios": "Seg-Sex 9h-20h, Sab 9h-14h",
        "differentials": [
            "Barbeiros com 10+ anos de experiencia",
            "Produtos importados",
            "Ambiente climatizado",
        ],
        "target_audience": "Homens de 25-55 anos que valorizam qualidade",
        "photos": [
            "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=1600",
            "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=1600",
        ],
    },
    "seo": {
        "primary_terms": [
            "barbearia pinhais",
            "corte masculino pinhais",
            "barba pinhais",
            "melhor barbearia pinhais",
        ],
    },
    "media": {
        "photos": [
            "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=1600",
            "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=1600",
        ],
    },
}


# ════════════════════════════════════════════════════════════════════
# TESTES Sprint 12.12
# ════════════════════════════════════════════════════════════════════


def test_1_nicho_modal_block_no_nameerror():
    """Sprint 12.12: _build_nicho_modal_block NAO quebra o modulo."""
    print("[TESTE 1/8] _build_nicho_modal_block nao quebra import...")
    from backend.services import vite_prompts

    # Se NameError existisse, o import acima falharia
    block = vite_prompts._build_nicho_modal_block(LEAD_TEST_FACTS)
    assert isinstance(block, str), "block deve ser string"
    assert "MODAL OBRIGATORIO" in block, "Modal block deve ter o titulo"
    assert "BookingModal" in block, "deve mencionar BookingModal"
    assert "useState" in block, "deve ensinar uso de useState"
    # Verifica que o segmento certo foi detectado
    assert "barbearia" in block.lower(), "deve detectar nicho barbearia"

    print("  OK _build_nicho_modal_block nao quebra import")
    print("  OK Detecta nicho barbearia corretamente")
    print("  OK Inclui codigo BookingModal com useState")


def test_2_caroço_block_agrega_tudo():
    """Sprint 12.12: _build_caroço_block agrega todos os contratos."""
    print("\n[TESTE 2/8] _build_caroço_block agrega todos os blocos...")
    from backend.services import vite_prompts

    caroco = vite_prompts._build_caroço_block(LEAD_TEST_FACTS)

    # Deve conter TUDO
    must_have = [
        ("Few-shot", "PREMIUM VISUAL"),
        ("SHADCN/UI", "SHADCN/UI COMPONENTS"),
        ("Premium contract", "COPY CONTRACT"),
        ("Visual direction", "VISUAL DIRECTION"),
        ("Motion pack (data-attrs)", "ANIMATION LIBRARY"),
        ("GSAP codigo real", "useGSAP"),
        ("Mobile-first", "MOBILE-FIRST"),
        ("Lead briefing REAL", "LEAD BRIEFING"),
        ("Modal obrigatorio", "MODAL OBRIGATORIO"),
        ("Blocos pre-fabricados", "BLOCOS PRÉ-FABRICADOS"),
        ("No contamination", "ZERO CROSS-SEGMENT"),
    ]
    for label, marker in must_have:
        assert marker in caroco, f"Falta bloco: {label} (marker={marker!r})"

    print(f"  OK {len(must_have)} blocos canonicos presentes no caroço")


def test_3_lead_briefing_block_injeta_dados_reais():
    """Sprint 12.12: briefing REAL do lead chega no system prompt."""
    print("\n[TESTE 3/8] Briefing real do lead...")
    from backend.services import vite_prompts

    briefing = vite_prompts._build_lead_briefing_block(LEAD_TEST_FACTS)

    # Dados REAIS que devem estar no briefing
    must_contain = [
        "Barbearia Fio Nobre Pinhais",  # name
        "barbearia",  # segment
        "Pinhais",  # city
        "4100000000",  # phone
        "Centro, Pinhais - PR",  # address
        "4.8",  # rating
        "127",  # reviews
        "Corte Masculino",  # service
        "Barba",  # service
        "Seg-Sex 9h-20h",  # hours
        "barbearia pinhais",  # SEO keyword
        "images.unsplash.com",  # photo URL
        "@context",  # JSON-LD
        "LocalBusiness",  # JSON-LD type
    ]

    for marker in must_contain:
        assert marker in briefing, f"Briefing deve conter: {marker!r}"

    # NAO pode ter texto placeholder generico
    assert "Lorem ipsum" not in briefing
    assert "TODO" not in briefing

    print(f"  OK {len(must_contain)} campos REAIS injetados no briefing")
    print("  OK JSON-LD LocalBusiness presente")
    print("  OK Fotos reais (Unsplash) listadas")


def test_4_gsap_code_block_tem_codigo_real():
    """Sprint 12.12: bloco GSAP tem codigo REAL (nao so lista data-attrs)."""
    print("\n[TESTE 4/8] GSAP code block com snippets reais...")
    from backend.services import vite_prompts

    gsap_block = vite_prompts._build_gsap_code_block()

    # Deve ter imports reais
    must_contain = [
        "import { gsap } from 'gsap'",  # import correto
        "import { ScrollTrigger } from 'gsap/ScrollTrigger'",  # import correto
        "import { useGSAP } from '@gsap/react'",  # hook React
        "gsap.registerPlugin",  # registro de plugin
        "ScrollTrigger",  # uso real
        "scrub",  # uso real de scrub
        "data-magnetic",  # data-magnetic
    ]
    for marker in must_contain:
        assert marker in gsap_block, f"GSAP block deve ter: {marker!r}"

    print(f"  OK {len(must_contain)} snippets de GSAP real presentes")
    print("  OK Padrao useGSAP + ScrollTrigger + scrub + data-magnetic")


def test_5_vite_prompt_with_facts_full():
    """Sprint 12.12: prompt FINAL com briefing real."""
    print("\n[TESTE 5/8] VITE_REACT_SYSTEM_PROMPT final com facts...")
    from backend.services import vite_prompts

    prompt = vite_prompts._build_vite_react_system_prompt_with_facts(LEAD_TEST_FACTS)

    # Validacoes de completude
    assert "LEAD BRIEFING" in prompt
    assert "Barbearia Fio Nobre Pinhais" in prompt
    assert "useGSAP" in prompt
    assert "SHADCN/UI COMPONENTS" in prompt
    assert "MODAL OBRIGATORIO" in prompt
    assert "BLOCOS PRÉ-FABRICADOS" in prompt
    assert "ZERO CROSS-SEGMENT" in prompt
    assert "LocalBusiness" in prompt
    assert "barbearia pinhais" in prompt.lower()
    assert "Seg-Sex 9h-20h" in prompt  # horario real

    # Deve ser grande (caroco rico)
    assert len(prompt) > 25000, f"Prompt com briefing deve ser >25k chars, tem {len(prompt)}"

    print(f"  OK Prompt final tem {len(prompt)} chars (>25k)")
    print("  OK Briefing + GSAP + shadcn + Modal + Blocos + JSON-LD")


def test_6_backward_compat_prompt_sem_facts():
    """Sprint 12.12: VITE_REACT_SYSTEM_PROMPT sem facts continua funcionando."""
    print("\n[TESTE 6/8] Backward-compat: prompt sem facts...")
    from backend.services import vite_prompts

    # Constante global deve funcionar (usada em testes retrocompat)
    prompt = vite_prompts.VITE_REACT_SYSTEM_PROMPT
    assert isinstance(prompt, str)
    assert len(prompt) > 15000, "Prompt base deve ser >15k chars"

    # Sem facts, briefing fica vazio (nao quebra)
    briefing_empty = vite_prompts._build_lead_briefing_block(None)
    assert briefing_empty == "", "Briefing sem facts deve ser string vazia"

    briefing_empty2 = vite_prompts._build_lead_briefing_block({})
    assert briefing_empty2 == "", "Briefing com dict vazio deve ser string vazia"

    # Caroço sem facts ainda funciona
    caroco_empty = vite_prompts._build_caroço_block()
    assert "MODAL OBRIGATORIO" in caroco_empty
    assert "useGSAP" in caroco_empty

    print(f"  OK VITE_REACT_SYSTEM_PROMPT (sem facts) tem {len(prompt)} chars")
    print("  OK _build_lead_briefing_block vazio retorna ''")
    print("  OK _build_caroço_block sem facts funciona")


def test_7_renderer_summarize_inclui_briefing_real():
    """Sprint 12.12: _summarize_builder_facts do renderer inclui briefing real."""
    print("\n[TESTE 7/8] _summarize_builder_facts enriquecido...")
    from backend.services.vite_react_renderer import _summarize_builder_facts

    summary = _summarize_builder_facts(LEAD_TEST_FACTS)

    # Antes (Sprint 12.5) so tinha name/segment/city
    # Agora deve ter TUDO
    must_contain = [
        "Barbearia Fio Nobre Pinhais",  # name
        "barbearia",  # segment
        "Pinhais",  # city
        "41999990000",  # whatsapp (preferido sobre phone)
        "Centro, Pinhais - PR",  # address
        "Corte Masculino",  # services
        "Barba",  # services
        "Seg-Sex 9h-20h",  # hours
        "barbearia pinhais",  # SEO keyword
        "images.unsplash.com",  # photo URL real
        "4.8",  # rating
        "127",  # reviews count
    ]

    for marker in must_contain:
        assert marker in summary, f"summarize deve conter: {marker!r}"

    print(f"  OK {len(must_contain)} campos REAIS em _summarize_builder_facts")
    print("  OK Services, hours, SEO keywords, fotos, rating - tudo presente")


def test_8_existing_prompt_blocks_intact():
    """Sprint 12.12: NAO quebrou os blocos existentes do prompt."""
    print("\n[TESTE 8/8] Blocos existentes preservados...")
    from backend.services import vite_prompts

    prompt = vite_prompts.VITE_REACT_SYSTEM_PROMPT
    caroco = vite_prompts._build_caroço_block()

    # Blocos ja existentes (Sprints 11 e 12.11) - devem estar no FOOT estatico
    must_preserve = [
        "SHADCN/UI COMPONENTS",
        "PREMIUM VISUAL + COPY CONTRACT",
        "VISUAL DIRECTION",
        "ANIMATION LIBRARY",
        "MOBILE-FIRST RESPONSIVENESS",
        "MODAL OBRIGATORIO",
        "BLOCOS PRÉ-FABRICADOS",
        "ZERO CROSS-SEGMENT CONTAMINATION",
        "Brazilian Portuguese",
        "WCAG",
    ]

    for marker in must_preserve:
        assert marker in prompt, f"Bloco existente perdido: {marker!r}"

    # GSAP code block novo - esta no _build_caroço_block (nao no FOOT constante)
    assert "useGSAP" in caroco, "GSAP code block deve estar no caroço"
    assert vite_prompts._build_gsap_code_block().__contains__("useGSAP")

    print(f"  OK {len(must_preserve)} blocos pre-existentes preservados no FOOT")
    print("  OK + GSAP code block novo integrado no caroço")


def test_9_studio_fallback_nutricionista_sem_contaminacao():
    """Sprint 12.20: fallback Studio de nutricionista nao herda matricula/treino."""
    print("\n[TESTE 9/10] Studio fallback nutricionista sem contaminacao...")
    from backend.services.vite_react_renderer import (
        _generate_studio_fallback_files,
        validate_vite_project_files,
    )

    facts = {
        "business": {
            "name": "Vitor Feitosa - Nutricionista Esportivo",
            "segment": "nutricionista",
            "subniche": "nutricao esportiva",
            "city": "Sao Paulo",
            "phone": "11984585259",
            "rating": "5.0",
        },
        "media": {
            "photos": [
                "https://images.unsplash.com/photo-1490645935967-10de6ba17061",
                "https://images.unsplash.com/photo-1505576399279-565b52d4ac71",
            ]
        },
    }
    files = _generate_studio_fallback_files(facts)
    modal = files["src/components/BookingModal.tsx"].lower()

    assert "matricula" not in modal
    assert "matrícula" not in modal
    assert "treino" not in modal
    validate_vite_project_files(files, facts, requested_paths=set())

    print("  OK BookingModal nao contem matricula/treino")
    print("  OK validate_vite_project_files aceita nutricionista")


def test_10_prepare_injeta_midia_aprovada_quando_llm_nao_usa_imagens():
    """Sprint 12.20: facts com fotos reais nao podem falhar como 0 refs."""
    print("\n[TESTE 10/10] prepare injeta midia aprovada antes do gate...")
    from backend.services.vite_react_renderer import (
        _generate_studio_fallback_files,
        prepare_vite_project_files,
        validate_vite_project_files,
    )

    facts = {
        "business": {
            "name": "Vitor Feitosa - Nutricionista Esportivo",
            "segment": "nutricionista",
            "subniche": "nutricao esportiva",
            "city": "Sao Paulo",
            "phone": "11984585259",
            "rating": "5.0",
        },
        "media": {
            "photos": [
                "https://images.unsplash.com/photo-1490645935967-10de6ba17061",
                "https://images.unsplash.com/photo-1505576399279-565b52d4ac71",
            ]
        },
    }
    files = _generate_studio_fallback_files(facts)
    files["src/components/HeroSection.tsx"] = (
        "export function HeroSection(){return <section id=\"topo\" "
        "className=\"min-h-[80svh] bg-zinc-950 text-white\">Nutricionista</section>}"
    )
    files["src/components/GallerySection.tsx"] = (
        "export function GallerySection(){return <section id=\"galeria\" "
        "className=\"bg-white text-zinc-950\">Galeria sem imagem</section>}"
    )

    prepared = prepare_vite_project_files(files, facts=facts)
    source = "\n".join(prepared.values())

    assert source.count("<img") >= 2
    assert source.count("images.unsplash.com") >= 2
    assert "photo-1490645935967-10de6ba17061" in source
    validate_vite_project_files(prepared, facts, requested_paths=set())

    print("  OK imagens reais entram em Hero/Galeria deterministicamente")
    print("  OK validate_vite_project_files nao acusa 0 refs")


def test_11_guard_nutricionista_esportivo_permite_musculacao_sem_matricula():
    """Sprint 12.20: nutricao esportiva pode citar musculacao, nao matricula."""
    print("\n[TESTE 11/11] guard nutricionista esportivo sem falso positivo...")
    import pytest
    from backend.services.vite_react_renderer import (
        ViteReactRenderError,
        _validate_segment_specificity,
    )

    business = {
        "name": "Vitor Feitosa - Nutricionista Esportivo",
        "segment": "nutricionista",
        "subniche": "nutricao esportiva",
    }
    valid_source = (
        "Nutricionista com consulta, plano alimentar, saude e acompanhamento "
        "para quem pratica musculação."
    )
    _validate_segment_specificity(valid_source, business)

    with pytest.raises(ViteReactRenderError, match="matricula"):
        _validate_segment_specificity(valid_source + " Faça sua matricula hoje.", business)

    print("  OK musculacao liberada apenas no contexto esportivo")
    print("  OK matricula segue bloqueada para nutricionista")


def test_12_vite_copy_only_usa_json_curto_e_codigo_deterministico(monkeypatch, tmp_path):
    """Sprint 14: LLM preenche JSON; FraLib gera TSX deterministico."""
    print("\n[TESTE 12/13] Vite copy_only nao pede codigo completo...")
    import backend.services.vite_react_renderer as renderer

    monkeypatch.setenv("FRALIB_VITE_LLM_POLICY", "copy_only")

    def fake_copy_llm(*args, **kwargs):
        return """{
          "blueprint": "local_service_fast_quote",
          "hero": {
            "headline": "Corte premium sem espera",
            "subheadline": "Agende seu horario em Pinhais com atendimento preciso",
            "cta_primary": "Agendar corte",
            "cta_secondary": "Ver servicos"
          },
          "services_title": "Servicos de barbearia",
          "services": [
            {"title": "Corte masculino", "description": "Corte alinhado ao estilo e rotina."}
          ],
          "lifestyle": {
            "title": "Ritual de cuidado",
            "description": "Ambiente preparado para corte, barba e acabamento."
          },
          "gallery_alt": "Barbearia Fio Nobre ambiente"
        }"""

    def fake_build(workspace):
        dist = workspace / "dist"
        assets = dist / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        (assets / "app.js").write_text("console.log('ok')", encoding="utf-8")
        (dist / "index.html").write_text(
            "<html><head></head><body>"
            "Corte premium sem espera Agendar corte "
            "<script type='module' src='assets/app.js'></script>"
            + ("x" * 320)
            + "</body></html>",
            encoding="utf-8",
        )

    monkeypatch.setattr(renderer, "_call_copy_only_llm", fake_copy_llm)
    monkeypatch.setattr(renderer, "build_vite_project", fake_build)

    result = renderer.render_vite_react_site(
        "",
        workspace_dir=tmp_path,
        facts=LEAD_TEST_FACTS,
        primary_model="sonnet",
        fallback_model="haiku",
        max_tokens=1200,
    )

    source = "\n".join(result.source_files.values())
    statuses = [attempt["status"] for attempt in result.attempts]
    assert result.model == "studio-copy-only"
    assert "copy_only_json_success" in statuses
    assert "studio_copy_only_success" in statuses
    assert "Corte premium sem espera" in source
    assert "Agendar corte" in source
    assert "src/components/ServicesSection.tsx" in result.source_files
    assert "src/components/HeroSection.tsx" in result.source_files

    print("  OK copy_only recebe JSON pequeno")
    print("  OK TSX final vem do Studio/FraLib, nao do LLM")


def test_13_vite_policy_none_nao_chama_llm(monkeypatch, tmp_path):
    """Sprint 14: policy none gera site com 0 chamada LLM."""
    print("\n[TESTE 13/13] Vite policy none com zero LLM...")
    import backend.services.vite_react_renderer as renderer

    monkeypatch.setenv("FRALIB_VITE_LLM_POLICY", "none")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("LLM nao deveria ser chamado com FRALIB_VITE_LLM_POLICY=none")

    def fake_build(workspace):
        dist = workspace / "dist"
        assets = dist / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        (assets / "app.js").write_text("console.log('ok')", encoding="utf-8")
        (dist / "index.html").write_text(
            "<html><head></head><body>"
            "Barbearia Fio Nobre Pinhais "
            "<script type='module' src='assets/app.js'></script>"
            + ("x" * 320)
            + "</body></html>",
            encoding="utf-8",
        )

    monkeypatch.setattr(renderer, "_call_copy_only_llm", fail_if_called)
    monkeypatch.setattr(renderer, "_call_vite_react_llm", fail_if_called)
    monkeypatch.setattr(renderer, "build_vite_project", fake_build)

    result = renderer.render_vite_react_site(
        "",
        workspace_dir=tmp_path,
        facts=LEAD_TEST_FACTS,
        primary_model="sonnet",
        fallback_model="haiku",
        max_tokens=1200,
    )

    statuses = [attempt["status"] for attempt in result.attempts]
    assert result.model == "studio-deterministic"
    assert statuses[0] == "policy_none_deterministic"
    assert "studio_deterministic_success" in statuses
    assert "src/components/ServicesSection.tsx" in result.source_files

    print("  OK policy none nao chama LLM")
    print("  OK Studio deterministico ainda gera site completo")


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    print("=" * 80)
    print("TESTES ANTI-REGRESSAO v1.14 - Sprint 12.12 (caroco enriquecido)")
    print("=" * 80)

    test_1_nicho_modal_block_no_nameerror()
    test_2_caroço_block_agrega_tudo()
    test_3_lead_briefing_block_injeta_dados_reais()
    test_4_gsap_code_block_tem_codigo_real()
    test_5_vite_prompt_with_facts_full()
    test_6_backward_compat_prompt_sem_facts()
    test_7_renderer_summarize_inclui_briefing_real()
    test_8_existing_prompt_blocks_intact()
    test_9_studio_fallback_nutricionista_sem_contaminacao()
    test_10_prepare_injeta_midia_aprovada_quando_llm_nao_usa_imagens()
    test_11_guard_nutricionista_esportivo_permite_musculacao_sem_matricula()

    print("\n" + "=" * 80)
    print("TODOS OS TESTES MANUAIS PASSARAM (11/11)")
    print("Obs: testes 12/13 usam fixtures do pytest; rode: pytest tests/test_anti_regressao_v114.py")
    print("Sprint 12.12 (v1.14) - caroco enriquecido com briefing real")
    print("Bug fix: NameError em _build_nicho_modal_block")
    print("Novo: _build_lead_briefing_block(facts) com JSON-LD + fotos reais")
    print("Novo: _build_gsap_code_block() com useGSAP + ScrollTrigger")
    print("Novo: _build_caroço_block(facts) agregando TUDO")
    print("Enriquece: _summarize_builder_facts do renderer (services/horarios/SEO)")
    print("=" * 80)
