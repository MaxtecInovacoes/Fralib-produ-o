from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "agents"))
sys.path.insert(0, str(ROOT / "backend"))


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_worker_first_contact_enqueues_without_direct_whatsapp_send():
    source = _read("worker.py")
    block = source[
        source.index("if tipo in SDR_OUTREACH_JOB_TYPES") :
        source.index('return False, "desconhecido"')
    ]

    assert "enqueue_outbound(" in block
    assert "source=\"franz_outreach\"" in block
    assert "f\"{meowhats_url}/api/sessions/{_tenant_key}/send\"" not in block
    assert "_salvar_interacao(" not in block


def test_cron_enqueues_intro_and_sends_followup_directly():
    source = _read("backend/endpoints/cron_endpoints.py")
    intro_block = source[
        source.index("async def despachar_fila_franz") :
        source.index("async def followup_franz")
    ]
    followup_block = source[source.index("async def followup_franz") :]

    assert "enqueue_outbound(" in intro_block
    assert "sdr_stage='pending_sdr_send'" in intro_block
    assert "_salvar_interacao(" not in intro_block

    first_followup = followup_block.index('fu_output = followup_automatico(telefone or whatsapp or "", tipo')
    first_guard = followup_block.index("if not is_tenant_connected(wpp_tenant):")
    assert first_guard < first_followup
    assert "_send_sdr_direct(user_id, tel, fu_output.reply)" in followup_block
    assert "source=\"followup\"" not in followup_block

    second_followup = followup_block.index(
        'fu_output = followup_automatico(telefone or whatsapp or "", "scheduled"'
    )
    second_guard = followup_block.rindex(
        "if not is_tenant_connected(wpp_tenant):", 0, second_followup
    )
    assert second_guard < second_followup


def test_listener_records_outbound_only_after_send_success():
    source = _read("backend/whatsapp_listener.py")
    process_block = source[source.index("def _processar_mensagem") :]
    executor = _read("backend/whatsapp/response_executor.py")
    send_block = executor[executor.index("def send_response") : executor.index("def execute_response")]

    assert process_block.index("if not is_tenant_connected(tenant_id):") < process_block.index(
        "from agents.sdr_langgraph import responder_lead"
    )
    assert process_block.index("if opt_out_like:") < process_block.index(
        "from agents.sdr_langgraph import responder_lead"
    )
    persist_marker = 'ctx.save_interaction_fn(ctx.lead_id, ctx.resposta, "saida", ctx.user_id)'
    assert send_block.index("if not send_ok:") < send_block.index(
        persist_marker
    )
    assert "return False" in send_block[send_block.index("if not send_ok:") : send_block.index(persist_marker)]
    assert "sera reenviada quando reconectar" not in source


def test_listener_cooldown_waits_instead_of_dropping_inbound_reply():
    source = _read("backend/whatsapp_listener.py")
    process_block = source[source.index("def _processar_mensagem") :]
    cooldown_block = process_block[
        process_block.index("if _check_cooldown(lead_key):") :
        process_block.index("# Limite diário")
    ]

    assert "_cooldown_remaining" in source
    assert "_time.sleep" in cooldown_block
    assert "return" not in cooldown_block
    assert "resposta adiada" not in cooldown_block


def test_followup_does_not_reveal_site_before_reveal(monkeypatch):
    import sdr_langgraph as bryan

    monkeypatch.setattr(bryan, "_agent_name_for_user", lambda user_id=None: "Franz")
    url = "https://seunegociofralib.site/sites/2/start-academia/"
    pre_reveal_stages = [
        "hook",
        "intro",
        "qualify",
        "pain",
        "amplify",
        "tease",
        "proof",
        "followup1",
        "followup2",
        "followup_24h",
        "followup_72h",
        "f1",
        "f2",
    ]

    for stage in pre_reveal_stages:
        msg = bryan.gerar_followup(
            {
                "nome": "Start Academia",
                "segmento": "academia",
                "cidade": "Curitiba",
                "site_url": url,
                "sdr_stage": stage,
            },
            "24h",
        )
        assert url not in msg
        assert "http" not in msg.lower()
        assert "o que achou" not in msg.lower()
        assert "projeto" not in msg.lower()


def test_langgraph_intro_guard_blocks_site_reveal_and_stage_jump():
    compat = _read("backend/agents/sdr_langgraph/compat.py")
    intro_block = compat[
        compat.index("def iniciar_contato") : compat.index("def _verificar_watchdog_outbound")
    ]

    assert "_verificar_watchdog_outbound" in intro_block
    assert intro_block.index("_verificar_watchdog_outbound") < intro_block.index("graph.invoke")
    assert '"incoming_message": ""' in intro_block

    prompts = _read("backend/agents/sdr_langgraph/prompts.py")
    tease_block = prompts[prompts.index('"tease":') : prompts.index('"proof":')]
    proof_block = prompts[prompts.index('"proof":') : prompts.index('"feedback":')]
    assert "{site_url}" not in tease_block
    assert "SEM revelar" in tease_block
    assert "{site_url}" in proof_block


def test_cron_followup_requires_prior_outbound_history():
    source = _read("backend/endpoints/cron_endpoints.py")
    followup_block = source[source.index("async def followup_franz") :]

    assert "EXISTS (" in followup_block
    assert "FROM interacoes i" in followup_block
    assert "i.direcao = 'saida'" in followup_block
    assert followup_block.index("FROM interacoes i") < followup_block.index(
        "ORDER BY l.atualizado_em ASC"
    )


def test_worker_and_cron_persist_successful_outbound_history():
    worker = _read("worker.py")
    bryan_block = worker[
        worker.index("if tipo in SDR_OUTREACH_JOB_TYPES") :
        worker.index('return False, "desconhecido"')
    ]
    assert "enqueue_outbound(" in bryan_block
    assert "_salvar_interacao(" not in bryan_block

    cron = _read("backend/endpoints/cron_endpoints.py")
    assert "from backend.whatsapp_listener import is_tenant_connected, _salvar_interacao" in cron
    assert cron.count('_salvar_interacao(lead_id,') >= 2
    assert "_send_sdr_direct(user_id, tel, fu_output.reply)" in cron

    queue = _read("backend/services/outbound_queue.py")
    assert "UPDATE outbound_queue SET status = 'sent'" in queue
    assert "INSERT INTO interacoes" in queue


def test_worker_does_not_mark_empty_bryan_reply_as_generic_success():
    worker = _read("worker.py")
    bryan_block = worker[
        worker.index("if tipo in SDR_OUTREACH_JOB_TYPES") :
        worker.index('return False, "desconhecido"')
    ]
    empty_reply_block = bryan_block[
        bryan_block.index("if not franz_output or not franz_output.reply") :
        bryan_block.index("tel = (payload.get(\"whatsapp\")")
    ]

    assert "Não é erro, só fora do horário" not in empty_reply_block
    assert 'intent == "fila"' in empty_reply_block
    assert 'return False, "franz_schedule", "Fora do horario do SDR"' in empty_reply_block
    assert 'intent == "skip_duplicado"' in empty_reply_block
    assert 'return False, "franz", "Franz retornou reply vazio"' in empty_reply_block


def test_all_real_sdr_send_paths_run_output_guard_before_send():
    worker = _read("worker.py")
    bryan_worker_block = worker[
        worker.index("if tipo in SDR_OUTREACH_JOB_TYPES") :
        worker.index('return False, "desconhecido"')
    ]
    assert "_sdr_quality_hold_reason" in bryan_worker_block
    assert bryan_worker_block.index("_sdr_quality_hold_reason") < bryan_worker_block.index(
        "franz_output = iniciar_contato"
    )
    assert "evaluate_sdr_output" in bryan_worker_block
    assert bryan_worker_block.index("evaluate_sdr_output") < bryan_worker_block.index(
        "enqueue_outbound("
    )

    executor = _read("backend/whatsapp/response_executor.py")
    execute_block = executor[executor.index("def execute_response") :]
    assert "evaluate_guard(ctx)" in execute_block
    assert execute_block.index("if not allowed:") < execute_block.index("send_response(ctx)")

    cron = _read("backend/endpoints/cron_endpoints.py")
    assert cron.count("evaluate_sdr_output(") >= 3
    assert cron.index("evaluate_sdr_output") < cron.index("_send_sdr_direct(user_id, tel, fu_output.reply)")


def test_manual_sdr_send_persists_outbound_and_uses_guard():
    source = _read("backend/endpoints/leads_crud_sdr.py")
    block = source[source.index("async def enviar_mensagem_lead") :]

    assert "evaluate_sdr_output" in block
    assert block.index("evaluate_sdr_output") < block.index("send_text_parts(")
    assert block.index("if not ok:") < block.index(
        '_salvar_interacao(lead_id, franz_output.reply, "saida", tenant_id)'
    ) < block.index("UPDATE leads SET sdr_stage=:stage")
    assert "async def _enviar_whatsapp" not in block


def test_outbound_watchdog_is_not_forced_as_lead_responded():
    compat = _read("backend/agents/sdr_langgraph/compat.py")
    watchdog_block = compat[
        compat.index("def _verificar_watchdog_outbound") : compat.index("def responder_lead")
    ]

    assert "lead_responded: bool = False" in watchdog_block
    assert "lead_responded=lead_responded" in watchdog_block
    assert "lead_responded=True" not in watchdog_block


def test_listener_passes_current_database_stage_to_franz_graph():
    source = _read("backend/whatsapp_listener.py")
    process_block = source[source.index("def _processar_mensagem") :]
    call_block = process_block[
        process_block.index("franz_output = responder_lead(") :
        process_block.index("resposta = franz_output.reply")
    ]

    assert "sdr_stage=sdr_stage_atual or \"\"" in call_block


def test_sdr_sanitize_script_loads_env_before_database_import():
    source = _read("scripts/sdr_sanitize_cold_followups.py")

    assert source.index("load_dotenv(ROOT / \".env\")") < source.index(
        "from database import SessionLocal"
    )


def test_active_sdr_paths_do_not_create_bryan_runtime():
    active_files = {
        "worker.py": _read("worker.py"),
        "ecosystem.config.js": _read("ecosystem.config.js"),
        "backend/whatsapp_listener.py": _read("backend/whatsapp_listener.py"),
        "backend/endpoints/cron_endpoints.py": _read("backend/endpoints/cron_endpoints.py"),
        "backend/endpoints/leads_endpoints.py": _read("backend/endpoints/leads_endpoints.py"),
        "backend/endpoints/pipeline_orchestrator_service.py": _read(
            "backend/endpoints/pipeline_orchestrator_service.py"
        ),
    }

    for path, source in active_files.items():
        assert "from agents.bryan" not in source, path
        assert "import agents.bryan" not in source, path
        assert "bryan_output = " not in source, path
        assert "bryan_input = " not in source, path

    assert "fralib-bryan-worker" not in active_files["ecosystem.config.js"]
    assert 'tipo="bryan_outreach"' not in active_files["backend/endpoints/pipeline_orchestrator_service.py"]
    assert "WORKER_JOB_TYPES: 'franz_outreach'" in active_files["ecosystem.config.js"]
