"""
Agent RAG - Sistema de Recuperação de Contexto
Versão 3.0 - Todos os chunks carregados, blocos por agente
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

RAG_DIR = Path(__file__).parent / "rag_knowledge"
_rag_usage_tracker: Dict[str, bool] = {}


def chunk_rag_content(content: str, max_chars: int = 25000) -> List[str]:
    """Divide conteúdo RAG em chunks — retorna TODOS"""
    if len(content) <= max_chars:
        return [content]
    chunks = []
    lines = content.split("\n")
    current_chunk: List[str] = []
    current_size = 0
    for line in lines:
        line_size = len(line) + 1
        if current_size + line_size > max_chars and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_size = line_size
        else:
            current_chunk.append(line)
            current_size += line_size
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    return chunks if chunks else [content[:max_chars]]


def buscar_contexto_rag(query: str, agente: str, top_k: int = 5) -> str:
    """Busca contexto RAG local para o agente ativo."""
    try:
        if not RAG_DIR.exists():
            RAG_DIR.mkdir(parents=True, exist_ok=True)

        agente_lower = agente.lower()
        rag_file = RAG_DIR / f"{agente_lower}.md"
        content = ""

        if rag_file.exists():
            with open(rag_file, "r", encoding="utf-8") as f:
                content = f.read()

        # Carregar blocos adicionais {agente}_*.md em ordem alfabetica
        extra_files = sorted(RAG_DIR.glob(f"{agente_lower}_*.md"))
        for ef in extra_files:
            with open(ef, "r", encoding="utf-8") as f:
                content = content + "\n\n" + f.read()

        if content:
            chunks = chunk_rag_content(content, max_chars=25000)
            full_context = "\n\n".join(chunks)
            print(
                f"[RAG Local] OK {agente}: {len(full_context)} chars ({len(chunks)} chunks, {1 + len(extra_files)} arquivos)"
            )
            return full_context

        # Fallback: arquivo geral
        general_file = RAG_DIR / "general.md"
        if general_file.exists():
            with open(general_file, "r", encoding="utf-8") as f:
                content = f.read()
            chunks = chunk_rag_content(content, max_chars=25000)
            full_context = "\n\n".join(chunks)
            print(
                f"[RAG Local] WARN Contexto geral para {agente}: {len(full_context)} chars"
            )
            return full_context

        print(f"[RAG Local] WARN Nenhum contexto para {agente}")
        return ""

    except Exception as e:
        print(f"[RAG Local] ERRO: {e}")
        return ""


def format_rag_prompt(base_prompt: str, rag_context: str) -> str:
    """Formata prompt com contexto RAG"""
    if not rag_context:
        return base_prompt
    rag_section = f"CONTEXTO RAG (conhecimento da base):\n{rag_context}\n\n---\n\n"
    return rag_section + base_prompt


def get_agent_temperature(agente: str) -> float:
    """Temperatura ideal por agente"""
    temperatures = {
        "caio": 0.3,
        "curadoria": 0.5,
        "designer": 0.7,
        "agente_nicho": 0.8,
        "builder_renderer": 0.82,
        "validador": 0.2,
        "bryan": 0.4,
    }
    return temperatures.get(agente, 0.7)


def load_agent_context(agente: str) -> str:
    return buscar_contexto_rag(f"contexto {agente}", agente, top_k=3)


def build_enhanced_prompt(base_prompt: str, agente: str) -> str:
    rag_context = load_agent_context(agente)
    return format_rag_prompt(base_prompt, rag_context)


def check_rag_usage(agente: str) -> bool:
    return _rag_usage_tracker.get(agente, False)


def reset_rag_tracker(agente: Optional[str] = None):
    global _rag_usage_tracker
    if agente:
        _rag_usage_tracker[agente] = False
    else:
        _rag_usage_tracker = {}


def mark_rag_used(agente: str):
    _rag_usage_tracker[agente] = True
    print(f"[RAG Local] OK RAG marcado como usado para {agente}")
