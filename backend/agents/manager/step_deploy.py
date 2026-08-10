"""Step: Deploy — Fase 6: Publica site em sites/<tenant>/<lead_id>/index.html."""
import logging
import os
import json
from pathlib import Path
from datetime import datetime
from backend.agents.manager.states import (
    PipelineState, STATE_PUBLISHING, STATE_OUTREACH, STATE_FAILED,
    _transition, _log_step_error,
)
from backend.core.knowledge_journal import record as journal_record

logger = logging.getLogger("manager.pipeline")


def step_deploy(state: PipelineState) -> PipelineState:
    """Fase 6: Deploy publica site."""
    if state.current_state != STATE_PUBLISHING:
        return state

    try:
        # Slug a partir do nome do lead
        slug = state.lead_data.get("nome", "site").lower()
        slug = "".join(c if c.isalnum() else "-" for c in slug).strip("-")[:50]
        if not slug:
            slug = "site"

        # Diretorio: sites/<tenant_id>/<slug>-<lead_id>/
        sites_root = Path(os.getenv("FRALIB_SITES_ROOT", "sites"))
        site_dir = sites_root / str(state.tenant_id) / f"{slug}-{state.lead_id[:8]}"
        site_dir.mkdir(parents=True, exist_ok=True)

        # Escreve index.html
        index_path = site_dir / "index.html"
        html = state.build_output.get("html", "")

        # Pos-processamento cinematografico
        try:
            from backend.agents.cinematic_post_processor import process as cinematic_process
            design_tokens = {}
            if state.design_output:
                design_tokens = state.design_output.get("tokens_oklch", {}) or {}
            html = cinematic_process(
                html,
                design_tokens=design_tokens,
                segmento=state.segmento or "",
                nome=state.lead_data.get("nome", "") if state.lead_data else "",
            )
        except Exception as e:
            print(f"[Deploy] Aviso: pos-processamento cinematico falhou: {e}")

        index_path.write_text(html, encoding="utf-8")

        # Metadata
        meta_path = site_dir / "metadata.json"
        meta_path.write_text(json.dumps({
            "tenant_id": state.tenant_id,
            "lead_id": state.lead_id,
            "slug": slug,
            "lead_name": state.lead_data.get("nome"),
            "cidade": state.cidade,
            "segmento": state.segmento,
            "quality_score": state.quality_score,
            "deployed_at": datetime.now().isoformat(),
            "size_bytes": len(html),
            "paleta": state.design_output.get("paleta", {}) if state.design_output else {},
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        # URL relativa + absoluta
        rel_path = site_dir.relative_to(sites_root)
        state.deploy_url = f"https://app.seunegociofralib.site/sites/{rel_path}/"
        state.deploy_path = str(site_dir.absolute())
        state.history.append(f"Deploy: salvo em {index_path} ({len(html)} bytes)")

        # Knowledge Journal: ProjectPublished
        try:
            journal_record(
                project_id=state.lead_id,
                event_type="project_published",
                hypothesis=f"Site publicado com quality_score {state.quality_score}, deploy em {state.deploy_url}",
                payload={"deploy_url": state.deploy_url, "quality_score": state.quality_score, "size_bytes": len(html)},
            )
        except Exception as exc:
            logger.warning("[manager] journal project_published falhou (lead=%s): %s",
                           state.lead_id, exc)

        # Persist status=concluido + site_url na tabela leads (fail-soft)
        try:
            from backend.core.database import SessionLocal
            from sqlalchemy import text as _sql
            _db = SessionLocal()
            try:
                _db.execute(
                    _sql("""
                        UPDATE leads SET
                            status = 'concluido',
                            site_url = :url,
                            url_site = :url,
                            atualizado_em = NOW()
                        WHERE id = :lid AND user_id = :tid
                          AND (status IS NULL OR status NOT IN ('qualificado', 'convertido', 'descartado'))
                    """),
                    {"url": state.deploy_url, "lid": state.lead_id, "tid": state.tenant_id},
                )
                _db.commit()
            except Exception as exc:
                logger.warning("[manager] deploy DB commit falhou (lead=%s), tentando rollback: %s",
                               state.lead_id, exc)
                try:
                    _db.rollback()
                except Exception as rb_exc:
                    logger.warning("[manager] deploy DB rollback falhou (lead=%s): %s",
                                   state.lead_id, rb_exc)
            finally:
                _db.close()
        except Exception as _pdb:
            logger.error("PIPELINE_DEPLOY_UPDATE_FAILED lead_id=%s tenant_id=%d: %s", state.lead_id, state.tenant_id, _pdb)
    except Exception as e:
        _log_step_error(state, "Deploy", e)
        state.error = f"Deploy falhou: {e}"
        state.history.append(f"Deploy ERRO: {e}")
        return _transition(state, STATE_FAILED)

    return _transition(state, STATE_OUTREACH)
