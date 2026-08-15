"""
Centralized router registration.

This module replaces the ~30 individual import + app.include_router()
pairs that used to live in server.py, reducing boilerplate and keeping
routing in one place.
"""
import sys
import os

# Ensure legacy absolute-import endpoints resolve both locally and on VPS.
# Some endpoint modules (auth_endpoints, etc.) use bare imports like
# `from database import get_db` that require `.../backend` and the repo root
# on sys.path when the app is launched via `uvicorn server:app`.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_BACKEND_DIR = os.path.join(_REPO_ROOT, "backend")
for _p in (_BACKEND_DIR, _REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)



def register_routers(app) -> None:
    """Register all endpoint routers on the given FastAPI app."""
    import auth_endpoints
    import dashboard_endpoints
    import pipeline_endpoints
    import pipeline_edit_endpoints
    import sse_endpoints
    import credits_endpoints
    import users_endpoints
    import leads_endpoints
    import beta_endpoints
    import whatsapp_endpoints
    import llm_endpoints
    import api_usage_endpoints
    import superadmin_endpoints
    import provider_keys_endpoints
    import provider_alerts_endpoints
    import agent_config_endpoints
    import falhas_endpoints
    import site_editor_endpoints
    import tracking_endpoints
    import cron_endpoints
    import blog_endpoints
    import obs_endpoints
    import queue_endpoints
    import abtest_endpoints
    import admin_pipeline_control_endpoints
    import agentes_endpoints
    import lead_supply_endpoints
    import franz_insights_endpoints

    routers: list[tuple] = [
        (auth_endpoints.router, "auth"),
        (dashboard_endpoints.router, "dashboard"),
        (pipeline_endpoints.router, "pipeline"),
        (pipeline_edit_endpoints.router, "pipeline_edit"),
        (sse_endpoints.router, "sse"),
        (credits_endpoints.router, "credits"),
        (users_endpoints.router, "users"),
        (leads_endpoints.router, "leads"),
        (beta_endpoints.router, "beta"),
        (whatsapp_endpoints.router, "whatsapp"),
        (llm_endpoints.router, "llm"),
        (api_usage_endpoints.router, "api_usage"),
        (superadmin_endpoints.router, "superadmin"),
        (provider_keys_endpoints.router, "provider_keys"),
        (provider_alerts_endpoints.router, "provider_alerts"),
        (agent_config_endpoints.router, "agent_config"),
        (falhas_endpoints.router, "falhas"),
        (site_editor_endpoints.router, "site_editor"),
        (tracking_endpoints.router, "tracking"),
        (cron_endpoints.router, "cron"),
        (blog_endpoints.router, "blog"),
        (obs_endpoints.router, "obs"),
        (queue_endpoints.router, "queue"),
        (abtest_endpoints.router, "abtest"),
        (admin_pipeline_control_endpoints.router, "admin_pipeline_control"),
        (agentes_endpoints.router, "agentes"),
        (lead_supply_endpoints.router, "lead_supply"),
        (franz_insights_endpoints.router, "franz_insights"),
    ]

    for router, name in routers:
        app.include_router(router)
