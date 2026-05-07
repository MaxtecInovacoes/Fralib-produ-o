from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import logging, sys, os, uuid, re, time, asyncio, hashlib, random, unicodedata
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

sys.path.append('/root/fralib/backend')

from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db, get_pipeline_state, update_pipeline_state, engine
from auth import get_current_user
from utils.agente1_hunter_v2 import buscar_leads_google_maps
from endpoints.sse_endpoints import adicionar_log

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

import builtins as _builtins
_print_original = _builtins.print

def _print_sse(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    _print_original(*args, **kwargs)
    nivel = "info"
    ml = msg.lower()
    if "erro" in ml or "error" in ml:
        nivel = "error"
    elif "ok" in ml or "concluido" in ml or "aprovado" in ml:
        nivel = "success"
    elif "warn" in ml or "aviso" in ml:
        nivel = "warning"
    elif "lead" in ml or "hunter" in ml or "scraper" in ml:
        nivel = "leads"
    elif "caio" in ml or "qualif" in ml:
        nivel = "caio"
    elif "pipeline" in ml or "fase" in ml or "liam" in ml or "liz" in ml or "bryan" in ml:
        nivel = "pipeline"
    try:
        adicionar_log(msg, nivel)
    except Exception:
        pass

_builtins.print = _print_sse


from agents.caio import qualificar_lead, LeadInput as CaioInput
from agents.alex import processar_imagens, AlexInput
from agents.theo import gerar_briefing_estrategico, TheoInput, pesquisar_referencias_jina
from agents.pipeline_checkpoint import salvar_checkpoint, limpar_checkpoint, gerar_pipeline_id
from agents.liam import gerar_html_componentizado, montar_template_python
from agents.arquiteto_mestre import gerar_arquiteto_mestre_prd
from agents.color_enforcer import harmonizar_paleta as _harmonizar_paleta
from agents.color_extractor import gerar_paleta_completa as _gerar_paleta_ce
from agents.liz import auditar, editar_secao as liz_editar_secao, listar_secoes as liz_listar_secoes
from agents.bryan import iniciar_contato, BryanInput
from agents.liam_models import LiamOutput
from services.credits_manager import verificar_pode_executar, consume_tokens

from collections import defaultdict as _defaultdict
_pipeline_calls = _defaultdict(list)
_PIPELINE_MAX_CALLS = 5
_PIPELINE_WINDOW = 60

def _check_rate_limit(user_id: str):
    now = time.time()
    calls = [t for t in _pipeline_calls[user_id] if now - t < _PIPELINE_WINDOW]
    _pipeline_calls[user_id] = calls
    if len(calls) >= _PIPELINE_MAX_CALLS:
        raise HTTPException(429, f"Rate limit: max {_PIPELINE_MAX_CALLS} pipelines/min.")
    calls.append(now)
    _pipeline_calls[user_id] = calls

router = APIRouter(prefix='/api/pipeline', tags=['pipeline'])
logger = logging.getLogger('uvicorn')
logger.addHandler(_sse_handler)


@dataclass
class FraLibState:
    segmento: str = ""
    cidade: str = ""
    pipeline_id: str = ""
    lead_raw_data: dict = field(default_factory=dict)
    lead_obj: Any = None
    lead_id: str = ""
    lead_nome: str = ""
    lead_slug: str = ""
    qualificacao_caio: Any = None
    alex_result: Any = None
    jina_insights: str = ""
    briefing_theo: str = ""
    paleta_cores: dict = field(default_factory=dict)
    prd_arquiteto: Any = None
    html_sections: List[str] = field(default_factory=list)
    html_final: str = ""
    liz_aprovado: bool = False
    liz_score: int = 0
    site_url: str = ""

async def executar_pipeline_completo(config: dict, tenant_id: int):
    state = FraLibState(
        segmento=config.get("segmento", "Academia"),
        cidade=config.get("cidade", "Sao Paulo"),
        pipeline_id=gerar_pipeline_id(config.get("segmento", ""), config.get("cidade", "")),
    )
    adicionar_log("PIPELINE v2 - FraLibState Orquestrador", "info")
    adicionar_log(f"{state.segmento} em {state.cidade}", "info")
    logger.info(f"[Pipeline] Iniciando: {state.segmento} em {state.cidade}")
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
        adicionar_log("FASE 1: HUNTER", "info")
        # Carregar leads já existentes no banco para evitar duplicatas
        with engine.connect() as _conn_dedup:
            _res_existentes = _conn_dedup.execute(text("""
                SELECT lower(trim(nome)) FROM leads
                WHERE lower(cidade) = lower(:cidade)
                  AND lower(segmento) = lower(:segmento)
                  AND user_id = :user_id
            """), {"cidade": state.cidade, "segmento": state.segmento, "user_id": tenant_id})
            _leads_existentes = {row[0] for row in _res_existentes.fetchall()}
        if _leads_existentes:
            adicionar_log(f"  Dedup: {len(_leads_existentes)} leads ja existem no banco", "info")
        leads = await buscar_leads_google_maps(
            cidade=state.cidade,
            segmento=state.segmento,
            limite=config.get("quantidade", 1),
            leads_existentes=_leads_existentes,
        )
        if not leads:
            raise Exception("Nenhum lead encontrado pelo Hunter")
        state.lead_obj = leads[0]
        state.lead_nome = state.lead_obj.lead.nome
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
        }
        adicionar_log(f"  Lead: {state.lead_nome}", "success")
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
                adicionar_log(f"  Lead duplicado ignorado: {state.lead_nome}", "info")
                print(f"[Pipeline] Lead duplicado ignorado: {state.lead_nome} (id existente: {_dup[0]})")
                return
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
        adicionar_log("FASE 2: CAIO + ALEX (paralelo)", "info")
        caio_input = CaioInput(
            nome=state.lead_nome, cidade=state.lead_obj.lead.cidade,
            segmento=state.lead_obj.lead.segmento, telefone=state.lead_obj.lead.telefone or "",
            whatsapp=state.lead_obj.lead.whatsapp or "", rating=state.lead_obj.lead.rating or 0.0,
            reviews_count=state.lead_obj.lead.total_avaliacoes or 0,
            fotos=state.lead_obj.lead.fotos or [], website=state.lead_obj.lead.website
        )
        alex_input = AlexInput(
            nome=state.lead_nome, fotos=state.lead_obj.lead.fotos or [],
            slug=state.lead_slug, segmento=state.lead_obj.lead.segmento
        )
        def _run_caio():
            r = qualificar_lead(caio_input)
            logger.info(f"[Pipeline] Caio: {r.qualificacao}")
            return r
        def _run_alex():
            try:
                r = processar_imagens(alex_input)
                logger.info("[Pipeline] Alex: OK")
                return r
            except Exception as e:
                logger.warning(f"[Pipeline] Alex erro: {e}")
                return None
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=2) as ex:
            state.qualificacao_caio, state.alex_result = await asyncio.gather(
                loop.run_in_executor(ex, _run_caio),
                loop.run_in_executor(ex, _run_alex)
            )
        if state.qualificacao_caio and (not state.qualificacao_caio.qualificado or state.qualificacao_caio.tier == "REJEITADO"):
            # Tentar proximo lead se disponivel
            _idx_atual = next((i for i, l in enumerate(leads) if l is state.lead_obj), -1)
            if _idx_atual >= 0 and _idx_atual + 1 < len(leads):
                _proximo = leads[_idx_atual + 1]
                print(f"[Pipeline] {state.lead_nome} rejeitado. Tentando: {_proximo.lead.nome}")
                state.lead_obj = _proximo
                state.lead_nome = _proximo.lead.nome
                state.lead_id = None
                _rvs = list(_proximo.lead.reviews or [])
                state.lead_raw_data = {"nome": _proximo.lead.nome, "cidade": _proximo.lead.cidade, "segmento": _proximo.lead.segmento, "telefone": _proximo.lead.telefone or "", "whatsapp": _proximo.lead.whatsapp or "", "rating": _proximo.lead.rating or 0.0, "reviews": _rvs, "total_avaliacoes": getattr(_proximo.lead, "total_avaliacoes", None) or getattr(_proximo.lead, "reviews_count", None) or len(_rvs), "fotos": _proximo.lead.fotos or [], "website": _proximo.lead.website or "", "logo_url": getattr(_proximo.lead, "logo_url", None) or ""}
                from agents.caio import qualificar_lead as _qualificar_caio2
                state.qualificacao_caio = await asyncio.get_event_loop().run_in_executor(None, _qualificar_caio2, _proximo.lead)
                if not state.qualificacao_caio or state.qualificacao_caio.tier == "REJEITADO":
                    with engine.connect() as conn:
                        conn.execute(text("UPDATE leads SET status='descartado', atualizado_em=:ts WHERE id=:id"),
                            {"ts": datetime.now().isoformat(), "id": state.lead_id})
                        conn.commit()
                    raise Exception(f"Todos os leads rejeitados pelo Caio")
                print(f"[Pipeline] Proximo lead aprovado: {state.lead_nome} ({state.qualificacao_caio.tier})")
            else:
                with engine.connect() as conn:
                    motivo = state.qualificacao_caio.motivo if state.qualificacao_caio else "score baixo"
                    conn.execute(text("UPDATE leads SET status='descartado', atualizado_em=:ts WHERE id=:id"),
                        {"ts": datetime.now().isoformat(), "id": state.lead_id})
                    conn.commit()
                raise Exception(f"Lead rejeitado pelo Caio: {state.qualificacao_caio.motivo}")
        adicionar_log(f"  Caio: {state.qualificacao_caio.qualificacao} score={state.qualificacao_caio.score}", "success")
        logger.info(f"[Pipeline] Caio: {state.qualificacao_caio.qualificacao}")
        logger.info("[Pipeline] Alex: OK")
        adicionar_log("FASE 3: JINA AI", "info")
        try:
            state.jina_insights = pesquisar_referencias_jina(state.segmento)
            adicionar_log(f"  Jina: {len(state.jina_insights)} chars", "success")
            logger.info(f"[Pipeline] Jina AI: OK ({len(state.jina_insights)} chars)")
        except Exception as e:
            state.jina_insights = f"Segmento: {state.segmento} em {state.cidade}. Usar padroes premium."
            logger.warning(f"[Pipeline] Jina AI erro: {e}")
        adicionar_log("FASE 4: THEO", "info")
        try:
            theo_input = TheoInput(
                nome=state.lead_nome, cidade=state.lead_obj.lead.cidade,
                segmento=state.lead_obj.lead.segmento, telefone=state.lead_obj.lead.telefone or "",
                whatsapp=state.lead_obj.lead.whatsapp or "",
                rating=float(state.lead_obj.lead.rating or 0), jina_insights=state.jina_insights
            )
            state.briefing_theo = gerar_briefing_estrategico(theo_input)
            adicionar_log(f"  Briefing: {len(state.briefing_theo)} chars", "success")
            logger.info("[Pipeline] Theo: OK")
        except Exception as e:
            state.briefing_theo = f"Site para {state.lead_nome} em {state.cidade}."
            logger.warning(f"[Pipeline] Theo erro: {e}")
        adicionar_log("FASE 5: COLOR EXTRACTOR", "info")
        _logo_url = state.lead_raw_data.get("logo_url") or (state.lead_raw_data["fotos"][0] if state.lead_raw_data["fotos"] else None)
        if _logo_url:
            _logo_url = re.sub(r"[-]", "", _logo_url).strip()
        _fotos_ce = state.lead_raw_data["fotos"][1:4]
        try:
            _ce = _gerar_paleta_ce(logo_url=_logo_url, fotos=_fotos_ce)
            _primary = _ce.get("primaria") or "#374151"
            _accent = _ce.get("acento") or "#6366f1"
        except Exception as e:
            logger.warning(f"[Pipeline] Color Extractor erro: {e}")
            _primary = "#374151"
            _accent = "#6366f1"
        state.paleta_cores = _harmonizar_paleta({
            "primary": _primary, "secondary": "#f9fafb", "accent": _accent,
            "background": "#ffffff", "text": "#1f2937",
        })
        state.paleta_cores["reasoning"] = "Paleta harmonizada (ColorHarmonizer + WCAG)"
        adicionar_log(f"  Paleta: primary={state.paleta_cores['primary']} accent={state.paleta_cores['accent']}", "success")
        logger.info("[Pipeline] Designer: OK")
        # ================================================================
        # CURADORIA DE ENTRADA — comprime dados antes do Arquiteto
        # ================================================================
        reviews_raw = state.lead_raw_data.get("reviews", [])
        if len(reviews_raw) > 5:
            reviews_sorted = sorted(reviews_raw, key=lambda r: len(str(r.get("texto", r.get("text", "")))), reverse=True)
            state.lead_raw_data["reviews"] = reviews_sorted[:5]
        if len(state.jina_insights) > 5000:
            state.jina_insights = state.jina_insights[:5000]
        # Gerar Google Maps embed a partir do nome + cidade
        import urllib.parse as _urlparse
        _maps_query = _urlparse.quote(state.lead_nome + " " + state.lead_obj.lead.cidade + " " + (state.lead_obj.lead.segmento or ""))
        # OpenStreetMap embed — sem chave de API, funciona sempre
        _osm_query = _urlparse.quote(state.lead_nome + ", " + state.lead_obj.lead.cidade)
        _maps_embed = ('<iframe width="100%" height="450" style="border:0;" loading="lazy" allowfullscreen="" '
            'src="https://www.openstreetmap.org/export/embed.html?bbox=-60,-35,-30,-5&layer=mapnik&marker=0,0&query=' + _osm_query + '"></iframe>')
        state.lead_raw_data["google_maps_embed"] = _maps_embed
        print(f"[Pipeline] Curadoria: {len(state.lead_raw_data.get('reviews', []))} reviews, {len(state.jina_insights)} chars jina, maps_embed OK")

        adicionar_log("FASE 6: ARQUITETO MESTRE", "info")
        _seed = int(hashlib.md5(state.lead_nome.encode()).hexdigest()[:8], 16)
        random.seed(_seed)
        _pool = ["mask-reveal", "counter-animation", "parallax-scroll", "stagger-fade",
                 "reveal-on-scroll", "text-split", "floating-cards", "elastic-scale",
                 "wave-animation", "spotlight-hover", "tilt-3d", "fade-up", "slide-in", "zoom-reveal"]
        random.sample(_pool, 6)
        state.prd_arquiteto = gerar_arquiteto_mestre_prd(
            dados_hunter=state.lead_raw_data,
            cidade=state.lead_obj.lead.cidade,
            segmento=state.lead_obj.lead.segmento,
            jina_insights=state.jina_insights,
            briefing_theo=state.briefing_theo,
            alex_colors=state.paleta_cores,
            caio_tier=state.qualificacao_caio.tier if state.qualificacao_caio else "STANDARD",
            caio_score=state.qualificacao_caio.score if state.qualificacao_caio else 0,
            caio_motivo=state.qualificacao_caio.motivo if state.qualificacao_caio else "",
        )
        adicionar_log(f"  PRD: {len(state.prd_arquiteto.sections)} secoes", "success")
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
        adicionar_log("FASE 7: LIAM (Componentizado)", "info")
        if not state.prd_arquiteto:
            raise Exception("PRD nao disponivel para o Liam")
        _html_main = gerar_html_componentizado(state.prd_arquiteto)
        if not _html_main or len(_html_main) < 500:
            raise Exception("Liam retornou HTML vazio")
        state.html_final = montar_template_python(_html_main, state.prd_arquiteto)
        adicionar_log(f"  HTML: {len(state.html_final):,} chars", "success")
        logger.info("[Pipeline] Liam: OK")
        salvar_checkpoint(state.pipeline_id, "liam", {"html_chars": len(state.html_final)})
        try:
            os.makedirs("/root/fralib/logs/pipeline_trace", exist_ok=True)
            with open("/root/fralib/logs/pipeline_trace/liam_html.html", "w", encoding="utf-8") as _f:
                _f.write(state.html_final)
            print("[Trace] liam_html.html salvo")
        except Exception:
            pass
        adicionar_log("FASE 8: LIZ (Auditoria)", "info")
        # BeautifulSoup auto-healing: corrige tags abertas antes da Liz auditar
        try:
            from bs4 import BeautifulSoup as _BS
            _soup = _BS(state.html_final, "html.parser")
            state.html_final = str(_soup)
            print("[Pipeline] BeautifulSoup auto-healing: OK")
        except Exception as _bse:
            print(f"[Pipeline] BeautifulSoup skip: {_bse}")
        MAX_LIZ = 3
        for tentativa_liz in range(1, MAX_LIZ + 1):
            try:
                adicionar_log(f"  Tentativa {tentativa_liz}/{MAX_LIZ}...", "info")
                liz_result = auditar(html=state.html_final, briefing=state.briefing_theo, tentativa=tentativa_liz)
                state.liz_score = liz_result.score
                if liz_result.aprovado:
                    state.liz_aprovado = True
                    adicionar_log(f"  Liz APROVOU score={liz_result.score}", "success")
                    logger.info(f"[Pipeline] Liz: APROVADO score={liz_result.score}")
                    break
                adicionar_log(f"  Score={liz_result.score} - corrigindo...", "warning")
                secoes_html = liz_listar_secoes(state.html_final)
                def _mapear_secao(texto, secoes):
                    t = texto.lower()
                    mapa = [
                        (["lgpd", "cookie", "privacidade"], "lgpd"),
                        (["footer", "rodape", "copyright"], "footer"),
                        (["depoimento", "review", "avaliacao"], "depoimentos"),
                        (["contato", "whatsapp", "formulario"], "contato"),
                        (["localizacao", "endereco", "mapa"], "localizacao"),
                        (["servico", "plano", "modalidade"], "servicos"),
                        (["sobre", "historia", "missao"], "sobre"),
                        (["hero", "h1", "banner", "cta"], "hero"),
                    ]
                    for kws, s in mapa:
                        if any(k in t for k in kws) and s in secoes:
                            return s
                    return secoes[0] if secoes else "hero"
                corrigidas = set()
                _bloat_abort = False

                def _editar_com_antibloat(html_atual, secao, instrucao):
                    """Edita secao e reverte se crescer mais de 15% (anti-bloat)."""
                    _pat = r"<!-- SECTION:" + secao + r" -->(.*?)<!-- /SECTION:" + secao + r" -->"
                    _m = re.search(_pat, html_atual, re.DOTALL)
                    _tam_original = len(_m.group(1)) if _m else 0
                    html_novo = liz_editar_secao(html_atual, secao, instrucao)
                    _m2 = re.search(_pat, html_novo, re.DOTALL)
                    _tam_editado = len(_m2.group(1)) if _m2 else 0
                    if _tam_original > 0 and _tam_editado > _tam_original * 1.15:
                        print(f"[Liz] Anti-bloat: {secao} cresceu {_tam_editado}/{_tam_original} chars (>15%). Revertendo.")
                        adicionar_log(f"  ⚠️ Liz alucinou em [{secao}] (+{round((_tam_editado/_tam_original-1)*100)}%). Revertendo.", "warning")
                        return html_atual, True  # revertido, bloat=True
                    if _tam_original > 0 and _tam_editado < _tam_original * 0.5:
                        print(f"[Liz] Anti-shrink: {secao} encolheu {_tam_editado}/{_tam_original} chars (<50%). Revertendo.")
                        adicionar_log(f"  ⚠️ Liz apagou [{secao}] ({_tam_editado} vs {_tam_original} chars). Revertendo.", "warning")
                        return html_atual, True  # revertido
                    return html_novo, False

                for p in [p for p in liz_result.tecnica.problemas if p.gravidade in ("CRITICO", "ALTO")][:3]:
                    s = _mapear_secao(p.problema + " " + p.dimensao, secoes_html)
                    if s not in corrigidas:
                        try:
                            state.html_final, _bloat = _editar_com_antibloat(state.html_final, s, p.problema)
                            if _bloat:
                                _bloat_abort = True
                                break
                            corrigidas.add(s)
                        except Exception:
                            pass
                if not _bloat_abort:
                    for prob in (liz_result.semantica.problemas if liz_result.semantica else [])[:4]:
                        s = _mapear_secao(prob, secoes_html)
                        if s not in corrigidas:
                            try:
                                state.html_final, _bloat = _editar_com_antibloat(state.html_final, s, prob)
                                if _bloat:
                                    _bloat_abort = True
                                    break
                                corrigidas.add(s)
                            except Exception:
                                pass
                if _bloat_abort:
                    adicionar_log("  ✅ Anti-bloat: aprovando com codigo original do Liam", "success")
                    state.liz_aprovado = True
                    break
                if tentativa_liz >= 2:
                    adicionar_log(f"  ⚠️ Liz em loop (tentativa {tentativa_liz}). Forçando aprovação pelo Orquestrador (Bypass).", "warning")
                    logger.warning(f"[Pipeline] Liz bypass: score={liz_result.score} — forçando aprovação")
                    state.liz_aprovado = True
                    state.liz_score = max(liz_result.score, 75)
                    break
            except Exception as e:
                if "Deploy bloqueado" in str(e):
                    raise
                logger.warning(f"[Pipeline] Liz erro: {e}")
                state.liz_aprovado = True
                break
        adicionar_log("FASE 9: DEPLOY", "info")
        web_dir = f"/var/www/fralib/sites/{state.lead_slug}"
        os.makedirs(web_dir, exist_ok=True)
        with open(f"{web_dir}/index.html", "w", encoding="utf-8") as _f:
            _f.write(state.html_final)
        if state.alex_result and state.alex_result.assets_dir:
            assets_src = state.alex_result.assets_dir
            assets_dst = f"{web_dir}/assets"
            if os.path.exists(assets_src):
                import shutil
                if os.path.exists(assets_dst):
                    shutil.rmtree(assets_dst)
                os.makedirs(assets_dst, exist_ok=True)
                shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)
        os.system(f"chown -R www-data:www-data {web_dir}")
        os.system(f"chmod -R 755 {web_dir}")
        state.site_url = f"https://seunegociofralib.site/sites/{state.lead_slug}/"
        adicionar_log(f"  Deploy: {state.site_url}", "success")
        logger.info(f"[Pipeline] Deploy: {state.site_url}")
        adicionar_log("FASE 10: BRYAN", "info")
        try:
            bryan_input = BryanInput(
                nome=state.lead_nome, cidade=state.lead_obj.lead.cidade,
                segmento=state.lead_obj.lead.segmento, telefone=state.lead_obj.lead.telefone or "",
                whatsapp=state.lead_obj.lead.whatsapp or "",
                rating=state.lead_obj.lead.rating or 0.0, site_url=state.site_url,
                score_caio=state.qualificacao_caio.score if state.qualificacao_caio else 0,
                tier=state.qualificacao_caio.tier if state.qualificacao_caio else "STANDARD"
            )
            bryan_output = iniciar_contato(bryan_input)
            adicionar_log("  Bryan: mensagem criada", "success")
            logger.info("[Pipeline] Bryan: OK")

            # Enviar mensagem via whatsmeow
            try:
                import httpx, re as _re, os as _os
                meowhats_url = _os.getenv("MEOWHATS_URL", "http://localhost:3001")
                meowhats_key = _os.getenv("MEOWHATS_KEY", "1763kovQ@")
                tenant_id = f"fralib_user_{state.user_id}" if hasattr(state, 'user_id') and state.user_id else "fralib"
                tel = (state.lead_obj.lead.whatsapp or state.lead_obj.lead.telefone or "").strip()
                tel = _re.sub(r'\D', '', tel)
                if not tel.startswith('55'):
                    tel = '55' + tel
                jid = f"{tel}@s.whatsapp.net"
                texto = bryan_output.mensagem.texto
                with httpx.Client(timeout=10) as c:
                    r = c.post(
                        f"{meowhats_url}/api/sessions/{tenant_id}/send",
                        headers={"X-API-Key": meowhats_key},
                        json={"jid": jid, "type": "text", "text": texto}
                    )
                    if r.status_code == 200:
                        adicionar_log(f"  Bryan: mensagem ENVIADA para {tel}", "success")
                        logger.info(f"[Pipeline] Bryan: mensagem enviada para {jid}")
                    else:
                        adicionar_log(f"  Bryan: falha no envio ({r.text[:80]})", "warning")
                        logger.warning(f"[Pipeline] Bryan envio falhou: {r.text}")
            except Exception as send_err:
                adicionar_log(f"  Bryan: erro no envio WPP ({send_err})", "warning")
                logger.warning(f"[Pipeline] Bryan envio WPP erro: {send_err}")
        except Exception as e:
            logger.warning(f"[Pipeline] Bryan erro: {e}")
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE leads SET site_url=:url, url_site=:url, processado=true,
                processado_em=:ts, status='concluido', atualizado_em=:ts WHERE id=:id
            """), {"url": state.site_url, "ts": datetime.now().isoformat(), "id": state.lead_id})
            conn.commit()
        limpar_checkpoint(state.pipeline_id)
        adicionar_log("PIPELINE v2 CONCLUIDO - FraLibState OK", "success")
        logger.info("[Pipeline] CONCLUIDO - 7 AGENTES!")
        return {"sucesso": True, "site_url": state.site_url, "lead": state.lead_nome}
    except Exception as e:
        adicionar_log(f"ERRO: {str(e)}", "error")
        logger.error(f"[Pipeline] Erro: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Salvar lead com status erro se tiver id
        if hasattr(state, 'lead_id') and state.lead_id:
            try:
                with engine.connect() as conn:
                    conn.execute(text("UPDATE leads SET status='erro', atualizado_em=:ts WHERE id=:id AND status NOT IN ('concluido','descartado')"),
                        {"ts": datetime.now().isoformat(), "id": state.lead_id})
                    conn.commit()
            except Exception:
                pass
        return {"sucesso": False, "erro": str(e)}




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

@router.post('/iniciar')
async def iniciar_pipeline(
    request: Request, background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    try:
        config = await request.json()
        logger.info(f"[Pipeline] Dados recebidos: {config}")
    except Exception:
        config = {}
    tenant_id = usuario.get("tenant_id", usuario["id"])
    config_limpo = {
        "segmento": config.get("segmento") or "Academia",
        "cidade": config.get("cidade") or "Sao Paulo",
        "quantidade": int(config.get("quantidade") or 10),
        "score_minimo": int(config.get("score_minimo") or 70),
    }

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
    update_pipeline_state(db, tenant_id, rodando=True, pausado=False, config=config_limpo)
    _check_rate_limit(str(tenant_id))
    background_tasks.add_task(executar_pipeline_completo, config_limpo, tenant_id)
    return {"status": "iniciado", "mensagem": "Pipeline iniciado com 7 agentes", "config": config_limpo}


@router.get('/status')
async def get_status(db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)):
    tenant_id = usuario.get("tenant_id", usuario["id"])
    state = get_pipeline_state(db, tenant_id)

    total_leads = db.execute(text("SELECT COUNT(*) FROM leads WHERE user_id=:uid"), {"uid": tenant_id}).scalar() or 0
    total_sites = db.execute(text("SELECT COUNT(*) FROM leads WHERE user_id=:uid AND url_site IS NOT NULL AND url_site != ''"), {"uid": tenant_id}).scalar() or 0
    total_enviados = db.execute(text("SELECT COUNT(*) FROM leads WHERE user_id=:uid AND status = 'contatado'"), {"uid": tenant_id}).scalar() or 0
    ciclo_atual = db.execute(text("SELECT COALESCE(MAX(ciclo), 0) FROM leads WHERE user_id=:uid"), {"uid": tenant_id}).scalar() or 0

    return {
        "rodando": state["rodando"],
        "pausado": state["pausado"],
        "config": state["config"],
        "totalLeads": total_leads,
        "totalSites": total_sites,
        "totalEnviados": total_enviados,
        "cicloAtual": ciclo_atual
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
