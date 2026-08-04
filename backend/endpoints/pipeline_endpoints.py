"""Pipeline endpoints — router agregador.

Importa rotas dos modulos especializados:
  - pipeline_execution: execucao pesada (sem rotas, so funcoes)
  - pipeline_crud: rotas CRUD (ciclos, fila, status, reprocessar)
  - pipeline_trigger: rotas de controle (iniciar, parar, reset, etc.)
  - pipeline_monitoring: rotas de monitoramento (cooldown, analytics, stats)
  - pipeline_edit_endpoints: rotas de edicao de site (editar-secao, listar-secoes)
"""
from fastapi import APIRouter

from .pipeline_execution import router as execution_router
from .pipeline_crud import router as crud_router
from .pipeline_trigger import router as trigger_router
from .pipeline_monitoring import router as monitoring_router
from .pipeline_edit_endpoints import router as edit_router

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

router.include_router(execution_router)
router.include_router(crud_router)
router.include_router(trigger_router)
router.include_router(monitoring_router)
router.include_router(edit_router)
