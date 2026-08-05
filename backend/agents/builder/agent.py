"""
Builder Agent — OpenUI HTTP Client.

Receives a DesignerPRD and calls the OpenUI service (port 3333)
to generate the complete HTML site via chunked LLM generation.
"""
import os
import json
import time
import requests

OPENUI_URL = os.environ.get("OPENUI_URL", "http://localhost:3333")
GENERATE_ENDPOINT = f"{OPENUI_URL}/generate-chunked"
HEALTH_ENDPOINT = f"{OPENUI_URL}/health"


class BuildResult:
    """Result of a site build."""
    def __init__(self, html: str, model: str = "", success: bool = True, error: str = ""):
        self.html = html
        self.model = model
        self.success = success
        self.error = error


def _wait_for_openui(max_wait: int = 30) -> bool:
    """Wait for OpenUI service to be ready."""
    for _ in range(max_wait):
        try:
            r = requests.get(HEALTH_ENDPOINT, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _prd_to_spec(prd) -> dict:
    """Convert DesignerPRD to JSON spec for OpenUI service."""
    sections = []
    for s in prd.sections:
        sections.append({
            "name": s.name,
            "title": s.title,
            "content": getattr(s, "content", getattr(s, "body", "")),
        })

    color_palette = {}
    if hasattr(prd, "color_palette") and prd.color_palette:
        cp = prd.color_palette
        if hasattr(cp, "model_dump"):
            color_palette = cp.model_dump()
        elif hasattr(cp, "dict"):
            color_palette = cp.dict()
        else:
            color_palette = {k: v for k, v in vars(cp).items() if not k.startswith("_")}

    animations = []
    if hasattr(prd, "animations") and prd.animations:
        for anim in prd.animations:
            if hasattr(anim, "model_dump"):
                animations.append(anim.model_dump())
            elif hasattr(anim, "dict"):
                animations.append(anim.dict())
            else:
                animations.append({k: v for k, v in vars(anim).items() if not k.startswith("_")})

    spec = {
        "business_name": prd.business_name,
        "sections": sections,
        "color_palette": color_palette,
        "typography": getattr(prd, "typography", {}),
        "animations": animations,
        "reviews_count": getattr(prd, "reviews_count", 0),
        "reviews_rating": getattr(prd, "reviews_rating", 0.0),
        "reviews_list": getattr(prd, "reviews_list", []),
        "address": getattr(prd, "address", ""),
        "phone": getattr(prd, "phone", ""),
        "hours": getattr(prd, "hours", None),
        "photos": getattr(prd, "photos", []),
    }
    return spec


def render_site(prd, usar_llm: bool = True) -> BuildResult:
    """
    Generate HTML site from DesignerPRD via OpenUI chunked generation.

    Args:
        prd: DesignerPRD object with all design specifications.
        usar_llm: If True, use LLM generation. If False, use template fallback.

    Returns:
        BuildResult with html, model, and success status.
    """
    if not usar_llm:
        return BuildResult(html="", model="", success=False, error="Template fallback not implemented")

    # Ensure OpenUI is ready
    if not _wait_for_openui(max_wait=10):
        return BuildResult(html="", model="", success=False, error="OpenUI service not available at " + OPENUI_URL)

    # Convert PRD to spec
    spec = _prd_to_spec(prd)

    # Call OpenUI chunked generation
    max_retries = 3
    retry_delays = [30, 60, 120]  # seconds — OpenUI handles 529 with its own retry

    last_error = ""
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                GENERATE_ENDPOINT,
                json={"prd": spec},
                headers={"Content-Type": "application/json"},
                timeout=600,  # 10 min max for full generation
            )

            if resp.status_code == 200:
                data = resp.json()
                html = data.get("html", "")
                model = data.get("model", "")
                if html and len(html) > 1000:
                    return BuildResult(html=html, model=model, success=True)
                return BuildResult(html="", model=model, success=False,
                                   error=f"HTML too short: {len(html)} chars")

            elif resp.status_code == 529:
                last_error = f"OpenUI 529 (overloaded) attempt {attempt + 1}"
                if attempt < max_retries - 1:
                    time.sleep(retry_delays[attempt])
                    continue

            else:
                last_error = f"OpenUI HTTP {resp.status_code}: {resp.text[:200]}"
                return BuildResult(html="", model="", success=False, error=last_error)

        except requests.exceptions.Timeout:
            last_error = f"OpenUI timeout (600s) attempt {attempt + 1}"
            if attempt < max_retries - 1:
                time.sleep(retry_delays[attempt])
                continue
            return BuildResult(html="", model="", success=False, error=last_error)

        except Exception as e:
            last_error = f"OpenUI error: {str(e)}"
            return BuildResult(html="", model="", success=False, error=last_error)

    return BuildResult(html="", model="", success=False, error=last_error)
