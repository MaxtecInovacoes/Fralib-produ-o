"""
Executa todos os testes SDR bugfix - VERSÃO STANDALONE.
Executar: python tests/run_sdr_bugfix_tests.py
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

print("=" * 70)
print("TESTES SDR BUGBIX - 3 BUGS CRITICOS DO FRANZ (SDR)")
print("=" * 70)

# ============================================
# TESTES UNITARIOS
# ============================================
print("\n=== TESTES UNITARIOS (12) ===\n")

passed = 0
failed = 0

# BUG 1: sanitize_sem_chamar_llm_extra
def test_sanitize_sem_chamar_llm_extra():
    from whatsapp.sdr_reply_service import sanitize_reply
    raw = '{"resposta":"Oi, tudo bem?","novo_stage":"intro"}'
    result = sanitize_reply(raw, retry_extractor=None)
    assert result == "Oi, tudo bem?"
    assert not result.startswith("{")

# BUG 1: sanitize_nao_chama_retry_extractor_quando_regex_funciona
def test_sanitize_nao_chama_retry_extractor():
    from whatsapp.sdr_reply_service import sanitize_reply
    call_count = {"count": 0}
    def mock_retry_extractor(raw):
        call_count["count"] += 1
        return "NAO DEVE SER CHAMADO"
    raw = '{"resposta":"Texto limpo","stage":"hook"}'
    result = sanitize_reply(raw, retry_extractor=mock_retry_extractor)
    assert call_count["count"] == 0
    assert result == "Texto limpo"

# BUG 1: sanitize_chama_retry_apenas_se_regex_falhar
def test_sanitize_chama_retry_se_regex_falhar():
    from whatsapp.sdr_reply_service import sanitize_reply
    call_count = {"count": 0}
    def mock_retry_extractor(raw):
        call_count["count"] += 1
        return "Fallback texto"
    raw = '{"foo": "bar", "baz": 123}'
    result = sanitize_reply(raw, retry_extractor=mock_retry_extractor)
    assert call_count["count"] == 1
    assert result == "Fallback texto"

# BUG 1: sanitize_lanca_excecao_em_json_invalido
def test_sanitize_lanca_excecao_em_json_invalido():
    """JSON invalido deve LANÇAR EXCEÇÃO - não usa fallback."""
    from whatsapp.sdr_reply_service import sanitize_reply
    raw = "{invalid json}"
    try:
        result = sanitize_reply(raw, retry_extractor=None)
        assert False, "Deveria ter lancado ValueError"
    except ValueError as e:
        assert "Cannot extract reply" in str(e)

# BUG 2: watchdog_libera_quando_lead_respondeu
def test_watchdog_libera_quando_lead_respondeu():
    from agents.sdr_langgraph.watchdog import can_send_next_outbound
    pode_enviar, motivo = can_send_next_outbound(
        telefone="5511999999999",
        user_id=1,
        sdr_stage="hook",
        lead_responded=True
    )
    assert pode_enviar is True
    assert motivo == "lead_responded_can_reply"

# BUG 2: watchdog_bloqueia_sem_lead_responded
def test_watchdog_bloqueia_sem_lead_responded():
    from agents.sdr_langgraph.watchdog import can_send_next_outbound
    import agents.sdr_langgraph.watchdog

    class MockResult:
        def __init__(self, rows):
            self._rows = rows
        def fetchall(self):
            return self._rows

    class MockConn:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def execute(self, *args, **kwargs):
            return MockResult([
                ("msg1", "saida", datetime.now(timezone.utc)),
                ("msg2", "saida", datetime.now(timezone.utc)),
            ])

    class MockEngine:
        def connect(self):
            return MockConn()

    original = agents.sdr_langgraph.watchdog._get_engine
    agents.sdr_langgraph.watchdog._get_engine = lambda: MockEngine()
    try:
        pode_enviar, motivo = can_send_next_outbound(
            telefone="5511999999999",
            user_id=1,
            sdr_stage="hook",
            lead_responded=False
        )
        assert pode_enviar is False
        assert motivo == "max_2_messages_without_response"
    finally:
        agents.sdr_langgraph.watchdog._get_engine = original

# BUG 2: responder_nao_envia_duplicado
def test_responder_nao_envia_duplicado():
    from whatsapp.sdr_reply_service import is_duplicate_reply
    history = [
        {"role": "user", "content": "Ola"},
        {"role": "assistant", "content": "Ola! Como posso ajudar?"},
    ]
    is_dup = is_duplicate_reply(history, "Ola! Como posso ajudar?")
    assert is_dup is True

# BUG 3: history_sincronizada_com_langgraph
def test_history_sincronizada_com_langgraph():
    db_history = [
        {"role": "user", "content": "Mensagem antiga do DB 1"},
        {"role": "assistant", "content": "Resposta antiga do DB 1"},
    ]
    lg_history = [
        {"type": "human", "content": "Mensagem do state LangGraph"},
        {"type": "ai", "content": "Resposta do state LangGraph"},
    ]
    merged = list(db_history)
    for msg in lg_history[-10:]:
        role = "assistant" if msg.get("type") == "ai" else "user"
        content = msg.get("content", "")
        if content:
            merged.insert(0, {"role": role, "content": content})
    seen = set()
    deduped = []
    for item in merged:
        key = f"{item.get('role')}:{item.get('content', '')[:50]}"
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    deduped = deduped[-20:]
    contents = [item["content"] for item in deduped]
    assert "Mensagem antiga do DB 1" in contents
    assert "Resposta antiga do DB 1" in contents
    assert "Mensagem do state LangGraph" in contents
    assert "Resposta do state LangGraph" in contents

# BUG 3: history_dedup_preserva_ordem
def test_history_dedup_preserva_ordem():
    history = [
        {"role": "user", "content": "Msg 1"},
        {"role": "assistant", "content": "Msg 2"},
        {"role": "user", "content": "Msg 1"},
        {"role": "assistant", "content": "Msg 2"},
        {"role": "user", "content": "Msg 3"},
    ]
    seen = set()
    deduped = []
    for item in history:
        key = f"{item.get('role')}:{item.get('content', '')[:50]}"
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    assert len(deduped) == 3
    assert deduped[0]["content"] == "Msg 1"
    assert deduped[1]["content"] == "Msg 2"
    assert deduped[2]["content"] == "Msg 3"

# BUG 3: history_limit_20_mensagens
def test_history_limit_20_mensagens():
    history = [{"role": "user", "content": f"Msg {i}"} for i in range(30)]
    limited = history[-20:]
    assert len(limited) == 20
    assert limited[0]["content"] == "Msg 10"
    assert limited[-1]["content"] == "Msg 29"

# Regressao: build_history_reversed_order
def test_build_history_reversed_order():
    from whatsapp.sdr_reply_service import build_history
    rows = [("msg_nova", "saida"), ("msg_velha", "saida")]
    history = build_history(rows)
    assert history[0]["content"] == "msg_velha"
    assert history[1]["content"] == "msg_nova"

# Regressao: is_emoji_reaction_only
def test_is_emoji_reaction_only():
    from agents.sdr_langgraph.watchdog import is_emoji_reaction_only
    assert is_emoji_reaction_only("👀") is True
    assert is_emoji_reaction_only("❤️") is True
    assert is_emoji_reaction_only("👍👍") is True
    assert is_emoji_reaction_only("") is True
    assert is_emoji_reaction_only("ok") is False
    assert is_emoji_reaction_only("sim, quero") is False

# ============================================
# TESTES DE INTEGRACAO
# ============================================
print("\n=== TESTES INTEGRACAO (9) ===\n")

def mock_lead_data():
    return {
        "telefone": "5511999999999",
        "lead_id": "lead_123",
        "nome": "Empresa Teste",
        "cidade": "Sao Paulo",
        "segmento": "tech",
        "rating": 4.5,
        "site_url": "https://empresa.com.br",
        "sdr_stage": "hook",
        "user_id": 1,
    }

def test_lead_responde_franz_responde_corretamente():
    from agents.sdr_langgraph.compat import responder_lead
    lead = mock_lead_data()
    history = [
        {"role": "user", "content": "Ola"},
        {"role": "assistant", "content": "Ola! Vi que voce tem um site."},
    ]
    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = {
            "outgoing_message": "Claro! Vamos agendar uma conversa?",
            "detected_intent": "interested",
            "guard_reason": None,
            "memory": MagicMock(
                stage="qualify", active_agent="qualificacao", previous_agent="",
                model_dump=lambda: {}
            ),
            "agent_handoff_reason": "",
        }
        mock_graph.return_value = mock_instance
        with patch("agents.memory.carregar_memoria") as mock_mem:
            mock_mem.return_value = {"nome": "Empresa Teste", "cidade": "Sao Paulo", "stage": "hook"}
            result = responder_lead(
                telefone=lead["telefone"],
                mensagem_recebida="Quero saber mais",
                nome_negocio=lead["nome"],
                lead_id=lead["lead_id"],
                cidade=lead["cidade"],
                segmento=lead["segmento"],
                rating=lead["rating"],
                site_url=lead["site_url"],
                history=history,
                sdr_stage=lead["sdr_stage"],
                user_id=lead["user_id"],
            )
    assert not result.reply.startswith("{")
    assert '"resposta"' not in result.reply
    assert result.reply == "Claro! Vamos agendar uma conversa?"

def test_responder_nao_envia_json_puro_e2e():
    from agents.sdr_langgraph.compat import responder_lead
    lead = mock_lead_data()
    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = {
            "outgoing_message": '{"invalid": "json"}',
            "detected_intent": "other",
            "guard_reason": None,
            "memory": MagicMock(stage="hook", active_agent="atendimento", previous_agent="", model_dump=lambda: {}),
            "agent_handoff_reason": "",
        }
        mock_graph.return_value = mock_instance
        with patch("agents.memory.carregar_memoria") as mock_mem:
            mock_mem.return_value = {}
            result = responder_lead(
                telefone=lead["telefone"],
                mensagem_recebida="Ola",
                lead_id=lead["lead_id"],
                user_id=lead["user_id"],
            )
    should_send = not (result.reply.startswith("{") or '"resposta"' in result.reply or '"novo_stage"' in result.reply)
    assert should_send is False

def test_lead_responde_nao_duplica_mensagem():
    from agents.sdr_langgraph.watchdog import can_send_next_outbound
    lead = mock_lead_data()
    pode_enviar, motivo = can_send_next_outbound(
        telefone=lead["telefone"],
        user_id=lead["user_id"],
        sdr_stage=lead["sdr_stage"],
        lead_responded=True,
    )
    assert pode_enviar is True
    assert motivo == "lead_responded_can_reply"

def test_outbound_introducao_continua_funcionando():
    from agents.sdr_langgraph.compat import iniciar_contato, BryanInput
    lead = mock_lead_data()
    lead_input = BryanInput(
        nome=lead["nome"], cidade=lead["cidade"], segmento=lead["segmento"],
        telefone=lead["telefone"], site_url=lead["site_url"], rating=lead["rating"],
    )
    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = {
            "outgoing_message": "Ola! Vi seu site e gostaria de ajudar.",
            "detected_intent": "outbound_intro",
            "guard_reason": None,
            "memory": MagicMock(stage="hook", active_agent="abordagem", previous_agent="", model_dump=lambda: {}),
            "agent_handoff_reason": "",
        }
        mock_graph.return_value = mock_instance
        with patch("agents.sdr_langgraph.compat._verificar_watchdog_outbound") as mock_watchdog:
            mock_watchdog.return_value = (True, "ok")
            with patch("agents.memory.carregar_memoria") as mock_mem:
                mock_mem.return_value = {}
                result = iniciar_contato(lead=lead_input, user_id=lead["user_id"])
    assert result.reply is not None
    assert len(result.reply) > 0

def test_history_e2e_com_state_anterior():
    from agents.sdr_langgraph.compat import responder_lead
    lead = mock_lead_data()
    db_history = [
        {"role": "user", "content": "Ola"},
        {"role": "assistant", "content": "Oi! Tudo bem?"},
    ]
    langgraph_state = {
        "conversation_history": [
            {"type": "human", "content": "Mensagem antiga 1"},
            {"type": "ai", "content": "Resposta antiga 1"},
        ],
        "stage": "hook",
    }
    captured_state = {}
    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        def capture_state(state):
            captured_state.update(state)
            return {
                "outgoing_message": "Entendi!",
                "detected_intent": "other",
                "guard_reason": None,
                "memory": MagicMock(stage="hook", active_agent="atendimento", previous_agent="", model_dump=lambda: {}),
                "agent_handoff_reason": "",
            }
        mock_instance.invoke.side_effect = capture_state
        mock_graph.return_value = mock_instance
        with patch("agents.memory.carregar_memoria") as mock_mem:
            mock_mem.return_value = langgraph_state
            result = responder_lead(
                telefone=lead["telefone"],
                mensagem_recebida="Continuando",
                lead_id=lead["lead_id"],
                history=db_history,
                user_id=lead["user_id"],
            )
    passed_history = captured_state.get("history", [])
    contents = [m["content"] for m in passed_history]
    assert "Ola" in contents
    assert "Mensagem antiga 1" in contents

def test_responder_lead_error_handling():
    from agents.sdr_langgraph.compat import responder_lead
    lead = mock_lead_data()
    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        mock_instance.invoke.side_effect = Exception("Grafo quebrou")
        mock_graph.return_value = mock_instance
        with patch("agents.memory.carregar_memoria") as mock_mem:
            mock_mem.return_value = {}
            result = responder_lead(
                telefone=lead["telefone"],
                mensagem_recebida="Ola",
                lead_id=lead["lead_id"],
                user_id=lead["user_id"],
            )
    assert result.reply is not None
    assert result.guard == "graph_error"

def test_followup_automatico_continua_funcionando():
    from agents.sdr_langgraph.compat import followup_automatico
    lead = mock_lead_data()
    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = {
            "outgoing_message": "Ola! Retomando nossa conversa...",
            "detected_intent": "followup",
            "guard_reason": None,
            "memory": MagicMock(stage="followup_24h", active_agent="followup", previous_agent="", model_dump=lambda: {}),
            "agent_handoff_reason": "",
        }
        mock_graph.return_value = mock_instance
        with patch("agents.memory.carregar_memoria") as mock_mem:
            mock_mem.return_value = {}
            with patch("agents.sdr_langgraph.compat._verificar_watchdog_outbound") as mock_watchdog:
                mock_watchdog.return_value = (True, "ok")
                result = followup_automatico(telefone=lead["telefone"], tipo="24h", user_id=lead["user_id"])
    assert result.reply is not None

def test_is_outbound_marcado_corretamente_para_intro():
    from agents.sdr_langgraph.compat import iniciar_contato, BryanInput
    lead = mock_lead_data()
    lead_input = BryanInput(
        nome=lead["nome"], cidade=lead["cidade"], segmento=lead["segmento"],
        telefone=lead["telefone"], site_url=lead["site_url"], rating=lead["rating"],
    )
    captured_state = {}
    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        def capture_state(state):
            captured_state.update(state)
            return {
                "outgoing_message": "Ola!",
                "detected_intent": "outbound_intro",
                "guard_reason": None,
                "memory": MagicMock(stage="hook", active_agent="abordagem", previous_agent="", model_dump=lambda: {}),
                "agent_handoff_reason": "",
            }
        mock_instance.invoke.side_effect = capture_state
        mock_graph.return_value = mock_instance
        with patch("agents.sdr_langgraph.compat._verificar_watchdog_outbound") as mock_watchdog:
            mock_watchdog.return_value = (True, "ok")
            with patch("agents.memory.carregar_memoria") as mock_mem:
                mock_mem.return_value = {}
                iniciar_contato(lead=lead_input, user_id=lead["user_id"])
    assert captured_state.get("is_outbound") is True

def test_is_outbound_false_para_resposta():
    from agents.sdr_langgraph.compat import responder_lead
    lead = mock_lead_data()
    captured_state = {}
    with patch("agents.sdr_langgraph.compat.get_sdr_graph") as mock_graph:
        mock_instance = MagicMock()
        def capture_state(state):
            captured_state.update(state)
            return {
                "outgoing_message": "Respondendo...",
                "detected_intent": "other",
                "guard_reason": None,
                "memory": MagicMock(stage="hook", active_agent="atendimento", previous_agent="", model_dump=lambda: {}),
                "agent_handoff_reason": "",
            }
        mock_instance.invoke.side_effect = capture_state
        mock_graph.return_value = mock_instance
        with patch("agents.memory.carregar_memoria") as mock_mem:
            mock_mem.return_value = {}
            responder_lead(
                telefone=lead["telefone"],
                mensagem_recebida="Ola",
                lead_id=lead["lead_id"],
                user_id=lead["user_id"],
            )
    assert captured_state.get("is_outbound") is False

# ============================================
# EXECUTAR TODOS OS TESTES
# ============================================

all_tests = [
    # Unitarios
    ("test_sanitize_sem_chamar_llm_extra", test_sanitize_sem_chamar_llm_extra),
    ("test_sanitize_nao_chama_retry_extractor", test_sanitize_nao_chama_retry_extractor),
    ("test_sanitize_chama_retry_se_regex_falhar", test_sanitize_chama_retry_se_regex_falhar),
    ("test_responder_nao_envia_json_puro", test_responder_nao_envia_json_puro),
    ("test_watchdog_libera_quando_lead_respondeu", test_watchdog_libera_quando_lead_respondeu),
    ("test_watchdog_bloqueia_sem_lead_responded", test_watchdog_bloqueia_sem_lead_responded),
    ("test_responder_nao_envia_duplicado", test_responder_nao_envia_duplicado),
    ("test_history_sincronizada_com_langgraph", test_history_sincronizada_com_langgraph),
    ("test_history_dedup_preserva_ordem", test_history_dedup_preserva_ordem),
    ("test_history_limit_20_mensagens", test_history_limit_20_mensagens),
    ("test_build_history_reversed_order", test_build_history_reversed_order),
    ("test_is_emoji_reaction_only", test_is_emoji_reaction_only),
    # Integracao
    ("test_lead_responde_franz_responde_corretamente", test_lead_responde_franz_responde_corretamente),
    ("test_responder_nao_envia_json_puro_e2e", test_responder_nao_envia_json_puro_e2e),
    ("test_lead_responde_nao_duplica_mensagem", test_lead_responde_nao_duplica_mensagem),
    ("test_outbound_introducao_continua_funcionando", test_outbound_introducao_continua_funcionando),
    ("test_history_e2e_com_state_anterior", test_history_e2e_com_state_anterior),
    ("test_responder_lead_error_handling", test_responder_lead_error_handling),
    ("test_followup_automatico_continua_funcionando", test_followup_automatico_continua_funcionando),
    ("test_is_outbound_marcado_corretamente_para_intro", test_is_outbound_marcado_corretamente_para_intro),
    ("test_is_outbound_false_para_resposta", test_is_outbound_false_para_resposta),
]

total_passed = 0
total_failed = 0

for name, test in all_tests:
    try:
        test()
        print(f"PASS: {name}")
        total_passed += 1
    except AssertionError as e:
        print(f"FAIL: {name}: {e}")
        total_failed += 1
    except Exception as e:
        print(f"ERROR: {name}: {e}")
        total_failed += 1

print("\n" + "=" * 70)
print(f"RESULTADO FINAL: {total_passed}/{len(all_tests)} TESTES PASSARAM")
print("=" * 70)

if total_failed == 0:
    print("\nSUCESSO! TODOS OS TESTES PASSARAM.")
else:
    print(f"\nFALHA: {total_failed} testes falharam.")
    sys.exit(1)
