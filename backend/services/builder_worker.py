"""Isolated Builder contract for sending the final prompt to the site Builder."""

from __future__ import annotations

import json
import os
import re
import shutil
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any

from backend.agents.site_prompt_agent import build_prompt_agent_payload
try:
    from backend.core.proxy_models import PROXY_BUILDER_MODEL
except Exception:
    from core.proxy_models import PROXY_BUILDER_MODEL  # type: ignore
try:
    from backend.core.proxy_models import PROXY_DEFAULT_MODEL
except Exception:
    from core.proxy_models import PROXY_DEFAULT_MODEL  # type: ignore
from backend.services.vite_react_renderer import render_vite_react_site


_SAFE_SCOPE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,95}$")
_DEFAULT_SANDBOX_ROOT = "/workspace/fralib-builder"
_ROOT = Path(__file__).resolve().parents[2]


def _fallbacks_disabled() -> bool:
    env = (os.getenv("FRALIB_FAIL_CLOSED_FALLBACKS") or "").strip().lower()
    if env in {"1", "true", "yes", "on"}:
        return True
    return (os.getenv("FRALIB_ENV") or "").strip().lower() == "prod"


def _builder_proxy_fallback_model() -> str:
    if os.getenv("FRALIB_DISABLE_PROXY_FAILOVER", "").strip().lower() in {"0", "false", "no", "off"}:
        return PROXY_DEFAULT_MODEL
    return ""


def build_builder_job_manifest(
    prd_or_facts: Any,
    *,
    tenant_id: int | str,
    job_id: int | str,
    target: str = "landing-page",
    agent: str = "claude",
    model: str = "sonnet",
    engine: str | None = None,
    sandbox_root: str = _DEFAULT_SANDBOX_ROOT,
    repair_context: dict[str, Any] | None = None,
    publication_url: str | None = None,
) -> dict[str, Any]:
    """Create one auditable, tenant-scoped builder job without running code."""
    tenant_scope = _safe_scope(tenant_id, label="tenant_id")
    job_scope = _safe_scope(job_id, label="job_id")
    workspace = _sandbox_workspace(sandbox_root, tenant_scope, job_scope)
    prompt_payload = build_prompt_agent_payload(prd_or_facts, target=target)
    _ensure_manifest_publication_url(prompt_payload, prd_or_facts, publication_url=publication_url)
    audit_payload = prompt_payload.get("prompt_agent_payload", prompt_payload)
    if isinstance(audit_payload, dict):
        _ensure_manifest_publication_url(audit_payload, prd_or_facts, publication_url=publication_url)
    prompt = prompt_payload["builder_prompt"]
    digest = _prompt_digest(tenant_scope, job_scope, prompt)
    output_dir = f"{workspace}/dist"
    engine_name = _builder_engine(engine)
    return {
        "version": 2,
        "contract": "fralib-site-builder-v2",
        "mode": "production",
        "engine": engine_name,
        "tenant_id": tenant_scope,
        "job_id": job_scope,
        "idempotency_key": digest,
        "sandbox": {
            "workspace": workspace,
            "output_dir": output_dir,
            "source_dir": f"{workspace}/src",
            "agent": engine_name,
            "model": str(model or "").strip(),
        },
        "prompt_agent": audit_payload,
        "prompt": prompt,
        "repair_context": repair_context or {},
    }


def _ensure_manifest_publication_url(
    prompt_payload: dict[str, Any], source: Any, *, publication_url: str | None = None
) -> None:
    canonical = str(publication_url or "").strip()
    if not canonical.startswith(("http://", "https://")):
        canonical = _publication_url_from_source(source)
    context = prompt_payload.get("context")
    if not isinstance(context, dict):
        return
    og_image = _publication_og_image_from_source(source)
    primary_terms = _publication_keywords_from_source(source)
    for key in ("business", "publication", "seo"):
        container = context.setdefault(key, {})
        if isinstance(container, dict):
            if canonical:
                container.setdefault("canonical_url", canonical)
                container.setdefault("site_url", canonical)
            if og_image:
                container.setdefault("og_image", og_image)
    if primary_terms:
        seo = context.setdefault("seo", {})
        if isinstance(seo, dict):
            seo["primary_terms"] = primary_terms


def _publication_url_from_source(source: Any) -> str:
    for key in ("canonical_url", "site_url", "url_site"):
        value = ""
        if isinstance(source, dict):
            value = str(source.get(key) or "").strip()
        else:
            value = str(getattr(source, key, "") or "").strip()
        if value.startswith(("http://", "https://")):
            return value
    return ""


def _publication_og_image_from_source(source: Any) -> str:
    candidates: list[str] = []
    if isinstance(source, dict):
        candidates.extend(
            str(source.get(key) or "").strip()
            for key in ("og_image",)
        )
        photos = source.get("photos")
        if isinstance(photos, list):
            candidates.extend(str(item or "").strip() for item in photos)
    else:
        candidates.extend(str(getattr(source, key, "") or "").strip() for key in ("og_image",))
        photos = getattr(source, "photos", None)
        if isinstance(photos, list):
            candidates.extend(str(item or "").strip() for item in photos)
    for value in candidates:
        if value.startswith(("http://", "https://")):
            return value
    return ""


def _publication_keywords_from_source(source: Any) -> list[str]:
    if isinstance(source, dict):
        raw = source.get("seo_keywords") or source.get("keywords") or []
    else:
        raw = getattr(source, "seo_keywords", None) or getattr(source, "keywords", None) or []
    if not isinstance(raw, list):
        raw = [item.strip() for item in str(raw or "").split(",") if item.strip()]
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw:
        term = str(item or "").strip()
        low = term.lower()
        if not term or low in seen:
            continue
        seen.add(low)
        cleaned.append(term)
    return cleaned[:12]


def write_builder_job_manifest(
    manifest: dict[str, Any], *, manifest_dir: str | os.PathLike[str]
) -> Path:
    """Persist a local manifest using a tenant/job scoped filename."""
    validate_manifest_scope(manifest)
    base = Path(manifest_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    tenant_scope = _safe_scope(manifest.get("tenant_id"), label="tenant_id")
    job_scope = _safe_scope(manifest.get("job_id"), label="job_id")
    path = (base / f"tenant-{tenant_scope}__job-{job_scope}.json").resolve()
    if path.parent != base:
        raise ValueError("manifest path escapou do diretorio permitido")
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("idempotency_key") != manifest.get("idempotency_key"):
            if not _same_manifest_business_identity(existing, manifest):
                raise FileExistsError("manifest existente tem idempotency_key diferente")
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def execute_builder_job(
    manifest_path: str | os.PathLike[str], *, node_binary: str = "node"
) -> int:
    """Deprecated compatibility entrypoint.

    The active Builder no longer shells out to the removed Sandbox Agent. Keep
    this function only so old scripts fail with a clear message instead of
    trying an old Node runner path.
    """
    raise RuntimeError("execute_builder_job legado: use render_site_with_builder")


def render_site_with_builder(
    prd_or_facts: Any,
    *,
    tenant_id: int | str,
    job_id: int | str,
    target: str = "landing-page",
    repair_context: dict[str, Any] | None = None,
    publication_url: str | None = None,
) -> dict[str, Any]:
    """Run the post-PRD Builder and return its publishable artifact."""
    sandbox_root = os.getenv(
        "FRALIB_BUILDER_SANDBOX_ROOT",
        str((_ROOT / ".tmp" / "builder-workspaces").resolve()).replace("\\", "/"),
    )
    manifest_dir = os.getenv(
        "FRALIB_BUILDER_MANIFEST_DIR",
        str((_ROOT / "logs" / "builder_manifests").resolve()),
    )
    engine = _builder_engine(os.getenv("FRALIB_BUILDER_ENGINE", "vite_react"))
    manifest = build_builder_job_manifest(
        prd_or_facts,
        tenant_id=tenant_id,
        job_id=job_id,
        target=target,
        agent=engine,
        model=os.getenv("FRALIB_OPENUI_PRIMARY_MODEL", PROXY_BUILDER_MODEL),
        sandbox_root=sandbox_root,
        repair_context=repair_context,
        engine=engine,
        publication_url=publication_url,
    )
    manifest_path = write_builder_job_manifest(manifest, manifest_dir=manifest_dir)

    workspace_dir = Path(manifest["sandbox"]["workspace"]).resolve()
    output_dir = Path(manifest["sandbox"]["output_dir"]).resolve()

    if engine == "openui":
        # OpenUI: HTML estatico, 1 chamada LLM, sem Vite/node_modules.
        # Mais rapido, sem truncamento de output, gera landing page completa.
        from services.openui_renderer import render_openui_site

        render_result = render_openui_site(
            manifest["prompt"],
            facts=manifest.get("prompt_agent", {}).get("context", {}),
            repair_context=repair_context,
            primary_model=os.getenv("FRALIB_OPENUI_PRIMARY_MODEL", PROXY_BUILDER_MODEL),
            fallback_model=os.getenv("FRALIB_OPENUI_FALLBACK_MODEL", PROXY_DEFAULT_MODEL),
            max_tokens=int(os.getenv("FRALIB_OPENUI_MAX_TOKENS", "8000")),
            temperature=float(os.getenv("FRALIB_OPENUI_TEMPERATURE", "0.35")),
        )
        index_target = output_dir / "index.html"
        index_target.write_text(render_result.html, encoding="utf-8")
        _write_builder_render_meta(
            output_dir,
            engine=engine,
            model=render_result.model,
            attempts=render_result.attempts,
            elapsed_ms=render_result.elapsed_ms,
            html_chars=len(render_result.html),
            visual_direction=(
                manifest.get("prompt_agent", {})
                .get("context", {})
                .get("visual_direction", {})
            ),
            source_files=[],
        )
        model = render_result.model
        attempts = render_result.attempts
    elif engine == "vite_react":
        fallback_model = _builder_proxy_fallback_model()
        render_result = render_vite_react_site(
            manifest["prompt"],
            workspace_dir=workspace_dir,
            facts=manifest.get("prompt_agent", {}).get("context", {}),
            repair_context=repair_context,
            primary_model=os.getenv("FRALIB_OPENUI_PRIMARY_MODEL", PROXY_BUILDER_MODEL),
            fallback_model=fallback_model,
            max_tokens=int(os.getenv("FRALIB_VITE_REACT_MAX_TOKENS", "64000")),
            temperature=float(os.getenv("FRALIB_OPENUI_TEMPERATURE", "0.55")),
        )
        _write_builder_render_meta(
            output_dir,
            engine=engine,
            model=render_result.model,
            attempts=render_result.attempts,
            elapsed_ms=render_result.elapsed_ms,
            html_chars=len(render_result.html),
            visual_direction=(
                manifest.get("prompt_agent", {})
                .get("context", {})
                .get("visual_direction", {})
            ),
            source_files=sorted(render_result.source_files),
        )
        model = render_result.model
        attempts = render_result.attempts
    else:
        # Fallback to vite_react if engine not recognized
        engine = "vite_react"
        fallback_model = _builder_proxy_fallback_model()
        render_result = render_vite_react_site(
            manifest["prompt"],
            workspace_dir=workspace_dir,
            facts=manifest.get("prompt_agent", {}).get("context", {}),
            repair_context=repair_context,
            primary_model=os.getenv("FRALIB_OPENUI_PRIMARY_MODEL", PROXY_BUILDER_MODEL),
            fallback_model=fallback_model,
            max_tokens=int(os.getenv("FRALIB_VITE_REACT_MAX_TOKENS", "64000")),
            temperature=float(os.getenv("FRALIB_OPENUI_TEMPERATURE", "0.55")),
        )
        _write_builder_render_meta(
            output_dir,
            engine=engine,
            model=render_result.model,
            attempts=render_result.attempts,
            elapsed_ms=render_result.elapsed_ms,
            html_chars=len(render_result.html),
            visual_direction=(
                manifest.get("prompt_agent", {})
                .get("context", {})
                .get("visual_direction", {})
            ),
            source_files=sorted(render_result.source_files),
        )
        model = render_result.model
        attempts = render_result.attempts

    index_path = _find_builder_index(output_dir)
    html = index_path.read_text(encoding="utf-8")
    html = _prepare_builder_html_for_publication(
        html,
        manifest.get("prompt_agent", {}).get("context", {}),
        engine=engine,
    )
    index_path.write_text(html, encoding="utf-8")
    if len(html) < 250:
        raise RuntimeError("builder_renderer retornou index.html vazio/incompleto")
    return {
        "html": html,
        "output_dir": str(output_dir),
        "index_path": str(index_path),
        "manifest_path": str(manifest_path),
        "prompt": manifest["prompt"],
        "engine": engine,
        "model": model,
        "attempts": attempts,
    }


def copy_builder_dist(output_dir: str | os.PathLike[str], publish_dir: str | os.PathLike[str]) -> None:
    """Copy builder dist assets into the FraLib public site directory."""
    src = Path(output_dir).resolve()
    dst = Path(publish_dir).resolve()
    if not src.exists() or not src.is_dir():
        raise FileNotFoundError(f"builder output_dir nao encontrado: {src}")
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if _is_internal_builder_artifact(item):
            continue
        target = dst / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target, ignore=_ignore_internal_builder_artifacts)
        else:
            shutil.copy2(item, target)


_INTERNAL_BUILDER_ARTIFACTS = {
    "builder-render.json",
    "vite-render.json",
    "openui-render.json",
}


def _is_internal_builder_artifact(path: Path) -> bool:
    return path.name in _INTERNAL_BUILDER_ARTIFACTS or path.suffix == ".map"


def _ignore_internal_builder_artifacts(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in _INTERNAL_BUILDER_ARTIFACTS or Path(name).suffix == ".map"
    }


def _find_builder_index(output_dir: Path) -> Path:
    direct = output_dir / "index.html"
    if direct.exists():
        return direct
    candidates = sorted(output_dir.glob("**/index.html"))
    if candidates:
        return candidates[0]
    raise FileNotFoundError(f"builder_renderer nao gerou index.html em {output_dir}")


def _prepare_builder_html_for_publication(
    html: str, facts: dict[str, Any], *, engine: str | None = None
) -> str:
    """Apply canonical publication repairs to the real dist/index.html."""
    marked = _ensure_builder_renderer_marker(html)
    marked = _ensure_builder_publication_head(marked, facts or {})
    if engine == "vite_react":
        marked = _ensure_vite_mobile_publication_guard(marked)
    # FraLib Motion Runtime: GSAP + ScrollTrigger + Lenis via CDN
    # Ativa data-parallax, data-reveal, data-marquee, smooth scroll
    marked = _inject_motion_runtime(marked, facts or {})
    try:
        from agents.html_quality_gate import sanitize_builder_html_for_publication
    except Exception:
        try:
            from backend.agents.html_quality_gate import sanitize_builder_html_for_publication
        except Exception:
            return marked
    return sanitize_builder_html_for_publication(
        marked,
        facts or {},
        include_phase6=engine != "vite_react",
    )


def _inject_motion_runtime(html: str, facts: dict[str, Any]) -> str:
    """Injeta motion_runtime.js no HTML OpenUI para ativar parallax/scroll/marquee.

    Carrega o JS inline (vindo de backend/services/motion_runtime.js).
    Detecta data-parallax, data-reveal, data-marquee no HTML e so injeta
    se houver pelo menos 1 hook. Idempotente: nao duplica se ja existe.
    """
    text = html or ""
    if "fralib-motion-runtime" in text:
        return text
    has_motion_hook = any(
        hook in text for hook in ("data-parallax", "data-reveal", "data-marquee")
    )
    if not has_motion_hook:
        return text
    # Carrega o motion_runtime.js do disco
    motion_js_path = Path(__file__).resolve().parent / "motion_runtime.js"
    try:
        motion_js = motion_js_path.read_text(encoding="utf-8")
    except Exception:
        return text
    # Inline o JS no HTML (sem request extra)
    script = (
        "<script id=\"fralib-motion-runtime-loader\">\n"
        + motion_js
        + "\n</script>"
    )
    # Injeta antes de </body>
    if "</body>" in text:
        return text.replace("</body>", script + "\n</body>", 1)
    # Fallback: antes de </head>
    if "</head>" in text:
        return text.replace("</head>", script + "\n</head>", 1)
    return text + script


def _ensure_vite_mobile_publication_guard(html: str) -> str:
    text = html or ""
    if "fralib-vite-mobile-publication-guard" in text:
        return text
    guard = """<style id="fralib-vite-mobile-publication-guard">
html,body,#root{max-width:100%;overflow-x:hidden}
#root,#root *{min-width:0;box-sizing:border-box}
#root img,#root video,#root canvas,#root svg{max-width:100%;height:auto}
#root h1,#root h2,#root h3,#root p,#root a,#root button{overflow-wrap:anywhere}
@media(max-width:640px){
  #root{max-width:100vw;overflow:hidden}
  #root h1{font-size:clamp(2.45rem,13vw,4rem)!important;line-height:1.03!important;letter-spacing:0!important}
  #root h2{font-size:clamp(1.8rem,9vw,2.8rem)!important;line-height:1.08!important}
  #root p{max-width:100%!important}
  [data-lgpd-banner]{left:1rem!important;right:1rem!important;bottom:1rem!important;width:auto!important;max-width:calc(100vw - 2rem)!important;display:flex!important;flex-wrap:wrap!important;gap:.65rem!important;align-items:center!important;padding:.75rem!important}
  [data-lgpd-banner] button,[data-lgpd-accept]{flex:0 0 auto!important;margin-left:auto!important;white-space:nowrap!important}
}
</style>"""
    if re.search(r"(?is)</head>", text):
        return re.sub(r"(?is)</head>", guard + "\n</head>", text, count=1)
    return guard + text


def _ensure_builder_publication_head(html: str, facts: dict[str, Any]) -> str:
    text = html or ""
    canonical = _publication_canonical_url(facts)
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    site_name = str(business.get("name") or business.get("business_name") or "").strip()
    theme_color = _publication_theme_color(facts)
    og_image = _publication_head_og_image(facts)
    inserts = []
    if canonical:
        if 'rel="canonical"' not in text.lower() and "rel='canonical'" not in text.lower():
            inserts.append(f'<link rel="canonical" href="{_escape_attr(canonical)}">')
        if 'property="og:url"' not in text.lower():
            inserts.append(f'<meta property="og:url" content="{_escape_attr(canonical)}">')
        else:
            text = re.sub(
                r"""(?is)(<meta\s+property=["']og:url["']\s+content=["'])([^"']*)(["'][^>]*>)""",
                lambda m: m.group(1) + _escape_attr(canonical) + m.group(3),
                text,
                count=1,
            )
    if og_image:
        if 'property="og:image"' not in text.lower():
            inserts.append(f'<meta property="og:image" content="{_escape_attr(og_image)}">')
        else:
            text = re.sub(
                r"""(?is)(<meta\s+property=["']og:image["']\s+content=["'])([^"']*)(["'][^>]*>)""",
                lambda m: m.group(1) + _escape_attr(og_image) + m.group(3),
                text,
                count=1,
            )
        if 'name="twitter:image"' not in text.lower():
            inserts.append(f'<meta name="twitter:image" content="{_escape_attr(og_image)}">')
        else:
            text = re.sub(
                r"""(?is)(<meta\s+name=["']twitter:image["']\s+content=["'])([^"']*)(["'][^>]*>)""",
                lambda m: m.group(1) + _escape_attr(og_image) + m.group(3),
                text,
                count=1,
            )
    if site_name and 'property="og:site_name"' not in text.lower():
        inserts.append(f'<meta property="og:site_name" content="{_escape_attr(site_name)}">')
    if theme_color and 'name="theme-color"' not in text.lower():
        inserts.append(f'<meta name="theme-color" content="{_escape_attr(theme_color)}">')
    if inserts:
        text = re.sub(r"(?is)</head>", "\n".join(inserts) + "\n</head>", text, count=1)
    return text


def _publication_canonical_url(facts: dict[str, Any]) -> str:
    for container_name in ("publication", "seo", "business"):
        container = facts.get(container_name)
        if not isinstance(container, dict):
            continue
        value = (
            container.get("canonical_url")
            or container.get("canonical")
            or container.get("site_url")
            or container.get("url_site")
        )
        url = str(value or "").strip()
        if url.startswith(("http://", "https://")):
            return url
    return ""


def _publication_theme_color(facts: dict[str, Any]) -> str:
    for container_name in ("design", "visual_dna", "visual_direction"):
        container = facts.get(container_name)
        if not isinstance(container, dict):
            continue
        tokens = container.get("tokens") or container.get("color_tokens") or container.get("color_palette")
        if not isinstance(tokens, dict):
            continue
        color = str(tokens.get("--primary") or tokens.get("primary") or tokens.get("--accent") or tokens.get("accent") or "").strip()
        if re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            return color
    return "#111827"


def _publication_head_og_image(facts: dict[str, Any]) -> str:
    for container_name in ("publication", "seo", "business", "media"):
        container = facts.get(container_name)
        if not isinstance(container, dict):
            continue
        value = str(container.get("og_image") or "").strip()
        if value.startswith(("http://", "https://")):
            return value
    for key in ("photos",):
        photos = facts.get(key)
        if isinstance(photos, list):
            for item in photos:
                value = str(item or "").strip()
                if value.startswith(("http://", "https://")):
                    return value
    business = facts.get("business") if isinstance(facts.get("business"), dict) else {}
    photos = business.get("photos")
    if isinstance(photos, list):
        for item in photos:
            value = str(item or "").strip()
            if value.startswith(("http://", "https://")):
                return value
    return ""


def _escape_attr(value: str) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _ensure_builder_renderer_marker(html: str) -> str:
    text = html or ""
    if 'data-renderer="builder"' in text.lower():
        return text
    return re.sub(
        r"(?is)<html\b([^>]*)>",
        lambda match: "<html" + match.group(1) + ' data-renderer="builder">',
        text,
        count=1,
    )


def _prompt_digest(tenant_scope: str, job_scope: str, prompt: str) -> str:
    import hashlib

    return hashlib.sha256(
        f"{tenant_scope}:{job_scope}:{prompt}".encode("utf-8")
    ).hexdigest()


def _builder_engine(value: str | None = None) -> str:
    engine = str(value or os.getenv("FRALIB_BUILDER_ENGINE", "vite_react")).strip().lower().replace("-", "_")
    if engine in {"vite", "react", "vite_react", "vite-react"}:
        return "vite_react"
    if engine in {"openui", "html", "static_html"}:
        return "openui"
    raise ValueError(f"engine de Builder invalido: {value!r}")


def _write_builder_render_meta(
    output_dir: Path,
    *,
    engine: str,
    model: str,
    attempts: list[dict[str, Any]],
    elapsed_ms: int,
    html_chars: int,
    visual_direction: dict[str, Any],
    source_files: list[str],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "engine": engine,
        "model": model,
        "attempts": attempts,
        "elapsed_ms": elapsed_ms,
        "html_chars": html_chars,
        "visual_direction": visual_direction,
        "source_files": source_files,
    }
    (output_dir / "builder-render.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if engine == "vite_react":
        (output_dir / "vite-render.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _same_manifest_business_identity(
    existing: dict[str, Any], manifest: dict[str, Any]
) -> bool:
    """Allow prompt upgrades for the same lead while blocking path collisions."""
    left = _manifest_business_identity(existing)
    right = _manifest_business_identity(manifest)
    if not left or not right:
        return False
    if not left.get("name") or not right.get("name") or left["name"] != right["name"]:
        return False
    shared = set(left).intersection(right)
    if any(left[key] != right[key] for key in shared):
        return False
    strong_fields = {"city", "address", "phone"}
    return bool(strong_fields.intersection(shared))


def _manifest_business_identity(manifest: dict[str, Any]) -> dict[str, str]:
    context = {}
    prompt_agent = manifest.get("prompt_agent")
    if isinstance(prompt_agent, dict) and isinstance(prompt_agent.get("context"), dict):
        context = prompt_agent["context"]
    business = context.get("business") if isinstance(context.get("business"), dict) else {}
    phone = _identity_digits(
        business.get("phone")
        or business.get("whatsapp")
        or context.get("phone")
        or context.get("whatsapp")
    )
    identity = {
        "name": _identity_text(
            business.get("name")
            or context.get("business_name")
            or context.get("nome_empresa")
            or manifest.get("business_name")
        ),
        "segment": _identity_text(
            business.get("segment")
            or context.get("segmento")
            or context.get("segment")
            or manifest.get("segmento")
        ),
        "city": _identity_text(
            business.get("city")
            or context.get("cidade")
            or context.get("city")
            or manifest.get("cidade")
        ),
        "address": _identity_text(
            business.get("address")
            or context.get("address")
            or context.get("endereco")
            or manifest.get("address")
        ),
        "phone": phone,
    }
    return {key: value for key, value in identity.items() if value}


def _identity_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, dict)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def _identity_digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _safe_scope(value: Any, *, label: str) -> str:
    scope = str(value or "").strip()
    if not _SAFE_SCOPE.fullmatch(scope):
        raise ValueError(f"{label} invalido: {value!r}")
    return scope


def _sandbox_workspace(root: str, tenant_scope: str, job_scope: str) -> str:
    clean_root = str(root or _DEFAULT_SANDBOX_ROOT).strip()
    if re.match(r"^[a-zA-Z]:/", clean_root):
        root_path = Path(clean_root).resolve()
        workspace = root_path / f"tenant-{tenant_scope}" / f"job-{job_scope}"
        return str(workspace).replace("\\", "/")
    root_path = PurePosixPath(clean_root)
    if not root_path.is_absolute() or ".." in root_path.parts:
        raise ValueError("sandbox_root precisa ser absoluto e sem traversal")
    workspace = root_path / f"tenant-{tenant_scope}" / f"job-{job_scope}"
    return str(workspace)


def validate_manifest_scope(manifest: dict[str, Any]) -> None:
    """Reject tampered manifests before the sandbox runner executes anything."""
    tenant_scope = _safe_scope(manifest.get("tenant_id"), label="tenant_id")
    job_scope = _safe_scope(manifest.get("job_id"), label="job_id")
    sandbox = manifest.get("sandbox") if isinstance(manifest.get("sandbox"), dict) else {}
    workspace = str(sandbox.get("workspace") or "")
    output_dir = str(sandbox.get("output_dir") or "")
    expected_suffix = f"/tenant-{tenant_scope}/job-{job_scope}"
    if not workspace.replace("\\", "/").endswith(expected_suffix):
        raise ValueError("workspace nao pertence ao tenant/job do manifest")
    norm_workspace = workspace.replace("\\", "/").rstrip("/")
    norm_output = output_dir.replace("\\", "/")
    if not norm_output.startswith(f"{norm_workspace}/"):
        raise ValueError("output_dir precisa ficar dentro do workspace")
