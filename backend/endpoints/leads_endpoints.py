"""
Leads Endpoints - Wrapper thin
Agrupa todos os routers de leads em um único router principal.
"""
from fastapi import APIRouter

# Importar routers de cada módulo
from backend.endpoints.leads_crud import router as router_crud
from backend.endpoints.leads_crud_sdr import router as router_sdr
from backend.endpoints.leads_queries import router as router_queries

# Router principal
router = APIRouter(prefix="/api/leads", tags=["leads"])

# Registrar rotas CRUD
for route in router_crud.routes:
    router.routes.append(route)

# Registrar rotas SDR
for route in router_sdr.routes:
    router.routes.append(route)

# Registrar rotas de Queries
for route in router_queries.routes:
    router.routes.append(route)
