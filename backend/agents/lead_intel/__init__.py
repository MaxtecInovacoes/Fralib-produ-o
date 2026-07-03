"""
Perguntas de cliente por nicho (Camada 4 do SDR Studio).

Usado pelo Franz pra iniciar conversa com perguntas que clientes REAIS
fariam do nicho - nao como vendedor, nao como "fingindo ser cliente" -
mas como se fosse alguem pesquisando o segmento.

Apos 1-2 respostas, leva pro pitch do site pronto.

Localizacao: /root/fralib/backend/agents/lead_intel/
Carregado em: prompts.py: load_buyer_questions(segmento)
"""

# Mapeamento nicho -> lista de 3-5 perguntas de cliente real
# Tom: curioso, casual, WhatsApp BR. NAO corporativo.
BUYER_QUESTIONS_BY_NICHO = {
    "academia": [
        "Oi! To pesquisando academia aqui em {cidade}. Como eh o plano de vcs? Tem taxa de matricula?",
        "E a flexibilidade de horario? Consigo treinar de manha cedo tipo 6h?",
        "Tem aula experimental gratis pra eu testar antes?",
    ],
    "restaurante": [
        "Oi! Vi que vcs tao no iFood. Como funciona o delivery ai? Tem taxa?",
        "E reserva pra fim de semana? Com quanto tempo de antecedencia precisa?",
        "Tem opcao vegetariana/vegana no cardapio?",
    ],
    "barbearia": [
        "E ai! To procurando uma barbearia aqui em {cidade}. Qual o preco do corte simples?",
        "E pra agendar, e melhor WhatsApp ou Instagram? Qual mais rapido?",
        "Atende sabado de manha?",
    ],
    "clinica": [
        "Oi! Preciso marcar uma consulta. Vcs atendem por qual plano?",
        "Demora muito pra conseguir uma vaga? Tem lista de espera?",
        "Aceita pagamento via Pix ou so cartao?",
    ],
    "dentista": [
        "Ola! To procurando dentista aqui em {cidade}. Fazem limpeza com quanto?",
        "Atendem emergencia? Tipo dor de dente fim de semana?",
        "Tem parcelamento pra tratamento maior tipo implante?",
    ],
    "nutricionista": [
        "Oi! To procurando nutricionista. A primeira consulta inclui o plano alimentar ou cobra separado?",
        "E online ou so presencial?",
        "Quantas sessoes costuma recomendar pra ter resultado?",
    ],
    "estetica": [
        "Ola! Vi o Instagram de vcs. Quanto ta o botox? Tem promocao pra quem faz mais de uma area?",
        "Preciso agendar com quanto tempo de antecedencia?",
        "Atende sabado?",
    ],
    "pet": [
        "Oi! Toca/banho pra cao de porte medio, quanto ta?",
        "E pra agendar, e mais facil pelo whats?",
        "Atende fim de semana?",
    ],
    "escola": [
        "Ola! To pesquisando escola pra meu filho. Qual a faixa etaria que vcs atendem?",
        "Tem matricula aberta ainda esse ano?",
        "Como eh o processo de rematricula? Tem desconto pra pagar anual?",
    ],
    "imobiliaria": [
        "Oi! To procurando apartamento pra alugar em {cidade}. Vcs tem opcao de 1 quarto na regiao central?",
        "O que esta incluso no aluguel - agua, condominio, internet?",
        "Tem fiador ou aceita seguro fianca?",
    ],
    "mecanica": [
        "E ai! Troca de oleo do carro - quanto ta em media ai?",
        "Demora quanto pra fazer? Consigo esperar?",
        "Atende sem agendamento ou tem que marcar?",
    ],
    "default": [
        "Oi! Vi vcs no Google. Como funciona o servico de vcs?",
        "E o horario de atendimento, como eh?",
        "Como faco pra contratar/agendar?",
    ],
}

# Templates de transicao (2a msg) - depois da resposta do lead,
# leva naturalmente pro pitch de apresentar o site pronto
TRANSITION_TO_PITCH = {
    "after_answer": [
        "Show, valeu pela info! Por curiosidade - vcs tem site? Pergunto pq tava procurando vcs no Google antes e nao achei facil.",
        "Massa! E sobre aparecer no Google - vcs ja tem site ou tao pensando em fazer?",
        "Boa! E quando alguém procura {segmento} em {cidade} no Google, vcs aparecem facil?",
    ],
    "when_lead_says_no_site": [
        "Pois eh, a maioria dos negocios locais nao tem. Eu inclusive ajudo com isso - tenho um exemplo pronto pra vcs. Posso mandar?",
        "Massa! A gente tem ajudado negocios de {cidade} a aparecer melhor no Google. Quer ver um exemplo? Leva 2 min, sem compromisso.",
    ],
    "when_lead_says_has_site": [
        "Show! E ele ta te gerando cliente ou vcs sentem que poderia render mais?",
        "Massa! E quando vcs pesquisam {segmento} em {cidade}, aparecem em qual posicao?",
    ],
}


def get_buyer_questions(segmento: str, cidade: str = "sua regiao") -> list:
    """Retorna 3 perguntas de cliente real baseado no segmento."""
    seg = (segmento or "default").lower().strip()
    # Match parcial (ex: "academia de danca" -> "academia")
    for key, qs in BUYER_QUESTIONS_BY_NICHO.items():
        if key in seg or seg in key:
            return [q.format(segmento=seg, cidade=cidade) for q in qs]
    return [q.format(segmento=seg, cidade=cidade) for q in BUYER_QUESTIONS_BY_NICHO["default"]]


def get_transition_to_pitch(segmento: str = "default") -> list:
    """Retorna templates de transicao pra 2a mensagem."""
    seg = (segmento or "default").lower().strip()
    for key, qs in BUYER_QUESTIONS_BY_NICHO.items():
        if key in seg or seg in key:
            return [q.format(segmento=seg) for q in TRANSITION_TO_PITCH["after_answer"]]
    return TRANSITION_TO_PITCH["after_answer"]


def get_pitch_response(segmento: str = "default", lead_has_site: bool = False) -> list:
    """Retorna respostas pro pitch quando lead diz se tem site ou nao."""
    key = "when_lead_says_has_site" if lead_has_site else "when_lead_says_no_site"
    seg = (segmento or "default").lower().strip()
    templates = TRANSITION_TO_PITCH[key]
    return [t.format(segmento=seg) for t in templates]
