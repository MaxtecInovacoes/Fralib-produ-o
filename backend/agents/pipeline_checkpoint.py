"""
Sistema de Checkpoint do Pipeline FraLib
Salva estado de cada agente para retomar de onde parou.

Multi-tenant: o pipeline_id e prefixado com 'u{user_id}-' para evitar que
dois usuarios do mesmo nicho/cidade sobrescrevam o checkpoint um do outro.

Cada fase que consome tokens (LLM calls) salva seu output completo.
Se o pipeline quebrar, retoma da ultima fase concluida sem gastar tokens de novo.
"""

import json
import re
import os
import unicodedata
from datetime import datetime
from backend.config import CHECKPOINT_DIR as _CFG_CKPT_DIR, DATABASE_URL as _CFG_DB_URL
from backend.agents.pipeline_identity import inferir_segmento_por_nome

os.makedirs(_CFG_CKPT_DIR, exist_ok=True)

DISABLE_CHECKPOINT_TEMP = False

_VALID_PIPELINE_ID = re.compile(r"^[a-z0-9][a-z0-9\-]*$")

CHECKPOINT_DIR = _CFG_CKPT_DIR
_DB_URL = os.environ.get("DATABASE_URL", _CFG_DB_URL)


def _backup_to_db(pipeline_id: str, checkpoint: dict):
    """Backup assíncrono do checkpoint no Postgres (best-effort)."""
    try:
        import psycopg2

        conn = psycopg2.connect(_DB_URL)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_checkpoints (pipeline_id, data, atualizado_em)
                VALUES (%s, %s, NOW())
                ON CONFLICT (pipeline_id) DO UPDATE SET data = %s, atualizado_em = NOW()
            """,
                (
                    pipeline_id,
                    json.dumps(checkpoint, default=str),
                    json.dumps(checkpoint, default=str),
                ),
            )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Checkpoint] DB backup skip: {e}")


def _load_from_db(pipeline_id: str) -> dict:
    """Carrega checkpoint do Postgres (fallback quando disco não tem)."""
    try:
        import psycopg2

        conn = psycopg2.connect(_DB_URL)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT data FROM pipeline_checkpoints WHERE pipeline_id = %s",
                (pipeline_id,),
            )
            row = cur.fetchone()
        conn.close()
        if row:
            return row[0] if isinstance(row[0], dict) else json.loads(row[0])
    except Exception as e:
        print(f"[Checkpoint] DB load skip: {e}")
    return None


def _safe_pipeline_id(pipeline_id: str) -> str:
    """Sanitiza pipeline_id pra evitar path traversal."""
    if not pipeline_id or not _VALID_PIPELINE_ID.match(pipeline_id):
        raise ValueError(f"pipeline_id invalido: {pipeline_id!r}")
    return pipeline_id


def get_checkpoint_path(pipeline_id: str) -> str:
    pid = _safe_pipeline_id(pipeline_id)
    return f"{CHECKPOINT_DIR}/{pid}.json"


def salvar_checkpoint(pipeline_id: str, agente: str, dados: dict):
    """Salva estado completo do agente no checkpoint (disco + Postgres backup)."""
    path = get_checkpoint_path(pipeline_id)
    checkpoint = carregar_checkpoint(pipeline_id) or {
        "pipeline_id": pipeline_id,
        "criado_em": datetime.now().isoformat(),
        "agentes": {},
    }
    checkpoint["agentes"][agente] = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "dados": dados,
    }
    checkpoint["ultimo_agente"] = agente
    checkpoint["atualizado_em"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, default=str)
    print(
        f"[Checkpoint] ✅ Salvo: {agente} ({len(json.dumps(dados, default=str)) // 1024}KB) -> {path}"
    )
    # Backup no Postgres (não bloqueia se falhar)
    _backup_to_db(pipeline_id, checkpoint)


def carregar_checkpoint(pipeline_id: str) -> dict:
    """Carrega checkpoint: disco primeiro, Postgres como fallback."""
    try:
        path = get_checkpoint_path(pipeline_id)
    except ValueError:
        return None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    # Fallback: tentar carregar do Postgres (disco pode ter sido limpo)
    db_data = _load_from_db(pipeline_id)
    if db_data:
        # Restaurar no disco pra próximas leituras serem rápidas
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(db_data, f, ensure_ascii=False, default=str)
            print(f"[Checkpoint] ♻️ Restaurado do Postgres: {pipeline_id}")
        except Exception:
            pass
        return db_data
    return None


def agente_concluido(pipeline_id: str, agente: str) -> bool:
    """Verifica se agente ja foi concluido"""
    checkpoint = carregar_checkpoint(pipeline_id)
    if not checkpoint:
        return False
    return agente in checkpoint.get("agentes", {})


def get_dados_agente(pipeline_id: str, agente: str) -> dict:
    """Recupera dados salvos de um agente"""
    if DISABLE_CHECKPOINT_TEMP:
        print(
            f"[Checkpoint] BYPASS | Checkpoint desativado para testes. Forçando execução de {agente}."
        )
        return None
    checkpoint = carregar_checkpoint(pipeline_id)
    if not checkpoint:
        return None
    return checkpoint.get("agentes", {}).get(agente, {}).get("dados")


def limpar_checkpoint(pipeline_id: str):
    """Remove checkpoint apos pipeline concluido com sucesso (disco + DB)."""
    try:
        path = get_checkpoint_path(pipeline_id)
    except ValueError:
        return
    if os.path.exists(path):
        os.remove(path)
        print(f"[Checkpoint] 🗑️ Removido disco: {path}")
    # Limpar do Postgres também
    try:
        import psycopg2

        conn = psycopg2.connect(_DB_URL)
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM pipeline_checkpoints WHERE pipeline_id = %s",
                (pipeline_id,),
            )
        conn.commit()
        conn.close()
    except Exception:
        pass


def limpar_checkpoints_expirados(max_age_hours: int = 24):
    """Remove checkpoints mais velhos que max_age_hours (disco + DB). Chamar periodicamente."""
    import time as _t

    removidos = 0
    try:
        for f in os.listdir(CHECKPOINT_DIR):
            if not f.endswith(".json"):
                continue
            path = os.path.join(CHECKPOINT_DIR, f)
            age = _t.time() - os.path.getmtime(path)
            if age > max_age_hours * 3600:
                os.remove(path)
                removidos += 1
    except Exception as e:
        print(f"[Checkpoint] Reaper disco erro: {e}")
    # Limpar DB também
    try:
        import psycopg2

        conn = psycopg2.connect(_DB_URL)
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM pipeline_checkpoints WHERE atualizado_em < NOW() - INTERVAL '%s hours'",
                (max_age_hours,),
            )
            db_removed = cur.rowcount
        conn.commit()
        conn.close()
        removidos += db_removed
    except Exception:
        pass
    if removidos:
        print(f"[Checkpoint] 🗑️ Reaper: {removidos} checkpoints expirados removidos")


def _slugify_identity(*parts: str, max_len: int = 64) -> str:
    raw = "-".join(str(part or "") for part in parts if str(part or "").strip())
    text = unicodedata.normalize("NFKD", raw)
    text = text.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:max_len]
    return slug or "pipeline"


def gerar_pipeline_id(
    user_id: int,
    nome: str,
    segmento: str,
    cidade: str = "",
    lead_id: str = "",
) -> str:
    """
    Gera ID unico para o pipeline baseado no lead, escopado ao user_id.
    Multi-tenant: prefixo 'u{user_id}-' garante que dois usuarios distintos
    nunca compartilhem o mesmo pipeline_id (e portanto nem o mesmo checkpoint).

    A identidade precisa ser por lead, nao por busca. Ex: "academia em Campina
    Grande do Sul" pode retornar Alfa Crosstraining e Aquaflex; eles nao podem
    compartilhar checkpoint nem projeto de renderizacao.
    """
    if not user_id:
        raise ValueError("user_id obrigatorio para gerar_pipeline_id (multi-tenant)")
    lead_marker = str(lead_id or "").strip()
    if lead_marker:
        lead_marker = lead_marker.replace("-", "")[:10]
    segmento_identidade = inferir_segmento_por_nome(nome, segmento)
    slug = _slugify_identity(nome, segmento_identidade, cidade, lead_marker)
    return f"u{int(user_id)}-{slug}"


def resumo_checkpoint(pipeline_id: str) -> str:
    """Retorna resumo legivel do checkpoint (pra logs)."""
    ckpt = carregar_checkpoint(pipeline_id)
    if not ckpt:
        return "nenhum checkpoint"
    agentes = list(ckpt.get("agentes", {}).keys())
    return f"checkpoint com {len(agentes)} fases: {', '.join(agentes)}"
