"""
Sistema de Checkpoint do Pipeline FraLib
Salva estado de cada agente para retomar de onde parou.

Multi-tenant: o pipeline_id e prefixado com 'u{user_id}-' para evitar que
dois usuarios do mesmo nicho/cidade sobrescrevam o checkpoint um do outro.
"""
import json
import re
import os
from datetime import datetime

CHECKPOINT_DIR = "/root/fralib/checkpoints"
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

_VALID_PIPELINE_ID = re.compile(r"^[a-z0-9][a-z0-9\-]*$")


def _safe_pipeline_id(pipeline_id: str) -> str:
    """Sanitiza pipeline_id pra evitar path traversal."""
    if not pipeline_id or not _VALID_PIPELINE_ID.match(pipeline_id):
        raise ValueError(f"pipeline_id invalido: {pipeline_id!r}")
    return pipeline_id


def get_checkpoint_path(pipeline_id: str) -> str:
    pid = _safe_pipeline_id(pipeline_id)
    return f"{CHECKPOINT_DIR}/{pid}.json"


def salvar_checkpoint(pipeline_id: str, agente: str, dados: dict):
    """Salva estado do agente no checkpoint"""
    path = get_checkpoint_path(pipeline_id)
    checkpoint = carregar_checkpoint(pipeline_id) or {
        "pipeline_id": pipeline_id,
        "criado_em": datetime.now().isoformat(),
        "agentes": {}
    }
    checkpoint["agentes"][agente] = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "dados": dados
    }
    checkpoint["ultimo_agente"] = agente
    checkpoint["atualizado_em"] = datetime.now().isoformat()
    with open(path, "w") as f:
        json.dump(checkpoint, f, ensure_ascii=False, default=str)
    print(f"[Checkpoint] Salvo: {agente} -> {path}")


def carregar_checkpoint(pipeline_id: str) -> dict:
    """Carrega checkpoint existente"""
    try:
        path = get_checkpoint_path(pipeline_id)
    except ValueError:
        return None
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def agente_concluido(pipeline_id: str, agente: str) -> bool:
    """Verifica se agente ja foi concluido"""
    checkpoint = carregar_checkpoint(pipeline_id)
    if not checkpoint:
        return False
    return agente in checkpoint.get("agentes", {})


def get_dados_agente(pipeline_id: str, agente: str) -> dict:
    """Recupera dados salvos de um agente"""
    checkpoint = carregar_checkpoint(pipeline_id)
    if not checkpoint:
        return None
    return checkpoint.get("agentes", {}).get(agente, {}).get("dados")


def limpar_checkpoint(pipeline_id: str):
    """Remove checkpoint apos pipeline concluido"""
    try:
        path = get_checkpoint_path(pipeline_id)
    except ValueError:
        return
    if os.path.exists(path):
        os.remove(path)
        print(f"[Checkpoint] Removido: {path}")


def gerar_pipeline_id(user_id: int, nome: str, segmento: str) -> str:
    """
    Gera ID unico para o pipeline baseado no lead, escopado ao user_id.
    Multi-tenant: prefixo 'u{user_id}-' garante que dois usuarios distintos
    nunca compartilhem o mesmo pipeline_id (e portanto nem o mesmo checkpoint).
    """
    if not user_id:
        raise ValueError("user_id obrigatorio para gerar_pipeline_id (multi-tenant)")
    slug = re.sub(r"[^a-z0-9]+", "-", (nome + "-" + segmento).lower()).strip("-")[:40]
    if not slug:
        slug = "pipeline"
    return f"u{int(user_id)}-{slug}"
