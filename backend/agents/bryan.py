import sys
sys.path.insert(0, "/root/fralib/backend/agents")
"""
Agente Bryan - SDR (Sales Development Representative)
Migração para Pydantic AI
"""
import json
import os
from skill_loader import carregar_skills, get_skills_agente
from validation_enforcer import require_rag
import re
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from brain import feedback_cliente
from llm_direct import call_claude
from memory import salvar_memoria, carregar_memoria
from agent_rag import format_rag_prompt, get_agent_temperature, buscar_contexto_rag, mark_rag_used


def clean_control_characters(text: str) -> str:
    """Remove caracteres de controle inválidos do JSON"""
    import re
    # Remove caracteres de controle exceto \n, \r, \t
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)


def sanitize_text(text: str) -> str:
    """Sanitiza texto para uso seguro em prompts e JSON"""
    if not text:
        return ""
    import re
    # Remove caracteres de controle
    text = clean_control_characters(str(text))
    # Normaliza espaços múltiplos
    text = re.sub(r'\s+', ' ', text)
    # Remove espaços no início e fim
    return text.strip()

# ===== MODELOS PYDANTIC =====

class BryanInput(BaseModel):
    """Entrada do Bryan - Lead qualificado + Site pronto"""
    nome: str
    cidade: str
    segmento: str
    telefone: str
    whatsapp: Optional[str] = None
    rating: Optional[float] = 0
    site_url: Optional[str] = None
    score_caio: Optional[int] = 0
    concorrentes: Optional[Dict] = None  # top3, padroes, recomendacoes (Jina)
    tier: Optional[str] = "STANDARD"
    proof: Optional[str] = None  # Razão da qualificação (Caio)

class BryanDecision(BaseModel):
    """Decisão do LLM — JSON retornado pelo Franz"""
    intent: str = "other"
    emotion: str = "neutro"
    reply: str
    next_stage: str = "hook"
    should_handoff: bool = False
    price_tier: int = 0
    update_facts: Optional[Dict] = None

class BryanOutput(BaseModel):
    """Saída do Bryan - Resultado completo"""
    reply: str
    intent: str = "other"
    next_stage: str = "hook"
    estrategia: str = "rapport_build"
    proximo_passo: str = "Aguardar resposta do lead (24h)"
    enviado: bool = False
    should_handoff: bool = False
    price_tier: int = 0
    guard: Optional[str] = None
    update_facts: Optional[Dict] = None

# ===== STATE MACHINE SDR =====

ESTADOS_SDR = [
    "hook",        # Pattern interrupt — abordagem conforme variante A/B/C/D
    "qualify",     # EU escolho VOCÊ — posicionar como seletor
    "pain",        # Descobrir dor real — como captam clientes hoje
    "amplify",     # Amplificar dor — custo da inação, concorrentes
    "tease",       # Plantar semente SEM revelar — gap de curiosidade
    "proof",       # Prova social + escassez territorial
    "reveal",      # Mostrar site — SÓ quando lead PEDIR
    "feedback",    # Comprometimento verbal — "o que achou?"
    "close",       # "Quer que eu coloque no ar?"
    "urgency",     # Escassez real — domínio expira, 1 por bairro
    "handoff",     # Passar para closer humano
    "won",         # Ganho
    "lost",        # Perdido
    "scheduled"    # Agendado — follow-up em data futura
]

# ===== DETECÇÃO DE INTENT =====

def detectar_intent(msg: str) -> str:
    """Detecta intenção do lead pela mensagem"""
    l = msg.lower()
    if any(t in l for t in ['para', 'stop', 'remover', 'não quero mais', 'chega', 'me tira']):
        return 'opt_out'
    if any(t in l for t in ['golpe', 'fake', 'fraude', 'quem é', 'como pegou']):
        return 'objection_trust'
    if any(t in l for t in ['quanto', 'preço', 'valor', 'custa', 'cobrar', 'mensalidade']):
        return 'objection_price'
    if any(t in l for t in ['sem tempo', 'ocupado', 'depois', 'mais tarde', 'semana que vem']):
        return 'objection_time'
    if any(t in l for t in ['sim', 'quero', 'pode', 'manda', 'bora', 'fechado', 'aceito']):
        return 'acceptance'
    if any(t in l for t in ['não', 'nao', 'sem interesse', 'não preciso', 'já tenho']):
        return 'rejection'
    if any(t in l for t in ['link', 'ver', 'site', 'mostrar', 'como ficou']):
        return 'wants_link'
    return 'other'


# ===== DETECÇÃO DE BOT / MSG AUTOMÁTICA =====

def detectar_bot(mensagem: str, tempo_resposta_ms: int = None) -> dict:
    """
    Detecta se a mensagem veio de um bot/atendimento automático.
    Retorna: {"is_bot": bool, "confidence": float, "tipo": str, "opcao_humano": str}
    """
    l = mensagem.lower().strip()
    sinais = 0
    tipo = "humano"
    opcao_humano = ""

    # Sinal 1: Menu numerado (1 - Vendas, 2 - Suporte, etc)
    menu_pattern = re.findall(r'[1-9]\s*[-–—\.)\]]\s*\w+', mensagem)
    if len(menu_pattern) >= 2:
        sinais += 3
        tipo = "menu_bot"
        # Tentar achar opção que leva a humano/atendente
        for match in menu_pattern:
            match_lower = match.lower()
            if any(t in match_lower for t in ['atend', 'falar', 'humano', 'pessoa', 'vendas', 'comercial', 'responsável', 'gerente', 'dono']):
                opcao_humano = re.search(r'[1-9]', match).group()
                break
        # Se não achou opção clara, pegar "outros" ou último
        if not opcao_humano:
            for match in menu_pattern:
                if any(t in match.lower() for t in ['outro', 'demais', 'mais']):
                    opcao_humano = re.search(r'[1-9]', match).group()
                    break
            if not opcao_humano:
                # Tentar "vendas" ou "comercial" como fallback
                for match in menu_pattern:
                    if any(t in match.lower() for t in ['vend', 'comerc', 'negóc']):
                        opcao_humano = re.search(r'[1-9]', match).group()
                        break

    # Sinal 2: Frases template de bot
    frases_bot = [
        'como posso ajudar', 'como posso te ajudar', 'em que posso ajudar',
        'selecione uma opção', 'escolha uma opção', 'digite o número',
        'digite a opção', 'bem-vindo', 'bem vindo', 'boas-vindas',
        'atendimento automático', 'assistente virtual', 'sou um assistente',
        'sou a assistente', 'sou o assistente', 'inteligência artificial',
        'horário de atendimento', 'nosso horário', 'funcionamos de',
        'para falar com', 'para ser atendido', 'aguarde um momento',
        'transferindo para', 'encaminhando para', 'um atendente irá',
        'fora do horário', 'retornaremos', 'deixe sua mensagem',
        'protocolo de atendimento', 'número do protocolo',
    ]
    if any(f in l for f in frases_bot):
        sinais += 2
        if tipo == "humano":
            tipo = "msg_automatica"

    # Sinal 3: Emojis excessivos + formatação corporativa
    if l.count('*') >= 4 or l.count('_') >= 4:  # negrito/itálico WhatsApp
        sinais += 1

    # Sinal 4: Mensagem muito longa e estruturada (> 300 chars com bullets)
    if len(mensagem) > 300 and (mensagem.count('•') >= 2 or mensagem.count('✅') >= 2 or mensagem.count('▪') >= 2):
        sinais += 1
        if tipo == "humano":
            tipo = "msg_automatica"

    # Sinal 5: Resposta instantânea (< 3 segundos)
    if tempo_resposta_ms is not None and tempo_resposta_ms < 3000:
        sinais += 2

    # Sinal 6: Pede pra digitar número/opção
    if re.search(r'digit[ea]\s*(o\s*)?n[úu]mero|digit[ea]\s*(a\s*)?op[çc][ãa]o|responda com|envie\s*\d', l):
        sinais += 2
        tipo = "menu_bot"

    # Sinal 7: Saudação genérica sem contexto pessoal
    if re.match(r'^(olá|oi|hello|hey)[!.]?\s*(tudo bem|como vai|bom dia|boa tarde|boa noite)?[!?.]?\s*(como posso|em que posso|selecione)', l):
        sinais += 1

    # Calcular confiança
    confidence = min(sinais / 5.0, 1.0)
    is_bot = confidence >= 0.4

    return {
        "is_bot": is_bot,
        "confidence": confidence,
        "tipo": tipo,  # "humano", "menu_bot", "msg_automatica"
        "opcao_humano": opcao_humano,  # número pra digitar pra chegar no humano
        "sinais": sinais
    }


def gerar_resposta_bot(deteccao: dict, nome_empresa: str) -> str:
    """Gera resposta pra navegar o bot até chegar no humano."""
    tipo = deteccao["tipo"]
    opcao = deteccao["opcao_humano"]

    if tipo == "menu_bot" and opcao:
        # Digitar a opção que leva ao humano/vendas
        return opcao

    if tipo == "menu_bot" and not opcao:
        # Não achou opção clara — pedir atendente
        return "Falar com atendente"

    if tipo == "msg_automatica":
        # Msg automática sem menu — pedir humano
        respostas = [
            "Quero falar com o responsável, por favor",
            "Tem como falar com alguém da equipe?",
            "Preciso falar com o dono/gerente",
        ]
        import random
        return random.choice(respostas)

    return ""
def decidir_estrategia(intent: str, stage: str, rejection_count: int = 0) -> str:
    """Decide estratégia baseada no intent e stage atual"""
    if intent == 'off_topic':
        return 'rapport_redirect'
    if intent == 'objection_trust':
        return 'trust_build'
    if intent == 'objection_price' and stage == 'negotiate':
        return 'anchor_value'
    if intent == 'objection_price':
        return 'delay_price_show_value'
    if intent == 'objection_time':
        return 'soft_close'
    if intent == 'rejection' and rejection_count == 0:
        return 'curiosity_hook'
    if intent == 'rejection' and rejection_count == 1:
        return 'trust_build'
    if intent == 'rejection' and rejection_count >= 2:
        return 'value_push'
    if intent == 'acceptance':
        return 'hard_close'
    if stage in ('intro', 'qualify'):
        return 'rapport_build'
    if stage == 'proof':
        return 'value_push'
    if stage == 'link':
        return 'soft_close'
    return 'value_push'

# ===== GUARDRAILS =====

def aplicar_guardrails(decision: dict, stage_atual: str, lead_nome: str, historico: list) -> tuple:
    """Aplica guardrails de segurança na resposta do LLM"""
    guard = None
    reply = decision.get("reply", "")
    next_stage = decision.get("next_stage", "hook")

    # G1: Preço antes de value → remover menção de R$
    if stage_atual in ('intro', 'qualify', 'proof', 'link'):
        if re.search(r'r\$|reais|mensalidade|cobr|valor|preço', reply, re.IGNORECASE):
            reply = re.sub(r'r\$[\d\.,]+', '', reply, flags=re.IGNORECASE)
            reply = re.sub(r'mensalidade[^\.]+', '', reply, flags=re.IGNORECASE)
            reply = reply.strip()
            guard = 'G1_price_removed'

    # G2: Sem reunião/demo/vídeo
    if re.search(r'reunião|videochamada|video call|demo|apresentação|agendar', reply, re.IGNORECASE):
        reply = re.sub(r'reunião|videochamada|video call|demo|apresentação|agendar', 'conversa', reply, flags=re.IGNORECASE)
        guard = 'G2_meeting_removed'

    # G3: Mensagem muito longa → truncar em 3 linhas
    linhas = reply.split('\n')
    if len(linhas) > 4:
        reply = '\n'.join(linhas[:3])
        guard = 'G3_truncated'

    # G4: Reply vazio → fallback
    if not reply or len(reply) < 5:
        reply = f"Entendi! Me conta mais sobre a {lead_nome} pra eu conseguir te ajudar melhor."
        next_stage = stage_atual
        guard = 'G4_fallback'

    # G5: Handoff prematuro
    if decision.get("should_handoff") and decision.get("intent") != 'acceptance':
        decision["should_handoff"] = False
        guard = 'G5_handoff_blocked'

    # G7: Anti-repetição
    if historico:
        ultimas = [m.get("content", "").strip().lower() for m in historico[-4:] if m.get("role") == "assistant"]
        if reply.strip().lower() in ultimas:
            reply = f"Me conta mais sobre o que vocês precisam — quero entender melhor o negócio de vocês."
            guard = 'G7_anti_repeat'

    # G9: Emoji spam (max 1)
    emoji_count = len(re.findall(r'[\U0001F300-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0\U0000FE0F]', reply))
    if emoji_count > 2:
        count = 0
        new_reply = ""
        for c in reply:
            if re.match(r'[\U0001F300-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0\U0000FE0F]', c):
                count += 1
                if count <= 1:
                    new_reply += c
            else:
                new_reply += c
        reply = new_reply
        guard = 'G9_emoji_limited'

    # G10: Sem promessas de ranking absoluto
    if re.search(r'1ª posição|primeira posição|garantimos ranking|posição 1 no google', reply, re.IGNORECASE):
        reply = re.sub(r'1ª posição|primeira posição|posição 1 no google', 'melhores posições locais', reply, flags=re.IGNORECASE)
        reply = re.sub(r'garantimos ranking', 'melhoramos o posicionamento', reply, flags=re.IGNORECASE)
        guard = 'G10_ranking_absoluto'

    # G11: Close sem nome do contato → pedir nome antes
    if next_stage == 'close':
        facts = decision.get("update_facts", {}) or {}
        if not facts.get("contact_name"):
            # Verifica se já temos nome no histórico
            has_name = any("contact_name" in str(m) for m in historico) if historico else False
            if not has_name and "nome" not in reply.lower() and "quem" not in reply.lower():
                reply += "\n\nMe passa seu nome pra eu finalizar?"
                guard = 'G11_ask_name'

    decision["reply"] = reply
    decision["next_stage"] = next_stage
    return decision, guard

# ===== HORÁRIO DE ATENDIMENTO =====

def _dentro_do_horario() -> bool:
    """Verifica se está dentro do horário de atendimento (seg-sáb, 8h-21h Brasília)"""
    from datetime import datetime, timezone, timedelta
    agora = datetime.now(timezone(timedelta(hours=-3)))
    # 0=segunda, 6=domingo
    if agora.weekday() == 6:  # domingo
        return False
    return 8 <= agora.hour < 21

# ===== SAUDAÇÃO POR HORÁRIO =====

def _saudacao_horario() -> str:
    """Retorna saudação baseada no horário de Brasília"""
    from datetime import datetime, timezone, timedelta
    hora = datetime.now(timezone(timedelta(hours=-3))).hour
    if hora < 12:
        return "Bom dia"
    if hora < 18:
        return "Boa tarde"
    return "Boa noite"

# ===== A/B VARIANT =====

def _escolher_variante(lead_id: str) -> str:
    """Escolhe variante A/B/C/D baseado no hash do lead para teste A/B"""
    h = sum(ord(c) for c in str(lead_id))
    variantes = ['A', 'B', 'C', 'D']
    return variantes[h % 4]

# ===== AGENTE BRYAN =====

BRYAN_INSTRUCTIONS = """Você é Franz — closer de elite disfarçado de cara normal.

═══════════════════════════════════
FILOSOFIA CENTRAL (NUNCA QUEBRE):

1. Você NÃO é vendedor. Você é um cara da região que DESCOBRIU algo sobre o negócio deles.
2. O site é a PROVA FINAL que sela o negócio — não a isca. O lead precisa IMPLORAR pra ver.
3. Você QUALIFICA o lead (ele precisa merecer sua atenção), não o contrário.
4. Cada mensagem extrai um micro-compromisso (um "sim" pequeno) antes do próximo passo.
5. Você AMPLIFICA a dor antes de oferecer solução. Sem dor = sem venda.
6. Você usa "Negative Reverse" — tira a oferta pra fazer o lead puxar de volta.
7. Escassez territorial: "só consigo fazer isso pra um negócio por bairro/segmento".

O lead NÃO sabe quem você é. NÃO estava esperando sua mensagem.
Se você parecer vendedor em qualquer momento antes do stage "tease" → PERDEU.

═══════════════════════════════════
VARIANTES A/B (use a variante indicada no contexto):

VARIANTE A — "O Vizinho Curioso":
  Finge ser alguém da região que conhece/frequenta o tipo de negócio.
  Ex hook: "Boa tarde! Vocês são de musculação ou funcional também?"
  Transição: conversa sobre o negócio → percebe que pode ajudar

VARIANTE B — "O Observador":
  Notou algo específico (avaliação, localização, movimento).
  Ex hook: "Boa tarde! Vi vocês no Google Maps — {rating}⭐, isso é raro aqui!"
  Transição: elogio genuíno → conversa → curiosidade do lead

VARIANTE C — "O Pesquisador":
  Fazendo um estudo/levantamento da região.
  Ex hook: "Boa tarde! Tô fazendo um levantamento sobre {segmento} aqui. Posso te fazer uma pergunta rápida?"
  Transição: pesquisa → insight → "descobri uma coisa sobre vocês"

VARIANTE D — "O Indicador":
  Alguém indicou ou ele viu em algum lugar.
  Ex hook: "Boa tarde! Me indicaram vocês — é academia de musculação mesmo?"
  Transição: conversa de potencial cliente → revela que pode ajudar

═══════════════════════════════════
FUNIL DE STAGES (NÃO PULE — cada stage é obrigatório):

  hook     → Pattern interrupt. Abordagem conforme variante. Máx 1-2 linhas.
  qualify  → EU escolho VOCÊ. Perguntas que posicionam Bryan como seletor.
  pain     → Descobrir a dor real. "Como vocês captam clientes hoje?"
  amplify  → Amplificar a dor. Custo da inação. "Quantos clientes por semana te acham pelo Google?"
  tease    → Plantar semente SEM revelar. "Descobri uma coisa interessante sobre vocês..."
  proof    → Prova social + concorrentes. "Fiz pra um [similar] e o resultado foi X"
  reveal   → Mostrar o site SOMENTE quando lead PEDIR ou demonstrar desejo forte.
  feedback → "O que achou?" — lead se compromete verbalmente com o que viu.
  close    → "Quer que eu coloque no ar pra vocês?" — próximo passo concreto.
  urgency  → Escassez: "Só consigo manter isso ativo até [data]" / "Só faço 1 por bairro"

═══════════════════════════════════
DETALHAMENTO DE CADA STAGE:

HOOK (1 mensagem):
• Pattern interrupt — quebrar o padrão do dia do lead
• Parecer humano normal, não vendedor
• Gerar curiosidade ou iniciar conversa natural
• Micro-compromisso: fazer o lead RESPONDER (qualquer coisa)

QUALIFY (1-2 mensagens):
• Posicionar Bryan como quem SELECIONA, não quem oferece
• "Vocês atendem bastante gente da região?" (implica que importa)
• "Há quanto tempo vocês tão aqui?" (valida se vale a pena)
• "Vocês trabalham mais com indicação ou pessoal novo?" (descobre canal)
• Tom: genuinamente curioso, como quem avalia se vai frequentar
• Micro-compromisso: lead responde sobre o próprio negócio

PAIN (1-2 mensagens):
• Descobrir como captam clientes HOJE
• "E pessoal novo, como te acha? Google, Instagram, boca a boca?"
• "Vocês aparecem quando alguém pesquisa [segmento] + [cidade]?"
• Se lead diz "só indicação" → DOR ENCONTRADA (depende de terceiros)
• Se lead diz "Google" → verificar se é verdade (provavelmente não é)
• Micro-compromisso: lead admite uma limitação

AMPLIFY (1-2 mensagens — STAGE MAIS IMPORTANTE):
• Fazer o lead SENTIR o custo de não agir
• "Sabe o que eu notei? Quando pesquiso [segmento] em [cidade], quem aparece primeiro é [concorrente]"
• "Imagina quantas pessoas por dia pesquisam isso e vão pro concorrente sem nem saber que vocês existem"
• "Só por curiosidade, quanto vale um cliente novo pra vocês? Se são 10 por mês que vão pro outro..."
• Future Pacing: "Imagina alguém pesquisando [serviço] em [cidade] e o primeiro resultado ser vocês"
• NÃO oferecer solução ainda — só amplificar
• Micro-compromisso: lead reconhece que está perdendo algo

TEASE (1-2 mensagens — CRIAR GAP DE CURIOSIDADE):
• Plantar a semente sem revelar o que é
• "Olha, eu não sei se faz sentido pra vocês..." (Negative Reverse)
• "Descobri uma coisa sobre o negócio de vocês que achei interessante"
• "Fiz uma análise aqui e... bom, não sei se vocês iam querer saber"
• "Talvez nem seja pra vocês, mas..." (takeaway)
• O lead TEM QUE PERGUNTAR "o que é?" / "me conta" / "fala"
• Se lead não perguntar → repetir tease com outro ângulo
• NUNCA revelar sem o lead pedir
• Micro-compromisso: lead pede pra saber mais

PROOF (1-2 mensagens):
• Prova social ANTES de mostrar o site
• "Fiz isso pra um [negócio similar] aqui perto e em 2 semanas já tava aparecendo no Google"
• "O [concorrente] de vocês já tem isso funcionando" (se verdade)
• Escassez: "Eu só faço pra um por bairro/segmento — pra não competir entre si"
• Micro-compromisso: lead demonstra interesse em ver

REVEAL (1 mensagem — SÓ QUANDO LEAD PEDIR):
• Enviar o link do site
• "Montei isso aqui pra vocês — dá uma olhada sem compromisso nenhum"
• "Não precisa decidir nada agora, só queria saber o que acha"
• Tom: casual, sem pressão, como quem mostra algo legal pra um amigo
• IMPORTANTE: o site já está pronto — isso é a prova de que Bryan fez o dever de casa

FEEDBACK (1-2 mensagens — COMPROMETIMENTO VERBAL):
• "E aí, o que achou?" — fazer o lead VERBALIZAR que gostou
• Se lead elogia → ancorar: "Legal né? Imagina isso aparecendo quando pesquisam [segmento] em [cidade]"
• Se lead neutro → "O que mudaria pra ficar a cara de vocês?"
• Se lead critica → "Entendi! Isso é 100% personalizável — logo, cores, fotos, tudo"
• Micro-compromisso: lead diz algo positivo sobre o site

CLOSE (1-2 mensagens):
• "Quer que eu coloque no ar pra vocês?"
• "Só paga depois que tiver 100% aprovado e no ar"
• "Não tem custo nenhum pra ajustar — só paga quando tiver perfeito"
• Se lead hesita → "Sem pressa! Mas só pra eu saber, o que falta pra fazer sentido?"
• Micro-compromisso: lead diz sim ou revela objeção real

URGENCY (se lead hesita no close):
• "Olha, eu mantenho isso no ar por 7 dias — depois disso o domínio libera"
• "Como eu disse, só faço 1 por bairro. Se outro [segmento] pedir..."
• "Não quero te pressionar, mas não consigo segurar isso muito tempo"
• Negative Reverse: "Olha, se não faz sentido agora, sem problema. Posso oferecer pra outro"
• NUNCA inventar urgência falsa — usar escassez real (1 por bairro, domínio expira)

═══════════════════════════════════
DECISOR — FLUXO GATEKEEPER (5 NÍVEIS DE INSISTÊNCIA):
Quando a pessoa diz "não sou o dono/responsável" — NÃO aceite de primeira.
Trate o gatekeeper como ALIADO, não obstáculo. Siga os níveis em ordem:

NÍVEL 1 — MICRO-COMPROMISSO IMEDIATO (primeira tentativa):
  - "Ah tranquilo! Ele tá aí agora? Só queria trocar uma ideia rápida com ele"
  - "Sem problema! Consegue me passar pra ele? É coisa de 2 min"
  - "De boa! Ele tá por perto? Queria só mostrar uma coisa"
  Objetivo: conseguir acesso AGORA, sem explicar o que é.

NÍVEL 2 — TORNAR O GATEKEEPER ALIADO (se nível 1 falhou):
  - "Entendi! E qual o nome dele? Pra eu não chegar perdido"
  - "Ah beleza! Você que cuida do dia a dia então? Deixa eu te perguntar uma coisa..."
  - Fazer rapport COM o gatekeeper — ele pode influenciar o dono
  - Perguntar sobre o negócio (discovery funciona com qualquer pessoa)
  Objetivo: extrair nome do dono + criar conexão com quem atendeu.

NÍVEL 3 — CRIAR URGÊNCIA LEVE (se nível 2 não gerou acesso):
  - "É que eu vi uma coisa sobre [negócio] que achei que ele ia querer saber"
  - "Sem stress! É que tem uma janela curta pra isso, por isso queria falar logo"
  - "Posso te mandar um negócio pra mostrar pra ele? Acho que ele vai curtir"
  Objetivo: fazer o gatekeeper sentir que é importante passar a msg.

NÍVEL 4 — PEDIR CONTATO DIRETO (se nível 3 não funcionou):
  - "Qual o WhatsApp dele? Mando direto pra não te incomodar"
  - "Ele tem outro número que eu consiga falar?"
  - "Qual o melhor horário pra pegar ele aqui?"
  Objetivo: conseguir canal direto com o decisor.

NÍVEL 5 — AGENDAR (ÚLTIMO RECURSO, só se tudo acima falhou):
  - "Beleza! Quando ele tá por aí normalmente?"
  - "Qual dia/horário ele costuma tá disponível?"
  - Só agendar se o gatekeeper EXPLICITAMENTE disser um dia/horário
  - next_stage: "scheduled" + followup_date

REGRAS DO FLUXO GATEKEEPER:
• NUNCA agendar na primeira resposta — sempre tentar nível 1 antes
• Cada nível = 1 mensagem. Avançar de nível só se o anterior não funcionou
• Se o gatekeeper demonstrar interesse próprio → fazer discovery COM ELE (pode virar aliado interno)
• Se conseguir nome do dono → salvar em update_facts.contact_name
• Se conseguir número direto → salvar em update_facts.decisor_contato
• Manter tom leve e natural — insistência ≠ pressão. É curiosidade genuína.
• Se gatekeeper ficar irritado/pedir pra parar → respeitar, agendar (nível 5)

═══════════════════════════════════
AGENDAMENTO:
Se o lead pedir pra voltar outro dia/horário (ou nível 5 do gatekeeper):
  - Confirmar: "Beleza, te mando mensagem [dia] então!"
  - Salvar em update_facts: "followup_date": "YYYY-MM-DD" (usar DATA DE HOJE do contexto pra calcular)
  - next_stage: "scheduled"
  - Bryan NÃO envia mais nada até a data chegar
  - IMPORTANTE: "amanhã" = DATA DE HOJE + 1 dia. "segunda" = próxima segunda. Calcular a partir da DATA DE HOJE informada no contexto.

═══════════════════════════════════
GATILHOS PARA AVANÇAR DE STAGE:

hook → qualify:
  Lead respondeu qualquer coisa (mesmo "quem é?")

qualify → pain:
  Lead respondeu 1+ pergunta sobre o negócio

pain → amplify:
  Lead admitiu limitação ou revelou como capta clientes

amplify → tease:
  Lead reconheceu que perde algo OU respondeu 2+ msgs no amplify

tease → proof:
  Lead PEDIU pra saber mais ("o que é?", "me conta", "fala", "como assim?")

proof → reveal:
  Lead pediu pra ver OU disse "mostra", "manda", "quero ver"

reveal → feedback:
  Site foi enviado (automático)

feedback → close:
  Lead verbalizou algo positivo sobre o site

close → urgency:
  Lead hesitou, pediu tempo, ou não respondeu ao close

REGRA: Se lead perguntar "quem é você?" / "o que você quer?" em qualquer stage antes do tease:
  → NÃO revelar. Responder evasivo: "Sou da região, tava pesquisando sobre {segmento} aqui"
  → Só avançar pra tease se lead INSISTIR (2+ vezes perguntando)

═══════════════════════════════════
ESTILO — TOM FRANZ:
• Cara normal da região, não vendedor
• Informal mas educado — WhatsApp real
• Curioso genuinamente sobre o negócio deles
• Humor leve e natural quando cabe
• NUNCA use: "presença digital", "marketing", "SEO", "site" antes do reveal
• NUNCA pareça que tem um script decorado
• Adapte ao segmento: se é academia, fale como quem treina. Se é restaurante, como quem come lá.

═══════════════════════════════════
INFORMAÇÕES DO PRODUTO (SÓ USAR APÓS STAGE REVEAL):

SOBRE O SITE:
• Já está PRONTO e montado especialmente para eles
• 100% personalizável: logo, dados, fotos, textos, cores
• Só paga DEPOIS que estiver 100% aprovado e no ar
• Não tem custo nenhum pra ver

SOBRE SEO E TRÁFEGO:
• Keywords com volume real de buscas
• Feito para ser indexado pelo Google
• Concorrência foi estudada e aplicada

SOBRE O CONTRATO:
• Protege os DOIS lados
• Inclui: domínio + hospedagem por 1 ano

═══════════════════════════════════
TABELA DE PREÇOS (SÓ APÓS STAGE VALUE):

DEGRAU 0 — ÂNCORA: "Projeto sai por R$ 2.000 — mas tenho condição especial: R$ 1.499 em 12x"
DEGRAU 1 — R$ 1.499 em 12x (R$ 124,92/mês) | Pix: R$ 1.424,05
DEGRAU 2 — R$ 999 em 12x (R$ 83,25/mês) | Pix: R$ 949,05
DEGRAU 3 — PISO: R$ 549 em 12x (R$ 45,75/mês) — NUNCA abaixo
DEGRAU 4 — PIX RECORRENTE: Entrada R$ 250 + parcelas mensais

ORDER BUMP (só após fechar): Blog R$ 49,90/mês

═══════════════════════════════════
REGRAS ABSOLUTAS:
1. Máx 3 linhas por mensagem
2. UMA pergunta por mensagem
3. Máx 1 emoji — zero se lead desconfiado
4. NUNCA revelar o que faz antes do stage tease
5. NUNCA mencionar site/preço antes do stage adequado
6. NUNCA parecer vendedor nos stages iniciais (hook → amplify)
7. Se lead disser NÃO antes do tease: curiosity hook (sem revelar)
8. Se lead disser NÃO após reveal: 3 tentativas antes de lost
9. Mínimo 4 trocas antes de qualquer tease (hook + qualify + pain + amplify)
10. Se lead perguntar "o que você quer?" → resposta evasiva + curiosidade
11. Após 3 rejeições: agradecer, deixar porta aberta, marcar lost
12. Se lead muito quente (stage close): sinalizar handoff humano
13. Se lead pedir pra voltar outro dia → agendar (scheduled + followup_date)
14. NUNCA pular stages — cada um constrói sobre o anterior
15. Se lead pular direto pra "quanto custa?" → responder com tease/proof primeiro, depois preço

═══════════════════════════════════
SAÍDA — responda SOMENTE JSON válido, sem markdown:
{{
  "intent": "greeting|curiosity|engagement|wants_link|objection_trust|objection_price|objection_time|acceptance|rejection|schedule|off_topic|other",
  "emotion": "neutro|curioso|desconfiado|animado|resistente|humorado|aberto",
  "reply": "mensagem (máx 3 linhas, tom natural de WhatsApp)",
  "next_stage": "hook|qualify|pain|amplify|tease|proof|reveal|feedback|close|urgency|handoff|won|lost|scheduled|followup_24h",
  "should_handoff": false,
  "price_tier": 0,
  "update_facts": {{ "contact_name": "", "is_decisor": null, "deal_status": "", "main_objection": "", "followup_date": "", "discovery_answers": 0, "lead_asked_what_i_do": false, "price_tier": 0, "order_bump_offered": false, "gatekeeper_level": 0, "decisor_contato": "", "pain_identified": "", "amplify_done": false }}
}}
"""

# ===== HISTÓRICO DE INTERAÇÕES =====

def _carregar_historico_interacoes(telefone: str, limite: int = 5) -> str:
    """
    Carrega as últimas N mensagens da tabela interacoes para o lead.
    Retorna string formatada 'Bryan: msg\\nLead: resposta' ou '' se falhar.
    """
    try:
        from sqlalchemy import create_engine, text as sa_text
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url:
            return ""
        engine = create_engine(db_url)
        with engine.connect() as conn:
            rows = conn.execute(
                sa_text(
                    """
                    SELECT i.mensagem, i.direcao
                    FROM interacoes i
                    JOIN leads l ON l.id = i.lead_id
                    WHERE :tel IN (l.telefone, l.telefone_whatsapp, l.whatsapp)
                       OR regexp_replace(COALESCE(l.telefone_whatsapp, l.whatsapp, l.telefone, ''), '\\D', '', 'g')
                          = regexp_replace(:tel, '\\D', '', 'g')
                    ORDER BY i.id DESC
                    LIMIT :lim
                    """
                ),
                {"tel": telefone, "lim": limite}
            ).fetchall()
        if not rows:
            return ""
        # Inverte para ordem cronológica
        rows = list(reversed(rows))
        linhas = []
        for row in rows:
            autor = "Bryan" if row.direcao == "saida" else "Lead"
            linhas.append(f"{autor}: {row.mensagem}")
        return "\n".join(linhas)
    except Exception as e:
        print(f"[Bryan] Aviso: não foi possível carregar histórico: {e}")
        return ""


# Função criar_agente_bryan() removida - não é mais necessária com HTTP direto

def clean_json_response(text: str) -> str:
    """Remove markdown code blocks do JSON"""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    return text.strip()

def safe_json_loads(text: str) -> dict:
    """Parse JSON com sanitizacao agressiva de caracteres de controle"""
    # 1. Remover chars de controle do texto completo
    text = clean_control_characters(text)
    # 2. Encode/decode para limpar qualquer char invalido residual
    text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
    # 3. Substituir chars de controle dentro de strings JSON por espaco
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', ' ', text)
    # 4. Normalizar quebras de linha dentro de strings
    text = re.sub(r'(?<!\\)\n', ' ', text)
    return json.loads(text)

@require_rag("Bryan")
def iniciar_contato(lead: BryanInput) -> BryanOutput:
    """
    Inicia contato com lead qualificado — gera mensagem de intro (lead FRIO).
    NÃO revela site na primeira msg. Se apresenta, explica como achou, pergunta pelo decisor.
    RESPEITA HORÁRIO: seg-sáb 8h-21h Brasília. Fora disso, retorna enviado=False com motivo.
    """
    # Verificar horário de atendimento — NÃO aborda fora do horário
    if not _dentro_do_horario():
        print(f"⏰ [Franz] Fora do horário — intro para {lead.nome} adiada (fila)")
        return BryanOutput(
            reply="",
            intent="fila",
            next_stage="hook",
            estrategia="fila",
            proximo_passo="Aguardando horário comercial (seg-sáb 8h-21h)",
            enviado=False
        )

    # Verificar se já contatou antes
    memoria = carregar_memoria(f"bryan_lead_{lead.telefone}")
    if memoria:
        print(f"⚠️ [Franz] Lead {lead.nome} já foi contatado antes")
        stage = memoria.get("estado", "hook")
        rejection_count = memoria.get("rejection_count", 0)
        price_tier = memoria.get("price_tier", 0)
    else:
        stage = "hook"
        rejection_count = 0
        price_tier = 0

    # Sanitizar campos
    nome_safe = sanitize_text(lead.nome)
    cidade_safe = sanitize_text(lead.cidade)
    segmento_safe = sanitize_text(lead.segmento)

    # Carregar histórico
    historico_raw = _carregar_historico_interacoes(lead.telefone, limite=8)

    # Montar bloco de concorrentes
    conc_bloco = ""
    if lead.concorrentes:
        top3 = lead.concorrentes.get("top3", [])
        padroes = lead.concorrentes.get("padroes", {})
        if top3:
            nomes_conc = [c.get("nome", "") for c in top3[:3] if c.get("nome")]
            conc_bloco = f"Concorrentes: {', '.join(nomes_conc)}\n"
        if padroes:
            conc_bloco += f"Padrões do mercado: {padroes.get('servicos', '')} | {padroes.get('diferenciais', '')}\n"

    # Decidir estratégia
    estrategia = decidir_estrategia("other", stage, rejection_count)
    variant = _escolher_variante(lead.telefone)
    saudacao = _saudacao_horario()

    # Montar user prompt completo
    prompt = f"""CONTEXTO DO LEAD:
- Empresa: {nome_safe} ({segmento_safe}) — {cidade_safe}
- Avaliação Google: {lead.rating or 'N/A'}⭐
- Stage atual: {stage}
- Variante: {variant}
- Saudação horário: {saudacao}
{conc_bloco}
{f"HISTÓRICO:{chr(10)}{historico_raw}" if historico_raw else "Primeiro contato — sem histórico."}

TAREFA: Gere a mensagem de INTRO usando a VARIANTE {variant}.

VARIANTE A — "O Vizinho Curioso":
  Finja ser alguém da região que frequenta/conhece o tipo de negócio.
  Faça uma pergunta como potencial cliente.
  Ex: "{saudacao}! Vocês são de musculação ou funcional também?"
  Ex: "{saudacao}! Vi que vocês são aqui da região — atendem iniciante?"

VARIANTE B — "O Observador":
  Notou algo específico (avaliação, localização).
  Ex: "{saudacao}! Vi vocês no Google Maps — {lead.rating or '4.5'}⭐, isso é raro aqui na região!"
  Ex: "{saudacao}! Vocês têm bastante avaliação positiva hein, como conseguem?"

VARIANTE C — "O Pesquisador":
  Fazendo um levantamento/estudo da região.
  Ex: "{saudacao}! Tô fazendo um levantamento sobre {segmento_safe} aqui da região. Posso te fazer uma pergunta rápida?"
  Ex: "{saudacao}! Tô pesquisando sobre {segmento_safe} aqui perto — vocês são os mais conhecidos?"

VARIANTE D — "O Indicador":
  Alguém indicou ou viu em algum lugar.
  Ex: "{saudacao}! Me indicaram vocês — é {segmento_safe} mesmo?"
  Ex: "{saudacao}! Vi vocês num grupo aqui da região — vocês atendem público geral?"

REGRAS DA INTRO:
- Máximo 1-2 linhas. Curta. Natural. Humana.
- NÃO se apresente. NÃO diga seu nome. NÃO mencione empresa.
- NÃO mencione site, marketing, presença digital, SEO, análise.
- NÃO diga "estava analisando" ou "me chamou atenção" — isso é vendedor.
- Pareça um ser humano normal mandando mensagem no WhatsApp.
- A pergunta deve ser sobre O NEGÓCIO DELES, não sobre você.

Responda SOMENTE JSON válido."""

    try:
        rag_context = buscar_contexto_rag("contato sdr whatsapp closer", "bryan")
        full_prompt = format_rag_prompt(prompt, rag_context)
        mark_rag_used("bryan")

        response_text = call_claude(
            system=BRYAN_INSTRUCTIONS,
            user=full_prompt,
            model="haiku",
            max_tokens=500,
            temperature=0.7,
            agent_name="Franz"
        )

        print(f"[Franz] Resposta recebida: {len(response_text)} chars")
        clean_text = clean_json_response(response_text)
        decision = safe_json_loads(clean_text)

        # Aplicar guardrails
        decision, guard = aplicar_guardrails(
            decision, stage, nome_safe,
            [{"role": "assistant", "content": m.split(": ", 1)[1] if ": " in m else m}
             for m in historico_raw.split("\n") if m.startswith("Bryan:")]
            if historico_raw else []
        )

        if guard:
            print(f"[Franz] Guardrail ativado: {guard}")

        # Salvar memória
        next_stage = decision.get("next_stage", "qualify")
        salvar_memoria(f"bryan_lead_{lead.telefone}", {
            "lead": lead.model_dump(),
            "estado": next_stage,
            "rejection_count": rejection_count,
            "price_tier": decision.get("price_tier", 0),
            "variant": variant,
            "facts": decision.get("update_facts", {}),
            "tentativas": 1
        })

        print(f"✅ [Franz] Intro criada para {lead.nome} (variante {variant})")
        print(f"   Reply: {decision['reply'][:80]}...")

        return BryanOutput(
            reply=decision["reply"],
            intent=decision.get("intent", "greeting"),
            next_stage=next_stage,
            estrategia=estrategia,
            proximo_passo="Aguardar resposta do lead (24h)",
            enviado=False,
            should_handoff=decision.get("should_handoff", False),
            price_tier=decision.get("price_tier", 0),
            guard=guard,
            update_facts=decision.get("update_facts")
        )

    except Exception as e:
        print(f"[Franz] ❌ Erro ao criar intro: {e}")
        # Fallback hardcoded — intro segura
        fallback_reply = f"{_saudacao_horario()}! Me chamo Franz, da FraLib — analiso presença digital de negócios locais.\n\nEncontrei a {nome_safe} pesquisando {segmento_safe} em {cidade_safe}. Falo com o responsável?"
        return BryanOutput(
            reply=fallback_reply,
            intent="greeting",
            next_stage="qualify",
            estrategia="rapport_build",
            proximo_passo="Aguardar resposta do lead (24h)",
            enviado=False
        )

def _consultar_aprendizado_segmento(segmento: str) -> str:
    """
    Consulta sdr_learning para o segmento e retorna contexto de aprendizado.
    Busca 3 convertidos e 3 perdidos mais recentes.
    """
    if not segmento:
        return ""
    try:
        from sqlalchemy import create_engine, text as sa_text
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url:
            return ""
        engine = create_engine(db_url)
        with engine.connect() as conn:
            convertidos = conn.execute(sa_text("""
                SELECT mensagem_usada, observacao
                FROM sdr_learning
                WHERE resultado = 'convertido'
                  AND (segmento ILIKE :seg OR nicho ILIKE :seg)
                ORDER BY id DESC
                LIMIT 3
            """), {"seg": f"%{segmento}%"}).fetchall()

            perdidos = conn.execute(sa_text("""
                SELECT mensagem_usada, observacao
                FROM sdr_learning
                WHERE resultado = 'perdido'
                  AND (segmento ILIKE :seg OR nicho ILIKE :seg)
                ORDER BY id DESC
                LIMIT 3
            """), {"seg": f"%{segmento}%"}).fetchall()

        linhas = []
        if convertidos:
            linhas.append("Abordagens que funcionaram neste segmento:")
            for r in convertidos:
                msg = r[0] or ""
                obs = r[1] or ""
                trecho = (msg[:120] + "...") if len(msg) > 120 else msg
                if obs:
                    linhas.append(f"  - {trecho} [obs: {obs[:80]}]")
                else:
                    linhas.append(f"  - {trecho}")

        if perdidos:
            linhas.append("Abordagens que NAO funcionaram neste segmento:")
            for r in perdidos:
                msg = r[0] or ""
                obs = r[1] or ""
                trecho = (msg[:120] + "...") if len(msg) > 120 else msg
                if obs:
                    linhas.append(f"  - {trecho} [obs: {obs[:80]}]")
                else:
                    linhas.append(f"  - {trecho}")

        return "\n".join(linhas) if linhas else ""
    except Exception as e:
        print(f"[Bryan] Aviso: não foi possível consultar sdr_learning: {e}")
        return ""


def responder_lead(
    telefone: str,
    mensagem_recebida: str,
    nome_negocio: str = ""
) -> BryanOutput:
    """
    Responde mensagem do lead — state machine completa com guardrails.
    Detecta intent, decide estratégia, chama LLM, aplica guardrails.
    """
    # Carregar contexto da conversa
    memoria = carregar_memoria(f"bryan_lead_{telefone}")
    if not memoria:
        print(f"⚠️ [Franz] Sem contexto para lead {telefone}")
        stage = "hook"
        rejection_count = 0
        price_tier = 0
        order_bump_offered = False
        lead_data = {}
        segmento_lead = ""
    else:
        stage = memoria.get("estado", "hook")
        rejection_count = memoria.get("rejection_count", 0)
        price_tier = memoria.get("price_tier", 0)
        order_bump_offered = memoria.get("facts", {}).get("order_bump_offered", False)
        lead_data = memoria.get("lead", {})
        segmento_lead = lead_data.get("segmento", "")

    # Detectar intent e estratégia
    intent = detectar_intent(mensagem_recebida)

    # Detectar se é bot/msg automática — responder direto sem LLM
    bot_check = detectar_bot(mensagem_recebida)
    if bot_check["is_bot"]:
        resposta_bot = gerar_resposta_bot(bot_check, nome_negocio)
        if resposta_bot:
            print(f"🤖 [Franz] Bot detectado ({bot_check['tipo']}, conf={bot_check['confidence']:.1f}) → respondendo: {resposta_bot}")
            # Salvar na memória que está navegando bot
            if memoria:
                memoria["navegando_bot"] = True
                memoria["bot_tentativas"] = memoria.get("bot_tentativas", 0) + 1
                salvar_memoria(f"bryan_lead_{telefone}", memoria)
            return BryanOutput(
                intent="other",
                emotion="neutro",
                reply=resposta_bot,
                next_stage=stage,  # Não avança stage enquanto fala com bot
                should_handoff=False,
                price_tier=price_tier
            )

    # OPT-OUT imediato
    if intent == 'opt_out':
        salvar_memoria(f"bryan_lead_{telefone}", {
            **(memoria or {}),
            "estado": "lost",
            "facts": {**(memoria or {}).get("facts", {}), "deal_status": "opt_out"}
        })
        return BryanOutput(
            reply="Entendido! Vou remover seu contato agora. Se mudar de ideia no futuro, pode chamar 👍",
            intent="opt_out",
            next_stage="lost",
            estrategia="opt_out",
            proximo_passo="Lead removido",
            enviado=False
        )

    # Incrementar rejeições
    new_rejection_count = rejection_count + 1 if intent == 'rejection' else rejection_count

    # 3 rejeições → lost
    if new_rejection_count >= 3:
        nome = nome_negocio or lead_data.get("nome", "vocês")
        reply_final = f"Tudo bem, respeito totalmente a decisão! 👍\n\nFoi um prazer. Se um dia fizer sentido, é só me chamar."
        salvar_memoria(f"bryan_lead_{telefone}", {
            **(memoria or {}),
            "estado": "lost",
            "rejection_count": new_rejection_count,
            "facts": {**(memoria or {}).get("facts", {}), "deal_status": "lost"}
        })
        return BryanOutput(
            reply=reply_final,
            intent="rejection",
            next_stage="lost",
            estrategia="value_push",
            proximo_passo="Lead perdido após 3 rejeições",
            enviado=False
        )

    estrategia = decidir_estrategia(intent, stage, new_rejection_count)

    # Carregar histórico e aprendizado
    historico_raw = _carregar_historico_interacoes(telefone, limite=8)
    aprendizado = _consultar_aprendizado_segmento(segmento_lead)

    # Dados do lead
    nome = nome_negocio or lead_data.get("nome", "Cliente")
    cidade = lead_data.get("cidade", "")
    segmento = segmento_lead
    site_url = lead_data.get("site_url", "")
    rating = lead_data.get("rating", "")
    proof = lead_data.get("proof", "Sem presença digital profissional")
    contact_name = (memoria or {}).get("facts", {}).get("contact_name", "")

    # Concorrentes
    conc_bloco = ""
    concorrentes = lead_data.get("concorrentes")
    if concorrentes:
        top3 = concorrentes.get("top3", [])
        padroes = concorrentes.get("padroes", {})
        if top3:
            nomes_conc = [c.get("nome", "") for c in top3[:3] if c.get("nome")]
            conc_bloco = f"Concorrentes: {', '.join(nomes_conc)}\n"
        if padroes:
            conc_bloco += f"Padrões: {padroes.get('servicos', '')} | {padroes.get('diferenciais', '')}\n"

    # Montar prompt
    from datetime import datetime as _dt, timedelta as _td
    import pytz as _tz
    _agora_br = _dt.now(_tz.timezone("America/Sao_Paulo"))
    _data_hoje = _agora_br.strftime("%Y-%m-%d")
    _dia_semana = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"][_agora_br.weekday()]
    _amanha = (_agora_br + _td(days=1)).strftime("%Y-%m-%d")

    prompt = f"""CONTEXTO DO LEAD:
- DATA DE HOJE: {_data_hoje} ({_dia_semana}) — AMANHÃ: {_amanha}
- Empresa: {nome} ({segmento}) — {cidade}
- Site gerado: {site_url or 'Em preparação'}
- Problema identificado: {proof}
- Avaliação Google: {rating or 'N/A'}⭐
- Nome do contato: {contact_name or 'Não identificado'}
- Stage atual: {stage}
- Estratégia: {estrategia}
- Tentativas de reversão: {new_rejection_count}/3
- Nível gatekeeper: {(memoria or {}).get("facts", {}).get("gatekeeper_level", 0)}/5 (0=não ativado, 1-5=níveis de insistência)
- Degrau de preço atual: {price_tier} (0=não revelado, 1=R$1.499, 2=R$999, 3=R$549, 4=pix)
- Order bump já ofertado: {order_bump_offered}
{conc_bloco}
{f"PADRÕES VENCEDORES:{chr(10)}{aprendizado}" if aprendizado else "Sem padrões ainda — primeiro ciclo neste nicho."}

=== HISTÓRICO ===
{historico_raw or "Sem histórico anterior."}

=== CLIENTE AGORA ===
"{mensagem_recebida}"

Responda SOMENTE JSON válido."""

    try:
        rag_context = buscar_contexto_rag("contato sdr whatsapp closer negociação", "bryan")
        full_prompt = format_rag_prompt(prompt, rag_context)
        mark_rag_used("bryan")

        response_text = call_claude(
            system=BRYAN_INSTRUCTIONS,
            user=full_prompt,
            model="haiku",
            max_tokens=500,
            temperature=0.7,
            agent_name="Franz"
        )

        print(f"[Franz] Resposta recebida: {len(response_text)} chars")
        clean_text = clean_json_response(response_text)
        decision = safe_json_loads(clean_text)

        # Aplicar guardrails
        historico_list = []
        if historico_raw:
            for line in historico_raw.split("\n"):
                if line.startswith("Bryan:"):
                    historico_list.append({"role": "assistant", "content": line.split(": ", 1)[1] if ": " in line else line})

        decision, guard = aplicar_guardrails(decision, stage, nome, historico_list)

        if guard:
            print(f"[Franz] Guardrail ativado: {guard}")

        # Atualizar memória
        next_stage = decision.get("next_stage", stage)
        new_price_tier = decision.get("price_tier", price_tier)
        new_facts = decision.get("update_facts", {})

        salvar_memoria(f"bryan_lead_{telefone}", {
            "lead": lead_data,
            "estado": next_stage,
            "rejection_count": new_rejection_count,
            "price_tier": new_price_tier if new_price_tier else price_tier,
            "facts": {
                **(memoria or {}).get("facts", {}),
                **(new_facts or {}),
                "order_bump_offered": order_bump_offered or (next_stage == "order_bump"),
            },
            "tentativas": (memoria or {}).get("tentativas", 0) + 1
        })

        print(f"✅ [Franz] Resposta para {telefone}: stage {stage}→{next_stage}")

        return BryanOutput(
            reply=decision["reply"],
            intent=decision.get("intent", intent),
            next_stage=next_stage,
            estrategia=estrategia,
            proximo_passo="Handoff para closer" if decision.get("should_handoff") else "Aguardar resposta do lead",
            enviado=False,
            should_handoff=decision.get("should_handoff", False),
            price_tier=new_price_tier if new_price_tier else price_tier,
            guard=guard,
            update_facts=new_facts
        )

    except Exception as e:
        print(f"[Franz] ❌ Erro ao criar resposta: {e}")
        # Fallback baseado no intent
        fallbacks = {
            'wants_link': f"Aqui está! 👇\n{site_url}\n\nMontei especialmente pra {nome}. É só ver, sem compromisso.",
            'objection_trust': f"Faz sentido questionar! Me chamo Franz, da FraLib, encontrei vocês no Google Maps.\n\nO site já está pronto, é gratuito pra ver 👇\n{site_url}",
            'objection_price': "Me conta o que pesou — foi o valor total ou a parcela?\n\nO que você acharia justo pagar por um site assim?",
            'acceptance': "Ótimo! Me passa seu nome pra eu personalizar melhor o atendimento?",
        }
        fallback_reply = fallbacks.get(intent, f"Entendi! Me conta mais sobre o que você precisa pra eu te ajudar melhor.")
        return BryanOutput(
            reply=fallback_reply,
            intent=intent,
            next_stage=stage,
            estrategia=estrategia,
            proximo_passo="Aguardar resposta do lead",
            enviado=False
        )

# ===== FOLLOW-UP AUTOMÁTICO =====

def gerar_followup(lead_data: dict, tipo: str) -> str:
    """Gera mensagem de follow-up baseada no tipo"""
    nome = lead_data.get("nome", "vocês")
    url = lead_data.get("site_url", "")
    cidade = lead_data.get("cidade", "")
    segmento = lead_data.get("segmento", "")

    msgs = {
        "24h": f"Oi! Franz aqui de novo — ainda tenho o projeto da {nome} reservado aqui 😄\n\n{url}\n\nO que achou? Qualquer ajuste é só falar.",
        "72h": f"{nome}, última passagem por aqui da minha parte!\n\nO link ainda tá no ar por mais uns dias: {url}\n\nSe fizer sentido no futuro, pode me chamar quando quiser 👋",
        "scheduled": f"Oi! Franz aqui, conforme combinamos 😄 Conseguiu dar uma olhada naquilo que te mandei?",
        "rejeicao_1": f"Sem problema! Antes de sumir — me diz uma coisa:\n\nQuando alguém pesquisa \"{segmento}\" em {cidade}, a {nome} aparece lá na frente ou fica escondida?",
        "rejeicao_2": f"Entendo, sem pressão! Só uma reflexão:\n\nSeu concorrente que aparece antes de vocês no Google — quantos clientes ele pega que seriam de vocês?\n\nO site já tá pronto, não custa nada dar uma olhada.",
        "rejeicao_3": f"Tudo bem, respeito totalmente a decisão! 👍\n\nFoi um prazer. Se um dia fizer sentido, é só me chamar.",
    }
    return msgs.get(tipo, msgs["24h"])


def followup_automatico(telefone: str, tipo: str = "24h") -> BryanOutput:
    """
    Envia follow-up automático para lead sem resposta.
    Chamado pelo cron/worker. Respeita horário de atendimento.

    Args:
        telefone: Telefone do lead
        tipo: "24h", "72h", "rejeicao_1", "rejeicao_2", "rejeicao_3"

    Returns:
        BryanOutput com a mensagem de follow-up
    """
    # Respeitar horário — follow-up só dentro do horário
    if not _dentro_do_horario():
        print(f"⏰ [Franz] Follow-up fora do horário — adiado")
        return BryanOutput(
            reply="",
            intent="fila",
            next_stage="followup_24h",
            estrategia="followup",
            proximo_passo="Aguardando horário comercial",
            enviado=False
        )

    # Carregar contexto
    memoria = carregar_memoria(f"bryan_lead_{telefone}")
    if not memoria:
        print(f"⚠️ [Franz] Sem contexto para follow-up de {telefone}")
        return BryanOutput(
            reply="",
            intent="other",
            next_stage="lost",
            estrategia="followup",
            proximo_passo="Sem contexto — ignorado",
            enviado=False
        )

    lead_data = memoria.get("lead", {})
    stage = memoria.get("estado", "hook")

    # Gerar mensagem
    reply = gerar_followup(lead_data, tipo)

    # Atualizar memória
    new_stage = f"followup_{tipo}" if "rejeicao" not in tipo else stage
    salvar_memoria(f"bryan_lead_{telefone}", {
        **memoria,
        "estado": new_stage,
        "tentativas": memoria.get("tentativas", 0) + 1
    })

    print(f"✅ [Franz] Follow-up '{tipo}' gerado para {lead_data.get('nome', telefone)}")

    return BryanOutput(
        reply=reply,
        intent="followup",
        next_stage=new_stage,
        estrategia="followup",
        proximo_passo="Aguardar resposta do lead",
        enviado=False
    )


def despachar_fila_leads(leads: list) -> list:
    """
    Despacha leads que ficaram na fila (site pronto, fora do horário).
    Chamado pelo cron/worker quando entra no horário comercial.

    Args:
        leads: Lista de dicts com dados dos leads (nome, cidade, segmento, telefone, etc)

    Returns:
        Lista de BryanOutput para cada lead processado
    """
    if not _dentro_do_horario():
        print(f"⏰ [Franz] Fora do horário — fila não despachada")
        return []

    resultados = []
    for lead_dict in leads:
        try:
            lead = BryanInput(**lead_dict)
            resultado = iniciar_contato(lead)
            resultados.append(resultado)
            print(f"[Franz] Fila: intro para {lead.nome} — {'OK' if resultado.reply else 'SKIP'}")
        except Exception as e:
            print(f"[Franz] Fila: erro em {lead_dict.get('nome', '?')}: {e}")
            resultados.append(BryanOutput(
                reply="",
                intent="error",
                next_stage="hook",
                estrategia="fila",
                proximo_passo=f"Erro: {str(e)[:50]}",
                enviado=False
            ))
    return resultados


# ===== TESTE =====

if __name__ == "__main__":

    # Teste com lead válido
    lead_teste = BryanInput(
        nome="Clínica Dental Sorriso",
        cidade="Curitiba",
        segmento="dentista",
        telefone="41999999999",
        whatsapp="5541999999999",
        rating=4.8,
        site_url="https://fralib.com.br/clinica-dental-sorriso",
        score_caio=85,
        tier="PREMIUM",
        proof="Sem site profissional, perde clientes para concorrentes com presença online"
    )

    def testar():
        # Teste 1: Iniciar contato
        resultado = iniciar_contato(lead_teste)
        print(f"\n📊 Resultado Intro:")
        print(f"   Estratégia: {resultado.estrategia}")
        print(f"   Reply: {resultado.reply}")
        print(f"   Next stage: {resultado.next_stage}")
        print(f"   Guard: {resultado.guard}")

        # Teste 2: Responder lead
        print("\n\n--- Teste de Resposta ---")
        resposta = responder_lead(
            telefone="41999999999",
            mensagem_recebida="Oi! Quanto custa esse site?",
            nome_negocio="Clínica Dental Sorriso"
        )
        print(f"   Reply: {resposta.reply}")
        print(f"   Intent: {resposta.intent}")
        print(f"   Stage: {resposta.next_stage}")
        print(f"   Guard: {resposta.guard}")

    testar()


def capturar_feedback_whatsapp(site_id: str, mensagem_cliente: str):
    """Captura feedback do cliente via WhatsApp e envia para Brain"""
    print(f"[Bryan] Capturando feedback do cliente para site {site_id}")
    feedback_cliente(site_id, mensagem_cliente)
