"""
Testes de validacao NO_FALLBACK - Garante que o SDR NAO usa fallbacks.

Executar: python -m pytest tests/unit/test_no_fallback.py -v
"""
import pytest


# ════════════════════════════════════════════════════════════════════
# REGRA: Sistema NAO pode usar fallbacks hardcoded
# ════════════════════════════════════════════════════════════════════

# Fallbacks que NAO podem existir no codigo
FORBIDDEN_PATTERNS = [
    ("Opa, tudo bem? Me dá um minuto", "fallback genérico de atendimento"),
    ("vi voces no Google Maps", "exemplo Google Maps"),
    ("Encontrei vocês no Google Maps", "exemplo Google Maps"),
    ("Boa tarde! Vi", "fallback hook genérico"),
    ("DEFAULT_REPLY", "constante de fallback"),
    ('fallback_reply="', "parâmetro fallback"),
    ("fallback to legacy", "fallback legado de orquestrador"),
    ("usando fallback", "fallback textual por contaminação"),
]

# Padroes que devem gerar excecao, nao fallback
INVALID_JSON_CASES = [
    "{invalid json}",
    '{"foo": "bar"}',  # sem campo resposta/reply
    "texto puro sem sentido",
    "",
    None,
]


class TestNoFallbackInCode:
    """Verifica que fallbacks hardcoded foram removidos."""

    def test_sdr_nao_tem_fallback_de_orquestrador_ou_contaminacao(self):
        """SDR deve falhar/retry, nao criar resposta legacy/template."""
        from pathlib import Path
        agent_path = Path(__file__).resolve().parents[2] / "backend" / "agents" / "sdr_langgraph" / "agent.py"
        content = agent_path.read_text(encoding="utf-8")

        assert "fallback to legacy" not in content
        assert "_build_legacy_decision(" not in content
        assert "usando fallback" not in content
        assert "hook reply contaminated" in content
        assert "reply contaminated" in content

    def test_watchdog_error_bloqueia_outbound(self):
        """Se o watchdog quebrar, outbound deve bloquear em vez de liberar spam."""
        from pathlib import Path
        compat_path = Path(__file__).resolve().parents[2] / "backend" / "agents" / "sdr_langgraph" / "compat.py"
        content = compat_path.read_text(encoding="utf-8")
        block = content[content.index("def _verificar_watchdog_outbound") : content.index("def responder_lead")]

        assert 'return False, "watchdog_error"' in block
        assert 'return True, "watchdog_error"' not in block

    def test_builder_template_nao_cai_para_llm_silencioso(self):
        """Template route nao pode cair para outro renderer sem falhar o job."""
        from pathlib import Path
        worker_path = Path(__file__).resolve().parents[2] / "backend" / "services" / "builder_worker.py"
        content = worker_path.read_text(encoding="utf-8")
        template_block = content[content.index("if use_templates:") : content.index("else:", content.index("if use_templates:"))]

        assert "fallback LLM" not in template_block
        assert "render_openui_site(" not in template_block
        assert "sem fallback" in template_block

    def test_vite_cinematic_media_nao_usa_imagem_generica(self):
        """Hero/galeria cinematica deve falhar se nao houver midia real no facts."""
        from pathlib import Path
        renderer_path = Path(__file__).resolve().parents[2] / "backend" / "services" / "vite_react_renderer.py"
        content = renderer_path.read_text(encoding="utf-8")
        block = content[
            content.index("def _cinematic_media_urls") : content.index("def _cinematic_copy")
        ]

        assert "ImageNotAvailableError" in block
        assert "images.unsplash.com/photo-1490645935967" not in block
        assert "images.unsplash.com/photo-1512621776951" not in block
        assert "images.unsplash.com/photo-1498837167922" not in block

    def test_sem_fallback_google_maps_no_rag(self):
        """FRANZ_RAG.md nao pode conter exemplo 'Google Maps'."""
        from pathlib import Path
        rag_path = Path(__file__).resolve().parents[2] / "backend" / "agents" / "FRANZ_RAG.md"
        if rag_path.exists():
            content = rag_path.read_text(encoding="utf-8")
            assert "Google Maps" not in content, "FRANZ_RAG.md ainda contem 'Google Maps'"
            assert "vi voces" not in content.lower(), "FRANZ_RAG.md ainda contem exemplo generico"

    def test_sem_fallback_na_funcao_sanitize(self):
        """sanitize_reply nao pode ter fallback_reply como default."""
        from pathlib import Path
        import sys
        ROOT = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(ROOT / "backend"))

        from whatsapp.sdr_reply_service import sanitize_reply
        import inspect
        sig = inspect.signature(sanitize_reply)
        params = sig.parameters

        # Verificar que nao existe parametro fallback_reply
        assert "fallback_reply" not in params, "sanitize_reply ainda tem parametro fallback_reply"

    def test_sem_fallback_na_persona(self):
        """FRANZ_PERSONA.md nao pode ter fallbacks genericos."""
        from pathlib import Path
        persona_path = Path(__file__).resolve().parents[2] / "backend" / "agents" / "FRANZ_PERSONA.md"
        if persona_path.exists():
            content = persona_path.read_text(encoding="utf-8")
            forbidden = ["Opa, tudo bem", "DEFAULT_REPLY", "fallback"]
            for pattern in forbidden:
                assert pattern not in content, f"FRANZ_PERSONA.md contem fallback: {pattern}"


class TestSanitizeReplyNoFallback:
    """Testa que sanitize_reply NAO usa fallbacks."""

    def test_empty_input_lanca_excecao(self):
        """Input vazio deve lancar excecao, nao retornar fallback."""
        from whatsapp.sdr_reply_service import sanitize_reply

        with pytest.raises(ValueError) as exc_info:
            sanitize_reply("")
        assert "empty reply" in str(exc_info.value).lower()

        with pytest.raises(ValueError):
            sanitize_reply(None)

    def test_invalid_json_lanca_excecao(self):
        """JSON invalido deve lancar excecao, nao usar fallback."""
        from whatsapp.sdr_reply_service import sanitize_reply

        invalid_cases = [
            "{invalid json}",
            '{"foo": "bar"}',
            "{not closed",
        ]

        for invalid in invalid_cases:
            with pytest.raises(ValueError) as exc_info:
                sanitize_reply(invalid)
            assert "cannot extract" in str(exc_info.value).lower() or "failed to extract" in str(exc_info.value).lower()

    def test_valid_json_extraido_corretamente(self):
        """JSON valido deve ser extraido sem chamar fallback."""
        from whatsapp.sdr_reply_service import sanitize_reply

        # Testa varios formatos de JSON valido
        cases = [
            ('{"reply":"Oi, tudo bem?"}', "Oi, tudo bem?"),
            ('{"resposta":"Ola!"}', "Ola!"),
            ('{"reply": "Mensagem", "stage": "hook"}', "Mensagem"),
        ]

        for json_input, expected in cases:
            result = sanitize_reply(json_input)
            assert result == expected, f"Expected '{expected}', got '{result}'"

    def test_plain_text_retornado_como_esta(self):
        """Texto plano deve ser retornado sem modificacao."""
        from whatsapp.sdr_reply_service import sanitize_reply

        cases = [
            "Oi, tudo bem?",
            "Qual o preco?",
            "Ola Franz!",
        ]

        for text in cases:
            result = sanitize_reply(text)
            assert result == text, f"Plain text deve ser retornado como esta: {text}"


class TestFollowupsNoTemplate:
    """Verifica que followups no RAG sao exemplos de padrao, nao templates."""

    def test_followups_tem_regra_de_nao_copiar(self):
        """Followups devem ter instrucao para NAO COPIAR os exemplos."""
        from pathlib import Path
        rag_path = Path(__file__).resolve().parents[2] / "backend" / "agents" / "FRANZ_RAG.md"

        if rag_path.exists():
            content = rag_path.read_text(encoding="utf-8")

            # Verificar que existe secao de regras para followups
            assert "## Follow-ups" in content or "## Followups" in content, "Falta secao de Follow-ups"

            # Verificar que ha instrucao para criar mensagens unicas
            if "24h sem resposta" in content:
                # Deve ter advertencia para NAO COPIAR
                assert "NAO COPIE" in content or "nao copie" in content or "REFERENCIA" in content, \
                    "Followups devem instruir para NAO COPIAR exemplos"


class TestRAGExamplesNoGeneric:
    """Verifica que exemplos no RAG sao de padrao, nao templates."""

    def test_exemplos_sao_de_padrao_nao_template(self):
        """Exemplos no RAG devem ser 'Exemplo de PADRAO', nao templates para copiar."""
        from pathlib import Path
        rag_path = Path(__file__).resolve().parents[2] / "backend" / "agents" / "FRANZ_RAG.md"

        if rag_path.exists():
            content = rag_path.read_text(encoding="utf-8")

            # Padroes que indicam que exemplos sao para copiar (ruim)
            bad_patterns = [
                '"Oi! Tudo bem?',
                '"Ola, tudo bem?',
                '\"Ola!\"',
            ]

            for pattern in bad_patterns:
                # Se existir, deve estar em contexto de excecao, nao como template
                if pattern in content:
                    # Verificar que ha comentario dizendo para NAO usar
                    lines_before = content[:content.index(pattern)]
                    recent_lines = lines_before.split('\n')[-5:]
                    context = '\n'.join(recent_lines)

                    assert ("Exemplo" in context or "PADRAO" in context.upper()), \
                        f"Exemplo generico encontrado sem advertencia: {pattern}"


class TestListenerNoFallback:
    """Verifica que whatsapp_listener nao usa fallbacks."""

    def test_json_detection_nao_usa_fallback(self):
        """Quando detecta JSON, deve lancar excecao ou extrair, NAO usar fallback."""
        from pathlib import Path
        import sys
        ROOT = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(ROOT / "backend"))

        listener_path = ROOT / "backend" / "whatsapp_listener.py"
        if listener_path.exists():
            content = listener_path.read_text(encoding="utf-8")

            # Nao pode ter fallback_reply no listener
            assert "fallback_reply" not in content, "whatsapp_listener nao pode usar fallback_reply"


# ════════════════════════════════════════════════════════════════════
# TESTES DE COMPORTAMENTO ESPERADO
# ════════════════════════════════════════════════════════════════════

class TestExpectedBehavior:
    """Testa comportamento esperado: LLM deve gerar respostas unicas."""

    def test_llm_deve_gerar_respostas_diferentes_para_contextos_diferentes(self):
        """Contexto diferente deve gerar resposta diferente (sem template).

        Este teste verifica que o sistema da contexto suficiente para a LLM
        gerar respostas unicas baseadas em:
        - Nome do lead
        - Cidade
        - Segmento
        - Estagio atual
        - Historico
        """
        # Este e um teste de arquitetura - verifica que o sistema DA contexto
        from pathlib import Path
        import sys
        ROOT = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(ROOT / "backend"))

        # Verificar que prompts incluem contexto dinamico
        from agents.sdr_langgraph import prompts as sdr_prompts

        # build_user_prompt deve usar parametros de contexto
        sig_prompt = sdr_prompts.build_user_prompt
        import inspect
        params = inspect.signature(sig_prompt).parameters

        required_context = ["nome", "cidade", "segmento", "rating", "history", "stage"]
        for ctx in required_context:
            assert ctx in params, f"build_user_prompt deve incluir contexto: {ctx}"

    def test_stage_prompts_tem_regra_de_nao_fallback(self):
        """Stage prompts devem instruir LLM a gerar resposta, nao usar fallback."""
        from pathlib import Path
        import sys
        ROOT = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(ROOT / "backend"))

        from agents.sdr_langgraph import prompts as sdr_prompts

        # Verificar que stage prompts consultivo nao tem fallbacks
        if hasattr(sdr_prompts, "STAGE_PROMPTS_CONSULTIVO"):
            for stage_name, stage_prompt in sdr_prompts.STAGE_PROMPTS_CONSULTIVO.items():
                # Nao pode ter "fallback" como estrategia
                assert "fallback" not in stage_prompt.lower() or "disabled" in stage_prompt.lower(), \
                    f"Stage {stage_name} contem fallback"
