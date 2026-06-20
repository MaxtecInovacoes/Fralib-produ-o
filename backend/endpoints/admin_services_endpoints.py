"""
admin_services_endpoints.py
============================
Endpoints administrativos para visualizar/controlar servicos FraLib.

Abstrai systemd vs PM2 via backend.services.service_manager.

Rotas:
  GET  /api/admin/services              - Lista todos os servicos
  GET  /api/admin/services/{name}       - Detalhes de um servico
  GET  /api/admin/services/{name}/logs  - Ultimas N linhas de log
  POST /api/admin/services/{name}/restart - Reinicia (acao destrutiva, requer role)
  GET  /api/admin/runtime               - Qual runtime esta ativo (systemd/pm2)
"""
from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Depends, Query, Request

from backend.services.service_manager import (
    ServiceManager,
    FRA_SERVICES,
    PM2_TO_SYSTEMD,
    detect_runtime,
    list_services,
    get_manager,
)

router = APIRouter(prefix="/api/admin", tags=["admin-services"])


def require_admin(request: Request):
    """Verifica que o requester e admin (reutiliza padrao do projeto)."""
    # O FraLib ja tem middleware de auth; aqui so bloqueamos explicitamente
    user = getattr(request.state, "user", None)
    if not user or not user.get("is_admin"):
        # Em dev, aceitar; em prod, retornar 403
        if os.getenv("FRALIB_ENV") == "production":
            raise HTTPException(status_code=403, detail="Acesso restrito a admin")
    return user


@router.get("/services")
async def api_list_services(request: Request) -> dict[str, Any]:
    """Lista todos os servicos FraLib com status."""
    require_admin(request)
    mgr = get_manager()
    summary = mgr.summary()
    # Adiciona informacao do runtime ativo
    summary["primary_runtime"] = detect_runtime()
    return summary


@router.get("/services/{name}")
async def api_service_detail(name: str, request: Request) -> dict[str, Any]:
    """Detalhes de um servico especifico."""
    require_admin(request)
    mgr = get_manager()

    # Aceitar nomes PM2 antigos (compatibilidade)
    canonical = PM2_TO_SYSTEMD.get(name, name)
    if canonical not in FRA_SERVICES and name not in FRA_SERVICES:
        raise HTTPException(status_code=404, detail=f"Servico desconhecido: {name}")

    info = mgr.status(canonical if canonical in FRA_SERVICES else name)
    return {
        "name": info.name,
        "runtime": info.runtime,
        "status": info.status,
        "pid": info.pid,
        "memory_mb": info.memory_mb,
        "cpu_percent": info.cpu_percent,
        "uptime_seconds": info.uptime_seconds,
        "restarts": info.restarts,
        "last_error": info.last_error,
        "raw_keys": list(info.raw.keys()) if info.raw else [],
    }


@router.get("/services/{name}/logs")
async def api_service_logs(
    name: str,
    request: Request,
    lines: int = Query(default=100, ge=1, le=1000)
) -> dict[str, Any]:
    """Ultimas N linhas de log do servico."""
    require_admin(request)
    mgr = get_manager()
    canonical = PM2_TO_SYSTEMD.get(name, name)
    effective = canonical if canonical in FRA_SERVICES else name

    logs = mgr.logs(effective, lines)
    return {
        "name": effective,
        "lines": lines,
        "log": logs,
        "runtime": mgr.resolve(effective)[0],
    }


@router.post("/services/{name}/restart")
async def api_service_restart(name: str, request: Request) -> dict[str, Any]:
    """Reinicia um servico (acao admin)."""
    user = require_admin(request)
    mgr = get_manager()
    canonical = PM2_TO_SYSTEMD.get(name, name)
    effective = canonical if canonical in FRA_SERVICES else name

    ok, msg = mgr.restart(effective)
    if not ok:
        raise HTTPException(status_code=500, detail=f"Falha ao reiniciar: {msg}")
    return {"ok": True, "service": effective, "message": msg}


@router.get("/runtime")
async def api_runtime(request: Request) -> dict[str, Any]:
    """Retorna o runtime primario (systemd/pm2)."""
    require_admin(request)
    return {
        "runtime": detect_runtime(),
        "has_systemd": get_manager().has_systemd,
        "has_pm2": get_manager().has_pm2,
    }


@router.get("/incidents")
async def api_incidents(request: Request) -> dict[str, Any]:
    """Incidentes recentes do Hermes (last 20)."""
    require_admin(request)
    # Reutiliza logica do hermes_watchdog
    try:
        from backend.services.hermes_watchdog import list_recent_incidents
        incidents = list_recent_incidents(limit=20)
        return {"incidents": incidents}
    except Exception as e:
        return {"incidents": [], "error": str(e)}


# Compat: rota legada usada pelo frontend atual
@router.get("/pm2")
async def api_pm2_legacy(request: Request) -> dict[str, Any]:
    """Compatibilidade com frontend que ainda consome 'pm2' como chave."""
    require_admin(request)
    summary = get_manager().summary()
    return {
        "status": "ok" if summary["primary_runtime"] != "none" else "error",
        "processes": summary["services"],  # mesmo formato do jlist
        "primary_runtime": summary["primary_runtime"],
    }