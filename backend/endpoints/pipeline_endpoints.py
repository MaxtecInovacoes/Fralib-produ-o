from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import logging, sys, os, uuid, re, time, asyncio, hashlib, random, unicodedata
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

sys.path.append('/root/fralib/backend')

from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db, get_pipeline_state, update_pipeline_state, engine, SessionLocal
from auth import get_current_user
from utils.agente1_hunter_v2 import buscar_leads_google_maps
from sse_endpoints import adicionar_log
from whatsapp_listener import is_tenant_connected

import logging as _logging

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

# Logs do pipeline chegam ao terminal via adicionar_log() chamado explicitamente


from agents.caio import qualificar_lead, LeadInput as CaioInput
# from agents.alex import processar_imagens, AlexInput  # DESATIVADO
from agents.unsplash_fetcher import buscar_fotos_unsplash
from agents.theo import gerar_briefing_estrategico, TheoInput, pesquisar_referencias_jina, decidir_modo_visual
# Theo Managed Agent (feature flag: THEO_AGENT_LOOP=1)
_THEO_AGENT = os.getenv("THEO_AGENT_LOOP", "0") == "1"
if _THEO_AGENT:
    from agents.theo_agent_loop import gerar_briefing_estrategico_agent as _gerar_briefing_agent
from agents.pipeline_checkpoint import salvar_checkpoint, limpar_checkpoint, gerar_pipeline_id, agente_concluido, get_dados_agente, resumo_checkpoint
from agents.liam import gerar_html_componentizado, montar_template_python, critique_theater_pass
from agents.arquiteto_mestre import gerar_arquiteto_mestre_prd
# Managed Agent (feature flag: ARQUITETO_AGENT_LOOP=1)
_ARQUITETO_AGENT = os.getenv("ARQUITETO_AGENT_LOOP", "0") == "1"
if _ARQUITETO_AGENT:
    from agents.arquiteto_agent_loop import gerar_arquiteto_mestre_prd_agent as _gerar_prd_agent
from agents.liz import auditar, editar_secao as liz_editar_secao, listar_secoes as liz_listar_secoes, auditar_secao_estruturado
from agents.bryan import iniciar_contato, BryanInput
from agents.liam_models import LiamOutput
from services.credits_manager import verificar_pode_executar, consume_tokens, validar_permissao_pipeline, consumir_credito_diario
from pipeline_queue_manager import pipeline_queue  # DEPRECATED: mantido apenas para /fila endpoint
from retry_helper import tentar

from collections import defaultdict as _defaultdict
_pipeline_calls = _defaultdict(list)
_PIPELINE_MAX_CALLS = 5
_PIPELINE_WINDOW = 60

# Cooldown por plano (segundos entre pipelines)
_COOLDOWN_POR_PLANO = {
    'trial': 0,        # trial: bloqueado por créditos (1 total), não precisa cooldown
    'starter': 3600,   # 1 hora
    'pro': 1800,       # 30 minutos
    'ilimitado': 0,    # sem cooldown
    'beta': 1800,      # beta = pro
    'free': 0,
}

def _check_rate_limit(user_id: str):
    now = time.time()
    calls = [t for t in _pipeline_calls[user_id] if now - t < _PIPELINE_WINDOW]
    _pipeline_calls[user_id] = calls
    if len(calls) >= _PIPELINE_MAX_CALLS:
        raise HTTPException(429, f"Rate limit: max {_PIPELINE_MAX_CALLS} pipelines/min.")
    calls.append(now)
    _pipeline_calls[user_id] = calls


def _check_cooldown(db, tenant_id: int):
    """Verifica cooldown entre pipelines baseado no plano do usuário. Usa pipeline_executions (com fallback)."""
    row = db.execute(text("SELECT plano FROM users WHERE id=:id"), {"id": tenant_id}).fetchone()
    plano = (row[0] if row else "trial") or "trial"
    cooldown_secs = _COOLDOWN_POR_PLANO.get(plano, 3600)
    if cooldown_secs <= 0:
        return
    # Buscar último pipeline concluído — pipeline_executions (robusto) com fallback pra leads
    last_row = db.execute(text(
        "SELECT finished_at FROM pipeline_executions WHERE user_id=:uid AND status='completed' ORDER BY finished_at DESC LIMIT 1"
    ), {"uid": tenant_id}).fetchone()
    if not last_row or not last_row[0]:
        # Fallback: leads.processado_em (transição)
        last_row = db.execute(text(
            "SELECT processado_em FROM leads WHERE user_id=:uid AND status='concluido' ORDER BY processado_em DESC LIMIT 1"
        ), {"uid": tenant_id}).fetchone()
    if not last_row or not last_row[0]:
        return
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    try:
        last_ts = last_row[0]
        if isinstance(last_ts, str):
            last_ts = _dt.fromisoformat(last_ts)
        if last_ts.tzinfo:
            elapsed = (_dt.now(_tz.utc) - last_ts).total_seconds()
        else:
            elapsed = (_dt.now() - last_ts).total_seconds()
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
            "proximo_em": (_dt.now() + _td(seconds=restante)).isoformat(),
            "plano": plano,
            "leads_na_fila": fila_count,
            "auto_run": fila_count > 0,
            "upsell": f"Upgrade para {'Pro (30min)' if plano == 'starter' else 'Ilimitado (sem espera)'} para rodar mais rápido." if plano in ('starter', 'pro') else None,
        }
        raise HTTPException(status_code=429, detail=detail)

router = APIRouter(prefix='/api/pipeline', tags=['pipeline'])
logger = logging.getLogger('uvicorn')
logger.addHandler(_sse_handler)


def emitir_erro_pipeline(tenant_id, error_code, message="", detalhes=None, **kwargs):
    """Emite erro tipado via SSE pro frontend renderizar popup/overlay."""
    import json as _json_err
    _TEMPLATES = {
        "RATE_LIMIT": {"severity": "wait", "title": "Servidor de IA ocupado"},
        "NO_LEADS": {"severity": "error", "title": "Nenhum lead qualificado"},
        "LLM_FAIL": {"severity": "error", "title": "Erro na geração do site"},
        "DEPLOY_FAIL": {"severity": "error", "title": "Erro ao publicar o site"},
        "SCRAPER_FAIL": {"severity": "error", "title": "Erro ao buscar negócios"},
        "TIMEOUT": {"severity": "wait", "title": "Geração demorou mais que o esperado"},
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

@router.get('/cooldown-status')
async def cooldown_status(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    """Status completo de cooldown, créditos e fila para dashboard."""
    tenant_id = usuario.get("tenant_id", usuario["id"])
    from services.credits_manager import validar_permissao_pipeline, get_user_tokens, LIMITES_DIARIOS, COOLDOWNS

    perm = validar_permissao_pipeline(db, tenant_id)
    info = get_user_tokens(db, tenant_id)
    plano = info.get("plano", "trial")
    cooldown_secs = COOLDOWNS.get(plano, 3600)
    limite = LIMITES_DIARIOS.get(plano, 1)

    pode_rodar = perm["allowed"]

    # Cooldown info
    cooldown_info = {"ativo": False, "total_seg": cooldown_secs, "restante_seg": 0, "percentual_completo": 100}
    if not pode_rodar and perm.get("reason") == "cooldown":
        cooldown_info = {
            "ativo": True,
            "total_seg": cooldown_secs,
            "restante_seg": perm.get("cooldown_restante_seg", 0),
            "proximo_em": perm.get("proximo_em"),
            "percentual_completo": round((1 - perm.get("cooldown_restante_seg", 0) / max(cooldown_secs, 1)) * 100, 1),
        }

    # Créditos info
    creditos_info = {
        "limite_diario": limite,
        "usados_hoje": info.get("sites_hoje", 0),
        "restantes_hoje": info.get("creditos_restantes_hoje", limite),
        "reset_at": None,
    }
    if not pode_rodar and perm.get("reason") == "creditos_esgotados":
        from services.credits_manager import _proximo_reset_iso
        creditos_info["reset_at"] = _proximo_reset_iso()

    # Fila de leads
    fila_row = db.execute(text("""
        SELECT COUNT(*) as total,
               (SELECT nome FROM leads WHERE user_id=:uid AND status='capturado' ORDER BY score DESC LIMIT 1),
               (SELECT cidade FROM leads WHERE user_id=:uid AND status='capturado' ORDER BY score DESC LIMIT 1)
        FROM leads WHERE user_id=:uid AND status='capturado'
    """), {"uid": tenant_id}).fetchone()
    fila = {
        "leads_aguardando": fila_row[0] if fila_row else 0,
        "proximo_lead_nome": fila_row[1] if fila_row else None,
        "proximo_lead_cidade": fila_row[2] if fila_row else None,
        "auto_run_ativo": (fila_row[0] or 0) > 0,
    }

    # Uso
    uso = {"sites_hoje": info.get("sites_hoje", 0), "sites_total": info.get("sites_used", 0)}

    # Upsell
    _UPSELL_MSGS = {
        "trial": {"plano_sugerido": "starter", "mensagem_curta": "Starter: 6 sites/dia", "mensagem_longa": "Com o Starter você gera 6 sites por dia com cooldown de 1h."},
        "starter": {"plano_sugerido": "pro", "mensagem_curta": "Pro: 16 sites/dia + cooldown 30min", "mensagem_longa": "No Pro são 16 sites/dia e cooldown de 30 minutos."},
        "pro": {"plano_sugerido": "ilimitado", "mensagem_curta": "Ilimitado: sem limite + sem espera", "mensagem_longa": "No Ilimitado não tem cooldown nem limite diário."},
    }
    mostrar_upsell = not pode_rodar
    upsell_data = _UPSELL_MSGS.get(plano)
    upsell = None
    if mostrar_upsell and upsell_data:
        upsell = {"mostrar": True, "plano_atual": plano, **upsell_data, "url": f"/planos?from=cooldown&current={plano}"}

    # Bloqueio
    bloqueio = None
    if not pode_rodar:
        bloqueio = {"motivo": perm.get("reason", "unknown"), "mensagem": perm.get("message", "Bloqueado")}

    return {
        "pode_rodar": pode_rodar,
        "plano": plano,
        "cooldown": cooldown_info,
        "creditos": creditos_info,
        "fila": fila,
        "uso": uso,
        "upsell": upsell,
        "bloqueio": bloqueio,
    }


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

async def executar_pipeline_completo(config: dict, tenant_id: int, queue_id: int = None, resume_from_phase: int = 0):
    # Setar user_id no contexto do LLM pra rastrear consumo por usuario
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
        """Valida que output não está truncado/quebrado antes de salvar checkpoint."""
        if not output:
            return False
        text = output if isinstance(output, str) else str(output)
        if len(text) < min_chars:
            return False
        # Detectar resposta truncada (termina no meio de frase sem pontuação final)
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
    # PRD #4: Token Tracker — rastreia custo LLM por run
    try:
        from agents.token_tracker import TokenTracker, set_tracker
        _token_tracker = TokenTracker(
            run_id=state.pipeline_id[:8],
            lead_nome="",  # preenchido após hunter
            nicho=state.segmento,
        )
        set_tracker(_token_tracker)
    except Exception:
        _token_tracker = None

    # PRD #6: Ledger Pattern — documento vivo do pipeline
    try:
        from pipeline_ledger import Ledger, FaseStatus, salvar_ledger
        _ledger = Ledger(run_id=state.pipeline_id[:8])
        _ledger.atualizar_fact("segmento", state.segmento)
        _ledger.atualizar_fact("cidade", state.cidade)
        _ledger.atualizar_fact("nicho", state.segmento)
    except Exception:
        _ledger = None

    # PRD #10: Observability — trace completo do pipeline
    try:
        from observability import Trace, salvar_trace, formatar_trace_log
        _trace = Trace(run_id=state.pipeline_id[:8], nicho=state.segmento)
    except Exception:
        _trace = None

    # PRD #11: Memory Tiered — agentes aprendem entre gerações
    try:
        from agent_memory import CoreMemory, WarmMemory, ColdMemory
        _memory_core = CoreMemory()
        _memory_warm = WarmMemory()
        _memory_cold = ColdMemory()
    except Exception:
        _memory_core = None
        _memory_warm = None
        _memory_cold = None

    _log("PIPELINE v2 - FraLibState Orquestrador", "info")
    _log(f"{state.segmento} em {state.cidade}", "info")
    logger.info(f"[Pipeline] Iniciando: {state.segmento} em {state.cidade}")
    # Checkpoint: verificar se existe progresso anterior
    _ckpt_resumo = resumo_checkpoint(state.pipeline_id)
    if "nenhum" not in _ckpt_resumo:
        _log(f"♻️ Retomando pipeline: {_ckpt_resumo}", "info")
        logger.info(f"[Pipeline] Retomando de checkpoint: {_ckpt_resumo}")
    # Limpar traces residuais de execucoes anteriores
    import os as _os
    _trace_dir = "/root/fralib/logs/pipeline_trace"
    _os.makedirs(_trace_dir, exist_ok=True)
    for _tf in ["liz_resultado.json", "designer_prd.json", "theo_briefing.md", "liam_html.html"]:
        _tp = f"{_trace_dir}/{_tf}"
        if _os.path.exists(_tp):
            _os.remove(_tp)
    print("[Pipeline] Traces residuais limpos")
    try:
        # ─── REPROCESSAMENTO: pular Hunter + Caio se lead já existe ───
        _lead_id_existente = config.get("_lead_id_existente")
        if _lead_id_existente:
            _log("REPROCESSAMENTO — pulando Hunter + Caio", "info")
            from utils.agente1_hunter_v2 import LeadRaw, LeadQualificado
            from agents.caio import CaioOutput
            import json as _json_reproc
            with engine.connect() as _conn_reproc:
                _row_reproc = _conn_reproc.execute(
                    text("SELECT * FROM leads WHERE id=:id AND user_id=:uid"),
                    {"id": _lead_id_existente, "uid": tenant_id},
                ).fetchone()
            if not _row_reproc:
                raise Exception(f"Lead {_lead_id_existente} nao encontrado")
            _ld = dict(_row_reproc._mapping)
            _dados_r = _ld.get("dados_completos") or {}
            if isinstance(_dados_r, str):
                try: _dados_r = _json_reproc.loads(_dados_r)
                except: _dados_r = {}
            _reviews_r = _dados_r.get("reviews") or []
            _lead_raw_r = LeadRaw(
                nome=_ld["nome"], cidade=_ld["cidade"], segmento=_ld.get("segmento") or state.segmento,
                telefone=_ld.get("telefone") or "", whatsapp=_ld.get("whatsapp") or "",
                rating=float(_ld.get("rating") or 0), total_avaliacoes=int(_ld.get("total_avaliacoes") or len(_reviews_r)),
                reviews=_reviews_r, fotos=_dados_r.get("fotos") or [],
                website=_ld.get("website") or _dados_r.get("website") or "",
                endereco=_ld.get("endereco") or _dados_r.get("endereco") or "",
                maps_url=_dados_r.get("maps_url") or "",
                horarios=_dados_r.get("horarios") or [], atributos=_dados_r.get("atributos") or [],
                servicos=_dados_r.get("servicos") or [],
            )
            state.lead_obj = LeadQualificado(
                lead=_lead_raw_r, score=int(_ld.get("score") or 50),
                tier=_ld.get("tier") or "STANDARD", razoes=[], sinais=[],
                presenca_digital="SITE" if _lead_raw_r.website else "ZERO_PRESENCA",
                dados_suficientes=True,
            )
            state.lead_nome = _ld["nome"]
            _slug_norm = unicodedata.normalize("NFKD", state.lead_nome).encode("ascii", "ignore").decode("ascii")
            state.lead_slug = re.sub(r"[^a-z0-9]+", "-", _slug_norm.lower()).strip("-")[:50]
            state.lead_id = _lead_id_existente
            # Refinar segmento pelo nome
            _nome_lower = state.lead_nome.lower()
            _SUB_SEGMENTOS = {"churrascaria": "churrascaria", "steakhouse": "churrascaria", "pizzaria": "pizzaria", "padaria": "padaria", "lanchonete": "lanchonete", "barbearia": "barbearia", "salão": "salao_beleza", "salao": "salao_beleza", "pet": "pet_shop"}
            for _kw, _seg_ref in _SUB_SEGMENTOS.items():
                if _kw in _nome_lower and state.segmento != _seg_ref:
                    _log(f"  Segmento refinado: {state.segmento} → {_seg_ref}", "info")
                    state.segmento = _seg_ref
                    break
            state.lead_raw_data = {
                "nome": state.lead_nome, "cidade": _ld["cidade"], "segmento": state.segmento,
                "telefone": _lead_raw_r.telefone, "whatsapp": _lead_raw_r.whatsapp,
                "rating": _lead_raw_r.rating, "reviews": _reviews_r,
                "total_avaliacoes": _lead_raw_r.total_avaliacoes, "fotos": _lead_raw_r.fotos,
                "website": _lead_raw_r.website, "logo_url": _dados_r.get("logo_url"),
                "horarios": _lead_raw_r.horarios, "atributos": _lead_raw_r.atributos,
                "servicos": _lead_raw_r.servicos, "endereco": _lead_raw_r.endereco,
            }
            # Caio: pular — usar qualificação anterior
            state.qualificacao_caio = CaioOutput(
                qualificado=True, qualificacao="QUENTE",
                tier=state.lead_obj.tier or "STANDARD",
                score=state.lead_obj.score or 50,
                motivo="Reprocessamento — qualificação anterior mantida",
            )
            state.alex_result = None
            _log(f"  Lead: {state.lead_nome} | Caio: PULADO (tier={state.qualificacao_caio.tier})", "success")
            # Unsplash — renovar fotos
            try:
                _fotos_u = buscar_fotos_unsplash(state.segmento, quantidade=8, nome=state.lead_nome, cidade=_ld["cidade"])
                state.lead_raw_data["fotos"] = _fotos_u
                state.lead_raw_data["logo_url"] = None
                _log(f"  Fotos Unsplash: {len(_fotos_u)}", "success")
            except Exception as _eu:
                logger.warning(f"[Pipeline] Unsplash erro: {_eu}")
            # Forcar renovacao de caches se pedido
            if config.get("_forcar_renovacao"):
                import hashlib as _hl_r
                _cache_key_r = _hl_r.md5((state.segmento.lower() + _ld["cidade"].lower()).encode()).hexdigest()[:12]
                _jina_file_r = f"/root/fralib/backend/agents/jina_cache/jina_{_cache_key_r}.txt"
                if _os.path.exists(_jina_file_r):
                    _os.remove(_jina_file_r)
                    _log("  Cache Jina invalidado", "info")
            # Reprocessamento: usar _executar_pipeline_a_partir_fase2 (mesmos agentes)
            if not getattr(state, 'keyword_research', ''):
                try:
                    from agents.keyword_research import pesquisar_keywords_nicho
                    state.keyword_research = pesquisar_keywords_nicho(state.segmento, state.lead_obj.lead.cidade)
                except: state.keyword_research = ""
            await _executar_pipeline_a_partir_fase2(state, tenant_id, config)
            return {"sucesso": True, "lead": state.lead_nome}
        _progress(1, "Buscando leads...")
        _log("FASE 1: HUNTER + KEYWORD RESEARCH (paralelo)", "info")
        if _ledger: _ledger.registrar_inicio_fase(1, "hunter_kw")
        _span = _trace.iniciar_span("hunter_kw", agente="hunter") if _trace else None
        # Carregar leads já existentes no banco para evitar duplicatas
        # Dedup por nome+cidade apenas (ignora segmento — mesmo negocio pode ter segmento diferente)
        with engine.connect() as _conn_dedup:
            _res_existentes = _conn_dedup.execute(text("""
                SELECT lower(trim(nome)) FROM leads
                WHERE lower(cidade) = lower(:cidade)
                  AND user_id = :user_id
            """), {"cidade": state.cidade, "user_id": tenant_id})
            _leads_existentes = {row[0] for row in _res_existentes.fetchall()}
        if _leads_existentes:
            _log(f"  Dedup: {len(_leads_existentes)} leads ja existem no banco", "info")

        # Keyword research em paralelo com o Hunter (cache 30 dias)
        from agents.keyword_research import pesquisar_keywords_nicho
        from concurrent.futures import ThreadPoolExecutor as _KWExec
        _kw_result = [None]
        def _run_kw():
            try:
                _kw_result[0] = pesquisar_keywords_nicho(state.segmento, state.cidade)
                _log(f"  Keywords: OK", "success")
            except Exception as _e:
                logger.warning(f"[Pipeline] Keyword research erro: {_e}")
        _kw_executor = _KWExec(max_workers=1)
        _kw_future = _kw_executor.submit(_run_kw)

        leads = await buscar_leads_google_maps(
            cidade=state.cidade,
            segmento=state.segmento,
            limite=config.get("quantidade", 10),
            leads_existentes=_leads_existentes,
        )
        _kw_future.result(timeout=30)  # aguarda keyword research terminar
        _kw_executor.shutdown(wait=False)
        state.keyword_research = _kw_result[0] or ""
        if not leads:
            raise Exception("Nenhum lead novo encontrado para '" + state.segmento + "' em '" + state.cidade + "'. Os leads dessa regiao ja estao sendo processados ou nao ha negocios com dados suficientes. Tente outro nicho ou cidade.")

        # Salvar leads capturados no banco com status 'capturado'
        # Limitar salvamento pela quantidade solicitada (trial=1, starter=10, etc)
        import json as _json_hunter
        _agora_hunter = datetime.now().isoformat()
        _salvos_hunter = 0
        _max_salvar = config.get("quantidade", 10)
        with engine.connect() as _conn_hunter:
            for _lq in leads:
                if _salvos_hunter >= _max_salvar:
                    break
                _l = _lq.lead
                _nome_norm_h = _l.nome.lower().strip() if _l.nome else ''
                if not _nome_norm_h:
                    continue
                # Checar se já existe (qualquer status)
                _dup_h = _conn_hunter.execute(text("""
                    SELECT id FROM leads
                    WHERE lower(trim(nome)) = lower(trim(:nome))
                      AND lower(cidade) = lower(:cidade)
                      AND user_id = :user_id
                    LIMIT 1
                """), {"nome": _l.nome, "cidade": _l.cidade or state.cidade, "user_id": tenant_id}).fetchone()
                if _dup_h:
                    continue
                _id_h = str(uuid.uuid4())
                _dados_h = {
                    "horarios": getattr(_l, "horarios", []) or [],
                    "maps_url": getattr(_l, "maps_url", None) or "",
                    "atributos": getattr(_l, "atributos", []) or [],
                    "servicos": getattr(_l, "servicos", []) or [],
                    "faixa_preco": getattr(_l, "faixa_preco", None) or "",
                    "website": getattr(_l, "website", "") or "",
                    "total_avaliacoes": getattr(_l, "total_avaliacoes", 0) or 0,
                    "google_maps_embed": getattr(_l, "google_maps_embed", "") or "",
                    "fotos": getattr(_l, "fotos", []) or [],
                    "reviews": [
                        {"autor": r.get("autor",""), "rating": r.get("rating",5), "texto": r.get("texto","")}
                        for r in (getattr(_l, "reviews", []) or [])
                    ],
                }
                try:
                    _conn_hunter.execute(text("""
                        INSERT INTO leads (id,nome,cidade,segmento,telefone,whatsapp,rating,score,tier,status,user_id,criado_em,atualizado_em,processado,tentativas,dados_completos)
                        VALUES (:id,:nome,:cidade,:segmento,:telefone,:whatsapp,:rating,:score,:tier,:status,:user_id,:criado_em,:atualizado_em,:processado,:tentativas,:dados_completos)
                        ON CONFLICT DO NOTHING
                    """), {
                        "id": _id_h, "nome": _l.nome,
                        "cidade": _l.cidade or state.cidade,
                        "segmento": _l.segmento or state.segmento,
                        "telefone": getattr(_l, "telefone", "") or "",
                        "whatsapp": getattr(_l, "whatsapp", "") or "",
                        "rating": getattr(_l, "rating", 0.0) or 0.0,
                        "score": _lq.score, "tier": _lq.tier,
                        "status": "capturado", "user_id": tenant_id,
                        "criado_em": _agora_hunter, "atualizado_em": _agora_hunter,
                        "processado": False, "tentativas": 0,
                        "dados_completos": _json_hunter.dumps(_dados_h),
                    })
                    _salvos_hunter += 1
                except Exception as _eh:
                    print(f"[Hunter] Erro ao salvar lead pendente {_l.nome}: {_eh}")
            _conn_hunter.commit()
        if _salvos_hunter:
            print(f"[Hunter] {_salvos_hunter} leads salvos como pendente no banco")

        state.lead_obj = leads[0]
        state.lead_nome = state.lead_obj.lead.nome
        # Refinar segmento pelo nome do lead (ex: "restaurante" → "churrascaria")
        _nome_lower = state.lead_nome.lower()
        _SUB_SEGMENTOS = {"churrascaria": "churrascaria", "steakhouse": "churrascaria", "pizzaria": "pizzaria", "padaria": "padaria", "lanchonete": "lanchonete", "barbearia": "barbearia", "salão": "salao_beleza", "salao": "salao_beleza", "pet": "pet_shop"}
        for _kw, _seg_ref in _SUB_SEGMENTOS.items():
            if _kw in _nome_lower and state.segmento != _seg_ref:
                _log(f"  Segmento refinado: {state.segmento} → {_seg_ref} (detectado '{_kw}' no nome)", "info")
                state.segmento = _seg_ref
                break
        # GUARD: se checkpoint tem dados de outro lead, limpar pra evitar contaminação
        _ckpt_lead_check = get_dados_agente(state.pipeline_id, "arquiteto")
        if _ckpt_lead_check and _ckpt_lead_check.get("prd_json"):
            _ckpt_bname = _ckpt_lead_check["prd_json"].get("business_name", "")
            if _ckpt_bname and _ckpt_bname.lower().strip() != state.lead_nome.lower().strip():
                print(f"[Pipeline] ⚠️ Checkpoint de outro lead ({_ckpt_bname}) — limpando pra {state.lead_nome}")
                limpar_checkpoint(state.pipeline_id)
        _slug_norm = unicodedata.normalize("NFKD", state.lead_nome).encode("ascii", "ignore").decode("ascii")
        state.lead_slug = re.sub(r"[^a-z0-9]+", "-", _slug_norm.lower()).strip("-")[:50]
        _reviews_raw = list(state.lead_obj.lead.reviews or [])
        state.lead_raw_data = {
            "nome": state.lead_nome,
            "cidade": state.lead_obj.lead.cidade,
            "segmento": state.lead_obj.lead.segmento,
            "telefone": state.lead_obj.lead.telefone or "",
            "whatsapp": state.lead_obj.lead.whatsapp or "",
            "rating": state.lead_obj.lead.rating or 0.0,
            "reviews": _reviews_raw,
            "total_avaliacoes": state.lead_obj.lead.total_avaliacoes or len(_reviews_raw),
            "fotos": state.lead_obj.lead.fotos or [],
            "website": state.lead_obj.lead.website or "",
            "logo_url": getattr(state.lead_obj.lead, "logo_url", None) or "",
            "endereco": getattr(state.lead_obj.lead, "endereco", "") or getattr(state.lead_obj.lead, "address", "") or "",
            "google_maps_embed": getattr(state.lead_obj.lead, "google_maps_embed", "") or "",
            "lat": getattr(state.lead_obj, "latitude", None) or getattr(state.lead_obj.lead, "latitude", None),
            "lng": getattr(state.lead_obj, "longitude", None) or getattr(state.lead_obj.lead, "longitude", None),
            "horarios": getattr(state.lead_obj, "horarios", None) or getattr(state.lead_obj.lead, "horarios", None),
            "atributos": getattr(state.lead_obj, "atributos", None) or getattr(state.lead_obj.lead, "atributos", None),
            "servicos": getattr(state.lead_obj, "servicos", None) or getattr(state.lead_obj.lead, "servicos", None),
            "faixa_preco": getattr(state.lead_obj, "faixa_preco", None) or getattr(state.lead_obj.lead, "faixa_preco", None),
            "place_id": getattr(state.lead_obj.lead, "place_id", "") or "",
        }
        _log(f"  Lead: {state.lead_nome}", "success")
        state.lead_id = str(uuid.uuid4())
        agora = datetime.now().isoformat()
        with engine.connect() as conn:
            # Checar duplicata por nome+cidade+user_id antes de inserir
            _dup = conn.execute(text("""
                SELECT id FROM leads
                WHERE lower(trim(nome)) = lower(trim(:nome))
                  AND lower(cidade) = lower(:cidade)
                  AND user_id = :user_id
                LIMIT 1
            """), {"nome": state.lead_nome, "cidade": state.lead_obj.lead.cidade, "user_id": tenant_id}).fetchone()
            if _dup:
                # Se lead existe com status pendente, foi salvo pelo Hunter agora — usar ele
                _status_dup = conn.execute(text("SELECT status FROM leads WHERE id = :id"), {"id": str(_dup[0])}).fetchone()
                if _status_dup and _status_dup[0] in ("pendente", "capturado"):
                    # Lead pendente salvo pelo Hunter — reutilizar diretamente
                    print(f"[Pipeline] Lead pendente reutilizado: {state.lead_nome} (id: {_dup[0]})")
                    _log(f"  Lead: {state.lead_nome}", "success")
                    state.lead_id = str(_dup[0])
                    # Atualizar reviews/dados se o lead antigo não tinha
                    _fresh_reviews = [
                        {"autor": r.get("autor",""), "rating": r.get("rating",5), "texto": r.get("texto","")}
                        for r in (getattr(state.lead_obj.lead, "reviews", []) or [])
                    ]
                    if _fresh_reviews:
                        import json as _json_reutil
                        conn.execute(text("""
                            UPDATE leads SET dados_completos = jsonb_set(
                                COALESCE(CAST(dados_completos AS jsonb), CAST('{}' AS jsonb)),
                                '{reviews}', CAST(:reviews AS jsonb)
                            ) WHERE id = :id AND (CAST(dados_completos AS jsonb)->'reviews' = CAST('[]' AS jsonb) OR CAST(dados_completos AS jsonb)->'reviews' IS NULL)
                        """), {"id": state.lead_id, "reviews": _json_reutil.dumps(_fresh_reviews)})
                        conn.commit()
                else:
                    _log(f"  Lead duplicado ignorado: {state.lead_nome}", "info")
                    print(f"[Pipeline] Lead duplicado ignorado: {state.lead_nome} (id existente: {_dup[0]})")
                    # Tentar proximo lead da lista em vez de abortar
                    _idx_dup = leads.index(state.lead_obj) if state.lead_obj in leads else 0
                    _proximo_valido = None
                    for _lq_dup in leads[_idx_dup + 1:]:
                        _dup2 = conn.execute(text("""
                            SELECT id FROM leads
                            WHERE lower(trim(nome)) = lower(trim(:nome))
                              AND lower(cidade) = lower(:cidade)
                              AND user_id = :user_id
                              AND status IN ('concluido', 'processando')
                            LIMIT 1
                        """), {"nome": _lq_dup.lead.nome, "cidade": _lq_dup.lead.cidade, "user_id": tenant_id}).fetchone()
                        if not _dup2:
                            _proximo_valido = _lq_dup
                            break
                    if not _proximo_valido:
                        _log("Todos os leads ja foram processados anteriormente", "warning")
                        print("[Pipeline] Todos os leads sao duplicatas — nada a processar")
                        return
                    # Redirecionar para o proximo lead valido
                    state.lead_obj = _proximo_valido
                    state.lead_nome = _proximo_valido.lead.nome
                    _slug_norm2 = unicodedata.normalize("NFKD", state.lead_nome).encode("ascii", "ignore").decode("ascii")
                    state.lead_slug = re.sub(r"[^a-z0-9]+", "-", _slug_norm2.lower()).strip("-")[:50]
                    _reviews_raw2 = list(_proximo_valido.lead.reviews or [])
                    state.lead_raw_data = {
                        "nome": state.lead_nome, "cidade": _proximo_valido.lead.cidade,
                        "segmento": _proximo_valido.lead.segmento,
                        "telefone": _proximo_valido.lead.telefone or "",
                        "whatsapp": _proximo_valido.lead.whatsapp or "",
                        "rating": _proximo_valido.lead.rating or 0.0,
                        "reviews": _reviews_raw2,
                        "total_avaliacoes": getattr(_proximo_valido.lead, "total_avaliacoes", None) or len(_reviews_raw2),
                        "fotos": _proximo_valido.lead.fotos or [],
                        "website": _proximo_valido.lead.website or "",
                        "logo_url": getattr(_proximo_valido.lead, "logo_url", None) or "",
                        "endereco": getattr(_proximo_valido.lead, "endereco", "") or "",
                        "google_maps_embed": getattr(_proximo_valido.lead, "google_maps_embed", "") or "",
                        "lat": getattr(_proximo_valido.lead, "latitude", None),
                        "lng": getattr(_proximo_valido.lead, "longitude", None),
                        "horarios": getattr(_proximo_valido.lead, "horarios", None),
                        "atributos": getattr(_proximo_valido.lead, "atributos", None),
                        "servicos": getattr(_proximo_valido.lead, "servicos", None),
                        "faixa_preco": getattr(_proximo_valido.lead, "faixa_preco", None),
                    }
                    # Buscar ID existente no banco para este lead (salvo pelo Hunter)
                    _id_existente = conn.execute(text("""
                        SELECT id FROM leads
                        WHERE lower(trim(nome)) = lower(trim(:nome))
                          AND lower(cidade) = lower(:cidade)
                          AND user_id = :user_id
                        LIMIT 1
                    """), {"nome": state.lead_nome, "cidade": _proximo_valido.lead.cidade, "user_id": tenant_id}).fetchone()
                    state.lead_id = str(_id_existente[0]) if _id_existente else str(uuid.uuid4())
                    _log(f"  Redirecionando para: {state.lead_nome}", "info")
                    print(f"[Pipeline] Redirecionando para proximo lead: {state.lead_nome} (id={state.lead_id})")
            import json as _json
            _dados_extras = {
                "horarios": getattr(state.lead_obj.lead, "horarios", []) or [],
                "maps_url": getattr(state.lead_obj.lead, "maps_url", None) or "",
                "atributos": getattr(state.lead_obj.lead, "atributos", []) or [],
                "servicos": getattr(state.lead_obj.lead, "servicos", []) or [],
                "faixa_preco": getattr(state.lead_obj.lead, "faixa_preco", None) or "",
                "website": state.lead_raw_data.get("website", ""),
                "total_avaliacoes": state.lead_raw_data.get("total_avaliacoes", 0),
            }
            conn.execute(text("""
                INSERT INTO leads (id,nome,cidade,segmento,telefone,whatsapp,rating,score,tier,status,user_id,criado_em,atualizado_em,processado,tentativas,dados_completos)
                VALUES (:id,:nome,:cidade,:segmento,:telefone,:whatsapp,:rating,:score,:tier,:status,:user_id,:criado_em,:atualizado_em,:processado,:tentativas,:dados_completos)
                ON CONFLICT DO NOTHING
            """), {
                "id": state.lead_id, "nome": state.lead_nome,
                "cidade": state.lead_obj.lead.cidade, "segmento": state.lead_obj.lead.segmento,
                "telefone": state.lead_obj.lead.telefone or "", "whatsapp": state.lead_obj.lead.whatsapp or "",
                "rating": state.lead_obj.lead.rating or 0.0, "score": state.lead_obj.score,
                "tier": state.lead_obj.tier, "status": "capturado", "user_id": tenant_id,
                "dados_completos": _json.dumps(_dados_extras),
                "criado_em": agora, "atualizado_em": agora, "processado": False, "tentativas": 0
            })
            conn.commit()
        _progress(2, "Qualificando lead...")
        _log("FASE 2: CAIO + ALEX (paralelo)", "info")
        if _ledger:
            _ledger.registrar_fim_fase(1, FaseStatus.CONCLUIDA, resultado=f"lead={state.lead_nome}")
            _ledger.atualizar_fact("lead_nome", state.lead_nome)
            _ledger.atualizar_fact("lead_telefone", state.lead_obj.lead.telefone or "")
            _ledger.atualizar_fact("lead_endereco", getattr(state.lead_obj.lead, "endereco", ""))
            _ledger.atualizar_fact("tem_reviews", bool(state.lead_obj.lead.reviews))
            _ledger.atualizar_fact("qtd_reviews", state.lead_obj.lead.total_avaliacoes or 0)
            _ledger.atualizar_fact("tem_site", bool(state.lead_obj.lead.website))
            _ledger.registrar_inicio_fase(2, "caio")
        if _span: _span.finalizar("success")
        if _trace:
            _trace.lead_nome = state.lead_nome
            _span = _trace.iniciar_span("caio", agente="caio", modelo="haiku")

        # Check rápido: lead já contatado? (evita gastar tokens gerando site pra lead repetido)
        try:
            with engine.connect() as _conn_dup:
                _ja_contatado = _conn_dup.execute(text(
                    "SELECT id FROM leads WHERE lower(trim(nome))=lower(trim(:nome)) AND user_id=:uid AND status IN ('contatado','concluido')"
                ), {"nome": state.lead_nome, "uid": tenant_id}).fetchone()
            if _ja_contatado:
                _log(f"  {state.lead_nome} já contatado anteriormente — pulando", "warning")
                # Simular rejeição do Caio pra entrar no loop de fallback
                from agents.caio import CaioOutput as _CaioOut
                state.qualificacao_caio = _CaioOut(qualificado=False, tier="REJEITADO", score=0, razoes=["Lead já contatado anteriormente"])
                # Pular direto pro bloco de fallback (não chamar Caio)
                if _span: _span.finalizar("skipped")
                # Jump handled below by the rejection fallback block
            else:
                raise StopIteration  # flag: não é duplicado, continuar normalmente
        except StopIteration:
            pass
        except Exception as _dup_err:
            print(f"[Pipeline] Check duplicado falhou (ignorando): {_dup_err}")

        if not (state.qualificacao_caio and state.qualificacao_caio.tier == "REJEITADO"):
            caio_input = CaioInput(
                nome=state.lead_nome, cidade=state.lead_obj.lead.cidade,
                segmento=state.segmento, telefone=state.lead_obj.lead.telefone or "",
                whatsapp=state.lead_obj.lead.whatsapp or "", rating=state.lead_obj.lead.rating or 0.0,
                reviews_count=state.lead_obj.lead.total_avaliacoes or len(state.lead_obj.lead.reviews or []) or 0,
                fotos=state.lead_obj.lead.fotos or [], website=state.lead_obj.lead.website,
                reprocessamento=True
            )
            # Alex DESATIVADO — fotos via Unsplash, paleta via paleta_nicho
            def _run_caio():
                r = qualificar_lead(caio_input)
                logger.info(f"[Pipeline] Caio: {r.qualificacao}")
                return r
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as ex:
                state.qualificacao_caio = await loop.run_in_executor(ex, _run_caio)
            state.alex_result = None
        if state.qualificacao_caio and (not state.qualificacao_caio.qualificado or state.qualificacao_caio.tier == "REJEITADO"):
            _idx_atual = next((i for i, l in enumerate(leads) if l is state.lead_obj), -1)
            _encontrou_aprovado = False
            _motivos_rejeicao = [{"nome": state.lead_nome, "motivo": (state.qualificacao_caio.razoes[0] if state.qualificacao_caio.razoes else "Rejeitado pelo Caio")}]
            for _try_idx in range(_idx_atual + 1, min(_idx_atual + 16, len(leads))):
                _proximo = leads[_try_idx]
                _log(f"  {state.lead_nome} rejeitado. Tentando: {_proximo.lead.nome}", "info")
                with engine.connect() as _conn_rej:
                    _conn_rej.execute(text("UPDATE leads SET status='descartado', atualizado_em=:ts WHERE id=:id AND user_id=:uid"), {"ts": datetime.now().isoformat(), "id": state.lead_id, "uid": state.tenant_id})
                    _conn_rej.commit()
                state.lead_obj = _proximo
                state.lead_nome = _proximo.lead.nome
                _slug_norm_caio = unicodedata.normalize("NFKD", state.lead_nome).encode("ascii", "ignore").decode("ascii")
                state.lead_slug = re.sub(r"[^a-z0-9]+", "-", _slug_norm_caio.lower()).strip("-")[:50]
                state.lead_id = None
                _rvs = list(_proximo.lead.reviews or [])
                state.lead_raw_data = {"nome": _proximo.lead.nome, "cidade": _proximo.lead.cidade, "segmento": _proximo.lead.segmento, "telefone": _proximo.lead.telefone or "", "whatsapp": _proximo.lead.whatsapp or "", "rating": _proximo.lead.rating or 0.0, "reviews": _rvs, "total_avaliacoes": getattr(_proximo.lead, "total_avaliacoes", None) or getattr(_proximo.lead, "reviews_count", None) or len(_rvs), "fotos": _proximo.lead.fotos or [], "website": _proximo.lead.website or "", "logo_url": getattr(_proximo.lead, "logo_url", None) or "", "endereco": getattr(_proximo.lead, "endereco", "") or getattr(_proximo.lead, "address", "") or "", "google_maps_embed": getattr(_proximo.lead, "google_maps_embed", "") or "", "lat": getattr(_proximo.lead, "latitude", None), "lng": getattr(_proximo.lead, "longitude", None), "horarios": getattr(_proximo.lead, "horarios", None), "atributos": getattr(_proximo.lead, "atributos", None), "servicos": getattr(_proximo.lead, "servicos", None), "faixa_preco": getattr(_proximo.lead, "faixa_preco", None)}
                from agents.caio import qualificar_lead as _qualificar_caio2, LeadInput as _CaioInput2
                _caio_input2 = _CaioInput2(
                    nome=_proximo.lead.nome, cidade=_proximo.lead.cidade,
                    segmento=state.segmento, telefone=_proximo.lead.telefone or "",
                    whatsapp=_proximo.lead.whatsapp or "", rating=_proximo.lead.rating or 0.0,
                    reviews_count=getattr(_proximo.lead, "total_avaliacoes", None) or len(getattr(_proximo.lead, "reviews", None) or []) or 0,
                    fotos=_proximo.lead.fotos or [], website=_proximo.lead.website,
                    reprocessamento=True
                )
                state.qualificacao_caio = await asyncio.get_event_loop().run_in_executor(None, _qualificar_caio2, _caio_input2)
                if state.qualificacao_caio and state.qualificacao_caio.qualificado and state.qualificacao_caio.tier != "REJEITADO":
                    _encontrou_aprovado = True
                    _log(f"  Lead aprovado: {state.lead_nome} ({state.qualificacao_caio.tier})", "success")
                    break
                else:
                    _motivo = (state.qualificacao_caio.razoes[0] if state.qualificacao_caio and state.qualificacao_caio.razoes else "Rejeitado")
                    _motivos_rejeicao.append({"nome": _proximo.lead.nome, "motivo": _motivo})
            if not _encontrou_aprovado:
                _detalhes = [f"{m['nome']} — {m['motivo']}" for m in _motivos_rejeicao[:8]]
                emitir_erro_pipeline(tenant_id, "NO_LEADS",
                    message=f"Todos os negócios encontrados para {state.segmento} em {state.cidade} foram descartados.",
                    detalhes=_detalhes)
                raise Exception("Nenhum lead qualificado encontrado para '" + state.segmento + "' em '" + state.cidade + "'. " + str(len(_motivos_rejeicao)) + " leads avaliados e rejeitados.")
            if _encontrou_aprovado:
                state.lead_id = str(uuid.uuid4())
                _agora_sub = datetime.now().isoformat()
                try:
                    import json as _json_sub
                    _dados_extras_sub = {
                        "horarios": getattr(_proximo.lead, "horarios", []) or [],
                        "maps_url": getattr(_proximo.lead, "maps_url", None) or "",
                        "atributos": getattr(_proximo.lead, "atributos", []) or [],
                        "servicos": getattr(_proximo.lead, "servicos", []) or [],
                        "faixa_preco": getattr(_proximo.lead, "faixa_preco", None) or "",
                        "website": state.lead_raw_data.get("website", ""),
                        "total_avaliacoes": state.lead_raw_data.get("total_avaliacoes", 0),
                    }
                    with engine.connect() as _conn_sub:
                        _dup_sub = _conn_sub.execute(text("SELECT id FROM leads WHERE lower(trim(nome)) = lower(trim(:nome)) AND lower(cidade) = lower(:cidade) AND user_id = :user_id LIMIT 1"), {"nome": state.lead_nome, "cidade": _proximo.lead.cidade, "user_id": tenant_id}).fetchone()
                        if _dup_sub:
                            state.lead_id = _dup_sub[0]
                        else:
                            _conn_sub.execute(text("INSERT INTO leads (id,nome,cidade,segmento,telefone,whatsapp,rating,score,tier,status,user_id,criado_em,atualizado_em,processado,tentativas,dados_completos) VALUES (:id,:nome,:cidade,:segmento,:telefone,:whatsapp,:rating,:score,:tier,:status,:user_id,:criado_em,:atualizado_em,:processado,:tentativas,:dados_completos) ON CONFLICT DO NOTHING"), {"id": state.lead_id, "nome": state.lead_nome, "cidade": _proximo.lead.cidade, "segmento": state.segmento, "telefone": _proximo.lead.telefone or "", "whatsapp": _proximo.lead.whatsapp or "", "rating": _proximo.lead.rating or 0.0, "score": state.qualificacao_caio.score, "tier": state.qualificacao_caio.tier, "status": "capturado", "user_id": tenant_id, "dados_completos": _json_sub.dumps(_dados_extras_sub), "criado_em": _agora_sub, "atualizado_em": _agora_sub, "processado": False, "tentativas": 0})
                            _conn_sub.commit()
                except Exception as _e_sub:
                    pass
        _log(f"  Caio: {state.qualificacao_caio.qualificacao} score={state.qualificacao_caio.score}", "success")
        logger.info(f"[Pipeline] Caio: {state.qualificacao_caio.qualificacao}")
        logger.info("[Pipeline] Alex: OK")
        if _ledger:
            _ledger.registrar_fim_fase(2, FaseStatus.CONCLUIDA, resultado=f"score={state.qualificacao_caio.score} tier={state.qualificacao_caio.tier}")
            _ledger.atualizar_fact("score_qualificacao", state.qualificacao_caio.score)
            _ledger.atualizar_fact("tier", state.qualificacao_caio.tier)
        if _span: _span.finalizar("success")
        # PRD #7: Agent Router — modelo dinâmico por complexidade
        try:
            from agent_router import AgentRouter, calcular_complexidade_lead, set_router
            _router_facts = {
                "qtd_reviews": state.lead_raw_data.get("total_avaliacoes", 0),
                "nicho": state.segmento,
                "tier": state.qualificacao_caio.tier if state.qualificacao_caio else "STANDARD",
                "tem_site": bool(state.lead_raw_data.get("website")),
                "servicos": state.lead_raw_data.get("servicos") or [],
            }
            _complexidade = calcular_complexidade_lead(_router_facts)
            _router = AgentRouter(_complexidade)
            set_router(_router)
            print(_router.resumo())
            if _ledger:
                _ledger.atualizar_fact("complexidade", _complexidade)
                _ledger.registrar_decisao(2, f"routing_{_complexidade}", f"Modelos ajustados por complexidade")
        except Exception as _router_err:
            print(f"[ROUTER] Erro (fallback medio): {_router_err}")
            _router = None
            _complexidade = "medio"
        # PRD #11: Ativar memória no thread pra call_claude injetar automaticamente
        if _memory_core and _memory_warm:
            try:
                from agent_memory import set_memory
                set_memory(_memory_core, _memory_warm, state.segmento)
            except Exception:
                pass
        _progress(3, "Pesquisa de mercado...")
        _log("FASE 3: JINA AI", "info")
        if _ledger: _ledger.registrar_inicio_fase(3, "jina")
        _span = _trace.iniciar_span("jina", agente="jina") if _trace else None
        _jina_cached = get_dados_agente(state.pipeline_id, "jina")
        if _jina_cached and _jina_cached.get("insights"):
            state.jina_insights = _jina_cached["insights"]
            _log(f"  Jina: ♻️ retomado do checkpoint ({len(state.jina_insights)} chars)", "success")
        else:
            try:
                state.jina_insights = pesquisar_referencias_jina(state.segmento, cidade=state.cidade)
                _log(f"  Jina: {len(state.jina_insights)} chars", "success")
                logger.info(f"[Pipeline] Jina AI: OK ({len(state.jina_insights)} chars)")
                if _validar_output(state.jina_insights, min_chars=30):
                    salvar_checkpoint(state.pipeline_id, "jina", {"insights": state.jina_insights})
            except Exception as e:
                state.jina_insights = ""
                logger.warning(f"[Pipeline] Jina AI erro (sem fallback): {e}")
        if _ledger:
            if state.jina_insights:
                _ledger.registrar_fim_fase(3, FaseStatus.CONCLUIDA, resultado=f"{len(state.jina_insights)} chars")
            else:
                _ledger.registrar_fim_fase(3, FaseStatus.PULADA, erro="sem resultado")
                _ledger.registrar_decisao(3, "pular_jina", "Fase não obrigatória")
        if _span: _span.finalizar("success" if state.jina_insights else "skipped")

        # ═══ MÓDULO DE INTELIGÊNCIA (paralelo) ═══
        _progress(4, "Analisando concorrência...")
        _log("FASE 4: INTELIGÊNCIA DE MERCADO", "info")
        state.inteligencia = {}
        try:
            from utils.espionar_concorrencia import espionar_concorrencia, extrair_insights_reviews, mapear_atributos_para_servicos, gerar_seo_context

            # Rodar espionagem + insights de reviews em paralelo
            async def _run_inteligencia():
                _tasks = []
                _tasks.append(espionar_concorrencia(state.segmento, state.cidade, max_concorrentes=3))
                return await asyncio.gather(*_tasks, return_exceptions=True)

            _intel_results = await _run_inteligencia()
            _concorrencia = _intel_results[0] if not isinstance(_intel_results[0], Exception) else {}

            # Insights de reviews (local, sem async)
            _reviews_raw = state.lead_raw_data.get("reviews", [])
            _reviews_insights = extrair_insights_reviews(_reviews_raw)

            # Serviços reais do Maps
            _atributos = state.lead_raw_data.get("atributos") or []
            _servicos_reais = mapear_atributos_para_servicos(_atributos, state.segmento)

            # SEO context
            _paa = _concorrencia.get("people_also_ask", []) if isinstance(_concorrencia, dict) else []
            _seo = gerar_seo_context(
                state.segmento, state.cidade, state.lead_nome,
                paa=_paa,
                rating=state.lead_raw_data.get("rating", 0),
                total_reviews=state.lead_raw_data.get("total_avaliacoes", 0)
            )

            state.inteligencia = {
                "concorrencia": _concorrencia if isinstance(_concorrencia, dict) else {},
                "reviews_insights": _reviews_insights,
                "servicos_reais": _servicos_reais,
                "seo": _seo,
            }
            _n_conc = len(state.inteligencia.get("concorrencia", {}).get("concorrentes", []))
            _log(f"  Inteligência: {_n_conc} concorrentes, {len(_servicos_reais)} serviços, {len(_paa)} PAA", "success")
        except Exception as _intel_err:
            print(f"[Pipeline] Módulo inteligência erro (não-fatal): {_intel_err}")
            state.inteligencia = {}

        # Enriquecer jina_insights com dados de concorrência (se disponível)
        if state.inteligencia.get("concorrencia", {}).get("concorrentes"):
            _conc_data = state.inteligencia["concorrencia"]
            _enrich = "\n\n=== CONCORRENTES REAIS (via Playwright) ===\n"
            for _c in _conc_data.get("concorrentes", [])[:3]:
                _enrich += f"- {_c.get('nome', '?')}: tema={_c.get('tema','?')}, CTA='{_c.get('cta_principal','')}', H1='{_c.get('h1_text','')[:60]}'\n"
            _pm = _conc_data.get("padroes_mercado", {})
            if _pm:
                _enrich += f"Padrão: {_pm.get('tema_dominante','?')}, fonte={_pm.get('fonte_h1_dominante','?')}\n"
            _paa_list = state.inteligencia.get("concorrencia", {}).get("people_also_ask", [])
            if _paa_list:
                _enrich += f"People Also Ask: {' | '.join(_paa_list[:4])}\n"
            state.jina_insights = (state.jina_insights or "") + _enrich

        _progress(5, "Preparando design...")
        _log("FASE 5: DESIGN (ArquitetoMestre)", "info")
        # Theo APOSENTADO — briefing gerado inline (ArquitetoMestre já monta brief próprio)
        state.briefing_theo = f"Site premium para {state.lead_nome} ({state.segmento}) em {state.cidade}. Rating: {state.lead_obj.lead.rating or 0}/5."
        _progress(5, "Buscando fotos...")
        _log("FASE 5: PALETA + UNSPLASH", "info")
        if _ledger: _ledger.registrar_inicio_fase(5, "unsplash")
        _span = _trace.iniciar_span("unsplash", agente="unsplash") if _trace else None
        # Unsplash — fotos de alta qualidade por nicho
        try:
            _nome_negocio = state.lead_raw_data.get("nome", "") or ""
            _cidade_negocio = getattr(state, "cidade", "") or state.lead_raw_data.get("cidade", "") or ""
            _fotos_unsplash = buscar_fotos_unsplash(
                state.segmento,
                quantidade=8,
                nome=_nome_negocio,
                cidade=_cidade_negocio,
            )
            # Usar APENAS Unsplash — fotos do Google Maps são de baixa qualidade
            state.lead_raw_data["fotos"] = _fotos_unsplash
            # Logo: manter texto (nome do negócio) — não usar logo do Google Maps
            if not state.lead_raw_data.get("logo_url"):
                state.lead_raw_data["logo_url"] = None
            print(f"[Pipeline] Unsplash: {len(_fotos_unsplash)} fotos para {_nome_negocio or state.segmento}")
            _log(f"  Fotos Unsplash: {len(_fotos_unsplash)}", "success")
        except Exception as e:
            logger.warning(f"[Pipeline] Unsplash erro: {e}")
            state.lead_raw_data["fotos"] = []
        logger.info("[Pipeline] Designer: OK")
        # ================================================================
        # CURADORIA DE ENTRADA — comprime dados antes do Arquiteto
        # ================================================================
        reviews_raw = state.lead_raw_data.get("reviews", [])
        if reviews_raw:
            # Filtrar reviews positivos (rating >= 4), fallback para >= 3
            def _get_rating(r):
                return float(r.get("rating") or r.get("nota") or r.get("stars") or r.get("estrelas") or 0)
            _positivos = [r for r in reviews_raw if _get_rating(r) >= 4]
            if len(_positivos) < 2:
                _positivos = [r for r in reviews_raw if _get_rating(r) >= 3]
            if not _positivos:
                # Sem reviews >= 3: usar os melhores disponiveis (top 3 por rating)
                _melhores = sorted(reviews_raw, key=lambda r: _get_rating(r), reverse=True)[:3]
                _positivos = [r for r in _melhores if _get_rating(r) >= 2]
                if not _positivos:
                    state.lead_raw_data["reviews"] = []
                else:
                    state.lead_raw_data["reviews"] = _positivos
            else:
                # Entre os positivos, priorizar os mais detalhados
                _positivos_sorted = sorted(_positivos, key=lambda r: len(str(r.get("texto", r.get("text", "")))), reverse=True)
                state.lead_raw_data["reviews"] = _positivos_sorted[:5]
        if len(state.jina_insights) > 5000:
            state.jina_insights = state.jina_insights[:5000]
        # Usar embed do Hunter (capturado do Google Maps real) se disponível
        # Só gerar fallback OSM se o Hunter não capturou
        import urllib.parse as _urlparse
        _embed_hunter = state.lead_raw_data.get("google_maps_embed", "") or ""
        if not _embed_hunter or len(_embed_hunter) < 50:
            # Fallback: Google Maps embed por nome+cidade com zoom correto
            _maps_query = _urlparse.quote(state.lead_nome + ", " + state.lead_obj.lead.cidade)
            _embed_hunter = ('<iframe width="100%" height="450" style="border:0;" loading="lazy" allowfullscreen="" ' 
                'referrerpolicy="no-referrer-when-downgrade" ' 
                'src="https://maps.google.com/maps?q=' + _maps_query + '&output=embed&z=16"></iframe>')
            print(f"[Pipeline] maps_embed: fallback Google Maps por nome+cidade")
        else:
            print(f"[Pipeline] maps_embed: usando embed real do Hunter ({len(_embed_hunter)} chars)")
        state.lead_raw_data["google_maps_embed"] = _embed_hunter
        print(f"[Pipeline] Curadoria: {len(state.lead_raw_data.get('reviews', []))} reviews, {len(state.jina_insights)} chars jina, maps_embed OK")

        # Injetar logo e fotos processadas pelo Alex no dados_hunter
        # Alex DESATIVADO — fotos ja injetadas via Unsplash na FASE 5
        print("[Pipeline] Alex desativado — fotos Unsplash e paleta nicho ja aplicados")

        _progress(6, "Arquitetando site...")
        _log("FASE 6: ARQUITETO MESTRE", "info")
        if _ledger:
            _n_fotos = len(state.lead_raw_data.get("fotos", []))
            _ledger.registrar_fim_fase(5, FaseStatus.CONCLUIDA, resultado=f"{_n_fotos} fotos")
            _ledger.atualizar_fact("fotos_disponiveis", _n_fotos)
            _ledger.registrar_inicio_fase(6, "arquiteto", modelo="sonnet")
        if _span: _span.finalizar("success")
        _span = _trace.iniciar_span("arquiteto", agente="arquiteto", modelo="sonnet") if _trace else None
        _arq_cached = get_dados_agente(state.pipeline_id, "arquiteto")
        if _arq_cached and _arq_cached.get("prd_json"):
            # Retomar PRD do checkpoint
            from designer_prd import DesignerPRD as PRDOutput
            try:
                state.prd_arquiteto = PRDOutput(**_arq_cached["prd_json"])
                _log(f"  PRD: ♻️ retomado do checkpoint ({len(state.prd_arquiteto.sections)} seções)", "success")
            except Exception as _prd_err:
                _log(f"  ⚠️ Checkpoint PRD inválido, regenerando: {_prd_err}", "warning")
                _arq_cached = None
        if not _arq_cached or not _arq_cached.get("prd_json"):
            _seed = int(hashlib.md5(state.lead_nome.encode()).hexdigest()[:8], 16)
            random.seed(_seed)
            _pool = ["mask-reveal", "counter-animation", "parallax-scroll", "stagger-fade",
                     "reveal-on-scroll", "text-split", "floating-cards", "elastic-scale",
                     "wave-animation", "spotlight-hover", "tilt-3d", "fade-up", "slide-in", "zoom-reveal"]
            random.sample(_pool, 6)
            _seg = state.segmento or state.lead_obj.lead.segmento or "negocio local"
            _cid = state.lead_obj.lead.cidade or state.cidade or ""
            _prd_fn = _gerar_prd_agent if _ARQUITETO_AGENT else gerar_arquiteto_mestre_prd
            state.prd_arquiteto = tentar(
                lambda: _prd_fn(
                    dados_hunter=state.lead_raw_data,
                    cidade=_cid,
                    segmento=_seg,
                    jina_insights=state.jina_insights,
                    briefing_theo=state.briefing_theo,
                    caio_tier=state.qualificacao_caio.tier if state.qualificacao_caio else "STANDARD",
                    caio_score=state.qualificacao_caio.score if state.qualificacao_caio else 0,
                    caio_motivo=state.qualificacao_caio.motivo if state.qualificacao_caio else "",
                    dark_mode=state.segmento in ("academia", "crossfit", "churrascaria", "barbearia"),
                    keyword_research=getattr(state, 'keyword_research', ''),
                    inteligencia=getattr(state, 'inteligencia', {}),
                ),
                fase="arquiteto", max_attempts=3, base_delay=2.0,
                log_fn=_log,
            )
            _log(f"  PRD: {len(state.prd_arquiteto.sections)} secoes", "success")
            # Salvar checkpoint do PRD (mais caro em tokens depois do Liam)
            try:
                _prd_dict = state.prd_arquiteto.model_dump() if hasattr(state.prd_arquiteto, "model_dump") else state.prd_arquiteto.__dict__
                if _validar_output(str(_prd_dict), min_chars=200):
                    salvar_checkpoint(state.pipeline_id, "arquiteto", {"prd_json": _prd_dict})
                else:
                    _log("  ⚠️ PRD output truncado — não salvou checkpoint", "warning")
            except Exception as _ckpt_e:
                print(f"[Checkpoint] PRD save skip: {_ckpt_e}")
        # White-label: verificar se tenant tem plano PRO (remove branding FraLib do footer)
        try:
            with engine.connect() as _wl_conn:
                _wl_row = _wl_conn.execute(text("SELECT plano FROM users WHERE id=:uid"), {"uid": tenant_id}).fetchone()
                if _wl_row and _wl_row[0] in ('pro', 'enterprise'):
                    state.prd_arquiteto.white_label = True
        except Exception:
            pass
        # Forcar google_maps_embed com iframe OSM (o Arquiteto nao tem place_id)
        state.prd_arquiteto.google_maps_embed = state.lead_raw_data.get("google_maps_embed", "")
        print(f"[Pipeline] Maps embed injetado no PRD: {len(state.prd_arquiteto.google_maps_embed)} chars")
        # Salvar PRD no trace para auditoria
        try:
            import json as _json
            _trace_dir = "/root/fralib/logs/pipeline_trace"
            _os.makedirs(_trace_dir, exist_ok=True)
            with open(f"{_trace_dir}/designer_prd.json", "w", encoding="utf-8") as _pf:
                _json.dump(state.prd_arquiteto.model_dump() if hasattr(state.prd_arquiteto, "model_dump") else state.prd_arquiteto.__dict__, _pf, ensure_ascii=False, indent=2, default=str)
        except Exception as _pe:
            print(f"[Pipeline] PRD trace skip: {_pe}")
        _progress(7, "Gerando HTML...")
        _log("FASE 7: LIAM (Componentizado)", "info")
        if _ledger:
            _ledger.registrar_fim_fase(6, FaseStatus.CONCLUIDA, resultado="PRD gerado")
            _ledger.registrar_inicio_fase(7, "liam", modelo="opus")
        if _span: _span.finalizar("success")
        _span = _trace.iniciar_span("liam", agente="liam", modelo="opus") if _trace else None
        if not state.prd_arquiteto:
            raise Exception("PRD nao disponivel para o Liam")
        _liam_cached = get_dados_agente(state.pipeline_id, "liam")
        if _liam_cached and _liam_cached.get("html_final") and len(_liam_cached["html_final"]) >= 500:
            state.html_final = _liam_cached["html_final"]
            _log(f"  HTML: ♻️ retomado do checkpoint ({len(state.html_final):,} chars)", "success")
        else:
            _html_main = tentar(
                lambda: gerar_html_componentizado(state.prd_arquiteto),
                fase="liam", max_attempts=3, base_delay=3.0,
                log_fn=_log,
            )
            if not _html_main or len(_html_main) < 500:
                raise Exception("Liam retornou HTML vazio")
            try: open("/root/fralib/logs/pipeline_trace/liam_sections.html","w").write(_html_main)
            except: pass
            state.html_final = montar_template_python(_html_main, state.prd_arquiteto)
            state.html_final = critique_theater_pass(state.html_final)

            # Sanitizador: substituir source.unsplash.com (deprecated) por URLs reais
            if "source.unsplash.com" in state.html_final:
                import re as _re_unsplash
                _fotos_disponiveis = getattr(state, '_fotos_unsplash', []) or state.lead_raw_data.get("fotos", [])
                _fallback_foto = _fotos_disponiveis[0] if _fotos_disponiveis else "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&q=80"
                _count_replaced = 0
                def _replace_source_unsplash(match):
                    nonlocal _count_replaced
                    idx = _count_replaced % len(_fotos_disponiveis) if _fotos_disponiveis else 0
                    replacement = _fotos_disponiveis[idx] if _fotos_disponiveis else _fallback_foto
                    _count_replaced += 1
                    return replacement
                state.html_final = _re_unsplash.sub(
                    r'https?://source\.unsplash\.com/[^\s"\'<>]+',
                    _replace_source_unsplash,
                    state.html_final
                )
                if _count_replaced:
                    print(f"[Sanitizer] {_count_replaced}x source.unsplash.com substituído por URLs permanentes")

            _log(f"  HTML: {len(state.html_final):,} chars", "success")
            logger.info("[Pipeline] Liam: OK")
            # Validar HTML antes de salvar checkpoint (não salvar truncado)
            _html_valid = (
                len(state.html_final) >= 2000 and
                "</html>" in state.html_final.lower()
            )
            if _html_valid:
                salvar_checkpoint(state.pipeline_id, "liam", {"html_final": state.html_final})
            else:
                _log("  ⚠️ HTML incompleto (sem </html>) — não salvou checkpoint", "warning")
                raise Exception(f"Liam gerou HTML truncado ({len(state.html_final)} chars, sem tag de fechamento)")
        try:
            os.makedirs("/root/fralib/logs/pipeline_trace", exist_ok=True)
            with open("/root/fralib/logs/pipeline_trace/liam_html.html", "w", encoding="utf-8") as _f:
                _f.write(state.html_final)
            print("[Trace] liam_html.html salvo")
        except Exception:
            pass
        _progress(8, "Auditoria de qualidade...")
        _log("FASE 8: LIZ (Auditoria)", "info")
        if _ledger:
            _ledger.registrar_fim_fase(7, FaseStatus.CONCLUIDA, resultado=f"{len(state.html_final)} chars HTML")
            _ledger.registrar_inicio_fase(8, "liz", modelo="haiku")
        if _span: _span.finalizar("success")
        _span = _trace.iniciar_span("liz", agente="liz", modelo="haiku") if _trace else None
        # BeautifulSoup auto-healing: corrige tags abertas antes da Liz auditar
        try:
            from bs4 import BeautifulSoup as _BS
            _soup = _BS(state.html_final, "html.parser")
            state.html_final = str(_soup)
            print("[Pipeline] BeautifulSoup auto-healing: OK")
        except ImportError:
            # Fallback robusto: fechar tags comuns não fechadas
            import re as _re_bs
            for _tag in ['div', 'section', 'span', 'p', 'a', 'ul', 'li', 'header', 'footer', 'nav', 'main']:
                _opens = len(_re_bs.findall(f'<{_tag}[\\s>]', state.html_final))
                _closes = state.html_final.count(f'</{_tag}>')
                if _opens > _closes:
                    state.html_final += f'</{_tag}>' * (_opens - _closes)
            print("[Pipeline] BeautifulSoup fallback (regex tag-close): OK")
        except Exception as _bse:
            print(f"[Pipeline] BeautifulSoup skip: {_bse}")
        MAX_LIZ = 3
        _reflection_context = ""
        _html_pre_liz = state.html_final  # backup original do Liam
        for tentativa_liz in range(1, MAX_LIZ + 1):
            try:
                _log(f"  Tentativa {tentativa_liz}/{MAX_LIZ}...", "info")

                # ── REFLECTION LOOP: auditar com feedback estruturado ──
                liz_result_struct = auditar_secao_estruturado(
                    html=state.html_final,
                    briefing=state.briefing_theo or "",
                    cidade=getattr(state, "cidade", ""),
                    nome=state.lead_nome if hasattr(state, "lead_nome") else "",
                    nicho=getattr(state, "segmento", "") or "",
                    tier=getattr(state.lead_obj, "tier", "STANDARD") if hasattr(state, "lead_obj") and state.lead_obj else "STANDARD",
                )
                state.liz_score = int(liz_result_struct["score"] * 10)  # normalizar pra 0-100

                if liz_result_struct["aprovado"]:
                    state.liz_aprovado = True
                    _log(f"  Liz APROVOU score={liz_result_struct['score']}", "success")
                    print(f"[REFLECTION] Seção completa | aprovada na tentativa {tentativa_liz} | score final: {liz_result_struct['score']}")
                    break

                # Montar reflection pra próxima tentativa
                problemas_texto = "\n".join([
                    f"- {p['dimensao']} ({p['score']}/10): {p['detalhe']}"
                    for p in liz_result_struct["problemas"] if p["score"] < 7
                ])
                _new_reflection = f"""## REFLEXÃO (tentativa {tentativa_liz} rejeitada)
Score: {liz_result_struct['score']}/10
Problemas encontrados:
{problemas_texto}

Instruções de correção:
{liz_result_struct['instrucoes_correcao']}

IMPORTANTE: Corrija EXATAMENTE os problemas acima. Não altere o que já estava correto."""

                _reflection_context = _reflection_context + "\n\n" + _new_reflection if _reflection_context else _new_reflection

                print(f"[REFLECTION] Tentativa {tentativa_liz} | score: {liz_result_struct['score']} | problemas: {[p['dimensao'] for p in liz_result_struct['problemas'] if p['score'] < 7]}")
                _log(f"  Score={liz_result_struct['score']} - regenerando com reflection...", "warning")

                if tentativa_liz >= MAX_LIZ:
                    # PRD #13: LATS — tree search antes de force-approve
                    try:
                        from agents.liam_lats import lats_retry
                        _lats_falhas = [{"html": state.html_final, "score": liz_result_struct.get('score', 0), "problemas": str([p['dimensao'] for p in liz_result_struct.get('problemas', []) if p.get('score', 10) < 7])}]
                        _lats_nicho = getattr(state, "segmento", "") or ""
                        _lats_tier = getattr(state.lead_obj, "tier", "STANDARD") if hasattr(state, "lead_obj") and state.lead_obj else "STANDARD"
                        _lats_fotos = state.lead_raw_data.get("fotos", []) if hasattr(state, "lead_raw_data") else []
                        _lats_tokens = str(getattr(state.prd_arquiteto, "design_tokens", ""))[:500]
                        _lats_prd = state.prd_arquiteto.__dict__ if hasattr(state.prd_arquiteto, "__dict__") else {}
                        _lats_result = lats_retry(
                            nome_secao="full_page",
                            prd_secao=_lats_prd,
                            design_tokens_str=_lats_tokens,
                            fotos=_lats_fotos,
                            historico_falhas=_lats_falhas,
                            nicho=_lats_nicho,
                            tier=_lats_tier,
                        )
                        if _lats_result.get("aprovado") and _lats_result.get("html") and len(_lats_result["html"]) >= 500:
                            from agents.liam import montar_template_python as _liam_tpl_lats
                            state.html_final = _liam_tpl_lats(_lats_result["html"], state.prd_arquiteto)
                            state.liz_aprovado = True
                            state.liz_score = int(_lats_result["score"] * 10)
                            _log(f"  LATS resolveu! strategy={_lats_result['strategy']} score={_lats_result['score']:.1f}", "success")
                            if _ledger: _ledger.registrar_decisao(8, "lats_sucesso", f"LATS resolveu via {_lats_result['strategy']}")
                            break
                    except Exception as _lats_err:
                        print(f"[LATS] Erro (force-approve): {_lats_err}")

                    # Force-approve após max tentativas (LATS não resolveu)
                    _log(f"  ⚠️ {MAX_LIZ} tentativas + LATS esgotados. Forçando aprovação (score={liz_result_struct['score']})", "warning")
                    print(f"[REFLECTION][WARN] Force-approved após {MAX_LIZ} tentativas + LATS | score: {liz_result_struct['score']}")
                    state.liz_aprovado = True
                    state.liz_score = max(state.liz_score, 70)
                    break

                # ── REGENERAR COM LIAM + REFLECTION ──
                try:
                    from agents.liam import gerar_html_componentizado as _liam_regen, montar_template_python as _liam_template, critique_theater_pass as _liam_critique
                    # Injetar reflection no PRD (campo extra que Liam lê)
                    _prd_com_reflection = state.prd_arquiteto
                    if hasattr(_prd_com_reflection, '__dict__'):
                        _prd_com_reflection.reflection_context = _reflection_context
                    elif isinstance(_prd_com_reflection, dict):
                        _prd_com_reflection["reflection_context"] = _reflection_context

                    _html_regen = _liam_regen(_prd_com_reflection)
                    if _html_regen and len(_html_regen) >= 500:
                        _html_novo = _liam_template(_html_regen, _prd_com_reflection)
                        _html_novo = _liam_critique(_html_novo)
                        # Anti-bloat: se cresceu >15%, reverter
                        if len(_html_novo) > len(_html_pre_liz) * 1.15:
                            print(f"[REFLECTION] Anti-bloat: HTML cresceu {len(_html_novo)} vs {len(_html_pre_liz)} (>15%). Mantendo original.")
                            _log("  ⚠️ Anti-bloat: regeneração inflou HTML. Aprovando original.", "warning")
                            state.liz_aprovado = True
                            break
                        state.html_final = _html_novo
                    else:
                        print(f"[REFLECTION] Liam retornou HTML curto ({len(_html_regen) if _html_regen else 0}). Mantendo anterior.")
                        state.liz_aprovado = True
                        break
                except Exception as e_regen:
                    print(f"[REFLECTION] Erro na regeneração: {e_regen}. Aprovando HTML atual.")
                    state.liz_aprovado = True
                    break

            except Exception as e:
                if "Deploy bloqueado" in str(e):
                    raise
                logger.warning(f"[Pipeline] Liz erro: {e}")
                state.liz_aprovado = True
                break
        _progress(9, "Publicando site...")
        _log("FASE 9: DEPLOY", "info")
        if _ledger:
            _ledger.registrar_fim_fase(8, FaseStatus.CONCLUIDA, resultado=f"liz_aprovado={state.liz_aprovado}")
            _ledger.registrar_inicio_fase(9, "deploy")
        if _span: _span.finalizar("success")
        _span = _trace.iniciar_span("deploy", agente="deploy") if _trace else None
        # PRD #8: Salvar PRD no cache semântico (só se Liz aprovou e não veio do cache)
        if state.liz_aprovado and state.prd_arquiteto and not getattr(state.prd_arquiteto, '_cache_hit', False):
            try:
                from prd_cache import salvar_prd_cache, atualizar_quality_score
                from design_context import get_design_context
                _dc_cache = get_design_context(state.segmento, state.lead_nome)
                _dir_cache = _dc_cache.get("direction", "default") if _dc_cache else "default"
                _tier_cache = state.qualificacao_caio.tier if state.qualificacao_caio else "STANDARD"
                _prd_dict = state.prd_arquiteto.model_dump() if hasattr(state.prd_arquiteto, "model_dump") else state.prd_arquiteto.__dict__
                salvar_prd_cache(state.segmento, _tier_cache, _dir_cache, _prd_dict, state.lead_raw_data)
            except Exception as _cache_save_err:
                print(f"[CACHE] Erro ao salvar PRD: {_cache_save_err}")
        web_dir = f"/var/www/fralib/sites/{tenant_id}/{state.lead_slug}"
        os.makedirs(web_dir, exist_ok=True)
        # PR15: substituir placeholder do pixel de tracking pelo lead_id real
        if hasattr(state, 'lead_id') and state.lead_id:
            state.html_final = state.html_final.replace("__FRALIB_LEAD_ID__", str(state.lead_id))
        with open(f"{web_dir}/index.html", "w", encoding="utf-8") as _f:
            _f.write(state.html_final)
        if state.alex_result and state.alex_result.assets_dir:
            assets_src = os.path.realpath(state.alex_result.assets_dir)
            assets_dst = os.path.realpath(f"{web_dir}/assets")
            if assets_src == assets_dst:
                # Alex já salvou direto no destino correto — não fazer nada
                print(f"[Pipeline] Assets já no lugar: {assets_dst}")
            elif os.path.exists(assets_src):
                import shutil
                if os.path.exists(assets_dst):
                    shutil.rmtree(assets_dst)
                shutil.copytree(assets_src, assets_dst)
                print(f"[Pipeline] Assets copiados: {assets_src} -> {assets_dst}")
            else:
                print(f"[Pipeline] Assets src não encontrado: {assets_src}")
        import subprocess as _sp
        _sp.run(["chown", "-R", "www-data:www-data", web_dir], check=False)
        _sp.run(["chmod", "-R", "755", web_dir], check=False)
        state.site_url = f"https://seunegociofralib.site/sites/{tenant_id}/{state.lead_slug}/"
        # Fix canonical + og:url pra bater com URL real do deploy
        _canonical_errada = f"https://seunegociofralib.site/sites/{state.lead_slug}/"
        if _canonical_errada in state.html_final:
            state.html_final = state.html_final.replace(_canonical_errada, state.site_url)
            print(f"[Pipeline] Canonical corrigida: {state.site_url}")
        _log(f"  Deploy: {state.site_url}", "success")
        logger.info(f"[Pipeline] Deploy: {state.site_url}")

        # FASE 9.5: HEALTH CHECK (PR14) - bloqueia Bryan se site quebrado
        _log("FASE 9.5: HEALTH CHECK", "info")
        from services.site_health_check import validar_site
        validar_site(state.site_url)
        _log("  Health check: OK", "success")
        logger.info(f"[Pipeline] HealthCheck OK: {state.site_url}")

        _progress(10, "Enviando contato...")
        _log("FASE 10: BRYAN", "info")
        if _ledger:
            _ledger.registrar_fim_fase(9, FaseStatus.CONCLUIDA, resultado=state.site_url)
            _ledger.registrar_inicio_fase(10, "bryan", modelo="haiku")
        if _span: _span.finalizar("success")
        _span = _trace.iniciar_span("bryan", agente="bryan", modelo="haiku") if _trace else None
        # Bryan como job separado — não bloqueia pipeline principal
        _sdr_stage_final = 'pendente_wpp'
        try:
            _bryan_payload = {
                "nome": state.lead_nome,
                "cidade": state.lead_obj.lead.cidade,
                "segmento": state.segmento,
                "telefone": state.lead_obj.lead.telefone or "",
                "whatsapp": state.lead_obj.lead.whatsapp or "",
                "rating": state.lead_obj.lead.rating or 0.0,
                "site_url": state.site_url,
                "score_caio": state.qualificacao_caio.score if state.qualificacao_caio else 0,
                "tier": state.qualificacao_caio.tier if state.qualificacao_caio else "STANDARD",
                "proof": state.qualificacao_caio.razoes[0] if state.qualificacao_caio and getattr(state.qualificacao_caio, 'razoes', None) else None,
                "lead_id": state.lead_id,
                "tenant_id": state.tenant_id,
            }
            import job_queue as _jq_bryan
            _db_bryan = SessionLocal()
            try:
                _jq_bryan.enqueue(
                    _db_bryan,
                    tipo="bryan_outreach",
                    payload=_bryan_payload,
                    tenant_id=state.tenant_id,
                    max_attempts=5,
                    idempotency_key=f"bryan-{state.lead_id}",
                )
                _db_bryan.close()
                _log("  Bryan: enfileirado como job separado", "info")
                _sdr_stage_final = 'hook'
            except Exception:
                _db_bryan.close()
                raise
        except Exception as e:
            logger.warning(f"[Pipeline] Bryan enqueue erro (não bloqueia): {e}")
            _log(f"  Bryan: falha ao enfileirar ({e}). Site gerado OK.", "warning")
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE leads SET site_url=:url, url_site=:url, processado=true,
                processado_em=:ts, status='concluido', sdr_stage=:stage, atualizado_em=:ts
                WHERE id=:id AND user_id=:uid
            """), {"url": state.site_url, "ts": datetime.now().isoformat(), "id": state.lead_id, "stage": _sdr_stage_final, "uid": state.tenant_id})
            conn.commit()
        limpar_checkpoint(state.pipeline_id)
        _log("PIPELINE v2 CONCLUIDO - FraLibState OK", "success")
        import json as _json_complete
        adicionar_log(_json_complete.dumps({
            "type": "complete",
            "url": state.site_url,
            "lead_nome": state.lead_nome
        }), "PIPELINE_STATUS", user_id=tenant_id)
        logger.info("[Pipeline] CONCLUIDO - 7 AGENTES!")

        # PRD #6: Ledger — finalizar e salvar
        if _ledger:
            _ledger.registrar_fim_fase(10, FaseStatus.CONCLUIDA, resultado="pipeline_completo")
            print(_ledger.snapshot())
            salvar_ledger(_ledger)

        # PRD #10: Trace — finalizar e salvar
        if _span: _span.finalizar("success")
        if _trace:
            _trace.lead_nome = state.lead_nome
            _trace.tier = state.qualificacao_caio.tier if state.qualificacao_caio else ""
            _trace.complexidade = _complexidade if '_complexidade' in dir() else ""
            _trace.finalizar("success")
            print(formatar_trace_log(_trace))
            salvar_trace(_trace)

        # PRD #11: Memory — salvar cold + promoção periódica
        if _memory_cold:
            try:
                _memory_cold.salvar_run(state.pipeline_id[:8], {
                    "nicho": state.segmento,
                    "lead": state.lead_nome,
                    "tier": state.qualificacao_caio.tier if state.qualificacao_caio else "",
                    "liz_aprovado": state.liz_aprovado,
                    "site_url": state.site_url,
                })
            except Exception:
                pass
        if _memory_warm and _memory_core:
            try:
                _memory_warm.promover_para_core(_memory_core)
            except Exception:
                pass

        # PRD #4: Token Tracking — log + salvar no DB
        try:
            if _token_tracker:
                _token_tracker.lead_nome = state.lead_nome or ""
                from agents.token_tracker import log_tracking, salvar_tracking, set_tracker
                _resumo = _token_tracker.resumo()
                log_tracking(_resumo)
                salvar_tracking(_resumo)
                set_tracker(None)  # limpar tracker do thread
        except Exception as _track_err:
            print(f"[TRACKING] Erro: {_track_err}")

        # PRD #7: Limpar router do thread
        try:
            from agent_router import set_router
            set_router(None)
        except Exception:
            pass
        # PRD #11: Limpar memória do thread
        try:
            from agent_memory import clear_memory
            clear_memory()
        except Exception:
            pass

        # Descontar 1 crédito diário + marcar ultimo_deploy_at
        try:
            with SessionLocal() as _db_cred:
                consumir_credito_diario(_db_cred, tenant_id, state.lead_nome)
                print(f"[Pipeline] Credito diario consumido (tenant={tenant_id})")
        except Exception as _cred_err:
            print(f"[Pipeline] ERRO ao descontar credito: {_cred_err}")

        # Limpar checkpoints expirados (>24h)
        try:
            from agents.pipeline_checkpoint import limpar_checkpoints_expirados
            limpar_checkpoints_expirados(max_age_hours=24)
        except Exception:
            pass

        # Auto-run: se tem leads na fila, agendar próximo após cooldown
        try:
            with SessionLocal() as _db_auto:
                _plano_row = _db_auto.execute(text("SELECT plano, plano_pago FROM users WHERE id=:id"), {"id": tenant_id}).fetchone()
                _plano_auto = (_plano_row[0] if _plano_row else "trial") or "trial"
                _plano_pago_auto = _plano_row[1] if _plano_row else False
                _fila_auto = _db_auto.execute(text(
                    "SELECT id, segmento, cidade FROM leads WHERE user_id=:uid AND status='capturado' ORDER BY score DESC LIMIT 1"
                ), {"uid": tenant_id}).fetchone()
                if _fila_auto and _plano_pago_auto:
                    _cooldown_auto = _COOLDOWN_POR_PLANO.get(_plano_auto, 3600)
                    _lead_id_auto = str(_fila_auto[0])
                    print(f"[Pipeline] Auto-run: lead {_lead_id_auto} na fila, agendando em {_cooldown_auto}s")
                    _log(f"Proximo pipeline automatico em {_cooldown_auto // 60}min ({_fila_auto[1]} - {_fila_auto[2]})", "info")

                    async def _auto_run_delayed():
                        await asyncio.sleep(_cooldown_auto)
                        try:
                            await executar_pipeline_lead_existente(_lead_id_auto, tenant_id)
                        except Exception as _ar_err:
                            print(f"[Pipeline] Auto-run erro: {_ar_err}")
                    asyncio.create_task(_auto_run_delayed())
        except Exception as _auto_err:
            print(f"[Pipeline] Auto-run check erro: {_auto_err}")

        # Buscar leads extras em background pra fila de processamento
        _qtd_extra = config.get("quantidade", 1) - 1
        if _qtd_extra > 0:
            async def _buscar_extras():
                try:
                    _existentes_agora = set()
                    with engine.connect() as _c:
                        _r = _c.execute(text("SELECT lower(trim(nome)) FROM leads WHERE lower(cidade)=lower(:c) AND user_id=:u"), {"c": state.cidade, "u": tenant_id})
                        _existentes_agora = {row[0] for row in _r.fetchall()}
                    _extras = await buscar_leads_google_maps(
                        cidade=state.cidade, segmento=state.segmento,
                        limite=_qtd_extra, leads_existentes=_existentes_agora,
                    )
                    if _extras:
                        import json as _jx
                        _agora = datetime.now().isoformat()
                        with engine.connect() as _cx:
                            for _lq in _extras:
                                _l = _lq.lead
                                _id = str(uuid.uuid4())
                                _dados = {"reviews": [{"autor": r.get("autor",""), "rating": r.get("rating",5), "texto": r.get("texto","")} for r in (_l.reviews or [])], "fotos": _l.fotos or [], "horarios": getattr(_l, "horarios", None), "servicos": getattr(_l, "servicos", None), "atributos": getattr(_l, "atributos", None)}
                                _cx.execute(text("""INSERT INTO leads (id,nome,cidade,segmento,telefone,whatsapp,rating,score,tier,status,user_id,criado_em,atualizado_em,processado,tentativas,dados_completos) VALUES (:id,:nome,:cidade,:segmento,:telefone,:whatsapp,:rating,:score,:tier,'capturado',:user_id,:criado_em,:atualizado_em,false,0,:dados_completos) ON CONFLICT DO NOTHING"""),
                                    {"id": _id, "nome": _l.nome, "cidade": _l.cidade, "segmento": _l.segmento, "telefone": _l.telefone or "", "whatsapp": _l.whatsapp or "", "rating": _l.rating or 0.0, "score": _lq.score, "tier": _lq.tier, "user_id": tenant_id, "criado_em": _agora, "atualizado_em": _agora, "dados_completos": _jx.dumps(_dados)})
                            _cx.commit()
                        print(f"[Pipeline] {len(_extras)} leads extras salvos na fila de processamento")
                except Exception as _ex:
                    logger.warning(f"[Pipeline] Busca extras erro: {_ex}")
            asyncio.create_task(_buscar_extras())

        # 3.2 — Atualizar pipeline_queue com sucesso
        if queue_id:
            try:
                with engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE pipeline_queue
                        SET status='concluido', concluido_em=NOW()
                        WHERE id=:qid
                    """), {"qid": queue_id})
                    conn.commit()
            except Exception:
                pass
        # Registrar execução concluída
        try:
            with engine.connect() as _conn_exec:
                _conn_exec.execute(text("""
                    UPDATE pipeline_executions SET finished_at=NOW(), status='completed',
                           lead_id=:lid, lead_nome=:lnome
                    WHERE user_id=:uid AND status='running'
                    AND id = (SELECT id FROM pipeline_executions WHERE user_id=:uid AND status='running' ORDER BY started_at DESC LIMIT 1)
                """), {"uid": tenant_id, "lid": state.lead_id, "lnome": state.lead_nome})
                _conn_exec.commit()
        except Exception:
            pass
        return {"sucesso": True, "site_url": state.site_url, "lead": state.lead_nome}
    except Exception as e:
        # Detectar tipo de erro e emitir SSE tipado
        from llm_direct import RateLimitError
        from services.site_health_check import HealthCheckError
        _fase_erro = None
        if isinstance(e, RateLimitError):
            _reset_min = max(1, e.reset_seconds // 60)
            emitir_erro_pipeline(tenant_id, "RATE_LIMIT",
                message=f"Servidor de IA ocupado. Retomando em ~{_reset_min}min.",
                detalhes=["O sistema retoma automaticamente quando liberar."],
                eta_seconds=e.reset_seconds, auto_retry=True)
            _log(f"⚠️ LIMITE DE USO ATINGIDO. Volte daqui {_reset_min} minuto(s).", "rate_limit")
        elif isinstance(e, HealthCheckError):
            _fase_erro = "healthcheck"
            emitir_erro_pipeline(tenant_id, "HEALTH_FAIL",
                message=f"Site gerado mas com problemas: {e.motivo}",
                detalhes=[e.detalhe] if hasattr(e, 'detalhe') else [])
            _log(f"❌ Site gerado quebrado: {e.motivo} ({e.detalhe})", "error")
        elif "NenhumLead" in type(e).__name__ or "no leads" in str(e).lower() or "nenhum lead" in str(e).lower():
            emitir_erro_pipeline(tenant_id, "NO_LEADS",
                message=str(e),
                detalhes=getattr(e, 'motivos', []) if hasattr(e, 'motivos') else [str(e)])
            _log(f"⚠️ {str(e)}", "warning")
        elif "deploy" in str(e).lower() or "nginx" in str(e).lower() or "filesystem" in str(e).lower():
            _fase_erro = "deploy"
            emitir_erro_pipeline(tenant_id, "DEPLOY_FAIL",
                message="Site gerado mas erro ao publicar no servidor.",
                detalhes=[str(e)[:200]])
            _log(f"❌ Deploy falhou: {str(e)}", "error")
        elif "scraper" in str(e).lower() or "playwright" in str(e).lower() or "google maps" in str(e).lower():
            emitir_erro_pipeline(tenant_id, "SCRAPER_FAIL",
                message="Não conseguimos buscar negócios no Google Maps.",
                detalhes=[str(e)[:200]])
            _log(f"❌ Scraper falhou: {str(e)}", "error")
        else:
            emitir_erro_pipeline(tenant_id, "LLM_FAIL",
                message="Erro na geração do site.",
                detalhes=[str(e)[:200]])
            _log(f"ERRO: {str(e)}", "error")
        logger.error(f"[Pipeline] Erro: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # 3.2 — Atualizar pipeline_queue com erro
        if queue_id:
            try:
                with engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE pipeline_queue
                        SET status='erro', concluido_em=NOW(), erro=:erro
                        WHERE id=:qid
                    """), {"qid": queue_id, "erro": str(e)[:500]})
                    conn.commit()
            except Exception:
                pass
        # Salvar lead com status erro se tiver id
        if hasattr(state, 'lead_id') and state.lead_id:
            try:
                with engine.connect() as conn:
                    conn.execute(text("UPDATE leads SET status='erro', atualizado_em=:ts WHERE id=:id AND user_id=:uid AND status NOT IN ('concluido','descartado')"),
                        {"ts": datetime.now().isoformat(), "id": state.lead_id, "uid": state.tenant_id})
                    conn.commit()
            except Exception:
                pass
        # PRD #6: Ledger — salvar com erro
        if _ledger:
            _fase_atual = _ledger.assignments.get("fase_atual", 0)
            if _fase_atual:
                _ledger.registrar_fim_fase(_fase_atual, FaseStatus.FALHOU, erro=str(e)[:200])
                _ledger.registrar_decisao(_fase_atual, "abortar_pipeline", f"Erro fatal: {str(e)[:100]}")
            print(_ledger.snapshot())
            salvar_ledger(_ledger)
        # PRD #10: Trace — salvar com erro
        if _trace:
            _cur_span = _trace.span_atual()
            if _cur_span: _cur_span.finalizar("error", erro=str(e)[:200])
            _trace.lead_nome = getattr(state, 'lead_nome', '') or ''
            _trace.finalizar("failed")
            salvar_trace(_trace)
        # Registrar execução falhada
        try:
            with engine.connect() as _conn_exec:
                _conn_exec.execute(text("""
                    UPDATE pipeline_executions SET finished_at=NOW(), status='failed'
                    WHERE user_id=:uid AND status='running'
                    AND id = (SELECT id FROM pipeline_executions WHERE user_id=:uid AND status='running' ORDER BY started_at DESC LIMIT 1)
                """), {"uid": tenant_id})
                _conn_exec.commit()
        except Exception:
            pass
        _ret = {"sucesso": False, "erro": str(e)}
        if _fase_erro:
            _ret["fase"] = _fase_erro
        return _ret




@router.get('/ciclos')
async def get_ciclos(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        tenant_id_c = usuario.get("tenant_id", usuario["id"])
        result = db.execute(text("""
            SELECT 
                id, numero, cidade, segmento,
                leads_buscados, sites_gerados, enviados, erros,
                iniciado_em, concluido_em, user_id
            FROM ciclos
            WHERE user_id = :uid
            ORDER BY id DESC
            LIMIT 100
        """), {"uid": tenant_id_c}).fetchall()
        
        ciclos = []
        for r in result:
            d = dict(r._mapping)
            leads = d['leads_buscados'] or 0
            sites = d['sites_gerados'] or 0
            conv = round(sites / leads * 100, 1) if leads > 0 else 0
            ciclos.append({
                "id": d['id'],
                "numero": d['numero'],
                "nicho": d['segmento'] or '—',
                "cidade": d['cidade'] or '—',
                "leads_buscados": leads,
                "sites_gerados": sites,
                "enviados": d['enviados'] or 0,
                "erros": d['erros'] or 0,
                "conversao": conv,
                "iniciado_em": str(d['iniciado_em'] or ''),
                "concluido_em": str(d['concluido_em'] or ''),
            })
        
        return {"ciclos": ciclos, "total": len(ciclos)}
    except Exception as e:
        print(f"[Ciclos] Erro: {e}")
        return {"ciclos": [], "total": 0}

async def executar_pipeline_multiplos(config: dict, tenant_id: int, queue_id: int = None):
    _log = lambda msg, tipo="info": adicionar_log(msg, tipo, user_id=tenant_id)
    quantidade_alvo = int(config.get("quantidade", 1))
    concluidos = 0
    tentativas = 0
    max_tentativas = max(quantidade_alvo * 5, 10)
    segmento = config.get("segmento", "")
    cidade = config.get("cidade", "")
    _log("Pipeline: buscando " + str(quantidade_alvo) + " lead(s) para " + segmento + " em " + cidade, "info")
    while concluidos < quantidade_alvo and tentativas < max_tentativas:
        tentativas += 1
        try:
            resultado = await executar_pipeline_completo(config, tenant_id, queue_id if tentativas == 1 else None)
            if resultado and resultado.get("sucesso"):
                concluidos += 1
                nome_lead = resultado.get("lead", "?")
                _log("Lead " + str(concluidos) + "/" + str(quantidade_alvo) + " concluido: " + nome_lead, "success")
                if concluidos >= quantidade_alvo:
                    break
            else:
                erro = (resultado.get("erro", "") or "") if resultado else ""
                sem_leads = any(x in erro.lower() for x in ["nenhum lead", "todos os leads", "duplicata", "sem leads"])
                if sem_leads:
                    _log("Sem mais leads disponiveis para " + segmento + " em " + cidade, "warning")
                    break
                _log("Lead nao qualificado, tentando proximo...", "warning")
        except Exception as e:
            err_str = str(e).lower()
            if any(x in err_str for x in ["nenhum lead", "todos os leads", "sem leads"]):
                _log("Sem mais leads disponiveis para " + segmento + " em " + cidade, "warning")
                break
            _log("Erro tentativa " + str(tentativas) + ": " + str(e)[:80], "warning")
    if concluidos >= quantidade_alvo:
        _log("Concluido: " + str(concluidos) + " lead(s) processado(s) com sucesso!", "success")
    elif concluidos > 0:
        _log("Encerrado: " + str(concluidos) + " de " + str(quantidade_alvo) + " leads qualificados para " + segmento + " em " + cidade + ". Tente outro nicho ou cidade.", "warning")
    else:
        _log("Nenhum lead qualificado para " + segmento + " em " + cidade + ". Tente outro nicho ou uma cidade maior.", "error")

@router.post('/iniciar')
async def iniciar_pipeline(
    request: Request,
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    try:
        config = await request.json()
        logger.info(f"[Pipeline] Dados recebidos: {config}")
    except Exception:
        config = {}
    tenant_id = usuario.get("tenant_id", usuario["id"])

    # Limites de quantidade por plano (server-side, não confia no frontend)
    _plano_row = db.execute(text("SELECT plano FROM users WHERE id=:id"), {"id": tenant_id}).fetchone()
    _plano_user = (_plano_row[0] if _plano_row else 'trial').lower()
    _MAX_QTD = {'trial': 1, 'starter': 10, 'pro': 50, 'beta': 50}
    _max_qtd = _MAX_QTD.get(_plano_user, 1)

    config_limpo = {
        "segmento": (config.get("segmento") or "").strip(),
        "cidade": (config.get("cidade") or "").strip(),
        "quantidade": min(int(config.get("quantidade") or 10), _max_qtd),
        "score_minimo": int(config.get("score_minimo") or 70),
    }

    if not config_limpo["segmento"] or not config_limpo["cidade"]:
        raise HTTPException(status_code=400, detail="Segmento e cidade são obrigatórios.")

    # Gate: WhatsApp deve estar conectado pra pipeline funcionar
    try:
        from whatsapp_listener import is_tenant_connected
        _tenant_wpp = f"fralib_user_{tenant_id}"
        if not is_tenant_connected(_tenant_wpp):
            raise HTTPException(
                status_code=428,
                detail={
                    "error": "whatsapp_not_connected",
                    "message": "Conecte seu WhatsApp antes de rodar o pipeline. Vá em Configurações > WhatsApp."
                }
            )
    except ImportError:
        pass  # Se módulo não disponível, não bloquear

    # Gate: apenas 1 pipeline por vez por tenant (com auto-reset se travou)
    _state = get_pipeline_state(db, tenant_id)
    if _state.get("rodando"):
        # Auto-reset se ficou preso por mais de 5 minutos
        _inicio = _state.get("atualizado_em") or _state.get("iniciado_em")
        _travou = False
        if _inicio:
            from datetime import datetime, timezone, timedelta
            try:
                if isinstance(_inicio, str):
                    _inicio = datetime.fromisoformat(_inicio)
                if _inicio.tzinfo is None:
                    _inicio = _inicio.replace(tzinfo=timezone.utc)
                _travou = datetime.now(timezone.utc) - _inicio > timedelta(minutes=5)
            except:
                _travou = True
        else:
            _travou = True

        if _travou:
            update_pipeline_state(db, tenant_id, rodando=False, pausado=False)
            print(f"[Pipeline] ⚠️ Auto-reset: pipeline do tenant {tenant_id} estava travado há >5min")
        else:
            raise HTTPException(status_code=429, detail="Você já tem um pipeline rodando. Aguarde a conclusão.")

    # Gate duplo: créditos diários + cooldown
    perm = validar_permissao_pipeline(db, tenant_id)
    if not perm["allowed"]:
        _status = 429 if perm.get("reason") == "cooldown" else 402
        raise HTTPException(status_code=_status, detail=perm)

    # Se processar_fila=true, processar leads capturados com seus próprios segmentos
    if config.get("processar_fila"):
        # Gate duplo já verificado acima (validar_permissao_pipeline)
        leads_fila = db.execute(text("""
            SELECT id, nome, segmento, cidade FROM leads
            WHERE user_id = :user_id AND status = 'capturado'
            ORDER BY score DESC, criado_em ASC
        """), {"user_id": tenant_id}).fetchall()
        if not leads_fila:
            return {"status": "erro", "mensagem": "Nenhum lead capturado na fila."}
        # Processar leads em sequência via background task
        lead_ids = [str(row[0]) for row in leads_fila]
        async def _processar_fila_sequencial(lead_ids, tenant_id):
            for lid in lead_ids:
                try:
                    await executar_pipeline_lead_existente(lid, tenant_id)
                except Exception as e:
                    logger.error(f"[Fila] Erro ao processar lead {lid}: {e}")
        background_tasks.add_task(_processar_fila_sequencial, lead_ids, tenant_id)
        adicionar_log(f"[Pipeline] Processando fila: {len(lead_ids)} lead(s)", "info", user_id=tenant_id)
        return {"status": "iniciado", "mensagem": f"Processando {len(lead_ids)} lead(s) da fila", "leads": len(lead_ids)}

    # Verificar fila: leads capturados mas nao processados para este segmento+cidade+usuario
    _cidade_norm = config_limpo["cidade"].lower().strip()
    _seg_norm = config_limpo["segmento"].lower().strip()
    _fila = db.execute(text("""
        SELECT COUNT(*) FROM leads
        WHERE lower(cidade) = :cidade
          AND lower(segmento) = :segmento
          AND user_id = :user_id
          AND status = 'capturado'
    """), {"cidade": _cidade_norm, "segmento": _seg_norm, "user_id": tenant_id}).scalar() or 0

    if _fila > 0:
        return {
            "status": "fila_pendente",
            "mensagem": f"Voce tem {_fila} lead(s) capturado(s) para {config_limpo['segmento']} em {config_limpo['cidade']} que ainda nao passaram pela pipeline. Processe-os antes de capturar mais.",
            "leads_na_fila": _fila,
            "config": config_limpo
        }

    # Verificar duplicatas: se lead com mesmo nome+cidade ja existe para este usuario, nao processar
    # (dedup e feito no INSERT com ON CONFLICT, mas aqui logamos para o frontend)

    state = get_pipeline_state(db, tenant_id)
    if state["rodando"]:
        raise HTTPException(400, "Pipeline ja esta rodando")
    _check_rate_limit(str(tenant_id))
    update_pipeline_state(db, tenant_id, rodando=True, pausado=False, config=config_limpo)

    # Registrar execução na pipeline_executions
    try:
        _plano_exec = _plano_user
        db.execute(text("""
            INSERT INTO pipeline_executions (user_id, status, plano_no_momento)
            VALUES (:uid, 'running', :plano)
        """), {"uid": tenant_id, "plano": _plano_exec})
        db.commit()
    except Exception:
        pass

    # Verificar se WhatsApp está conectado (não bloqueia, apenas seta flag)
    _wpp_conectado = is_tenant_connected(f"fralib_user_{tenant_id}")
    if not _wpp_conectado:
        print("[Pipeline] ⚠️ WhatsApp não conectado. O site será gerado mas o contato NÃO será enviado. Conecte o WhatsApp no painel para ativar o envio.", "warning")

    # 3.2 — Salvar job na pipeline_queue com status='em_andamento'
    queue_id = None
    try:
        result_q = db.execute(text("""
            INSERT INTO pipeline_queue
                (user_id, segmento, cidade, quantidade, score_minimo, status, iniciado_em)
            VALUES
                (:user_id, :segmento, :cidade, :quantidade, :score_minimo, 'em_andamento', NOW())
            RETURNING id
        """), {
            "user_id": tenant_id,
            "segmento": config_limpo["segmento"],
            "cidade": config_limpo["cidade"],
            "quantidade": config_limpo["quantidade"],
            "score_minimo": config_limpo["score_minimo"],
        })
        queue_id = result_q.fetchone()[0]
        db.commit()
        adicionar_log(f"[Pipeline] Job #{queue_id} registrado na fila persistente", "info", user_id=usuario["id"])
    except Exception as eq:
        print(f"[Pipeline] Aviso: nao foi possivel salvar na pipeline_queue: {eq}")

    # PR2: enfileira no job_queue (Postgres) em vez de BackgroundTasks.
    # Se enqueue falhar (banco indisponivel etc), faz fallback pra BackgroundTasks
    # pra nao quebrar o fluxo do cliente.
    import job_queue as _jq
    try:
        idem = f"pipeline-{tenant_id}-{queue_id}" if queue_id else None
        # Priority baseada no plano: Pro=1, Starter=2, Trial/Free=3
        _plano = (creditos_check.get("plano") or "").lower()
        _priority = 1 if _plano == "pro" else (2 if _plano == "starter" else 3)
        job_id = _jq.enqueue(
            db,
            tipo="pipeline_multiplos",
            payload={**config_limpo, "queue_id": queue_id},
            tenant_id=tenant_id,
            max_attempts=3,
            idempotency_key=idem,
            priority=_priority,
        )
        if job_id is None:
            # Idempotency colisao -> ja tem job equivalente rodando
            adicionar_log(f"[Pipeline] Job ja enfileirado (idem={idem})", "info", user_id=tenant_id)
            return {"status": "ja_enfileirado", "mensagem": "Pipeline ja esta na fila", "config": config_limpo, "queue_id": queue_id}
        adicionar_log(f"[Pipeline] Job #{job_id} enfileirado (queue_id={queue_id})", "info", user_id=tenant_id)
        return {"status": "iniciado", "mensagem": "Pipeline iniciado com 7 agentes", "config": config_limpo, "queue_id": queue_id, "job_id": job_id}
    except Exception as e_enq:
        logger.error(f"[Pipeline] enqueue falhou: {e_enq}")
        raise HTTPException(status_code=503, detail="Sistema de filas temporariamente indisponível. Tente novamente em alguns segundos.")


@router.get('/fila')
async def get_fila_status(usuario: dict = Depends(get_current_user)):
    """Status da fila global de pipelines — quantos rodando, quantos esperando."""
    status = pipeline_queue.status()
    tenant_id = usuario.get("tenant_id", usuario["id"])
    # Posição deste usuário na fila
    minha_posicao = None
    for entry in pipeline_queue._waiting:
        if entry.user_id == tenant_id:
            minha_posicao = entry.position
            break
    rodando_agora = tenant_id in pipeline_queue._running
    return {
        **status,
        "meu_status": "rodando" if rodando_agora else ("aguardando" if minha_posicao else "livre"),
        "minha_posicao": minha_posicao,
        "minha_espera_minutos": minha_posicao * 7 if minha_posicao else 0,
    }


@router.get('/status')
async def get_status(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    state = get_pipeline_state(db, tenant_id)

    total_leads = db.execute(text("SELECT COUNT(*) FROM leads WHERE user_id=:uid"), {"uid": tenant_id}).scalar() or 0
    total_sites = db.execute(text("SELECT COUNT(*) FROM leads WHERE user_id=:uid AND url_site IS NOT NULL AND url_site != ''"), {"uid": tenant_id}).scalar() or 0
    total_enviados = db.execute(text("SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status = 'contatado'"), {"uid": tenant_id}).scalar() or 0
    ciclo_atual = db.execute(text("SELECT COALESCE(MAX(ciclo), 0) FROM leads WHERE user_id=:uid"), {"uid": tenant_id}).scalar() or 0

    # Checkpoint info: mostrar pro user se tem progresso salvo
    _ckpt_info = None
    try:
        _cfg = state.get("config") or {}
        _pid = gerar_pipeline_id(tenant_id, _cfg.get("segmento", ""), _cfg.get("cidade", ""))
        from agents.pipeline_checkpoint import carregar_checkpoint as _load_ckpt
        _ckpt = _load_ckpt(_pid)
        if _ckpt and _ckpt.get("agentes"):
            _ckpt_info = {
                "fases_concluidas": list(_ckpt["agentes"].keys()),
                "total_fases": len(_ckpt["agentes"]),
                "ultimo_agente": _ckpt.get("ultimo_agente"),
                "atualizado_em": _ckpt.get("atualizado_em"),
            }
    except Exception:
        pass

    # Verificar último erro do pipeline (job mais recente com falha)
    _ultimo_erro = None
    try:
        _job_erro = db.execute(text("""
            SELECT erro, tipo, atualizado_em FROM pipeline_queue
            WHERE tenant_id = :uid AND status = 'erro'
            ORDER BY concluido_em DESC LIMIT 1
        """), {"uid": tenant_id}).fetchone()
        if _job_erro and _job_erro[0]:
            _erro_msg = str(_job_erro[0])[:200]
            _recomendacao = "Tente novamente. Se persistir, entre em contato com o suporte."
            if "Nenhum lead qualificado" in _erro_msg:
                _recomendacao = "Tente outro segmento ou uma cidade maior com mais negócios."
            elif "reviews" in _erro_msg.lower() or "depoimentos" in _erro_msg.lower():
                _recomendacao = "Os negócios dessa região não têm avaliações suficientes. Tente outra cidade."
            elif "timeout" in _erro_msg.lower() or "connection" in _erro_msg.lower():
                _recomendacao = "Erro de conexão temporário. Atualize a página e tente novamente."
            _ultimo_erro = {
                "mensagem": _erro_msg,
                "recomendacao": _recomendacao,
                "quando": _job_erro[2].isoformat() if _job_erro[2] else None,
            }
    except Exception:
        pass

    # Cooldown info para o frontend (usa ultimo_deploy_at)
    _cooldown_info = None
    try:
        _user_row = db.execute(text("SELECT plano, ultimo_deploy_at FROM users WHERE id=:id"), {"id": tenant_id}).fetchone()
        _plano = (_user_row[0] if _user_row else "trial") or "trial"
        _cd_secs = _COOLDOWN_POR_PLANO.get(_plano, 3600)
        _fila_count = db.execute(text("SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status='capturado'"), {"uid": tenant_id}).scalar() or 0
        if _cd_secs > 0 and _user_row and _user_row[1]:
            from datetime import datetime as _dtx, timezone as _tzx, timedelta as _tdx
            _BRT = _tzx(_tdx(hours=-3))
            _last_ts = _user_row[1]
            if _last_ts.tzinfo is None:
                _last_ts = _last_ts.replace(tzinfo=_tzx.utc)
            _elapsed = (_dtx.now(_BRT) - _last_ts.astimezone(_BRT)).total_seconds()
            _restante = max(0, int(_cd_secs - _elapsed))
            _cooldown_info = {
                "plano": _plano,
                "cooldown_total": _cd_secs,
                "cooldown_restante": _restante,
                "bloqueado": _restante > 0,
                "leads_na_fila": _fila_count,
                "auto_run": _fila_count > 0 and _restante > 0,
            }
        elif _cd_secs > 0:
            _cooldown_info = {"plano": _plano, "cooldown_total": _cd_secs, "cooldown_restante": 0, "bloqueado": False, "leads_na_fila": _fila_count, "auto_run": False}
        else:
            _cooldown_info = {"plano": _plano, "cooldown_total": 0, "cooldown_restante": 0, "bloqueado": False, "leads_na_fila": _fila_count, "auto_run": False}
    except Exception:
        pass

    return {
        "rodando": state["rodando"],
        "pausado": state["pausado"],
        "config": state["config"],
        "iniciado_em": state.get("iniciado_em").isoformat() if state.get("iniciado_em") else None,
        "totalLeads": total_leads,
        "totalSites": total_sites,
        "totalEnviados": total_enviados,
        "cicloAtual": ciclo_atual,
        "checkpoint": _ckpt_info,
        "ultimo_erro": _ultimo_erro,
        "cooldown": _cooldown_info,
    }


@router.post('/parar')
async def parar_pipeline(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    update_pipeline_state(db, tenant_id, rodando=False, pausado=False)
    return {"status": "parado"}


@router.post('/reset')
async def reset_pipeline(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    update_pipeline_state(db, tenant_id, rodando=False, pausado=False)
    logger.info(f"[Pipeline] Reset forcado para tenant {tenant_id}")
    return {"status": "resetado", "mensagem": "Pipeline resetado com sucesso"}



@router.post('/pausar')
async def pausar_pipeline(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    update_pipeline_state(db, tenant_id, pausado=True)
    adicionar_log("Pipeline pausado pelo usuario", "warning", user_id=tenant_id)
    return {"status": "pausado"}

@router.post('/retomar')
async def retomar_pipeline(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    update_pipeline_state(db, tenant_id, pausado=False)
    adicionar_log("Pipeline retomado pelo usuario", "info", user_id=tenant_id)
    return {"status": "retomado"}

@router.post('/arquivar-tudo')
async def arquivar_tudo(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    try:
        result = db.execute(text(
            "UPDATE leads SET status='arquivado', atualizado_em=:ts WHERE user_id=:uid AND status != 'arquivado'"
        ), {"uid": tenant_id, "ts": datetime.now().isoformat()})
        db.commit()
        count = result.rowcount
        adicionar_log(f"{count} leads arquivados", "info", user_id=tenant_id)
        return {"ok": True, "message": f"{count} leads arquivados com sucesso"}
    except Exception as e:
        raise HTTPException(500, str(e))

async def executar_pipeline_lead_existente(lead_id: str, tenant_id: int, forcar_renovacao: bool = False):
    """Pipeline de site para lead já existente no banco — pula o hunter."""
    _log = lambda msg, tipo="info": adicionar_log(msg, tipo, user_id=tenant_id)

    # Verificar permissão (créditos + cooldown) antes de executar
    with SessionLocal() as _db_check:
        _perm = validar_permissao_pipeline(_db_check, tenant_id)
        if not _perm["allowed"]:
            _msg = _perm.get("message", "Bloqueado")
            _log(f"Pipeline bloqueado: {_msg}", "warning")
            logger.info(f"[Pipeline] Lead {lead_id} bloqueado — {_perm.get('reason', '?')} (tenant={tenant_id})")
            return

    _log("Iniciando reprocessamento...", "info")
    import json as _json
    from utils.agente1_hunter_v2 import LeadRaw, LeadQualificado

    # Carregar lead do banco — valida ownership pelo tenant_id
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM leads WHERE id=:id AND user_id=:uid"),
            {"id": lead_id, "uid": tenant_id},
        ).fetchone()
        if not row:
            logger.error(f"[Pipeline] Lead {lead_id} nao encontrado ou nao pertence ao usuario {tenant_id}")
            return
        lead_dict = dict(row._mapping)

    nome = lead_dict.get("nome", "")
    cidade = lead_dict.get("cidade", "")
    segmento = lead_dict.get("segmento", "")

    # Guard: inferir segmento pelo nome quando o Hunter capturou o segmento da busca em vez do real
    # Ex: "Nutricionista Carolina Ribeiro" com segmento="Academia" no banco
    _SEGMENTOS_NOME = [
        "nutricionista", "dentista", "psicologo", "psicologa", "advogado", "advogada",
        "contador", "contadora", "arquiteto", "arquiteta", "fotografo", "fotografa",
        "medico", "medica", "fisioterapeuta", "veterinario", "veterinaria",
        "fonoaudiologo", "fonoaudiologa", "terapeuta", "esteticista",
    ]
    _nome_lower = nome.lower()
    for _seg_c in _SEGMENTOS_NOME:
        if _seg_c in _nome_lower:
            _seg_inferido = _seg_c.capitalize()
            if _seg_inferido.lower() != segmento.lower():
                logger.info(f"[Pipeline] Segmento corrigido pelo nome: '{_seg_inferido}' (era '{segmento}')")
                segmento = _seg_inferido
            break
    dados = lead_dict.get("dados_completos") or {}
    if isinstance(dados, str):
        try: dados = _json.loads(dados)
        except: dados = {}

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
    _reviews_raw = list(lead_raw.reviews or [])
    state.lead_raw_data = {
        "nome": nome, "cidade": cidade, "segmento": segmento,
        "telefone": lead_raw.telefone or "",
        "whatsapp": lead_raw.whatsapp or "",
        "rating": lead_raw.rating or 0.0,
        "reviews": _reviews_raw,
        "total_avaliacoes": lead_raw.total_avaliacoes or len(_reviews_raw),
        "fotos": fotos,
        "website": lead_raw.website or "",
        "logo_url": lead_dict.get("logo_url") or dados.get("logo_url") or "",
        "horarios": lead_raw.horarios or [],
        "atributos": lead_raw.atributos or [],
        "servicos": lead_raw.servicos or [],
        "endereco": lead_raw.endereco or "",
    }
    _log(f"[Reprocessar] Lead: {nome} ({cidade})", "info")

    # Substituir fotos reais por Unsplash — zero fotos do Google Maps no HTML
    try:
        from agents.unsplash_fetcher import buscar_fotos_unsplash as _buscar_unsplash
        import asyncio as _asyncio
        _loop = _asyncio.get_event_loop()
        _fotos_unsplash = await _loop.run_in_executor(
            None, lambda: _buscar_unsplash(segmento, quantidade=8, nome=nome, cidade=cidade)
        )
        state.lead_raw_data["fotos"] = _fotos_unsplash
        state.lead_raw_data["logo_url"] = None
        _log(f"  Fotos Unsplash: {len(_fotos_unsplash)}", "success")
    except Exception as _e:
        logger.warning(f"[Pipeline] Unsplash erro no reprocessar: {_e}")
        state.lead_raw_data["fotos"] = []
        state.lead_raw_data["logo_url"] = None

    # Forcar renovacao: invalidar caches de Jina e keyword_research
    if forcar_renovacao:
        import hashlib, os as _os
        _cache_key = hashlib.md5((segmento.lower() + cidade.lower()).encode()).hexdigest()[:12]
        _jina_file = f"/root/fralib/backend/agents/jina_cache/jina_{_cache_key}.txt"
        if _os.path.exists(_jina_file):
            _os.remove(_jina_file)
            _log("  Cache Jina invalidado", "info")
        try:
            from core.database import engine as _eng
            with _eng.connect() as _kc:
                _kc.execute(text("DELETE FROM keyword_cache WHERE segmento=:s AND cidade=:c"),
                            {"s": segmento.lower(), "c": cidade.lower()})
                _kc.commit()
            _log("  Cache Keywords invalidado", "info")
        except Exception as _kce:
            logger.warning(f"[Pipeline] Erro ao invalidar keyword cache: {_kce}")

    # Pular FASE 1 (hunter) e ir direto para FASE 2+
    # Reusar executar_pipeline_completo a partir da FASE 2
    # Injetar state no pipeline via config especial
    config["_lead_existente"] = True
    config["_lead_id_existente"] = lead_id
    await _executar_pipeline_a_partir_fase2(state, tenant_id, config)


async def _executar_pipeline_a_partir_fase2(state, tenant_id, config):
    """Executa o pipeline a partir da FASE 2 com state já populado."""
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

        # Keyword research — usa cache 30 dias, não bloqueia se falhar
        if not state.keyword_research:
            try:
                from agents.keyword_research import pesquisar_keywords_nicho
                state.keyword_research = pesquisar_keywords_nicho(
                    state.lead_obj.lead.segmento, state.lead_obj.lead.cidade
                )
                _log("  Keywords: OK (cache)", "success")
            except Exception as _kwe:
                logger.warning(f"[Pipeline] Keyword research erro: {_kwe}")

        # Caio: pular se já qualificado (reprocessamento)
        if not state.qualificacao_caio:
            from agents.caio import CaioOutput
            state.qualificacao_caio = CaioOutput(
                qualificado=True,
                qualificacao="QUENTE",
                tier=state.lead_obj.tier or "STANDARD",
                score=state.lead_obj.score or 50,
                motivo="Reprocessamento — qualificação anterior mantida",
            )
        state.alex_result = None
        _log(f"  Caio: {state.qualificacao_caio.qualificacao} (tier={state.qualificacao_caio.tier})", "info")

        # Theo
        # Theo REMOVIDO — pipeline atual não usa mais
        state.briefing_theo = f"Site para {state.lead_nome} em {state.lead_obj.lead.cidade}."

        # Jina insights
        _log("FASE 3: JINA", "info")
        try:
            state.jina_insights = pesquisar_referencias_jina(state.lead_obj.lead.segmento)
        except Exception as e:
            state.jina_insights = ""
            logger.warning(f"[Pipeline] Jina erro: {e}")

        # Cores: design_context.py e a fonte unica de verdade (tokens OKLch)
        # paleta_nicho removido — ArquitetoMestre usa design_context diretamente

        # Curadoria
        reviews_raw = state.lead_raw_data.get("reviews", [])
        if len(reviews_raw) > 5:
            state.lead_raw_data["reviews"] = sorted(reviews_raw, key=lambda r: len(str(r.get("texto", r.get("text", "")))), reverse=True)[:5]
        if len(state.jina_insights) > 5000:
            state.jina_insights = state.jina_insights[:5000]
        import urllib.parse as _urlparse
        _osm_query = _urlparse.quote(state.lead_nome + ", " + state.lead_obj.lead.cidade)
        state.lead_raw_data["google_maps_embed"] = f'<iframe width="100%" height="450" style="border:0;" loading="lazy" src="https://www.openstreetmap.org/export/embed.html?bbox=-60,-35,-30,-5&layer=mapnik&query={_osm_query}"></iframe>'

        # Arquiteto Mestre
        _log("FASE 6: ARQUITETO MESTRE", "info")
        _seed = int(hashlib.md5(state.lead_nome.encode()).hexdigest()[:8], 16)
        random.seed(_seed)
        # Refinar segmento pelo nome (ex: "churrascaria" no nome)
        _nome_lower_r = state.lead_nome.lower()
        _SUB_SEG_R = {"churrascaria": "churrascaria", "steakhouse": "churrascaria", "pizzaria": "pizzaria", "padaria": "padaria", "lanchonete": "lanchonete", "barbearia": "barbearia"}
        for _kw_r, _seg_r in _SUB_SEG_R.items():
            if _kw_r in _nome_lower_r and state.segmento != _seg_r:
                _log(f"  Segmento refinado: {state.segmento} → {_seg_r}", "info")
                state.segmento = _seg_r
                break
        _seg = state.segmento or state.lead_obj.lead.segmento or "negocio local"
        _cid = state.lead_obj.lead.cidade or state.cidade or ""
        _dark_mode = state.segmento in ("academia", "crossfit", "churrascaria", "barbearia")
        _prd_fn2 = _gerar_prd_agent if _ARQUITETO_AGENT else gerar_arquiteto_mestre_prd
        state.prd_arquiteto = _prd_fn2(
            dados_hunter=state.lead_raw_data,
            cidade=_cid,
            segmento=_seg,
            jina_insights=state.jina_insights,
            briefing_theo=state.briefing_theo,
            caio_tier=state.qualificacao_caio.tier if state.qualificacao_caio else "STANDARD",
            caio_score=state.qualificacao_caio.score if state.qualificacao_caio else 0,
            caio_motivo=state.qualificacao_caio.motivo if state.qualificacao_caio else "",
            dark_mode=_dark_mode,
            keyword_research=state.keyword_research,
        )

        # Liam
        _log("FASE 7: LIAM", "info")
        from agents.liam import gerar_html_componentizado, montar_template_python, critique_theater_pass
        _html_main = gerar_html_componentizado(state.prd_arquiteto)
        state.html_final = montar_template_python(_html_main, state.prd_arquiteto)
        state.html_final = critique_theater_pass(state.html_final)
        logger.info(f"[Pipeline] Liam: OK | {len(state.html_final):,} chars")

        # Liz
        _log("FASE 8: LIZ", "info")
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

        # Deploy
        _log("FASE 9: DEPLOY", "info")
        web_dir = f"/var/www/fralib/sites/{tenant_id}/{state.lead_slug}"
        os.makedirs(web_dir, exist_ok=True)
        # PR15: substituir placeholder do pixel de tracking pelo lead_id real
        if hasattr(state, 'lead_id') and state.lead_id:
            state.html_final = state.html_final.replace("__FRALIB_LEAD_ID__", str(state.lead_id))
        with open(f"{web_dir}/index.html", "w", encoding="utf-8") as _f:
            _f.write(state.html_final)
        if state.alex_result and state.alex_result.assets_dir:
            assets_src = os.path.realpath(state.alex_result.assets_dir)
            assets_dst = os.path.realpath(f"{web_dir}/assets")
            if assets_src == assets_dst:
                print(f"[Pipeline] Assets já no lugar: {assets_dst}")
            elif os.path.exists(assets_src):
                import shutil
                if os.path.exists(assets_dst):
                    shutil.rmtree(assets_dst)
                shutil.copytree(assets_src, assets_dst)
        import subprocess as _sp
        _sp.run(["chown", "-R", "www-data:www-data", web_dir], check=False)
        _sp.run(["chmod", "-R", "755", web_dir], check=False)
        state.site_url = f"https://seunegociofralib.site/sites/{tenant_id}/{state.lead_slug}/"
        _log(f"  Deploy: {state.site_url}", "success")

        # Salvar no banco
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE leads SET
                    processado=true, site_url=:url, url_site=:url,
                    atualizado_em=:ts, pipeline_stage='concluido',
                    html_gerado=:html
                WHERE id=:id AND user_id=:uid
            """), {
                "url": state.site_url, "ts": datetime.now().isoformat(),
                "html": state.html_final[:50000], "id": state.lead_id,
                "uid": state.tenant_id,
            })
            conn.commit()

        # Bryan
        _log("FASE 10: BRYAN", "info")
        try:
            bryan_input = BryanInput(
                nome=state.lead_nome, cidade=state.lead_obj.lead.cidade,
                segmento=state.lead_obj.lead.segmento,
                telefone=state.lead_obj.lead.telefone or "",
                whatsapp=state.lead_obj.lead.whatsapp or "",
                rating=state.lead_obj.lead.rating or 0.0,
                site_url=state.site_url,
                score_caio=state.qualificacao_caio.score if state.qualificacao_caio else 0,
                tier=state.qualificacao_caio.tier if state.qualificacao_caio else "STANDARD",
                proof=state.qualificacao_caio.razoes[0] if state.qualificacao_caio and getattr(state.qualificacao_caio, 'razoes', None) else None,
                concorrentes=getattr(state, 'concorrentes', None),
            )
            bryan_result = iniciar_contato(bryan_input, user_id=state.tenant_id)
            logger.info(f"[Pipeline] Bryan: OK | msg={str(bryan_result)[:60]}")
        except Exception as e:
            logger.warning(f"[Pipeline] Bryan erro: {e}")

        _log(f"Pipeline concluído: {state.site_url}", "success")
        logger.info(f"[Pipeline] Reprocessar concluído: {state.site_url}")

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


@router.post('/reprocessar/{lead_id}')
async def reprocessar_lead(lead_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), usuario: dict = Depends(get_current_user), forcar_renovacao: bool = False):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    # Gate duplo: créditos + cooldown
    _perm = validar_permissao_pipeline(db, tenant_id)
    if not _perm["allowed"]:
        _status = 429 if _perm.get("reason") == "cooldown" else 402
        raise HTTPException(status_code=_status, detail=_perm)
    lead = db.execute(text("SELECT * FROM leads WHERE id=:id AND user_id=:uid"), {"id": lead_id, "uid": tenant_id}).fetchone()
    if not lead:
        raise HTTPException(404, "Lead nao encontrado")
    db.execute(text("UPDATE leads SET status='capturado', processado=false, atualizado_em=:ts WHERE id=:id AND user_id=:uid"),
               {"ts": datetime.now().isoformat(), "id": lead_id, "uid": tenant_id})
    db.commit()
    _renovacao_label = " (renovacao forcada)" if forcar_renovacao else ""
    adicionar_log(f"Lead {lead.nome} reprocessando{_renovacao_label}...", "info", user_id=tenant_id)
    # Enfileirar como job normal no worker — usa pipeline principal com flag pra pular Hunter+Caio
    import job_queue as _jq
    config_reproc = {
        "segmento": lead.segmento or "",
        "cidade": lead.cidade or "",
        "quantidade": 1,
        "_lead_id_existente": lead_id,
        "_forcar_renovacao": forcar_renovacao,
    }
    try:
        job_id = _jq.enqueue(
            db, tipo="pipeline_lead",
            payload={**config_reproc},
            tenant_id=tenant_id, max_attempts=3, priority=1,
        )
        if job_id:
            adicionar_log(f"[Pipeline] Reprocessamento enfileirado (job #{job_id})", "info", user_id=tenant_id)
        else:
            background_tasks.add_task(executar_pipeline_lead_existente, lead_id, tenant_id, forcar_renovacao=forcar_renovacao)
    except Exception as _e:
        print(f"[Reprocessar] Enqueue falhou: {_e}")
        background_tasks.add_task(executar_pipeline_lead_existente, lead_id, tenant_id, forcar_renovacao=forcar_renovacao)
    return {"ok": True, "mensagem": "Lead marcado para reprocessamento"}

@router.get('/fila-reprocessamento')
async def fila_reprocessamento(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    leads = db.execute(text(
        "SELECT id, nome, cidade, segmento, rating, score, tier FROM leads WHERE user_id=:uid AND status='capturado' ORDER BY criado_em DESC"
    ), {"uid": tenant_id}).fetchall()
    return {"leads": [dict(r._mapping) for r in leads], "total": len(leads)}

@router.get('/analytics/overview')
async def get_analytics(periodo: str = 'mes', db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    from datetime import datetime, timedelta

    agora = datetime.now()
    if periodo == 'hoje':
        inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == 'semana':
        inicio = agora - timedelta(days=7)
    elif periodo == 'mes':
        inicio = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif periodo == 'ano':
        inicio = agora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        inicio = None

    tenant_id_a = usuario.get("tenant_id", usuario["id"])
    if inicio:
        where = 'WHERE user_id = :uid AND criado_em >= :inicio'
        and_clause = 'AND'
        params = {'uid': tenant_id_a, 'inicio': inicio.isoformat()}
    else:
        where = 'WHERE user_id = :uid'
        and_clause = 'AND'
        params = {'uid': tenant_id_a}

    total_leads = db.execute(text(f'SELECT COUNT(*) FROM leads {where}'), params).scalar() or 0
    total_sites = db.execute(text(f"SELECT COUNT(*) FROM leads {where} AND url_site IS NOT NULL AND url_site != ''"), params).scalar() or 0
    total_vendidos = db.execute(text(f"SELECT COUNT(*) FROM leads {where} AND valor_venda > 0"), params).scalar() or 0
    receita = db.execute(text(f"SELECT COALESCE(SUM(valor_venda),0) FROM leads {where} AND valor_venda > 0"), params).scalar() or 0

    conversao_site = round((total_sites / total_leads * 100), 1) if total_leads > 0 else 0
    conversao_venda = round((total_vendidos / total_sites * 100), 1) if total_sites > 0 else 0

    sql_por_dia = (
        'SELECT DATE(criado_em::timestamp) as dia, COUNT(*) as total '
        'FROM leads '
        "WHERE user_id = :uid AND criado_em IS NOT NULL AND criado_em != '' "
        'GROUP BY dia ORDER BY dia DESC LIMIT 30'
    )
    leads_por_dia_rows = db.execute(text(sql_por_dia), {'uid': tenant_id_a}).fetchall()

    sql_cidades = f'SELECT cidade, COUNT(*) as total FROM leads {where} GROUP BY cidade ORDER BY total DESC LIMIT 8'
    top_cidades_rows = db.execute(text(sql_cidades), params).fetchall()

    sql_nichos = f'SELECT segmento, COUNT(*) as total FROM leads {where} GROUP BY segmento ORDER BY total DESC LIMIT 8'
    top_nichos_rows = db.execute(text(sql_nichos), params).fetchall()

    total_ciclos = db.execute(text('SELECT COUNT(*) FROM ciclos WHERE user_id = :uid'), {'uid': tenant_id_a}).scalar() or 0

    return {
        'periodo': periodo,
        'total_leads': total_leads,
        'total_sites': total_sites,
        'total_vendidos': total_vendidos,
        'receita': float(receita),
        'conversao': conversao_site,
        'conversao_venda': conversao_venda,
        'total_ciclos': total_ciclos,
        'leads_qualificados': total_sites,
        'taxa_conversao': conversao_site,
        'por_dia': [{'dia': str(r.dia), 'total': r.total} for r in leads_por_dia_rows],
        'por_cidade': [{'nome': r.cidade or '-', 'total': r.total} for r in top_cidades_rows],
        'por_nicho': [{'nome': r.segmento or '-', 'total': r.total} for r in top_nichos_rows],
    }



@router.get('/stats')
async def get_stats(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    try:
        uid = usuario.get("tenant_id", usuario["id"])
        total_com_site = db.execute(text("SELECT COUNT(*) FROM leads WHERE user_id=:uid AND url_site IS NOT NULL AND url_site != ''"), {"uid": uid}).scalar() or 0
        total_respondeu = db.execute(text("SELECT COUNT(DISTINCT i.lead_nome) FROM interacoes i JOIN leads l ON l.nome=i.lead_nome WHERE l.user_id=:uid AND i.direcao='entrada'"), {"uid": uid}).scalar() or 0
        taxa_resposta = round(total_respondeu / total_com_site * 100, 1) if total_com_site > 0 else 0

        nicho_top = db.execute(text("""
            SELECT segmento,
                   COUNT(CASE WHEN url_site IS NOT NULL AND url_site != '' THEN 1 END) * 100.0 / COUNT(*) as conv
            FROM leads
            WHERE user_id = :uid AND segmento IS NOT NULL AND segmento != ''
            GROUP BY segmento
            HAVING COUNT(*) >= 3
            ORDER BY conv DESC
            LIMIT 1
        """), {"uid": uid}).fetchone()

        cidade_top = db.execute(text("""
            SELECT cidade, COUNT(*) as total
            FROM leads
            WHERE user_id = :uid AND cidade IS NOT NULL AND cidade != ''
            GROUP BY cidade
            ORDER BY total DESC
            LIMIT 1
        """), {"uid": uid}).fetchone()

        ticket_medio = db.execute(text("SELECT COALESCE(AVG(valor_venda), 0) FROM leads WHERE user_id=:uid AND valor_venda > 0"), {"uid": uid}).scalar() or 0
        total_msgs = db.execute(text("SELECT COUNT(*) FROM interacoes i JOIN leads l ON l.nome=i.lead_nome WHERE l.user_id=:uid AND i.direcao='saida'"), {"uid": uid}).scalar() or 0

        return {
            "taxa_resposta": taxa_resposta,
            "nicho_top": nicho_top.segmento if nicho_top else "—",
            "nicho_top_conv": round(nicho_top.conv, 1) if nicho_top else 0,
            "cidade_top": cidade_top.cidade if cidade_top else "—",
            "cidade_top_total": cidade_top.total if cidade_top else 0,
            "ticket_medio": float(ticket_medio),
            "total_msgs_bryan": total_msgs,
        }
    except Exception as e:
        print(f"[Stats] Erro: {e}")
        return {
            "taxa_resposta": 0, "nicho_top": "—", "nicho_top_conv": 0,
            "cidade_top": "—", "cidade_top_total": 0, "ticket_medio": 0, "total_msgs_bryan": 0
        }
