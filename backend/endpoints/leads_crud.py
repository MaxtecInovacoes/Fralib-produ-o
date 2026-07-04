"""Leads CRUD endpoints - basic operations without SDR."""

import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY
import os, sys, re as _re2

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, "core"))
from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.core.config import SITES_DIR
from backend.endpoints.sse_endpoints import adicionar_log

logger = logging.getLogger("uvicorn")

# Import models from leads_crud_models
from backend.endpoints.leads_crud_models import (
    EditarSiteRequest,
    LeadManualRequest,
    CamposLeadRequest,
)


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════


def _reject_unsafe_site_html(html: str) -> None:
    allowed_tailwind = _re2.compile(
        r"<script\b[^>]*\bsrc\s*=\s*['\"]https://cdn\.tailwindcss\.com['\"][^>]*>\s*</script>",
        _re2.IGNORECASE,
    )
    check = allowed_tailwind.sub("", html or "")
    if _re2.search(r"<script\b", check, _re2.IGNORECASE):
        raise HTTPException(status_code=400, detail="HTML contem <script> nao permitido")
    if _re2.search(r"<(?:iframe|object|embed|base)\b", check, _re2.IGNORECASE):
        raise HTTPException(status_code=400, detail="HTML contem tag ativa nao permitida")
    if _re2.search(r"<meta\b[^>]*http-equiv\s*=\s*['\"]?refresh", check, _re2.IGNORECASE):
        raise HTTPException(status_code=400, detail="HTML contem meta refresh nao permitido")
    if _re2.search(r"\son[a-z0-9_-]+\s*=", check, _re2.IGNORECASE):
        raise HTTPException(status_code=400, detail="HTML contem event handler inline nao permitido")
    if _re2.search(r"\b(?:href|src|action|srcdoc)\s*=\s*['\"]?\s*(?:javascript|data|vbscript):", check, _re2.IGNORECASE):
        raise HTTPException(status_code=400, detail="HTML contem URL ativa nao permitida")


# ═══════════════════════════════════════════════════════════════════
# CRUD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════


router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("/sites")
async def get_sites(
    db: Session = Depends(get_db), usuario: dict = Depends(get_current_user)
):
    try:
        tenant_id_s = usuario.get("tenant_id", usuario["id"])
        result = db.execute(
            text("""
            SELECT
                id,
                nome,
                cidade,
                segmento,
                COALESCE(site_url, url_site) AS site_url,
                valor_venda,
                status,
                COALESCE(atualizado_em, criado_em) AS gerado_em,
                criado_em AS lead_criado_em,
                score
            FROM leads
            WHERE user_id = :uid
              AND (
                (site_url IS NOT NULL AND site_url != '')
                OR (url_site IS NOT NULL AND url_site != '')
              )
            ORDER BY COALESCE(atualizado_em, criado_em) DESC
        """),
            {"uid": tenant_id_s},
        ).fetchall()

        sites = []
        for r in result:
            d = dict(r._mapping)
            url = d.get("site_url") or d.get("url_site") or ""
            slug = (
                url.rstrip("/").split("/sites/")[-1].rstrip("/")
                if "/sites/" in url
                else ""
            )
            thumb = f"/sites/{slug}/assets/foto_1.webp" if slug else ""
            sites.append(
                {
                    "id": d["id"],
                    "nome": d["nome"] or "—",
                    "cidade": d["cidade"] or "—",
                    "segmento": d["segmento"] or "—",
                    "url_site": url,
                    "thumb": thumb,
                    "valor_venda": float(d["valor_venda"] or 0),
                    "status": d["status"] or "—",
                    # Compat frontend: this field means "site generated at" in the sites view.
                    "criado_em": str(d["gerado_em"] or ""),
                    "gerado_em": str(d["gerado_em"] or ""),
                    "lead_criado_em": str(d["lead_criado_em"] or ""),
                    "score": d["score"] or 0,
                }
            )

        return {"sites": sites, "total": len(sites)}
    except Exception as e:
        logger.warning("[Sites] Erro: %s", e)
        return {"sites": [], "total": 0}



def _sanitize_lead_text(valor: str, max_len: int = 5000) -> str:
    """P0 hotfix: sanitize texto livre do lead (observacoes).

    Remove NUL bytes que quebram exports; strip control chars perigosos;
    cap em max_len pra evitar DoS via payload gigante.
    NAO escapa HTML - saida eh gravada no banco, escape acontece no consumer.
    """
    if not isinstance(valor, str):
        return ""
    _forbidden = {chr(0), chr(11), chr(12), chr(26), chr(27)}
    cleaned = "".join(ch for ch in valor if ch not in _forbidden)
    return cleaned[:max_len]




@router.patch("/{lead_id}")
async def atualizar_lead(
    lead_id: str,
    request_data: dict,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    try:
        campos = {}
        campos_permitidos = [
            "whatsapp",
            "telefone_whatsapp",
            "telefone",
            "nome",
            "segmento",
            "cidade",
            "observacoes",
            "valor_venda",
            "status",
        ]
        for k in campos_permitidos:
            if k in request_data:
                valor = request_data[k]
                # P0 hotfix: sanitize 'observacoes' (campo livre).
                if k == "observacoes" and isinstance(valor, str):
                    valor = _sanitize_lead_text(valor, max_len=5000)
                campos[k] = valor
        # Alias: whatsapp → telefone_whatsapp
        if "whatsapp" in request_data:
            campos["telefone_whatsapp"] = request_data["whatsapp"]
            # Se está atualizando WhatsApp, limpa flag de pendente
            if request_data["whatsapp"]:
                campos["whatsapp_pendente"] = False

        if not campos:
            return {"ok": True}

        tenant_id = usuario.get("tenant_id", usuario["id"])
        sets = ", ".join([f"{k}=:{k}" for k in campos.keys()])
        campos["lead_id"] = lead_id
        campos["uid"] = tenant_id
        db.execute(
            text(
                f"UPDATE leads SET {sets}, atualizado_em=NOW()::text WHERE id=:lead_id AND user_id=:uid"
            ),
            campos,
        )
        db.commit()
        return {"ok": True}
    except Exception as e:
        logger.warning("[Leads] Erro ao atualizar: %s", e)
        raise HTTPException(status_code=500, detail="Erro ao atualizar lead. Tente novamente.")


@router.post("/{lead_id}/reprocessar")
async def reprocessar_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        lead = db.execute(
            text("SELECT * FROM leads WHERE id=:id AND user_id=:uid"),
            {"id": lead_id, "uid": tenant_id},
        ).fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead nao encontrado")
        db.execute(
            text(
                "UPDATE leads SET status='pendente', atualizado_em=NOW()::text WHERE id=:id AND user_id=:uid"
            ),
            {"id": lead_id, "uid": tenant_id},
        )
        db.commit()
        return {"ok": True, "mensagem": "Lead marcado para reprocessamento"}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("[Leads] Erro: %s", e)
        raise HTTPException(status_code=500, detail="Erro interno. Tente novamente.")


@router.post("/{lead_id}/editar-site")
async def editar_site(
    lead_id: str,
    req: EditarSiteRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    from sqlalchemy import text as _text

    plano = db.execute(
        _text("SELECT plano FROM users WHERE id=:id"), {"id": usuario["id"]}
    ).scalar()
    if plano not in ("pro", "beta", "admin"):
        raise HTTPException(
            403,
            "Edicao de site disponivel apenas no plano Pro. Faca upgrade em /planos",
        )
    from services.credits_manager import consume_tokens

    consume_tokens(db, int(usuario["id"]), 1, "Edicao de site")
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents"
        ),
    )
    from llm_direct import call_claude

    adicionar_log(f"[Edicao Site] Iniciando: {req.prompt[:60]}", "info")
    tenant_id = usuario.get("tenant_id", usuario["id"])
    lead = db.execute(
        text("SELECT * FROM leads WHERE id=:id AND user_id=:uid"),
        {"id": lead_id, "uid": tenant_id},
    ).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nao encontrado")

    lead_dict = dict(lead._mapping)
    url_site = lead_dict.get("url_site") or lead_dict.get("site_url") or ""
    if not url_site:
        raise HTTPException(status_code=400, detail="Lead nao tem site gerado")

    slug = url_site.rstrip("/").split("/")[-1]
    # Defesa em profundidade: bloquear path traversal mesmo que url_site venha corrompido do banco
    import re as _re_path

    if not _re_path.match(r"^[a-z0-9][a-z0-9-]{0,80}$", slug):
        raise HTTPException(status_code=400, detail="Slug do site invalido")
    html_path = f"{SITES_DIR}/{tenant_id}/{slug}/index.html"

    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="Arquivo HTML nao encontrado")

    with open(html_path, "r", encoding="utf-8") as f:
        html_atual = f.read()

    try:
        body_match = _re2.search(
            r"<body[^>]*>(.*?)</body>", html_atual, _re2.DOTALL | _re2.IGNORECASE
        )
        if not body_match:
            raise HTTPException(status_code=400, detail="HTML invalido: sem tag body")

        body_inner = body_match.group(1)

        # Guardar styles do body para reinserir depois
        styles_body = _re2.findall(r"<style[^>]*>.*?</style>", body_inner, _re2.DOTALL)

        # Body limpo sem style/script para reduzir tokens
        body_limpo = _re2.sub(
            r"<style[^>]*>.*?</style>", "", body_inner, flags=_re2.DOTALL
        )
        body_limpo = _re2.sub(
            r"<script[^>]*>.*?</script>", "", body_limpo, flags=_re2.DOTALL
        )
        body_limpo = _re2.sub(r"\n{3,}", "\n\n", body_limpo).strip()
        if len(body_limpo) > 28000:
            body_limpo = body_limpo[:28000]

        bt = chr(96) * 3
        system_edit = (
            "Voce e um editor de sites HTML. "
            "Recebera o conteudo do BODY (sem style/script) e uma instrucao. "
            "Retorne APENAS o conteudo do body modificado, sem tags html/head/body/style/script, "
            "sem markdown, sem " + bt + ", sem explicacoes. "
            "Aplique SOMENTE a modificacao pedida. Preserve TODAS as classes, IDs e atributos."
        )
        user_edit = "INSTRUCAO: " + req.prompt + "\n\nBODY HTML:\n" + body_limpo

        adicionar_log(
            f"[Edicao Site] Enviando {len(body_limpo)} chars ao LLM...", "info"
        )
        body_novo = call_claude(
            system_edit, user_edit, model="sonnet", max_tokens=16000, temperature=0.2
        )

        if not body_novo or len(body_novo) < 50:
            adicionar_log("[Edicao Site] LLM retornou resposta invalida", "error")
            raise HTTPException(
                status_code=500, detail="LLM retornou resposta invalida"
            )

        adicionar_log(
            f"[Edicao Site] LLM respondeu ({len(body_novo)} chars), remontando...",
            "success",
        )

        # Limpar markdown
        stripped = body_novo.strip()
        if stripped.startswith(bt):
            parts = stripped.split(bt)
            if len(parts) >= 2:
                body_novo = parts[1]
                if body_novo.startswith("html"):
                    body_novo = body_novo[4:]

        # Remontar body com styles originais, sem scripts no body.
        body_final = body_novo.strip()
        if styles_body:
            body_final = "\n".join(styles_body) + "\n" + body_final

        # Remontar HTML completo
        body_tag = html_atual[body_match.start() : body_match.start(1)]
        html_novo = (
            html_atual[: body_match.start()]
            + body_tag
            + "\n"
            + body_final
            + "\n</body>"
            + html_atual[body_match.end() :]
        )
        _reject_unsafe_site_html(html_novo)

        # Backup e salvar
        backup_path = html_path.replace("index.html", "index.html.bak")
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(html_atual)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_novo)

        adicionar_log("[Edicao Site] Site atualizado com sucesso!", "success")
        return {"ok": True, "mensagem": "Site atualizado com sucesso!", "url": url_site}

    except HTTPException:
        raise
    except Exception as e:
        adicionar_log(f"[Edicao Site] Erro: {str(e)[:80]}", "error")
        raise HTTPException(status_code=500, detail="Erro ao editar site. Tente novamente.")


@router.post("/{lead_id}/upload-foto")
async def upload_foto(
    lead_id: str,
    foto: UploadFile = File(...),
    tipo: str = Form(default="foto"),
    numero: int = Form(default=1),
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    import os

    tenant_id = usuario.get("tenant_id", usuario["id"])
    lead = db.execute(
        text("SELECT * FROM leads WHERE id=:id AND user_id=:uid"),
        {"id": lead_id, "uid": tenant_id},
    ).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nao encontrado")

    lead_dict = dict(lead._mapping)
    url_site = lead_dict.get("url_site") or lead_dict.get("site_url") or ""
    if not url_site:
        raise HTTPException(status_code=400, detail="Lead nao tem site gerado")

    slug = url_site.rstrip("/").split("/sites/")[-1].rstrip("/")
    if not slug or slug == url_site.rstrip("/"):
        slug = url_site.rstrip("/").split("/")[-1]

    # Validacao anti-traversal
    import re as _re_upload

    slug_parts = slug.split("/")
    for part in slug_parts:
        if not _re_upload.match(r"^[a-zA-Z0-9_\-]+$", part):
            raise HTTPException(status_code=400, detail="Slug invalido")

    assets_dir = f"{SITES_DIR}/{tenant_id}/{slug_parts[-1]}/assets"
    os.makedirs(assets_dir, exist_ok=True)

    if tipo == "logo":
        filename = "logo.webp"
    else:
        filename = "foto_" + str(numero) + ".webp"

    filepath = assets_dir + "/" + filename
    contents = await foto.read()

    # Limite de 10MB por upload
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Arquivo muito grande (max 10MB)")

    # P0 hotfix security review: whitelist rigorosa de extensoes e content_type.
    # Sem isso, atacante envia .html/.svg/.js disfarçado de imagem; cai no
    # except Exception; extensao vem crua do filename; nginx serve estatico
    # no mesmo dominio dos cookies -> stored XSS com session hijack.
    _ALLOWED_IMG_EXT = {"jpg", "jpeg", "png", "webp"}
    _ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

    ext_raw = ""
    if foto.filename and "." in foto.filename:
        ext_raw = foto.filename.rsplit(".", 1)[-1].lower()
    ext = ext_raw if ext_raw in _ALLOWED_IMG_EXT else "jpg"

    # Validar content_type se uploadfile fornece
    if getattr(foto, "content_type", None) and foto.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Tipo {foto.content_type} nao permitido. Use jpg/png/webp.")

    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(contents))
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        if img.width > 1920:
            ratio = 1920 / img.width
            img = img.resize((1920, int(img.height * ratio)), Image.LANCZOS)
        output = io.BytesIO()
        img.save(output, format="WEBP", quality=85)
        with open(filepath, "wb") as f:
            f.write(output.getvalue())
    except ImportError:
        # PIL indisponivel: gravar como data binaria com extensao controlada
        # NUNCA aceitar filename cru do user.
        safe_filepath = filepath.replace(".webp", ".jpg")
        with open(safe_filepath, "wb") as f:
            f.write(contents)
        filepath = safe_filepath
        filename = filename.replace(".webp", ".jpg")
    except Exception:
        # Imagem invalida/corrompida: gravar como jpg generico (nao confiar no filename).
        safe_filepath = filepath.replace(".webp", ".jpg")
        with open(safe_filepath, "wb") as f:
            f.write(contents)
        filepath = safe_filepath
        filename = filename.replace(".webp", ".jpg")

    foto_url = "/sites/" + slug + "/assets/" + filename
    return {
        "ok": True,
        "url": foto_url,
        "filename": filename,
        "mensagem": "Foto salva em " + foto_url,
    }


@router.post("/manual")
async def criar_lead_manual(
    req: LeadManualRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    from datetime import datetime
    import uuid as _uuid
    from services.credits_manager import validar_permissao_pipeline

    tenant_id = int(usuario.get("tenant_id", usuario.get("id")))
    if req.briefing:
        perm = validar_permissao_pipeline(db, tenant_id)
        if not perm.get("allowed"):
            status_code = 429 if perm.get("reason") == "cooldown" else 402
            raise HTTPException(status_code=status_code, detail=perm)
    lead_id = str(_uuid.uuid4())
    agora = datetime.now().isoformat()

    # Calcular se WhatsApp está pendente (ausente)
    telefone_ou_whatsapp = req.whatsapp or req.telefone
    whatsapp_pendente = not bool(telefone_ou_whatsapp)

    db.execute(
        text("""
        INSERT INTO leads (id, nome, cidade, segmento, telefone, whatsapp, telefone_whatsapp, score, status, criado_em, atualizado_em, processado, tentativas, observacoes, user_id, whatsapp_pendente, refs_visuais, font_preferencia)
        VALUES (:id, :nome, :cidade, :segmento, :telefone, :whatsapp, :telefone_wpp, :score, 'pendente', :criado_em, :criado_em, false, 0, :briefing, :user_id, :whatsapp_pendente, :refs_visuais, :font_preferencia)
        ON CONFLICT DO NOTHING
    """),
        {
            "id": lead_id,
            "nome": req.nome,
            "cidade": req.cidade,
            "segmento": req.nicho,
            "telefone": req.telefone,
            "whatsapp": req.whatsapp or req.telefone,
            "telefone_wpp": req.whatsapp or req.telefone,
            "score": req.score or 80,
            "criado_em": agora,
            "briefing": req.briefing or "",
            "user_id": tenant_id,
            "whatsapp_pendente": whatsapp_pendente,
            "refs_visuais": req.refs_visuais or "",
            "font_preferencia": req.font_preferencia or "",
        },
    )
    db.commit()
    if req.briefing:
        import job_queue as _jq

        run_id = _uuid.uuid4().hex[:12]
        job_id = _jq.enqueue(
            db,
            tipo="pipeline_lead",
            payload={
                "_lead_id_existente": lead_id,
                "_forcar_renovacao": True,
                "_prompt_agent_flow": True,
                "_run_id": run_id,
                "segmento": req.nicho,
                "cidade": req.cidade,
                "quantidade": 1,
                "score_minimo": 0,
            },
            tenant_id=tenant_id,
            max_attempts=3,
            idempotency_key=f"manual-pipeline-{lead_id}",
            priority=1,
            run_id=run_id,
        )
    return {
        "ok": True,
        "lead_id": lead_id,
        "job_id": job_id if req.briefing else None,
        "whatsapp_pendente": whatsapp_pendente,
        "mensagem": "Lead criado!"
        + (
            " Site enfileirado no worker."
            if req.briefing
            else " Sem briefing — site não gerado."
        ),
    }


@router.delete("/{lead_id}")
async def deletar_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])

        # PERF: DELETE com RETURNING elimina SELECT previo (3 queries -> 2)
        deleted = db.execute(
            text("""
                DELETE FROM leads
                WHERE id = :lead_id AND user_id = :uid
                RETURNING id
            """),
            {"lead_id": lead_id, "uid": tenant_id},
        ).fetchone()

        if not deleted:
            raise HTTPException(status_code=404, detail="Lead não encontrado")

        # Deletar interações - ja sabemos que o lead existe e pertence ao tenant
        db.execute(
            text("""
                DELETE FROM interacoes
                WHERE lead_id = :lead_id
                AND lead_id IN (SELECT id FROM leads WHERE user_id = :uid)
            """),
            {"lead_id": lead_id, "uid": tenant_id},
        )
        db.commit()
        return {"ok": True, "mensagem": "Lead deletado com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("[Leads] Erro: %s", e)
        raise HTTPException(status_code=500, detail="Erro interno. Tente novamente.")


@router.patch("/{lead_id}/aprovar-pipeline")
async def aprovar_lead_pipeline(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        lead = db.execute(
            text("SELECT id FROM leads WHERE id=:id AND user_id=:uid"),
            {"id": lead_id, "uid": tenant_id},
        ).fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")
        db.execute(
            text("""
            UPDATE leads SET status='qualificado', score=50
            WHERE id=:id AND user_id=:uid
        """),
            {"id": lead_id, "uid": tenant_id},
        )
        db.commit()
        return {"ok": True, "mensagem": "Lead aprovado manualmente para o pipeline"}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("[Leads] Erro: %s", e)
        raise HTTPException(status_code=500, detail="Erro interno. Tente novamente.")


@router.patch("/{lead_id}/descartar")
async def descartar_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        lead = db.execute(
            text("SELECT id FROM leads WHERE id=:id AND user_id=:uid"),
            {"id": lead_id, "uid": tenant_id},
        ).fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")
        db.execute(
            text("""
            UPDATE leads SET status='descartado', atualizado_em=NOW()::text
            WHERE id=:id AND user_id=:uid
        """),
            {"id": lead_id, "uid": tenant_id},
        )
        db.commit()
        return {"ok": True, "mensagem": "Lead descartado"}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("[Leads] Erro: %s", e)
        raise HTTPException(status_code=500, detail="Erro interno. Tente novamente.")


@router.patch("/{lead_id}/campos")
async def atualizar_campos_lead(
    lead_id: str,
    req: CamposLeadRequest,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    try:
        tenant_id = usuario.get("tenant_id", usuario["id"])
        lead = db.execute(
            text("SELECT id FROM leads WHERE id=:id AND user_id=:uid"),
            {"id": lead_id, "uid": tenant_id},
        ).fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")
        campos = {}
        if req.nome is not None:
            campos["nome"] = req.nome
        if req.telefone is not None:
            campos["telefone"] = req.telefone
            campos["whatsapp"] = req.telefone
            campos["telefone_whatsapp"] = req.telefone
            # Se está definindo telefone, limpa flag de pendente
            if req.telefone:
                campos["whatsapp_pendente"] = False
        if req.segmento is not None:
            campos["segmento"] = req.segmento
        if req.cidade is not None:
            campos["cidade"] = req.cidade
        if req.observacao is not None:
            campos["observacoes"] = req.observacao
        if req.sdr_stage is not None:
            campos["sdr_stage"] = req.sdr_stage
        if req.status is not None:
            campos["status"] = req.status
        if req.refs_visuais is not None:
            campos["refs_visuais"] = req.refs_visuais
        if req.font_preferencia is not None:
            campos["font_preferencia"] = req.font_preferencia
        if not campos:
            return {"ok": True, "mensagem": "Nenhum campo para atualizar"}
        tenant_id = usuario.get("tenant_id", usuario["id"])
        sets = ", ".join([f"{k}=:{k}" for k in campos.keys()])
        campos["lead_id"] = lead_id
        campos["uid"] = tenant_id
        db.execute(
            text(f"UPDATE leads SET {sets} WHERE id=:lead_id AND user_id=:uid"), campos
        )
        db.commit()
        return {"ok": True, "mensagem": "Campos atualizados com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("[Leads] Erro: %s", e)
        raise HTTPException(status_code=500, detail="Erro interno. Tente novamente.")
