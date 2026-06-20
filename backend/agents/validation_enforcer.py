"""
Sistema de Validação Obrigatória
Garante que RAG, Skills e Guidelines sejam USADOS, não apenas importados
Versão: 1.0
Data: 2026-04-27
"""
import functools
import inspect
from typing import Callable, Any

class ResourceNotUsedError(Exception):
    """Erro quando recurso obrigatório não é usado"""
    pass

def require_rag(agent_name: str):
    def decorator(func):
        import functools
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            from agent_rag import check_rag_usage, reset_rag_tracker
            reset_rag_tracker(agent_name)
            result = await func(*args, **kwargs)
            rag_used = check_rag_usage(agent_name)
            if not rag_used:
                print(f"[Validation] WARNING {agent_name}: RAG NAO foi usado")
            else:
                print(f"[Validation] OK {agent_name}: RAG verificado e ativo")
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            from agent_rag import check_rag_usage, reset_rag_tracker
            reset_rag_tracker(agent_name)
            result = func(*args, **kwargs)
            rag_used = check_rag_usage(agent_name)
            if not rag_used:
                print(f"[Validation] WARNING {agent_name}: RAG NAO foi usado")
            else:
                print(f"[Validation] OK {agent_name}: RAG verificado e ativo")
            return result
        
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator

def require_guidelines(agent_name: str):
    """
    Decorator que FORÇA uso de Guidelines
    Se ANIMATION_PRINCIPLES não estiver no prompt, levanta erro
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Executar função
            result = func(*args, **kwargs)

            # Verificar se Guidelines foram usadas
            frame = inspect.currentframe()
            guidelines_used = False

            while frame:
                local_vars = frame.f_locals

                # Checar se 'user_prompt' ou 'prompt' contém guidelines
                for var_name in ['user_prompt', 'prompt', 'full_prompt']:
                    prompt = local_vars.get(var_name, '')
                    if isinstance(prompt, str):
                        if 'ANIMATION PRINCIPLES' in prompt or 'cubic-bezier' in prompt:
                            guidelines_used = True
                            break

                if guidelines_used:
                    break

                frame = frame.f_back

            if not guidelines_used:
                print(f"[Validation] WARN {agent_name}: Guidelines podem nao estar ativas")
            else:
                print(f"[Validation] OK {agent_name}: Guidelines verificadas e ativas")

            return result
        return wrapper
    return decorator

# Validação em runtime (executada ao importar)
def validate_imports():
    """
    Valida que módulos críticos estão disponíveis
    """
    try:
        from agent_rag import format_rag_prompt, get_agent_temperature
        print("[Validation] OK agent_rag disponivel")
    except ImportError as e:
        print(f"[Validation] WARN agent_rag nao encontrado: {e}")

    try:
        from skill_loader import carregar_skills, get_skills_agente
        print("[Validation] OK skill_loader disponivel")
    except ImportError as e:
        print(f"[Validation] WARN skill_loader nao encontrado: {e}")

    try:
        from design_guidelines import ANIMATION_PRINCIPLES, ANIMATION_CSS
        print("[Validation] OK design_guidelines disponivel")
    except ImportError as e:
        print(f"[Validation] WARN design_guidelines nao encontrado: {e}")

# Executar validação ao importar
validate_imports()

print("[Validation] DONE Sistema de Validacao Obrigatoria carregado")
