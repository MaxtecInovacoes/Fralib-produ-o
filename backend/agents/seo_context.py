"""seo_context.py - SEO Framework por nicho"""

CIDADE = "{" + "cidade" + "}"
NOME = "{" + "nome" + "}"

ALIASES = {
    "restaurantes": "restaurante", "barbearias": "barbearia",
    "clinicas": "clinica", "pet": "pet_shop", "pets": "pet_shop",
    "advogado": "advocacia", "dentista": "odontologia",
    "pizzarias": "pizzaria", "farmacias": "farmacia",
    "imoveis": "imobiliaria", "contabil": "contabilidade",
    "escolas": "escola", "salao": "salao_beleza",
    "auto_peca": "auto_pecas", "mecanica": "auto_pecas"
}

SEO_NICHOS = {
    "barbearia": {"schema": "BarberShop", "h1": "Barbearia em " + CIDADE + " - " + NOME, "kw": "barbearia em " + CIDADE + ", corte masculino " + CIDADE, "kw_long": "melhor barbearia " + CIDADE + ", barbearia perto de mim " + CIDADE, "intent": "transacional", "faq": ["Quanto custa um corte?", "Precisa agendar?", "Qual o horario?", "Fazem barba?"]},
    "restaurante": {"schema": "Restaurant", "h1": "Restaurante em " + CIDADE + " - " + NOME, "kw": "restaurante em " + CIDADE + ", onde comer " + CIDADE, "kw_long": "melhor restaurante " + CIDADE + ", jantar " + CIDADE, "intent": "comercial/transacional", "faq": ["Faz reservas?", "Tem delivery?", "Qual o horario?", "Tem estacionamento?"]},
    "clinica": {"schema": "MedicalBusiness", "h1": "Clinica em " + CIDADE + " - " + NOME, "kw": "clinica em " + CIDADE + ", medico " + CIDADE, "kw_long": "clinica particular " + CIDADE + ", medico perto de mim " + CIDADE, "intent": "transacional", "faq": ["Aceita convenio?", "Como agendar?", "Qual o valor?"]},
    "academia": {"schema": "SportsActivityLocation", "h1": "Academia em " + CIDADE + " - " + NOME, "kw": "academia em " + CIDADE + ", musculacao " + CIDADE, "kw_long": "academia perto de mim " + CIDADE + ", planos academia " + CIDADE, "intent": "transacional", "faq": ["Qual a mensalidade?", "Tem aula experimental?", "Qual o horario?"]},
    "pet_shop": {"schema": "AnimalShelter", "h1": "Pet Shop em " + CIDADE + " - " + NOME, "kw": "pet shop " + CIDADE + ", banho e tosa " + CIDADE, "kw_long": "pet shop perto de mim " + CIDADE, "intent": "transacional", "faq": ["Faz banho e tosa?", "Tem veterinario?", "Qual o preco?"]},
    "advocacia": {"schema": "LegalService", "h1": "Advogado em " + CIDADE + " - " + NOME, "kw": "advogado " + CIDADE + ", escritorio advocacia " + CIDADE, "kw_long": "advogado trabalhista " + CIDADE, "intent": "comercial", "faq": ["Quanto custa a consulta?", "Atende online?", "Como funcionam os honorarios?"]},
    "odontologia": {"schema": "Dentist", "h1": "Dentista em " + CIDADE + " - " + NOME, "kw": "dentista " + CIDADE + ", implante " + CIDADE, "kw_long": "dentista perto de mim " + CIDADE + ", clareamento dental " + CIDADE, "intent": "transacional", "faq": ["Aceita convenio?", "Faz clareamento?", "Como agendar?"]},
    "estetica": {"schema": "BeautySalon", "h1": "Estetica em " + CIDADE + " - " + NOME, "kw": "estetica " + CIDADE + ", limpeza de pele " + CIDADE, "kw_long": "estetica facial " + CIDADE + ", depilacao laser " + CIDADE, "intent": "transacional", "faq": ["Quais tratamentos?", "Quanto custa?", "Precisa agendar?"]},
    "pizzaria": {"schema": "FoodEstablishment", "h1": "Pizzaria em " + CIDADE + " - " + NOME, "kw": "pizzaria " + CIDADE + ", pizza delivery " + CIDADE, "kw_long": "melhor pizzaria " + CIDADE, "intent": "transacional", "faq": ["Faz delivery?", "Qual o horario?", "Qual a area de entrega?"]},
    "farmacia": {"schema": "Pharmacy", "h1": "Farmacia em " + CIDADE + " - " + NOME, "kw": "farmacia " + CIDADE + ", manipulacao " + CIDADE, "kw_long": "farmacia 24h " + CIDADE, "intent": "transacional", "faq": ["Faz manipulacao?", "Tem plantao 24h?", "Faz delivery?"]},
    "imobiliaria": {"schema": "RealEstateAgent", "h1": "Imobiliaria em " + CIDADE + " - " + NOME, "kw": "imobiliaria " + CIDADE + ", apartamento a venda " + CIDADE, "kw_long": "comprar apartamento " + CIDADE, "intent": "comercial", "faq": ["Tem imoveis disponiveis?", "Como funciona o financiamento?", "Qual regiao atende?"]},
    "contabilidade": {"schema": "AccountingService", "h1": "Contabilidade em " + CIDADE + " - " + NOME, "kw": "contabilidade " + CIDADE + ", contador " + CIDADE, "kw_long": "contador MEI " + CIDADE + ", declaracao IR " + CIDADE, "intent": "comercial", "faq": ["Quanto custa abrir empresa?", "Atende MEI?", "Faz IR?"]},
    "escola": {"schema": "School", "h1": "Escola em " + CIDADE + " - " + NOME, "kw": "escola " + CIDADE + ", colegio " + CIDADE, "kw_long": "escola particular " + CIDADE, "intent": "comercial", "faq": ["Como fazer matricula?", "Qual a mensalidade?", "Tem transporte?"]},
    "salao_beleza": {"schema": "HairSalon", "h1": "Salao de Beleza em " + CIDADE + " - " + NOME, "kw": "salao de beleza " + CIDADE + ", cabeleireiro " + CIDADE, "kw_long": "salao perto de mim " + CIDADE + ", progressiva " + CIDADE, "intent": "transacional", "faq": ["Precisa agendar?", "Faz progressiva?", "Qual o preco?"]},
    "auto_pecas": {"schema": "AutoRepair", "h1": "Auto Pecas em " + CIDADE + " - " + NOME, "kw": "auto pecas " + CIDADE + ", mecanica " + CIDADE, "kw_long": "auto pecas perto de mim " + CIDADE, "intent": "transacional", "faq": ["Quais marcas atende?", "Faz orcamento?", "Tem garantia?"]}
}


def get_seo_context(segmento: str, cidade: str, nome: str) -> str:
    seg = segmento.lower().replace(" ", "_").replace("-", "_")
    seg = ALIASES.get(seg, seg)
    seo = SEO_NICHOS.get(seg, {
        "schema": "LocalBusiness", "h1": nome + " em " + cidade,
        "kw": segmento + " em " + cidade, "kw_long": "melhor " + segmento + " " + cidade,
        "intent": "transacional", "faq": ["Como entrar em contato?", "Qual o horario?", "Onde fica?"]
    })
    h1 = seo["h1"]
    kw = seo["kw"]
    kw_long = seo["kw_long"]
    faq_str = "\n  ".join(["Q: " + q for q in seo["faq"]])
    schema = seo["schema"]
    intent = seo["intent"]
    return (
        "\n=== SEO FRAMEWORK - SIGA OBRIGATORIAMENTE ===\n"
        "SCHEMA.ORG: " + schema + " (usar no JSON-LD)\n"
        "H1 OBRIGATORIO: \"" + h1 + "\"\n"
        "INTENCAO DE BUSCA: " + intent + "\n\n"
        "KEYWORDS PRIMARIAS:\n  " + kw + "\n\n"
        "KEYWORDS CAUDA LONGA:\n  " + kw_long + "\n\n"
        "FAQ OBRIGATORIO (dados reais do lead, nunca inventar):\n  " + faq_str + "\n\n"
        "REGRAS SEO LOCAL:\n"
        "  - H1 deve conter cidade e nome do negocio\n"
        "  - Endereco completo visivel no footer\n"
        "  - Telefone em formato clicavel (tel:)\n"
        "  - Google Maps embed obrigatorio\n"
        "  - Meta description: 150-160 chars com keyword + cidade + CTA\n"
        "  - Title tag: " + h1 + " | FraLib\n"
        "=== FIM SEO ===\n"
    )
