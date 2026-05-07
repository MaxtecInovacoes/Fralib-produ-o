"""
Sistema de Checkpoint do Pipeline FraLib
Salva estado de cada agente para retomar de onde parou
"""
import json
import re
import os
import time
from datetime import datetime

CHECKPOINT_DIR = "/root/fralib/checkpoints"
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

def get_checkpoint_path(pipeline_id: str) -> str:
    return f"{CHECKPOINT_DIR}/{pipeline_id}.json"

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
    path = get_checkpoint_path(pipeline_id)
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
    path = get_checkpoint_path(pipeline_id)
    if os.path.exists(path):
        os.remove(path)
        print(f"[Checkpoint] Removido: {path}")

def gerar_pipeline_id(nome: str, segmento: str) -> str:
    """Gera ID unico para o pipeline baseado no lead"""
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", (nome + "-" + segmento).lower()).strip("-")[:40]
    return slug
