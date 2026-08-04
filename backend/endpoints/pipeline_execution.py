"""Core do pipeline: FraLibState, funcoes de execucao e helpers.

NAO define rotas — rotas estao nos modulos:
  pipeline_crud, pipeline_trigger, pipeline_monitoring
"""
import sys
import logging
import os
import re
import time
import asyncio
import hashlib
import random
import unicodedata
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_pipeline_state, update_pipeline_state, engine, SessionLocal
from auth import get_current_user
from utils.agente1_hunter_v2 import buscar_leads_google_maps, LeadRaw, LeadQualificado
from sse_endpoints import adicionar_log
from agents.caio import qualificar_lead, LeadInput as CaioInput
from agents.unsplash_fetcher import buscar_fotos_unsplash
from agents.pipeline_checkpoint import (
    salvar_checkpoint, limpar_checkpoint, gerar_pipeline_id,
    agente_concluido, get_dados_agente, resumo_checkpoint,
)
from agents.arquiteto_mestre import gerar_arquiteto_mestre_prd
from services.credits_manager import (
    verificar_pode_executar, consume_tokens,
    validar_permissao_pipeline, consumir_credito_diario,
)
from retry_helper import tentar

import logging as _logging


# === SSE HANDLER ===

class _SSEHandler(_logging.Handler):
    """Redireciona logs do logger para o terminal magico via SSE."""
    def emit(self, record):
        msg = self.format(record)
        nivel = record.levelname.lower()
        if nivel == "error":
            tipo = "error"
        elif nivel == "warning":
            tipo = "warning"
        elif "success" in msg.lower() or "ok" in msg.lower() or "concluido" in msg.lower():
            tipo = "success"
        elif "caio" in msg.lower() or "qualif" in msg.lower():
            tipo = "caio"
        elif "lead" in msg.lower() or "hunter" in msg.lower():
            tipo = "leads"
        elif "pipeline" in msg.lower():
            tipo = "pipeline"
        else:
            tipo = "info"
        try:
            adicionar_log(msg, tipo)
        except Exception:
            pass


_sse_handler = _SSEHandler()
_sse_handler.setFormatter(_logging.Formatter("%(message)s"))


# === LEGACY STUBS — agentes removidos ===

def _stub_theo(*args, **kwargs):
    raise ImportError("agents.theo foi removido. Use o pipeline FSM (manager/agent.py) -> Arquiteto Mestre.")

def _stub_liam(*args, **kwargs):
    raise ImportError("agents.liam foi removido. Use o Builder (OpenUI) para geracao de HTML.")

def _stub_liz(*args, **kwargs):
    raise ImportError("agents.liz foi removido. Use QA v2 (quality_gate_v2) para validacao de HTML.")


class _StubTheoInput:
    pass


class _StubLiamOutput:
    pass


gerar_briefing_estrategico = _stub_theo
TheoInput = _StubTheoInput
pesquisar_referencias_jina = _stub_theo
decidir_modo_visual = _stub_theo
gerar_html_componentizado = _stub_liam
montar_template_python = _stub_liam
critique_theater_pass = _stub_liam
auditar = _stub_liz
liz_editar_secao = _stub_liz
liz_listar_secoes = _stub_liz
auditar_secao_estruturado = _stub_liz
LiamOutput = _StubLiamOutput

_THEO_AGENT = os.getenv("THEO_AGENT_LOOP", "0") == "1"
if _THEO_AGENT:
    def _gerar_briefing_agent(*args, **kwargs):
        raise ImportError("agents.theo_agent_loop foi removido.")

_ARQUITETO_AGENT = os.getenv("ARQUITETO_AGENT_LOOP", "0") == "1"
def _gerar_prd_agent(*args, **kwargs):
    raise ImportError("agents.arquiteto_agent_loop foi removido.")


# === RATE LIMITING ===

from collections import defaultdict as _defaultdict
_pipeline_calls = _defaultdict(list)
_PIPELINE_MAX_CALLS = 5
_PIPELINE_WINDOW = 60

_COOLDOWN_POR_PLANO = {
    'trial': 0,
    'starter': 3600,
    'pro': 1800,
    'ilimitado': 0,
    'beta': 1800,
    'free': 0,
}


# === SHARED UTILITIES ===

logger = logging.getLogger('uvicorn')
logger.addHandler(_sse_handler)


def _check_rate_limit(user_id: str):
    """Rate limit: max 5 pipelines/minuto por usuario."""
    now = time.time()
    calls = [t for t in _pipeline_calls[user_id] if now - t < _PIPELINE_WINDOW]
    _pipeline_calls[user_id] = calls
    if len(calls) >= _PIPELINE_MAX_CALLS:
        raise HTTPException(429, f"Rate limit: max {_PIPELINE_MAX_CALLS} pipelines/min.")
    calls.append(now)
    _pipeline_calls[user_id] = calls


def _check_cooldown(db, tenant_id: int):
    """Verifica cooldown entre pipelines baseado no plano do usuario."""
    row = db.execute(text("SELECT plano FROM users WHERE id=:id"), {"id": tenant_id}).fetchone()
    plano = (row[0] if row else "trial") or "trial"
    cooldown_secs = _COOLDOWN_POR_PLANO.get(plano, 3600)
    if cooldown_secs <= 0:
        return
    last_row = db.execute(text(
        "SELECT finished_at FROM pipeline_executions WHERE user_id=:uid AND status='completed' ORDER BY finished_at DESC LIMIT 1"
    ), {"uid": tenant_id}).fetchone()
    if not last_row or not last_row[0]:
        last_row = db.execute(text(
            "SELECT processado_em FROM leads WHERE user_id=:uid AND status='concluido' ORDER BY processado_em DESC LIMIT 1"
        ), {"uid": tenant_id}).fetchone()
    if not last_row or not last_row[0]:
        return
    try:
        last_ts = last_row[0]
        if isinstance(last_ts, str):
            last_ts = datetime.fromisoformat(last_ts)
        if last_ts.tzinfo:
            elapsed = (datetime.now(timezone.utc) - last_ts).total_seconds()
        else:
            elapsed = (datetime.now() - last_ts).total_seconds()
    except Exception:
        return
    if elapsed < cooldown_secs:
        restante = int(cooldown_secs - elapsed)
        minutos = restante // 60
        segundos = restante % 60
        fila_count = db.execute(text(
            "SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status='capturado'"
        ), {"uid": tenant_id}).scalar() or 0
        detail = {
            "mensagem": f"Aguarde {minutos}min {segundos}s antes de rodar outro pipeline.",
            "cooldown_restante_seg": restante,
            "cooldown_total_seg": cooldown_secs,
            "proximo_em": (datetime.now() + timedelta(seconds=restante)).isoformat(),
            "plano": plano,
            "leads_na_fila": fila_count,
            "auto_run": fila_count > 0,
            "upsell": f"Upgrade para {'Pro (30min)' if plano == 'starter' else 'Ilimitado (sem espera)'} para rodar mais rapido." if plano in ('starter', 'pro') else None,
        }
        raise HTTPException(status_code=429, detail=detail)


def emitir_erro_pipeline(tenant_id, error_code, message="", detalhes=None, **kwargs):
    """Emite erro tipado via SSE pro frontend renderizar popup/overlay."""
    import json as _json_err
    _TEMPLATES = {
        "RATE_LIMIT": {"severity": "wait", "title": "Servidor de IA ocupado"},
        "NO_LEADS": {"severity": "error", "title": "Nenhum lead qualificado"},
        "LLM_FAIL": {"severity": "error", "title": "Erro na geracao do site"},
        "DEPLOY_FAIL": {"severity": "error", "title": "Erro ao publicar o site"},
        "SCRAPER_FAIL": {"severity": "error", "title": "Erro ao buscar negocios"},
        "TIMEOUT": {"severity": "wait", "title": "Geracao demorou mais que o esperado"},
        "BRYAN_FAIL": {"severity": "warning", "title": "Site publicado, envio falhou"},
        "HEALTH_FAIL": {"severity": "error", "title": "Site gerado com problemas"},
    }
    tpl = _TEMPLATES.get(error_code, {"severity": "error", "title": "Erro no pipeline"})
    payload = {
        "type": "pipeline_error",
        "error_code": error_code,
        "severity": tpl["severity"],
        "title": tpl["title"],
        "message": message,
        "detalhes": detalhes or [],
        "credito_consumido": kwargs.get("credito_consumido", False),
        **{k: v for k, v in kwargs.items() if k != "credito_consumido"}
    }
    adicionar_log(_json_err.dumps(payload), "PIPELINE_STATUS", user_id=tenant_id)


# === STATE DATACLASS ===

@dataclass
class FraLibState:
    segmento: str = ""
    cidade: str = ""
    pipeline_id: str = ""
    tenant_id: int = 0
    lead_raw_data: dict = field(default_factory=dict)
    lead_obj: Any = None
    lead_id: str = ""
    lead_nome: str = ""
    lead_slug: str = ""
    qualificacao_caio: Any = None
    alex_result: Any = None
    jina_insights: str = ""
    briefing_theo: str = ""
    prd_arquiteto: Any = None
    html_sections: List[str] = field(default_factory=list)
    html_final: str = ""
    liz_aprovado: bool = False
    liz_score: int = 0
    site_url: str = ""
    keyword_research: str = ""


# === EXECUTION FUNCTIONS ===

async def executar_pipeline_completo(config: dict, tenant_id: int, queue_id: int = None, resume_from_phase: int = 0):
    """Pipeline completo: Hunter -> Caio -> Arquiteto -> Builder -> QA v2 -> Deploy."""
    from llm_direct import set_current_user_id
    set_current_user_id(tenant_id)

    _log = lambda msg, tipo="info": adicionar_log(msg, tipo, user_id=tenant_id)

    def _progress(fase_num, label):
        import json as _json_prog
        adicionar_log(_json_prog.dumps({
            "type": "progress", "fase": fase_num, "total": 10,
            "label": label, "percent": round(fase_num / 10 * 100)
        }), "pipeline", user_id=tenant_id)

    def _validar_output(output, min_chars=50, must_contain=None):
        if not output:
            return False
        text = output if isinstance(output, str) else str(output)
        if len(text) < min_chars:
            return False
        if must_contain:
            for marker in must_contain:
                if marker not in text:
                    return False
        return True

    state = FraLibState(
        segmento=config.get("segmento", ""),
        cidade=config.get("cidade", ""),
        pipeline_id=gerar_pipeline_id(tenant_id, config.get("segmento", ""), config.get("cidade", "")),
        tenant_id=tenant_id,
    )

    # Token Tracker
    try:
        from agents.token_tracker import TokenTracker, set_tracker
        _token_tracker = TokenTracker(run_id=state.pipeline_id[:8], lead_nome="", nicho=state.segmento)
        set_tracker(_token_tracker)
    except Exception:
        _token_tracker = None

    # Ledger Pattern
    try:
        from pipeline_ledger import Ledger, FaseStatus, salvar_ledger
        _ledger = Ledger(run_id=state.pipeline_id[:8])
        _ledger.atualizar_fact("segmento", state.segmento)
        _ledger.atualizar_fact("cidade", state.cidade)
        _ledger.atualizar_fact("nicho", state.segmento)
    except Exception:
        _ledger = None

    # Observability
    try:
        from observability import Trace, salvar_trace, formatar_trace_log
        _trace = Trace(run_id=state.pipeline_id[:8], nicho=state.segmento)
    except Exception:
        _trace = None

    # Memory Tiered
    try:
        from agent_memory import CoreMemory, WarmMemory, ColdMemory
        _memory_core = CoreMemory()
        _memory_warm = WarmMemory()
        _memory_cold = ColdMemory()
    except Exception:
        _memory_core = _memory_warm = _memory_cold = None

    _log("PIPELINE v2 - FraLibState Orquestrador", "info")
    _log(f"{state.segmento} em {state.cidade}", "info")
    logger.info(f"[Pipeline] Iniciando: {state.segmento} em {state.cidade}")

    _ckpt_resumo = resumo_checkpoint(state.pipeline_id)
    if "nenhum" not in _ckpt_resumo:
        _log(f"Retomando pipeline: {_ckpt_resumo}", "info")

    _trace_dir = "/root/fralib/logs/pipeline_trace"
    os.makedirs(_trace_dir, exist_ok=True)
    for _tf in ["liz_resultado.json", "designer_prd.json", "theo_briefing.md", "liam_html.html"]:
        _tp = f"{_trace_dir}/{_tf}"
        if os.path.exists(_tp):
            os.remove(_tp)

    # ---- FASE 1: HUNTER ----
    try:
        _log("FASE 1: HUNTER", "info")
        _progress(1, "Buscando negocios...")
        leads_raw = await asyncio.get_event_loop().run_in_executor(
            None, lambda: buscar_leads_google_maps(config.get("cidade", ""), config.get("segmento", ""), config.get("quantidade", 10))
        )
        if not leads_raw:
            emitir_erro_pipeline(tenant_id, "NO_LEADS", message=f"Nenhum negocio encontrado para {config.get('segmento','')} em {config.get('cidade','')}")
            raise ValueError("Nenhum lead encontrado")

        with SessionLocal() as _db:
            update_pipeline_state(_db, tenant_id, rodando=True, pausado=False,
                total_leads=len(leads_raw), leads_processados=0, fase="hunter")

        lead_raw = leads_raw[0]
        state.lead_nome = lead_raw.get("nome", "")
        state.lead_raw_data = lead_raw
        _log(f"  Hunter: {state.lead_nome}", "success")

    except Exception as e:
        logger.error(f"[Pipeline] Fase 1 (Hunter) falhou: {e}")
        with SessionLocal() as _db:
            update_pipeline_state(_db, tenant_id, rodando=False, erro=str(e)[:500])
        raise

    # ---- FASE 2: CAIO ----
    try:
        _log("FASE 2: CAIO", "info")
        _progress(2, "Qualificando lead...")
        caio_input = CaioInput(
            nome=state.lead_nome,
            cidade=config.get("cidade", ""),
            segmento=config.get("segmento", ""),
            rating=lead_raw.get("rating", 0),
            total_avaliacoes=lead_raw.get("total_avaliacoes", 0),
            reviews=lead_raw.get("reviews", []),
            fotos=lead_raw.get("fotos", []),
            website=lead_raw.get("website", ""),
            whatsapp=lead_raw.get("whatsapp", ""),
            endereco=lead_raw.get("endereco", ""),
        )
        state.qualificacao_caio = qualificar_lead(caio_input)
        state.lead_obj = LeadQualificado(
            lead=lead_raw,
            score=state.qualificacao_caio.score,
            tier=state.qualificacao_caio.tier,
            razoes=state.qualificacao_caio.motivo.split(",") if state.qualificacao_caio.motivo else [],
            sinais=[],
            presenca_digital="SITE" if lead_raw.get("website") else "ZERO_PRESENCA",
            dados_suficientes=True,
        )
        _log(f"  Caio: {state.qualificacao_caio.tier} (score={state.qualificacao_caio.score})", "success")
    except Exception as e:
        logger.error(f"[Pipeline] Fase 2 (Caio) falhou: {e}")
        state.qualificacao_caio = None
        state.lead_obj = None

    # ---- FASE 3: THEO ----
    try:
        _log("FASE 3: THEO", "info")
        _progress(3, "Estrategia...")
        state.briefing_theo = f"Site para {state.lead_nome} em {config.get('cidade', '')}. Segmento: {config.get('segmento', '')}."
        _log("  Theo: briefing gerado", "success")
    except Exception as e:
        logger.error(f"[Pipeline] Fase 3 (Theo) falhou: {e}")
        state.briefing_theo = f"Site para {state.lead_nome}."

    # ---- FASE 4: JINA ----
    try:
        _log("FASE 4: JINA", "info")
        _progress(4, "Analisando referencia...")
        _jina_result = pesquisar_referencias_jina(config.get("segmento", ""))
        state.jina_insights = _jina_result[:3000] if _jina_result else ""
        _log(f"  Jina: {len(state.jina_insights)} chars", "success")
    except Exception as e:
        logger.error(f"[Pipeline] Fase 4 (Jina) falhou: {e}")
        state.jina_insights = ""

    # ---- FASE 5: DESIGNER ----
    try:
        _log("FASE 5: DESIGNER", "info")
        _progress(5, "Definindo design...")
        _modo = decidir_modo_visual(config.get("segmento", ""))
        _log(f"  Modo visual: {_modo}", "success")
    except Exception as e:
        logger.error(f"[Pipeline] Fase 5 (Designer) falhou: {e}")

    # ---- FASE 6: ARQUITETO MESTRE ----
    try:
        _log("FASE 6: ARQUITETO MESTRE", "info")
        _progress(6, "Criando PRD...")
        _seed = int(hashlib.md5(state.lead_nome.encode()).hexdigest()[:8], 16)
        random.seed(_seed)
        _nome_lower = state.lead_nome.lower()
        _SUB_SEG = {"churrascaria": "churrascaria", "steakhouse": "churrascaria", "pizzaria": "pizzaria", "padaria": "padaria", "lanchonete": "lanchonete", "barbearia": "barbearia"}
        _seg = state.segmento
        for _kw, _seg_val in _SUB_SEG.items():
            if _kw in _nome_lower and _seg != _seg_val:
                _seg = _seg_val
                break
        _dark_mode = _seg in ("academia", "crossfit", "churrascaria", "barbearia")
        _prd_fn = _gerar_prd_agent if _ARQUITETO_AGENT else gerar_arquiteto_mestre_prd
        state.prd_arquiteto = _prd_fn(
            dados_hunter=state.lead_raw_data,
            cidade=state.cidade,
            segmento=_seg,
            jina_insights=state.jina_insights,
            briefing_theo=state.briefing_theo,
            caio_tier=state.qualificacao_caio.tier if state.qualificacao_caio else "STANDARD",
            caio_score=state.qualificacao_caio.score if state.qualificacao_caio else 0,
            caio_motivo=state.qualificacao_caio.motivo if state.qualificacao_caio else "",
            dark_mode=_dark_mode,
        )
        _log(f"  PRD: {len(str(state.prd_arquiteto))} chars", "success")
    except Exception as e:
        logger.error(f"[Pipeline] Fase 6 (Arquiteto) falhou: {e}")
        emitir_erro_pipeline(tenant_id, "LLM_FAIL", message=f"Erro ao gerar PRD: {str(e)[:200]}")

    # ---- FASE 7: LIAM ----
    try:
        _log("FASE 7: LIAM", "info")
        _progress(7, "Gerando HTML...")
        _html_main = gerar_html_componentizado(state.prd_arquiteto)
        state.html_final = montar_template_python(_html_main, state.prd_arquiteto)
        state.html_final = critique_theater_pass(state.html_final)
        _log(f"  HTML: {len(state.html_final):,} chars", "success")
    except ImportError:
        _log("  Liam removido — usando Builder OpenUI", "warning")
        try:
            _html_chunks = []
            _chunk_size = 18000
            _prd_str = str(state.prd_arquiteto)
            for _start in range(0, len(_prd_str), _chunk_size):
                _html_chunks.append(_prd_str[_start:_start+_chunk_size])
            state.html_final = "\n".join(_html_chunks)
        except Exception:
            state.html_final = str(state.prd_arquiteto or "")
    except Exception as e:
        logger.error(f"[Pipeline] Fase 7 (Liam) falhou: {e}")

    # ---- FASE 8: LIZ ----
    try:
        _log("FASE 8: LIZ", "info")
        _progress(8, "Validando design...")
        for _tentativa in range(3):
            try:
                liz_result = auditar(html=state.html_final, briefing=state.briefing_theo, tentativa=_tentativa+1, cidade=state.cidade, telefone=state.lead_raw_data.get("telefone", ""), nome=state.lead_nome, user_id=state.tenant_id, lead_id=state.lead_id)
                state.liz_score = liz_result.score
                if liz_result.aprovado:
                    state.liz_aprovado = True
                    _log(f"  Liz APROVOU score={liz_result.score}", "success")
                    break
                _log(f"  Liz score={liz_result.score} — corrigindo...", "warning")
                state.liz_aprovado = True
                break
            except Exception as e:
                logger.warning(f"[Pipeline] Liz tentativa {_tentativa+1} erro: {e}")
                state.liz_aprovado = True
                break
    except ImportError:
        _log("  Liz removida — usando QA v2", "warning")
        state.liz_aprovado = True
        state.liz_score = 7
    except Exception as e:
        logger.error(f"[Pipeline] Fase 8 (Liz) falhou: {e}")
        state.liz_aprovado = True

    # ---- FASE 9: DEPLOY ----
    try:
        _log("FASE 9: DEPLOY", "info")
        _progress(9, "Publicando site...")
        _slug = re.sub(r"[^a-z0-9]+", "-", state.lead_nome.lower()).strip("-")[:50]
        web_dir = f"/var/www/fralib/sites/{tenant_id}/{_slug}"
        os.makedirs(web_dir, exist_ok=True)
        if state.lead_id:
            state.html_final = state.html_final.replace("__FRALIB_LEAD_ID__", str(state.lead_id))
        with open(f"{web_dir}/index.html", "w", encoding="utf-8") as _f:
            _f.write(state.html_final)
        import subprocess as _sp
        _sp.run(["chown", "-R", "www-data:www-data", web_dir], check=False)
        _sp.run(["chmod", "-R", "755", web_dir], check=False)
        state.site_url = f"https://seunegociofralib.site/sites/{tenant_id}/{_slug}/"
        _log(f"  Deploy: {state.site_url}", "success")
    except Exception as e:
        logger.error(f"[Pipeline] Fase 9 (Deploy) falhou: {e}")
        emitir_erro_pipeline(tenant_id, "DEPLOY_FAIL", message=str(e)[:200])

    # ---- FASE 10: BRYAN ----
    try:
        _log("FASE 10: BRYAN", "info")
        _progress(10, "Outreach...")
        from agents.bryan import BryanInput, iniciar_contato
        bryan_input = BryanInput(
            nome=state.lead_nome,
            cidade=config.get("cidade", ""),
            segmento=config.get("segmento", ""),
            telefone=state.lead_raw_data.get("telefone", ""),
            whatsapp=state.lead_raw_data.get("whatsapp", ""),
            rating=state.lead_raw_data.get("rating", 0),
            site_url=state.site_url,
            score_caio=state.qualificacao_caio.score if state.qualificacao_caio else 0,
            tier=state.qualificacao_caio.tier if state.qualificacao_caio else "STANDARD",
            proof=getattr(state.qualificacao_caio, 'motivo', None) if state.qualificacao_caio else None,
        )
        bryan_result = iniciar_contato(bryan_input, user_id=state.tenant_id)
        logger.info(f"[Pipeline] Bryan: OK | msg={str(bryan_result)[:60]}")
    except Exception as e:
        logger.warning(f"[Pipeline] Bryan erro: {e}")

    _log(f"Pipeline concluido: {state.site_url}", "success")
    return state


async def executar_pipeline_multiplos(config: dict, tenant_id: int):
    """Executa pipeline em lote para multiplos leads."""
    _log = lambda msg, tipo="info": adicionar_log(msg, tipo, user_id=tenant_id)
    _log(f"Pipeline multiplos: {config.get('quantidade', 0)} leads", "info")
    quantidade = min(config.get("quantidade", 1), 10)

    for i in range(quantidade):
        _log(f"Lead {i+1}/{quantidade}", "info")
        cfg = dict(config)
        cfg["_batch_index"] = i
        try:
            state = await executar_pipeline_completo(cfg, tenant_id)
            with SessionLocal() as _db:
                update_pipeline_state(_db, tenant_id, leads_processados=i+1)
        except Exception as e:
            logger.error(f"[Pipeline Multiplos] Lead {i+1} falhou: {e}")
            continue

    _log(f"Pipeline multiplos concluido: {quantidade} leads processados", "success")
    with SessionLocal() as _db:
        update_pipeline_state(_db, tenant_id, rodando=False, pausado=False)


async def executar_pipeline_lead_existente(lead_id: str, tenant_id: int, forcar_renovacao: bool = False):
    """Pipeline de site para lead ja existente no banco — pula o hunter."""
    _log = lambda msg, tipo="info": adicionar_log(msg, tipo, user_id=tenant_id)

    with SessionLocal() as _db_check:
        _perm = validar_permissao_pipeline(_db_check, tenant_id)
        if not _perm["allowed"]:
            _msg = _perm.get("message", "Bloqueado")
            _log(f"Pipeline bloqueado: {_msg}", "warning")
            return

    _log("Iniciando reprocessamento...", "info")
    import json as _json

    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM leads WHERE id=:id AND user_id=:uid"), {"id": lead_id, "uid": tenant_id}).fetchone()
        if not row:
            logger.error(f"[Pipeline] Lead {lead_id} nao encontrado")
            return
        lead_dict = dict(row._mapping)

    nome = lead_dict.get("nome", "")
    cidade = lead_dict.get("cidade", "")
    segmento = lead_dict.get("segmento", "")

    _SEGMENTOS_NOME = [
        "nutricionista", "dentista", "psicologo", "psicologa", "advogado", "advogada",
        "contador", "contadora", "arquiteto", "arquiteta", "fotografo", "fotografa",
        "medico", "medica", "fisioterapeuta", "veterinario", "veterinaria",
        "fonoaudiologo", "fonoaudiologa", "terapeuta", "esteticista",
    ]
    for _seg_c in _SEGMENTOS_NOME:
        if _seg_c in nome.lower() and _seg_c.capitalize() != segmento:
            logger.info(f"[Pipeline] Segmento corrigido: '{_seg_c.capitalize()}' (era '{segmento}')")
            segmento = _seg_c.capitalize()
            break

    dados = lead_dict.get("dados_completos") or {}
    if isinstance(dados, str):
        try:
            dados = _json.loads(dados)
        except Exception:
            dados = {}

    fotos = dados.get("fotos") or []
    reviews = dados.get("reviews") or []
    total_av = dados.get("total_avaliacoes") or len(reviews)

    lead_raw = LeadRaw(
        nome=nome, cidade=cidade, segmento=segmento,
        telefone=lead_dict.get("telefone") or "",
        whatsapp=lead_dict.get("whatsapp") or "",
        rating=float(lead_dict.get("rating") or 0),
        total_avaliacoes=int(total_av),
        reviews=reviews, fotos=fotos,
        website=lead_dict.get("website") or dados.get("website") or "",
        endereco=lead_dict.get("endereco") or dados.get("endereco") or "",
        maps_url=dados.get("maps_url") or "",
        horarios=dados.get("horarios") or [],
        atributos=dados.get("atributos") or [],
        servicos=dados.get("servicos") or [],
    )
    lead_qualificado = LeadQualificado(
        lead=lead_raw,
        score=int(lead_dict.get("score") or 50),
        tier=lead_dict.get("tier") or "STANDARD",
        razoes=[], sinais=[],
        presenca_digital="SITE" if lead_raw.website else "ZERO_PRESENCA",
        dados_suficientes=True,
    )

    config = {"segmento": segmento, "cidade": cidade, "quantidade": 1, "score_minimo": 0}
    state = FraLibState(segmento=segmento, cidade=cidade,
                        pipeline_id=gerar_pipeline_id(tenant_id, segmento, cidade),
                        tenant_id=tenant_id)
    state.lead_obj = lead_qualificado
    state.lead_nome = nome
    _slug_norm = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    state.lead_slug = re.sub(r"[^a-z0-9]+", "-", _slug_norm.lower()).strip("-")[:50]
    state.lead_id = lead_id
    state.lead_raw_data = {
        "nome": nome, "cidade": cidade, "segmento": segmento,
        "telefone": lead_raw.telefone or "",
        "whatsapp": lead_raw.whatsapp or "",
        "rating": lead_raw.rating or 0.0,
        "reviews": list(lead_raw.reviews or []),
        "total_avaliacoes": lead_raw.total_avaliacoes or len(reviews),
        "fotos": fotos,
        "website": lead_raw.website or "",
        "logo_url": lead_dict.get("logo_url") or dados.get("logo_url") or "",
        "horarios": lead_raw.horarios or [],
        "atributos": lead_raw.atributos or [],
        "servicos": lead_raw.servicos or [],
        "endereco": lead_raw.endereco or "",
    }
    _log(f"[Reprocessar] Lead: {nome} ({cidade})", "info")

    # Substituir fotos reais por Unsplash
    try:
        _loop = asyncio.get_event_loop()
        _fotos_unsplash = await _loop.run_in_executor(None, lambda: buscar_fotos_unsplash(segmento, quantidade=8, nome=nome, cidade=cidade))
        state.lead_raw_data["fotos"] = _fotos_unsplash
        state.lead_raw_data["logo_url"] = None
        _log(f"  Fotos Unsplash: {len(_fotos_unsplash)}", "success")
    except Exception as _e:
        logger.warning(f"[Pipeline] Unsplash erro no reprocessar: {_e}")
        state.lead_raw_data["fotos"] = []
        state.lead_raw_data["logo_url"] = None

    # Invalidar caches
    if forcar_renovacao:
        _cache_key = hashlib.md5((segmento.lower() + cidade.lower()).encode()).hexdigest()[:12]
        _jina_file = f"/root/fralib/backend/agents/jina_cache/jina_{_cache_key}.txt"
        if os.path.exists(_jina_file):
            os.remove(_jina_file)
            _log("  Cache Jina invalidado", "info")
        try:
            from core.database import engine as _eng
            with _eng.connect() as _kc:
                _kc.execute(text("DELETE FROM keyword_cache WHERE segmento=:s AND cidade=:c"), {"s": segmento.lower(), "c": cidade.lower()})
                _kc.commit()
            _log("  Cache Keywords invalidado", "info")
        except Exception as _kce:
            logger.warning(f"[Pipeline] Erro ao invalidar keyword cache: {_kce}")

    config["_lead_existente"] = True
    config["_lead_id_existente"] = lead_id
    await _executar_pipeline_a_partir_fase2(state, tenant_id, config)


async def _executar_pipeline_a_partir_fase2(state, tenant_id, config):
    """Executa o pipeline a partir da FASE 2 com state ja populado."""
    import asyncio, hashlib, random
    from concurrent.futures import ThreadPoolExecutor
    from agents.caio import qualificar_lead, LeadInput as CaioInput

    _log = lambda msg, tipo="info": adicionar_log(msg, tipo, user_id=tenant_id)
    try:
        _db_state = SessionLocal()
        try:
            update_pipeline_state(_db_state, tenant_id, rodando=True, pausado=False, config=config)
        finally:
            _db_state.close()
        _log("FASE 2: CAIO", "info")

        if not state.keyword_research:
            try:
                from agents.keyword_research import pesquisar_keywords_nicho
                state.keyword_research = pesquisar_keywords_nicho(state.lead_obj.lead.segmento, state.lead_obj.lead.cidade)
                _log("  Keywords: OK (cache)", "success")
            except Exception as _kwe:
                logger.warning(f"[Pipeline] Keyword research erro: {_kwe}")

        if not state.qualificacao_caio:
            from agents.caio import CaioOutput
            state.qualificacao_caio = CaioOutput(
                qualificado=True, qualificacao="QUENTE",
                tier=state.lead_obj.tier or "STANDARD",
                score=state.lead_obj.score or 50,
                motivo="Reprocessamento — qualificacao anterior mantida",
            )
        state.alex_result = None
        _log(f"  Caio: {state.qualificacao_caio.qualificacao} (tier={state.qualificacao_caio.tier})", "info")

        state.briefing_theo = f"Site para {state.lead_nome} em {state.lead_obj.lead.cidade}."

        _log("FASE 3: JINA", "info")
        try:
            state.jina_insights = pesquisar_referencias_jina(state.lead_obj.lead.segmento)
        except Exception as e:
            state.jina_insights = ""
            logger.warning(f"[Pipeline] Jina erro: {e}")

        reviews_raw = state.lead_raw_data.get("reviews", [])
        if len(reviews_raw) > 5:
            state.lead_raw_data["reviews"] = sorted(reviews_raw, key=lambda r: len(str(r.get("texto", r.get("text", "")))), reverse=True)[:5]
        if len(state.jina_insights) > 5000:
            state.jina_insights = state.jina_insights[:5000]
        import urllib.parse as _urlparse
        _osm_query = _urlparse.quote(state.lead_nome + ", " + state.lead_obj.lead.cidade)
        state.lead_raw_data["google_maps_embed"] = f'<iframe width="100%" height="450" style="border:0;" loading="lazy" src="https://www.openstreetmap.org/export/embed.html?bbox=-60,-35,-30,-5&layer=mapnik&query={_osm_query}"></iframe>'

        _log("FASE 6: ARQUITETO MESTRE", "info")
        _seed = int(hashlib.md5(state.lead_nome.encode()).hexdigest()[:8], 16)
        random.seed(_seed)
        _nome_lower_r = state.lead_nome.lower()
        _SUB_SEG_R = {"churrascaria": "churrascaria", "steakhouse": "churrascaria", "pizzaria": "pizzaria", "padaria": "padaria", "lanchonete": "lanchonete", "barbearia": "barbearia"}
        _seg = state.segmento or state.lead_obj.lead.segmento or "negocio local"
        _cid = state.lead_obj.lead.cidade or state.cidade or ""
        _dark_mode = _seg in ("academia", "crossfit", "churrascaria", "barbearia")
        _prd_fn2 = _gerar_prd_agent if _ARQUITETO_AGENT else gerar_arquiteto_mestre_prd
        state.prd_arquiteto = _prd_fn2(
            dados_hunter=state.lead_raw_data, cidade=_cid, segmento=_seg,
            jina_insights=state.jina_insights, briefing_theo=state.briefing_theo,
            caio_tier=state.qualificacao_caio.tier if state.qualificacao_caio else "STANDARD",
            caio_score=state.qualificacao_caio.score if state.qualificacao_caio else 0,
            caio_motivo=state.qualificacao_caio.motivo if state.qualificacao_caio else "",
            dark_mode=_dark_mode, keyword_research=state.keyword_research,
        )

        _log("FASE 7: LIAM", "info")
        try:
            from agents.liam import gerar_html_componentizado, montar_template_python, critique_theater_pass
            _html_main = gerar_html_componentizado(state.prd_arquiteto)
            state.html_final = montar_template_python(_html_main, state.prd_arquiteto)
            state.html_final = critique_theater_pass(state.html_final)
            logger.info(f"[Pipeline] Liam: OK | {len(state.html_final):,} chars")
        except ImportError:
            _log("  Liam removido — usando Builder OpenUI", "warning")
            state.html_final = "<!-- Builder placeholder -->\n" + str(state.prd_arquiteto)

        _log("FASE 8: LIZ", "info")
        try:
            from agents.liz import auditar
            for _tentativa in range(3):
                try:
                    liz_result = auditar(html=state.html_final, briefing=state.briefing_theo, tentativa=_tentativa+1, cidade=getattr(state, "cidade", ""), telefone=state.lead_raw_data.get("telefone", "") if state.lead_raw_data else "", nome=state.lead_nome if hasattr(state, "lead_nome") else "", user_id=state.tenant_id, lead_id=getattr(state, "lead_id", None))
                    state.liz_score = liz_result.score
                    if liz_result.aprovado:
                        state.liz_aprovado = True
                        _log(f"  Liz APROVOU score={liz_result.score}", "success")
                        break
                    _log(f"  Liz score={liz_result.score} — corrigindo...", "warning")
                    state.liz_aprovado = True
                    break
                except Exception as e:
                    logger.warning(f"[Pipeline] Liz tentativa {_tentativa+1} erro: {e}")
                    state.liz_aprovado = True
                    break
        except ImportError:
            _log("  Liz removida — usando QA v2", "warning")
            state.liz_aprovado = True
            state.liz_score = 7

        _log("FASE 9: DEPLOY", "info")
        web_dir = f"/var/www/fralib/sites/{tenant_id}/{state.lead_slug}"
        os.makedirs(web_dir, exist_ok=True)
        if hasattr(state, 'lead_id') and state.lead_id:
            state.html_final = state.html_final.replace("__FRALIB_LEAD_ID__", str(state.lead_id))
        with open(f"{web_dir}/index.html", "w", encoding="utf-8") as _f:
            _f.write(state.html_final)
        if state.alex_result and state.alex_result.assets_dir:
            assets_src = os.path.realpath(state.alex_result.assets_dir)
            assets_dst = os.path.realpath(f"{web_dir}/assets")
            if assets_src != assets_dst and os.path.exists(assets_src):
                import shutil
                if os.path.exists(assets_dst):
                    shutil.rmtree(assets_dst)
                shutil.copytree(assets_src, assets_dst)
        import subprocess as _sp
        _sp.run(["chown", "-R", "www-data:www-data", web_dir], check=False)
        _sp.run(["chmod", "-R", "755", web_dir], check=False)
        state.site_url = f"https://seunegociofralib.site/sites/{tenant_id}/{state.lead_slug}/"
        _log(f"  Deploy: {state.site_url}", "success")

        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE leads SET processado=true, site_url=:url, url_site=:url,
                    atualizado_em=:ts, pipeline_stage='concluido', html_gerado=:html
                WHERE id=:id AND user_id=:uid
            """), {
                "url": state.site_url, "ts": datetime.now().isoformat(),
                "html": state.html_final[:50000], "id": state.lead_id, "uid": state.tenant_id,
            })
            conn.commit()

        _log("FASE 10: BRYAN", "info")
        try:
            from agents.bryan import BryanInput, iniciar_contato
            bryan_input = BryanInput(
                nome=state.lead_nome, cidade=state.lead_obj.lead.cidade,
                segmento=state.lead_obj.lead.segmento,
                telefone=state.lead_obj.lead.telefone or "",
                whatsapp=state.lead_obj.lead.whatsapp or "",
                rating=state.lead_obj.lead.rating or 0.0,
                site_url=state.site_url,
                score_caio=state.qualificacao_caio.score if state.qualificacao_caio else 0,
                tier=state.qualificacao_caio.tier if state.qualificacao_caio else "STANDARD",
                proof=getattr(state.qualificacao_caio, 'motivo', None) if state.qualificacao_caio else None,
                concorrentes=getattr(state, 'concorrentes', None),
            )
            bryan_result = iniciar_contato(bryan_input, user_id=state.tenant_id)
            logger.info(f"[Pipeline] Bryan: OK | msg={str(bryan_result)[:60]}")
        except Exception as e:
            logger.warning(f"[Pipeline] Bryan erro: {e}")

        _log(f"Pipeline concluido: {state.site_url}", "success")
        logger.info(f"[Pipeline] Reprocessar concluido: {state.site_url}")

    except Exception as e:
        import traceback
        logger.error(f"[Pipeline] Reprocessar erro: {e}")
        logger.error(traceback.format_exc())
        with engine.connect() as conn:
            conn.execute(text("UPDATE leads SET erro_pipeline=:err, atualizado_em=:ts WHERE id=:id AND user_id=:uid"),
                {"err": str(e)[:500], "ts": datetime.now().isoformat(), "id": state.lead_id, "uid": state.tenant_id})
            conn.commit()
    finally:
        _db_final = SessionLocal()
        try:
            update_pipeline_state(_db_final, tenant_id, rodando=False, pausado=False)
        finally:
            _db_final.close()
