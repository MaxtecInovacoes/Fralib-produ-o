"""
Sistema de Memoria Simples - JSON
Substitui SQLite do Agno por arquivos JSON.

Multi-tenant: todas as memorias sao escopadas a um user_id. O parametro
user_id e OBRIGATORIO em todas as funcoes publicas para impedir vazamento
de contexto de leads entre tenants distintos.
"""
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

MEMORY_DIR = "/root/FRALIB_FINAL/agents_python/memory"


def ensure_memory_dir(user_id: int) -> str:
    """Garante que diretorio de memoria do tenant existe e retorna o path."""
    tenant_dir = os.path.join(MEMORY_DIR, f"u{int(user_id)}")
    os.makedirs(tenant_dir, exist_ok=True)
    return tenant_dir


def _validar_user_id(user_id) -> int:
    if not user_id:
        raise ValueError("user_id obrigatorio para acessar memoria (multi-tenant)")
    return int(user_id)


def salvar_memoria(session_id: str, dados: Dict[str, Any], user_id: int = None) -> None:
    """
    Salva memoria de uma sessao no escopo do user_id.

    Args:
        session_id: ID da sessao (ex: "lead_123", "caio_session")
        dados: Dados a salvar
        user_id: ID do usuario dono da memoria (obrigatorio)
    """
    uid = _validar_user_id(user_id)
    tenant_dir = ensure_memory_dir(uid)

    memory_file = os.path.join(tenant_dir, f"{session_id}.json")

    dados['_updated_at'] = datetime.now().isoformat()
    dados['_user_id'] = uid

    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

    print(f"[Memory] Salvo: u{uid}/{session_id}")


def carregar_memoria(session_id: str, user_id: int = None) -> Optional[Dict[str, Any]]:
    """
    Carrega memoria de uma sessao escopada ao user_id.

    Args:
        session_id: ID da sessao
        user_id: ID do usuario dono da memoria (obrigatorio)

    Returns:
        Dados salvos ou None se nao existir
    """
    uid = _validar_user_id(user_id)
    tenant_dir = ensure_memory_dir(uid)

    memory_file = os.path.join(tenant_dir, f"{session_id}.json")

    if not os.path.exists(memory_file):
        return None

    with open(memory_file, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    print(f"[Memory] Carregado: u{uid}/{session_id}")
    return dados


def limpar_memoria(session_id: str, user_id: int = None) -> None:
    """
    Remove memoria de uma sessao escopada ao user_id.

    Args:
        session_id: ID da sessao
        user_id: ID do usuario dono da memoria (obrigatorio)
    """
    uid = _validar_user_id(user_id)
    tenant_dir = ensure_memory_dir(uid)

    memory_file = os.path.join(tenant_dir, f"{session_id}.json")

    if os.path.exists(memory_file):
        os.remove(memory_file)
        print(f"[Memory] Removido: u{uid}/{session_id}")
