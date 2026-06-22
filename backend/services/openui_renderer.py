"""OpenUI-style site renderer for FraLib Builder output.

The OpenUI project is a UI generation contract: a compact system prompt asks an
LLM to return Tailwind HTML that can be rendered immediately. FraLib keeps that
idea in-process so the pipeline does not need an extra OpenUI server, browser
session, Node build or Sandbox Agent.
"""

from __future__ import annotations

import html as _html
import re
import time
from dataclasses import dataclass
from typing import Any


OPENUI_SYSTEM_PROMPT = """You are an OpenUI-style senior product interface designer.

Transform the user's complete business brief into polished, responsive HTML
using Tailwind CSS classes. Build a complete landing page, not a component
demo. Return only BODY HTML, without doctype, html, head or body wrappers.

Rules:
- Preserve confirmed business facts exactly: name, phone, WhatsApp, address,
  city, rating, review count, hours, site and social links.
- Do not invent operational facts such as years in market, delivery time,
  prices, awards, guarantee, team size, certifications or imported ingredients.
- If a fact is absent, use neutral commercial copy or a contact CTA.
- Use real media URLs from the brief when available. If no reliable media URL
  exists, create CSS-only visual blocks; do not use broken image URLs, /icons
  paths, inline SVG, source.unsplash.com or generic map iframes.
- Do not output scripts, inline event handlers, javascript: URLs, data: URLs,
  iframes, objects, embeds, forms that post to external services, or any active
  browser behavior. The page must be static HTML/CSS.
- Do not embed maps. Use an address card and an external map link when present.
- Avoid fixed-header clipping, horizontal overflow, invisible inputs and text
  overlap on mobile or desktop.
- Prefer quiet premium composition, clear hierarchy, strong CTA, readable
  contrast and mobile-first sections.
"""


@dataclass(frozen=True)
class OpenUIRenderResult:
    html: str
    body_html: str
    model: str
    attempts: list[dict[str, Any]]
    elapsed_ms: int


class OpenUIRenderError(RuntimeError):
    """Raised when OpenUI primary and fallback attempts cannot produce a site."""


def render_openui_site(
    builder_prompt: str,
    *,
    facts: dict[str, Any] | None = None,
    repair_context: dict[str, Any] | None = None,
    primary_model: str = "sonnet",
    fallback_model: str = "opus",
    max_tokens: int = 8000,
    temperature: float = 0.35,
) -> OpenUIRenderResult:
    """Generate a publishable HTML document using the OpenUI contract."""
    started = time.time()
    facts = facts or {}
    attempts: list[dict[str, Any]] = []
    prompt = _compose_user_prompt(builder_prompt, repair_context=repair_context)

    for index, model in enumerate([primary_model, fallback_model], start=1):
        if not model:
            continue
        attempt_started = time.time()
        try:
            raw = _call_openui_llm(
                prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature if index == 1 else min(temperature, 0.25),
                facts=facts,
            )
            body_html = extract_openui_html(raw)
            document = build_openui_document(body_html)
            validate_openui_document(
                document, body_html, facts, source_text=builder_prompt
            )
            attempts.append(
                {
                    "model": model,
                    "status": "success",
                    "elapsed_ms": int((time.time() - attempt_started) * 1000),
                    "html_chars": len(document),
                }
            )
            return OpenUIRenderResult(
                html=document,
                body_html=body_html,
                model=model,
                attempts=attempts,
                elapsed_ms=int((time.time() - started) * 1000),
            )
        except Exception as exc:
            attempts.append(
                {
                    "model": model,
                    "status": "failed",
                    "elapsed_ms": int((time.time() - attempt_started) * 1000),
                    "error": str(exc)[:500],
                }
            )
            prompt = _compose_user_prompt(
                builder_prompt,
                repair_context={
                    "validation_errors": str(exc),
                    "previous_html": raw if "raw" in locals() else "",
                },
            )

    raise OpenUIRenderError(f"OpenUI renderer falhou: {attempts}")


def extract_openui_html(raw: str) -> str:
    """Extract body HTML from common OpenUI/LLM response formats."""
    text = (raw or "").strip()
    if not text:
        raise OpenUIRenderError("resposta vazia")
    fence = re.search(r"```(?:html)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    text = re.sub(r"^---[\s\S]*?---\s*", "", text).strip()
    body_match = re.search(r"<body[^>]*>([\s\S]*?)</body>", text, re.IGNORECASE)
    if body_match:
        text = body_match.group(1).strip()
    if re.search(r"<!doctype|<html\b", text, re.IGNORECASE):
        return text
    if "<" not in text or ">" not in text:
        raise OpenUIRenderError("resposta nao contem HTML")
    return text


def build_openui_document(body_or_document: str) -> str:
    """Wrap OpenUI body output in FraLib's publishable static document."""
    content = (body_or_document or "").strip()
    if re.search(r"<!doctype|<html\b", content, re.IGNORECASE):
        document = content
        if "data-renderer=" not in document[:400].lower():
            document = re.sub(
                r"<html\b",
                '<html data-renderer="builder" data-builder-engine="openui"',
                document,
                count=1,
                flags=re.IGNORECASE,
            )
        return document

    return f"""<!doctype html>
<html lang="pt-BR" data-renderer="builder" data-builder-engine="openui">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="FraLib OpenUI Builder">
  <title>FraLib Site</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root {{
      --background: 12 12 14;
      --foreground: 248 250 252;
      --primary: 225 29 72;
      --primary-foreground: 255 255 255;
      --secondary: 210 179 110;
      --secondary-foreground: 12 12 14;
      --muted: 39 39 42;
      --muted-foreground: 161 161 170;
      --card: 24 24 27;
      --card-foreground: 250 250 250;
      --border: 63 63 70;
      --input: 39 39 42;
      --ring: 210 179 110;
      --accent: 127 29 29;
      --accent-foreground: 255 255 255;
    }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background: rgb(var(--background));
      color: rgb(var(--foreground));
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    img {{ max-width: 100%; height: auto; }}
    .bg-background {{ background-color: rgb(var(--background)); }}
    .text-foreground {{ color: rgb(var(--foreground)); }}
    .bg-primary {{ background-color: rgb(var(--primary)); }}
    .text-primary {{ color: rgb(var(--primary)); }}
    .text-primary-foreground {{ color: rgb(var(--primary-foreground)); }}
    .bg-secondary {{ background-color: rgb(var(--secondary)); }}
    .text-secondary {{ color: rgb(var(--secondary)); }}
    .text-secondary-foreground {{ color: rgb(var(--secondary-foreground)); }}
    .bg-card {{ background-color: rgb(var(--card)); }}
    .text-card-foreground {{ color: rgb(var(--card-foreground)); }}
    .text-muted-foreground {{ color: rgb(var(--muted-foreground)); }}
    .border-border {{ border-color: rgb(var(--border)); }}
  </style>
</head>
<body>
{content}
</body>
</html>"""


def validate_openui_document(
    document: str,
    body_html: str,
    facts: dict[str, Any] | None = None,
    *,
    source_text: str = "",
) -> None:
    """Small publication gate: completeness, no broken OpenUI placeholders, facts."""
    low = document.lower()
    if len(document) < 1500:
        raise OpenUIRenderError("HTML menor que o minimo publicavel")
    if "</html>" not in low and "<html" in low:
        raise OpenUIRenderError("HTML completo sem fechamento </html>")
    forbidden = ("lorem ipsum", "/icons/", "source.unsplash.com")
    found = [item for item in forbidden if item in low]
    if found:
        raise OpenUIRenderError(f"HTML contem placeholder invalido: {', '.join(found)}")
    facts = facts or {}
    business = facts.get("business") or {}
    name = str(business.get("name") or "").strip()
    if name and not _contains_business_identity(document, name):
        raise OpenUIRenderError(f"nome confirmado ausente: {name}")
    phone = str(business.get("whatsapp") or business.get("phone") or "").strip()
    if phone and _digits(phone)[-8:] and _digits(phone)[-8:] not in _digits(document):
        raise OpenUIRenderError("telefone/WhatsApp confirmado ausente")
    rating = str(business.get("rating") or "").strip().replace(",", ".")
    if rating and rating not in document.replace(",", "."):
        raise OpenUIRenderError(f"rating confirmado ausente: {rating}")
    if "0.6" in document and rating != "0.6":
        raise OpenUIRenderError("HTML contem rating alucinado 0.6")
    _reject_active_content(body_html)
    _reject_unconfirmed_operational_claims(document, source_text)
    if not body_html.strip():
        raise OpenUIRenderError("body HTML vazio")


def _call_openui_llm(
    user_prompt: str,
    *,
    model: str,
    max_tokens: int,
    temperature: float,
    facts: dict[str, Any] | None = None,
) -> str:
    try:
        from agents.llm_direct import call_claude
    except Exception:
        from llm_direct import call_claude

    # Compila system prompt final = base + contratos FraLib (SEO, Design,
    # Motion, A11y, Factual, LGPD, Deploy) com dados do lead.
    final_system_prompt = OPENUI_SYSTEM_PROMPT
    if facts:
        try:
            from services.openui_contracts import build_openui_context_block
        except Exception:
            try:
                from backend.services.openui_contracts import build_openui_context_block
            except Exception:
                build_openui_context_block = None
        if build_openui_context_block:
            final_system_prompt = OPENUI_SYSTEM_PROMPT + "\n\n" + build_openui_context_block(facts)

    return call_claude(
        final_system_prompt,
        user_prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        agent_name="builder_renderer",
        respect_agent_config=False,
        enable_context=False,
    )


def _compose_user_prompt(
    builder_prompt: str, *, repair_context: dict[str, Any] | None = None
) -> str:
    prompt = f"""Use this FraLib Prompt Agent request as the complete business brief.

Return only the BODY HTML for the page. Do not include doctype, html, head,
body tags, markdown fences or explanations.

FRA LIB BUILDER REQUEST:
{builder_prompt}
"""
    if repair_context:
        errors = repair_context.get("validation_errors") or ""
        previous = str(repair_context.get("previous_html") or "")[:3500]
        prompt += f"""

The previous generation failed validation. Correct the issue without changing
confirmed facts.

Validation errors:
{errors}

Previous HTML excerpt:
{_html.escape(previous)}
"""
    return prompt


def _digits(value: str) -> str:
    return re.sub(r"\D+", "", value or "")


def _contains_business_identity(document: str, name: str) -> bool:
    low = document.lower()
    normalized_name = name.lower()
    if normalized_name in low:
        return True
    tokens = [
        token
        for token in re.split(r"[^a-zA-Z0-9À-ÿ]+", normalized_name)
        if len(token) >= 4
    ]
    if not tokens:
        return False
    return all(token in low for token in tokens)


def _reject_active_content(body_html: str) -> None:
    """Reject active browser behavior in generated body HTML.

    FraLib publishes generated sites under public web origins. The Builder may
    decide layout freely, but it cannot ship executable code.
    """
    text = body_html or ""
    low = text.lower()
    blocked_tags = ("<script", "<iframe", "<object", "<embed")
    found_tags = [tag for tag in blocked_tags if tag in low]
    if found_tags:
        raise OpenUIRenderError(
            "HTML contem conteudo ativo proibido: " + ", ".join(found_tags)
        )
    if re.search(r"\son[a-z0-9_-]+\s*=", text, re.IGNORECASE):
        raise OpenUIRenderError("HTML contem event handler inline proibido")
    if re.search(r"\b(?:href|src|action)\s*=\s*['\"]?\s*(?:javascript|data|vbscript):", text, re.IGNORECASE):
        raise OpenUIRenderError("HTML contem URL ativa proibida")


def _reject_unconfirmed_operational_claims(document: str, source_text: str) -> None:
    low_doc = document.lower()
    low_source = (source_text or "").lower()
    guarded_patterns = {
        "ingredientes importados": r"\bimportad[oa]s?\b",
        "ano de fundacao/desde": r"\bdesde\s+(19|20)\d{2}\b",
        "tempo de entrega": r"\b\d{1,3}\s*minutos\b",
        "premiacao": r"\bpremiad[oa]s?\b|\bpr[eê]mio\b",
        "certificacao": r"\bcertificad[oa]s?\b|\bcertifica[cç][aã]o\b",
    }
    for label, pattern in guarded_patterns.items():
        if re.search(pattern, low_doc, re.IGNORECASE) and not re.search(
            pattern, low_source, re.IGNORECASE
        ):
            raise OpenUIRenderError(f"claim operacional nao confirmada: {label}")
