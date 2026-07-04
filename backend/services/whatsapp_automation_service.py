"""
WhatsApp Automation Service
Serviço completo para automação de sequências de 7 dias, follow-ups e urgência
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
from enum import Enum

from backend.core.db_imports import Session, text  # noqa: F401  — B3 DRY
from backend.core.database import get_db
from backend.services.sdr_settings import fetch_sdr_settings
from backend.whatsapp.sender import send_text_parts
from backend.whatsapp.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Configuração do Meowhats
MEOWHATS_URL = "http://localhost:3001"
MEOWHATS_KEY = ""

class AutomationType(Enum):
    SEQUENCE_7_DAYS = "sequence_7_days"
    FOLLOWUP = "followup"
    URGENCY = "urgency"
    LEAD_SCORING = "lead_scoring"
    UPSELL = "upsell"

class SequenceStage(Enum):
    DAY_1_WELCOME = "day1_welcome"
    DAY_2_TUTORIAL = "day2_tutorial"
    DAY_3_SUCCESS = "day3_success"
    DAY_4_TIP = "day4_tip"
    DAY_5_PROOF = "day5_proof"
    DAY_6_OFFER = "day6_offer"
    DAY_7_URGENCY = "day7_urgency"
    FOLLOWUP_1 = "followup1"
    FOLLOWUP_2 = "followup2"
    FOLLOWUP_3 = "followup3"
    CART_RECOVERY = "cart_recovery"

@dataclass
class AutomationConfig:
    tenant_id: str
    lead_id: str
    lead_name: str
    lead_phone: str
    lead_email: str
    lead_segment: str
    site_url: str
    plan_type: str
    trial_expires_at: Optional[datetime] = None
    next_sequence_day: int = 1
    last_message_sent: Optional[datetime] = None
    engagement_score: int = 0

class WhatsAppAutomationService:
    """Serviço principal de automação do WhatsApp"""

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.session = httpx.AsyncClient(timeout=30.0)

    async def send_automation_message(
        self,
        db: Session,
        config: AutomationConfig,
        sequence_stage: SequenceStage,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Envia mensagem de automação com base no estágio"""

        # Verificar rate limit
        if not self.rate_limiter.can_send(config.tenant_id):
            return {"success": False, "error": "Rate limit atingido"}

        # Buscar configurações do usuário
        sdr_settings = fetch_sdr_settings(db, int(config.tenant_id.split("_")[-1]))

        # Obter template de mensagem
        message_template = self._get_message_template(
            sequence_stage,
            config,
            sdr_settings,
            custom_message
        )

        if not message_template:
            return {"success": False, "error": "Template não encontrado"}

        # Enviar mensagem
        try:
            response = await self.session.post(
                f"{MEOWHATS_URL}/api/sessions/{config.tenant_id}/send",
                headers={"X-API-Key": MEOWHATS_KEY},
                json={
                    "jid": f"{config.lead_phone}@s.whatsapp.net",
                    "type": "text",
                    "text": message_template
                }
            )

            if response.status_code == 200:
                # Registrar envio no banco
                await self._log_message_sent(db, config, sequence_stage, message_template)

                # Atualizar lead
                await self._update_lead_status(db, config, sequence_stage)

                return {"success": True, "message_id": response.json().get("id")}
            else:
                return {"success": False, "error": response.text}

        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return {"success": False, "error": str(e)}

    def _get_message_template(
        self,
        stage: SequenceStage,
        config: AutomationConfig,
        sdr_settings: Dict,
        custom_message: Optional[str] = None
    ) -> Optional[str]:
        """Retorna template de mensagem formatado"""

        if custom_message:
            return custom_message.format(nome=config.lead_name)

        templates = {
            SequenceStage.DAY_1_WELCOME: f"""
Oi {config.lead_name}! 👋
Chegou! Seu acesso ao FraLib foi liberado.
Bora começar?
{config.site_url}
Qual seu objetivo com o FraLib?
            """.strip(),

            SequenceStage.DAY_2_TUTORIAL: f"""
Oi {config.lead_name}!
Tudo certo por lá?
Fiz um mini-tutorial pra você:
https://youtube.com/fralib/tutorial-basico
Dúvida? Me chama.
            """.strip(),

            SequenceStage.DAY_3_SUCCESS: f"""
{config.lead_name}, viu esse caso?
Um profissional como você:
Sem site → Site profissional no FraLib
Trial → Cliente pagante
"O FraLib mudou meu negócio. Fechei 3 clientes no primeiro mês!"
            """.strip(),

            SequenceStage.DAY_4_TIP: f"""
Oi {config.lead_name}!
Uma dica que poucos usam:
Use o recurso de "Templates Rápidos" para criar sites em 5 minutos.
Isso fez diferença pra muita gente.
Quer mais?
            """.strip(),

            SequenceStage.DAY_5_PROOF: f"""
Sabe quantos profissionais já criaram site pelo FraLib?
1.247 já transformaram seu negócio.
E 82% continuaram depois do trial.
Acha que pode te ajudar também?
            """.strip(),

            SequenceStage.DAY_6_OFFER: f"""
{config.lead_name}, seu trial tá acabando.
E queria te contar:
Quem continua, tem acesso a:
✓ Templates premium
✓ Suporte prioritário
✓ Domínio próprio
Só R{self._get_plan_price(config.plan_type)}/mês.
Quer continuar?
            """.strip(),

            SequenceStage.DAY_7_URGENCY: f"""
Último dia! ⏰
Amanhã seu acesso ao FraLib expira.
Se quiser continuar, é agora:
{config.site_url}/upgrade
Se não der, tudo certo! 🙏
            """.strip(),

            SequenceStage.FOLLOWUP_1: f"""
Oi {config.lead_name}!
Vi que você acessou o FraLib mas ainda não enviou seu primeiro site.
Precisa de ajuda com algo específico?
            """.strip(),

            SequenceStage.FOLLOWUP_2: f"""
{config.lead_name}, tudo bem?
Vi que você abriu o tutorial mas não enviou o site.
Alguma dúvida?
            """.strip(),

            SequenceStage.FOLLOWUP_3: f"""
{config.lead_name}, notei que você demonstrou interesse no FraLib.
Tem alguma dúvida sobre como funciona na prática?
            """.strip(),

            SequenceStage.CART_RECOVERY: f"""
Oi {config.lead_name}! 👋
Percebi que você começou a criar seu site mas não finalizou.
Seu trabalho está salvo em:
{config.site_url}
Quer continuar de onde parou?
            """.strip(),
        }

        return templates.get(stage)

    def _get_plan_price(self, plan_type: str) -> str:
        """Retorna preço do plano"""
        prices = {
            "starter": "97",
            "pro": "497",
            "business": "997"
        }
        return prices.get(plan_type.lower(), "97")

    async def _log_message_sent(
        self,
        db: Session,
        config: AutomationConfig,
        stage: SequenceStage,
        message: str
    ):
        """Registra mensagem enviada no banco"""

        db.execute(
            text("""
                INSERT INTO interacoes (
                    lead_id, user_id, tipo, mensagem,
                    direcao, etapa, created_at
                ) VALUES (
                    :lead_id, :user_id, 'automation', :mensagem,
                    'saida', :etapa, NOW()
                )
            """),
            {
                "lead_id": config.lead_id,
                "user_id": int(config.tenant_id.split("_")[-1]),
                "mensagem": message,
                "etapa": stage.value
            }
        )
        db.commit()

    async def _update_lead_status(
        self,
        db: Session,
        config: AutomationConfig,
        stage: SequenceStage
    ):
        """Atualiza status do lead"""

        # Atualizar próximo dia da sequência
        if stage.value.startswith("day"):
            day_num = int(stage.value.split("_")[1])
            next_day = day_num + 1

            db.execute(
                text("""
                    UPDATE leads
                    SET sdr_stage = :next_stage,
                        proximo_sequencia_dia = :next_day,
                        atualizado_em = NOW()
                    WHERE id = :lead_id
                """),
                {
                    "next_stage": f"day{next_day}",
                    "next_day": next_day,
                    "lead_id": config.lead_id
                }
            )

        # Atualizar engajamento
        if stage in [SequenceStage.DAY_2_TUTORIAL, SequenceStage.DAY_3_SUCCESS]:
            config.engagement_score += 10
            db.execute(
                text("""
                    UPDATE leads
                    SET engajamento_score = :score,
                        atualizado_em = NOW()
                    WHERE id = :lead_id
                """),
                {
                    "score": config.engagement_score,
                    "lead_id": config.lead_id
                }
            )

        db.commit()

    async def trigger_sequence_7_days(self, db: Session, tenant_id: str):
        """Inicia sequência de 7 dias para leads qualificados"""

        # Buscar leads qualificados
        leads = await self._get_leads_for_sequence(db, tenant_id)

        for lead in leads:
            config = AutomationConfig(
                tenant_id=tenant_id,
                lead_id=lead["id"],
                lead_name=lead["nome"],
                lead_phone=lead["telefone"],
                lead_email=lead["email"],
                lead_segment=lead["segmento"],
                site_url=lead["site_url"],
                plan_type=lead["plano"],
                trial_expires_at=lead["trial_expires_at"],
                next_sequence_day=lead["proximo_sequencia_dia"] or 1
            )

            # Determinar estágio atual
            stage = self._get_current_sequence_stage(config)

            if stage:
                await self.send_automation_message(db, config, stage)

    async def trigger_followups(self, db: Session, tenant_id: str):
        """Dispara follow-ups baseados em comportamento"""

        # Follow-up 1: Quem não abriu
        await self._trigger_followup_no_open(db, tenant_id)

        # Follow-up 2: Quem abriu mas não respondeu
        await self._trigger_followup_no_response(db, tenant_id)

        # Follow-up 3: Quem demonstrou interesse
        await self._trigger_followup_interest(db, tenant_id)

    async def trigger_urgency(self, db: Session, tenant_id: str):
        """Dispara mensagens de urgência"""

        # 24h antes do trial acabar
        await self._trigger_trial_ending(db, tenant_id)

        # Lead inativo há 3 dias
        await self._trigger_lead_inactivity(db, tenant_id)

        # Último dia de oferta
        await self._trigger_offer_ending(db, tenant_id)

    async def _get_leads_for_sequence(self, db: Session, tenant_id: str) -> List[Dict]:
        """Busca leads qualificados para sequência"""

        user_id = int(tenant_id.split("_")[-1])

        result = db.execute(
            text("""
                SELECT l.id, l.nome, l.telefone, l.email, l.segmento,
                       l.site_url, l.plano, l.trial_expires_at,
                       l.proximo_sequencia_dia
                FROM leads l
                WHERE l.user_id = :user_id
                  AND l.status = 'concluido'
                  AND l.sdr_stage IN ('pendente_wpp', 'hook', 'intro')
                  AND l.proximo_sequencia_dia <= 7
                  AND l.trial_expires_at > NOW()
                ORDER BY l.proximo_sequencia_dia ASC, l.created_at ASC
                LIMIT 50
            """),
            {"user_id": user_id}
        )

        return [dict(row) for row in result.fetchall()]

    def _get_current_sequence_stage(self, config: AutomationConfig) -> Optional[SequenceStage]:
        """Determina o estágio atual da sequência"""

        day = config.next_sequence_day
        stages = {
            1: SequenceStage.DAY_1_WELCOME,
            2: SequenceStage.DAY_2_TUTORIAL,
            3: SequenceStage.DAY_3_SUCCESS,
            4: SequenceStage.DAY_4_TIP,
            5: SequenceStage.DAY_5_PROOF,
            6: SequenceStage.DAY_6_OFFER,
            7: SequenceStage.DAY_7_URGENCY,
        }

        return stages.get(day)

    async def _trigger_followup_no_open(self, db: Session, tenant_id: str):
        """Follow-up para leads que não abriram o site"""

        user_id = int(tenant_id.split("_")[-1])

        # Buscar leads com site pronto mas sem acesso registrado
        result = db.execute(
            text("""
                SELECT l.id, l.nome, l.telefone, l.email, l.site_url
                FROM leads l
                WHERE l.user_id = :user_id
                  AND l.status = 'concluido'
                  AND l.site_url IS NOT NULL
                  AND l.sdr_stage = 'pendente_wpp'
                  AND l.created_at < NOW() - INTERVAL '24 hours'
                ORDER BY l.created_at ASC
                LIMIT 20
            """),
            {"user_id": user_id}
        )

        for row in result.fetchall():
            config = AutomationConfig(
                tenant_id=tenant_id,
                lead_id=row[0],
                lead_name=row[1],
                lead_phone=row[2],
                lead_email=row[3],
                lead_segment="",
                site_url=row[4],
                plan_type="trial"
            )

            await self.send_automation_message(db, config, SequenceStage.FOLLOWUP_1)

    async def _trigger_followup_no_response(self, db: Session, tenant_id: str):
        """Follow-up para leads que não responderam"""

        user_id = int(tenant_id.split("_")[-1])

        # Buscar leads com mensagem enviada mas sem resposta
        result = db.execute(
            text("""
                SELECT l.id, l.nome, l.telefone, l.email, l.site_url
                FROM leads l
                WHERE l.user_id = :user_id
                  AND l.status = 'concluido'
                  AND EXISTS (
                      SELECT 1 FROM interacoes i
                      WHERE i.lead_id = l.id
                        AND i.direcao = 'saida'
                        AND i.created_at < NOW() - INTERVAL '48 hours'
                        AND NOT EXISTS (
                            SELECT 1 FROM interacoes i2
                            WHERE i2.lead_id = l.id
                              AND i2.direcao = 'entrada'
                              AND i2.created_at > i.created_at
                        )
                  )
                ORDER BY l.id ASC
                LIMIT 20
            """),
            {"user_id": user_id}
        )

        for row in result.fetchall():
            config = AutomationConfig(
                tenant_id=tenant_id,
                lead_id=row[0],
                lead_name=row[1],
                lead_phone=row[2],
                lead_email=row[3],
                lead_segment="",
                site_url=row[4],
                plan_type="trial"
            )

            await self.send_automation_message(db, config, SequenceStage.FOLLOWUP_2)

    async def _trigger_followup_interest(self, db: Session, tenant_id: str):
        """Follow-up para leads que demonstraram interesse"""

        user_id = int(tenant_id.split("_")[-1])

        # Buscar leads com múltipas interações positivas
        result = db.execute(
            text("""
                SELECT l.id, l.nome, l.telefone, l.email, l.site_url
                FROM leads l
                JOIN interacoes i ON l.id = i.lead_id
                WHERE l.user_id = :user_id
                  AND l.status = 'concluido'
                  AND i.tipo IN ('pergunta', 'duvida')
                  GROUP BY l.id
                  HAVING COUNT(i.id) >= 2
                ORDER BY COUNT(i.id) DESC
                LIMIT 15
            """),
            {"user_id": user_id}
        )

        for row in result.fetchall():
            config = AutomationConfig(
                tenant_id=tenant_id,
                lead_id=row[0],
                lead_name=row[1],
                lead_phone=row[2],
                lead_email=row[3],
                lead_segment="",
                site_url=row[4],
                plan_type="trial"
            )

            await self.send_automation_message(db, config, SequenceStage.FOLLOWUP_3)

    async def _trigger_trial_ending(self, db: Session, tenant_id: str):
        """Mensagem de urgência 24h antes do trial acabar"""

        user_id = int(tenant_id.split("_")[-1])

        # Buscar trial que expiram em 24h
        result = db.execute(
            text("""
                SELECT l.id, l.nome, l.telefone, l.email, l.site_url
                FROM leads l
                WHERE l.user_id = :user_id
                  AND l.status = 'concluido'
                  AND l.trial_expires_at BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
                ORDER BY l.trial_expires_at ASC
                LIMIT 30
            """),
            {"user_id": user_id}
        )

        for row in result.fetchall():
            config = AutomationConfig(
                tenant_id=tenant_id,
                lead_id=row[0],
                lead_name=row[1],
                lead_phone=row[2],
                lead_email=row[3],
                lead_segment="",
                site_url=row[4],
                plan_type="trial",
                trial_expires_at=row["trial_expires_at"]
            )

            custom_message = f"""
Oi {config.lead_name}! ⏰
Seu trial do FraLib termina em 24 horas!
Ainda dá tempo de aproveitar:
{config.site_url}
Quer continuar usando a plataforma?
            """.strip()

            await self.send_automation_message(
                db, config, SequenceStage.DAY_7_URGENCY, custom_message
            )

    async def _trigger_lead_inactivity(self, db: Session, tenant_id: str):
        """Mensagem para leads inativos há 3 dias"""

        user_id = int(tenant_id.split("_")[-1])

        # Buscar leads sem interações há 3 dias
        result = db.execute(
            text("""
                SELECT l.id, l.nome, l.telefone, l.email, l.site_url
                FROM leads l
                WHERE l.user_id = :user_id
                  AND l.status = 'concluido'
                  AND (
                      NOT EXISTS (SELECT 1 FROM interacoes i WHERE i.lead_id = l.id)
                      OR NOT EXISTS (
                          SELECT 1 FROM interacoes i
                          WHERE i.lead_id = l.id
                            AND i.created_at >= NOW() - INTERVAL '3 days'
                      )
                  )
                ORDER BY l.id ASC
                LIMIT 20
            """),
            {"user_id": user_id}
        )

        for row in result.fetchall():
            config = AutomationConfig(
                tenant_id=tenant_id,
                lead_id=row[0],
                lead_name=row[1],
                lead_phone=row[2],
                lead_email=row[3],
                lead_segment="",
                site_url=row[4],
                plan_type="trial"
            )

            custom_message = f"""
Oi {config.lead_name}!
Tudo bem? Notei que você não acessou o FraLib há alguns dias.
Precisa de ajuda com algo?
{config.site_url}/ajuda
            """.strip()

            await self.send_automation_message(
                db, config, SequenceStage.FOLLOWUP_1, custom_message
            )

    async def _trigger_offer_ending(self, db: Session, tenant_id: str):
        """Mensagem de último dia de oferta"""

        # Implementar lógica de oferta especial
        pass

    async def calculate_lead_scoring(self, db: Session, lead_id: str) -> int:
        """Calcula score de lead baseado em engajamento"""

        result = db.execute(
            text("""
                SELECT
                    COUNT(CASE WHEN i.direcao = 'entrada' THEN 1 END) as responses,
                    COUNT(CASE WHEN i.tipo = 'pergunta' THEN 1 END) as questions,
                    COUNT(CASE WHEN i.tipo = 'duvida' THEN 1 END) as doubts,
                    EXTRACT(EPOCH FROM (MAX(i.created_at) - MIN(i.created_at))) / 86400 as days_active
                FROM interacoes i
                WHERE i.lead_id = :lead_id
            """),
            {"lead_id": lead_id}
        )

        row = result.fetchone()
        if not row:
            return 0

        responses = row[0] or 0
        questions = row[1] or 0
        doubts = row[2] or 0
        days_active = row[3] or 0

        # Cálculo do score
        score = 0
        score += responses * 10  # Respostas valem 10 pts cada
        score += questions * 15  # Perguntas valem 15 pts cada
        score += doubts * 20    # Dúvidas valem 20 pts cada
        score += min(days_active * 5, 50)  # Atividade contínua

        return min(score, 100)

    async def trigger_upsell(self, db: Session, tenant_id: str):
        """Dispara upsell para trial finalizado"""

        user_id = int(tenant_id.split("_")[-1])

        # Buscar trial finalizados com alto score
        result = db.execute(
            text("""
                SELECT l.id, l.nome, l.telefone, l.email, l.site_url, l.engajamento_score
                FROM leads l
                WHERE l.user_id = :user_id
                  AND l.status = 'concluido'
                  AND l.trial_expires_at < NOW()
                  AND l.engajamento_score >= 70
                ORDER BY l.engajamento_score DESC
                LIMIT 10
            """),
            {"user_id": user_id}
        )

        for row in result.fetchall():
            config = AutomationConfig(
                tenant_id=tenant_id,
                lead_id=row[0],
                lead_name=row[1],
                lead_phone=row[2],
                lead_email=row[3],
                lead_segment="",
                site_url=row[4],
                plan_type="trial"
            )

            custom_message = f"""
{config.lead_name}! 👋
Vi que você gostou do FraLib durante o trial.
Agora você pode acessar todos os recursos:
✓ Templates premium
✓ Suporte 24/7
✓ Domínio próprio
Upgrade para Pro: R497/mês
{config.site_url}/upgrade
            """.strip()

            await self.send_automation_message(
                db, config, SequenceStage.DAY_6_OFFER, custom_message
            )

# Instância global
_automation_service: Optional[WhatsAppAutomationService] = None

def get_automation_service() -> WhatsAppAutomationService:
    global _automation_service
    if _automation_service is None:
        _automation_service = WhatsAppAutomationService()
    return _automation_service