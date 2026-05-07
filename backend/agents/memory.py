"""
Sistema de Memória Simples - JSON
Substitui SQLite do Agno por arquivos JSON
"""
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

MEMORY_DIR = "/root/FRALIB_FINAL/agents_python/memory"

def ensure_memory_dir():
    """Garante que diretório de memória existe"""
    os.makedirs(MEMORY_DIR, exist_ok=True)

def salvar_memoria(session_id: str, dados: Dict[str, Any]) -> None:
    """
    Salva memória de uma sessão

    Args:
        session_id: ID da sessão (ex: "lead_123", "caio_session")
        dados: Dados a salvar
    """
    ensure_memory_dir()

    memory_file = os.path.join(MEMORY_DIR, f"{session_id}.json")

    # Adicionar timestamp
    dados['_updated_at'] = datetime.now().isoformat()

    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

    print(f"[Memory] Salvo: {session_id}")

def carregar_memoria(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Carrega memória de uma sessão

    Args:
        session_id: ID da sessão

    Returns:
        Dados salvos ou None se não existir
    """
    ensure_memory_dir()

    memory_file = os.path.join(MEMORY_DIR, f"{session_id}.json")

    if not os.path.exists(memory_file):
        return None

    with open(memory_file, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    print(f"📂 [Memory] Carregado: {session_id}")
    return dados

def limpar_memoria(session_id: str) -> None:
    """
    Remove memória de uma sessão

    Args:
        session_id: ID da sessão
    """
    ensure_memory_dir()

    memory_file = os.path.join(MEMORY_DIR, f"{session_id}.json")

    if os.path.exists(memory_file):
        os.remove(memory_file)
        print(f"🗑️ [Memory] Removido: {session_id}")
