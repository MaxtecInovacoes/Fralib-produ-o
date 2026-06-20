"""
Módulo de contexto LLM para o pipeline.

Fornece a função `set_llm_context_for_pipeline` que configura o contexto
do LLM (user_id, run_id, job_id) para rastreamento de consumo por usuário.
"""


def set_llm_context_for_pipeline(tenant_id=None, run_id=None, job_id=None):
    """
    Configura o contexto LLM para rastreamento de consumo por usuário.

    Args:
        tenant_id: ID do tenant/usuário para rastreamento de consumo
        run_id: ID da execução do pipeline
        job_id: ID do job (opcional)
    """
    import importlib

    for _module_name in ("llm_direct", "agents.llm_direct"):
        try:
            _mod = importlib.import_module(_module_name)
            if hasattr(_mod, "set_llm_context"):
                _mod.set_llm_context(user_id=tenant_id, run_id=run_id, job_id=job_id)
            elif hasattr(_mod, "set_current_user_id"):
                _mod.set_current_user_id(tenant_id)
        except Exception:
            pass
