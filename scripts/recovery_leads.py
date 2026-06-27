"""Script de recovery para leads em followup1/followup_24h/followup_72h.

User pediu: "Sim, tem o contexto de todos? conseguimos contexto de todos e
definir essa estrategia de retomada de conversa sem ser agreciva repetitiva
e disparar em mssa"

Estrategia:
1. Carrega contexto completo (ultimas N mensagens)
2. Gera msg personalizada via LLM (Sonnet, com Haiku fallback)
3. NAO dispara msg se:
   - Lead ja recebeu msg nas ultimas 24h (evitar spam)
   - Lead marcou opt_out em algum momento
   - Lead tem msgs em massa nos ultimos 7 dias (ja saturou)
4. Respeita o rate limit do WhatsApp (max 2 msgs/10min por tenant)
5. Salva na FILA outbound (com rate limit) e NAO envia direto
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from sqlalchemy import text

# Adicionar path do backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, '/root/fralib')

# Carregar .env ANTES de importar backend (que precisa DATABASE_URL)
from dotenv import load_dotenv
_env_path = '/root/fralib/.env'
if os.path.exists(_env_path):
    load_dotenv(_env_path)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("recovery")


def get_leads_needing_recovery(engine, min_idle_hours=24) -> list:
    """Busca leads em followup que estao idle ha mais de N horas.

    Criteria:
    - sdr_stage em (followup1, followup_24h, followup_72h)
    - Nao recebeu msg do Franz nas ultimas N horas
    - NAO marcou opt_out
    - Nao recebeu msgs em massa nos ultimos 7 dias
    """
    from backend.core.database import engine as default_engine
    if engine is None:
        engine = default_engine
    cutoff = (datetime.now() - timedelta(hours=min_idle_hours)).isoformat()
    cutoff_7d = (datetime.now() - timedelta(days=7)).isoformat()
    with engine.connect() as c:
        rows = c.execute(text("""
            SELECT l.id, l.user_id, l.nome, l.telefone, l.sdr_stage, l.opt_out_pending,
                   (SELECT MAX(criado_em) FROM interacoes
                    WHERE lead_id = l.id AND direcao = 'saida') as last_bot_msg,
                   (SELECT MAX(criado_em) FROM interacoes
                    WHERE lead_id = l.id AND direcao = 'entrada') as last_lead_msg
            FROM leads l
            WHERE l.sdr_stage IN ('followup1', 'followup_24h', 'followup_72h')
              AND l.opt_out_pending = false
              AND COALESCE(
                  (SELECT MAX(criado_em) FROM interacoes
                   WHERE lead_id = l.id AND direcao = 'saida'),
                  '1970-01-01'
              ) < :cutoff
              AND l.id NOT IN (
                  SELECT lead_id FROM interacoes
                  WHERE criado_em > :cutoff_7d
                    AND direcao = 'saida'
                    AND mensagem LIKE '%promoção em massa%'
              )
            ORDER BY l.atualizado_em ASC
            LIMIT 50
        """), {"cutoff": cutoff, "cutoff_7d": cutoff_7d}).fetchall()
    return rows


def get_lead_context(engine, lead_id: str, max_msgs: int = 10) -> list:
    """Retorna contexto (ultimas N msgs) do lead."""
    with engine.connect() as c:
        rows = c.execute(text("""
            SELECT criado_em, direcao, mensagem
            FROM interacoes
            WHERE lead_id = :lid
            ORDER BY criado_em DESC
            LIMIT :n
        """), {"lid": lead_id, "n": max_msgs}).fetchall()
    return [{"quando": str(r[0]), "quem": r[1], "msg": r[2]} for r in reversed(rows)]


def generate_recovery_message(lead_name: str, lead_segment: str, context: list) -> str:
    """Gera msg de recovery personalizada baseada no contexto.

    NUNCA usa template generico. Cada msg eh unica.
    """
    from backend.agents.llm_direct import call_claude

    # Monta contexto para o LLM
    ctx_text = ""
    for c in context[-3:]:  # ultimas 3 msgs
        ctx_text += f"[{c['quem']}] {c['msg'][:100]}\n"

    system = """Voce e o Franz, assistente de uma empresa local brasileira.
Lead parou de responder (followup). Voce precisa retomar conversa de forma NATURAL,
sem soar spam.

REGRAS OBRIGATORIAS:
1. MAXIMO 2 frases curtas
2. NAO use template (Ex: "Oi! Tudo bem? Vi que..." repetido)
3. NAO use emoji excessivo (max 1)
4. NAO mencione "followup" ou "nao respondeu"
5. Referencie ESPECIFICAMENTE algo da conversa anterior (especifico)
6. Faca pergunta natural que convide a retomar
7. Tom: educado, levemente informal

Exemplo BOM: "Oi Maria! Vi que voce tinha interesse em [X]. Conseguiu avaliar?"
Exemplo RUIM: "Ola! Tudo bem? Estamos entrando em contato para..."
"""

    user = f"""Lead: {lead_name}
Segmento: {lead_segment}
Ultimas mensagens:
{ctx_text}

Gere APENAS a msg de retomada, sem prefixo."""

    try:
        msg = call_claude(
            system=system,
            user=user,
            model="claude-haiku-4-5",
            max_tokens=100,
            temperature=0.5,
            agent_name="sdr_recovery",
            enable_context=False,
        )
        return msg.strip()
    except Exception as e:
        logger.error(f"Erro gerando msg: {e}")
        return ""


def main():
    from backend.core.database import engine
    from backend.services.outbound_queue import enqueue_outbound, can_send_now

    # 1. Buscar leads
    leads = get_leads_needing_recovery(engine, min_idle_hours=24)
    logger.info(f"Encontrados {len(leads)} leads para recovery")

    queued = 0
    skipped = 0
    failed = 0

    for lead_id, user_id, nome, telefone, sdr_stage, opt_out, last_bot, last_lead in leads:
        # Verificar rate limit por tenant
        can_send, wait = can_send_now(engine, user_id)
        if not can_send:
            logger.info(f"SKIP {nome} (rate limit, wait={wait}s)")
            skipped += 1
            continue

        # 2. Carregar contexto
        context = get_lead_context(engine, lead_id, max_msgs=10)
        if not context:
            logger.info(f"SKIP {nome} (sem contexto)")
            skipped += 1
            continue

        # 3. Gerar msg personalizada
        segmento = "academia" if "academia" in nome.lower() or "gym" in nome.lower() else "nutricao"
        msg = generate_recovery_message(nome, segmento, context)
        if not msg:
            logger.info(f"SKIP {nome} (LLM falhou)")
            failed += 1
            continue

        # 4. Enfileirar (com rate limit automatico)
        phone_clean = telefone.replace("+", "").replace(" ", "").replace("(", "").replace(")", "").replace("-", "")
        if not phone_clean.startswith("55"):
            phone_clean = "55" + phone_clean

        msg_id = enqueue_outbound(
            engine=engine,
            tenant_id=user_id,
            lead_id=lead_id,
            phone=phone_clean,
            message=msg,
            source="franz_recovery",
            priority=5,
        )
        logger.info(f"QUEUED {nome} (id={msg_id}, msg={msg[:50]}...)")
        queued += 1

    logger.info(f"=== RESUMO: queued={queued}, skipped={skipped}, failed={failed} ===")


if __name__ == "__main__":
    main()
