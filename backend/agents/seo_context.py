"""seo_context.py - SEO Framework por nicho

DEPRECATED (Sprint 12.x): SEO_NICHOS existe apenas como fallback legacy.
Fonte unica de verdade: backend/config/nicho_registry.py::NichoConfig
que ja expoe seo_keywords e modal_config por nicho.

Este modulo mantem compatibilidade com imports externos, mas o codigo
de producao (get_seo_context abaixo) ja consulta o registry primeiro
e cai no SEO_NICHOS apenas se o nicho nao existir la.
"""

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
    "barbearia": {"schema": "BarberShop", "h1": "Barbearia em {cidade} - {nome}", "kw": "barbearia em {cidade}, corte masculino {cidade}", "kw_long": "melhor barbearia {cidade}, barbearia perto de mim {cidade}", "intent": "transacional", "faq": ["Quanto custa um corte?", "Precisa agendar?", "Qual o horario?", "Fazem barba?"]},
    "restaurante": {"schema": "Restaurant", "h1": "Restaurante em {cidade} - {nome}", "kw": "restaurante em {cidade}, onde comer {cidade}", "kw_long": "melhor restaurante {cidade}, jantar {cidade}", "intent": "comercial/transacional", "faq": ["Faz reservas?", "Tem delivery?", "Qual o horario?", "Tem estacionamento?"]},
    "clinica": {"schema": "MedicalBusiness", "h1": "Clinica em {cidade} - {nome}", "kw": "clinica em {cidade}, medico {cidade}", "kw_long": "clinica particular {cidade}, medico perto de mim {cidade}", "intent": "transacional", "faq": ["Aceita convenio?", "Como agendar?", "Qual o valor?"]},
    "academia": {"schema": "SportsActivityLocation", "h1": "Academia em {cidade} - {nome}", "kw": "academia em {cidade}, musculacao {cidade}", "kw_long": "academia perto de mim {cidade}, planos academia {cidade}", "intent": "transacional", "faq": ["Qual a mensalidade?", "Tem aula experimental?", "Qual o horario?"]},
    "pet_shop": {"schema": "AnimalShelter", "h1": "Pet Shop em {cidade} - {nome}", "kw": "pet shop {cidade}, banho e tosa {cidade}", "kw_long": "pet shop perto de mim {cidade}", "intent": "transacional", "faq": ["Faz banho e tosa?", "Tem veterinario?", "Qual o preco?"]},
    "advocacia": {"schema": "LegalService", "h1": "Advogado em {cidade} - {nome}", "kw": "advogado {cidade}, escritorio advocacia {cidade}", "kw_long": "advogado trabalhista {cidade}", "intent": "comercial", "faq": ["Quanto custa a consulta?", "Atende online?", "Como funcionam os honorarios?"]},
    "odontologia": {"schema": "Dentist", "h1": "Dentista em {cidade} - {nome}", "kw": "dentista em {cidade}, implante {cidade}", "kw_long": "dentista perto de mim {cidade}, clareamento dental {cidade}", "intent": "transacional", "faq": ["Aceita convenio?", "Faz clareamento?", "Como agendar?"]},
    "estetica": {"schema": "BeautySalon", "h1": "Estetica em {cidade} - {nome}", "kw": "estetica em {cidade}, limpeza de pele {cidade}", "kw_long": "estetica facial {cidade}, depilacao laser {cidade}", "intent": "transacional", "faq": ["Quais tratamentos?", "Quanto custa?", "Precisa agendar?"]},
    "pizzaria": {"schema": "FoodEstablishment", "h1": "Pizzaria em {cidade} - {nome}", "kw": "pizzaria em {cidade}, pizza delivery {cidade}", "kw_long": "melhor pizzaria {cidade}", "intent": "transacional", "faq": ["Faz delivery?", "Qual o horario?", "Qual a area de entrega?"]},
    "farmacia": {"schema": "Pharmacy", "h1": "Farmacia em {cidade} - {nome}", "kw": "farmacia em {cidade}, manipulacao {cidade}", "kw_long": "farmacia 24h {cidade}", "intent": "transacional", "faq": ["Faz manipulacao?", "Tem plantao 24h?", "Faz delivery?"]},
    "imobiliaria": {"schema": "RealEstateAgent", "h1": "Imobiliaria em {cidade} - {nome}", "kw": "imobiliaria em {cidade}, apartamento a venda {cidade}", "kw_long": "comprar apartamento {cidade}", "intent": "comercial", "faq": ["Tem imoveis disponiveis?", "Como funciona o financiamento?", "Qual regiao atende?"]},
    "contabilidade": {"schema": "AccountingService", "h1": "Contabilidade em {cidade} - {nome}", "kw": "contabilidade em {cidade}, contador {cidade}", "kw_long": "contador MEI {cidade}, declaracao IR {cidade}", "intent": "comercial", "faq": ["Quanto custa abrir empresa?", "Atende MEI?", "Faz IR?"]},
    "escola": {"schema": "School", "h1": "Escola em {cidade} - {nome}", "kw": "escola em {cidade}, colegio {cidade}", "kw_long": "escola particular {cidade}", "intent": "comercial", "faq": ["Como fazer matricula?", "Qual a mensalidade?", "Tem transporte?"]},
    "salao_beleza": {"schema": "HairSalon", "h1": "Salao de Beleza em {cidade} - {nome}", "kw": "salao de beleza {cidade}, cabeleireiro {cidade}", "kw_long": "salao perto de mim {cidade}, progressiva {cidade}", "intent": "transacional", "faq": ["Precisa agendar?", "Faz progressiva?", "Qual o preco?"]},
    "auto_pecas": {"schema": "AutoRepair", "h1": "Auto Pecas em {cidade} - {nome}", "kw": "auto pecas em {cidade}, mecanica {cidade}", "kw_long": "auto pecas perto de mim {cidade}", "intent": "transacional", "faq": ["Quais marcas atende?", "Faz orcamento?", "Tem garantia?"]}
}


def get_seo_context(segmento: str, cidade: str, nome: str) -> str:
    seg = segmento.lower().replace(" ", "_").replace("-", "_")
    seg = ALIASES.get(seg, seg)
    # Sprint 12.x: consultar nicho_registry primeiro (fonte unica)
    seo = None
    try:
        from backend.config.nicho_registry import get_nicho_config, get_schema_type
        cfg = get_nicho_config(seg)
        seo = {
            "schema": get_schema_type(seg),
            "h1": f"{{nome}} em {{cidade}}",
            "kw": ", ".join(cfg.seo_keywords[:3]),
            "kw_long": ", ".join(cfg.seo_keywords),
            "intent": "transacional",
            "faq": list(cfg.faq),
        }
    except Exception:
        pass
    # Fallback para SEO_NICHOS legacy
    if seo is None:
        seo = SEO_NICHOS.get(seg, {
            "schema": "LocalBusiness", "h1": "{nome} em {cidade}",
            "kw": "{segmento} em {cidade}", "kw_long": "melhor {segmento} {cidade}",
            "intent": "transacional", "faq": ["Como entrar em contato?", "Qual o horario?", "Onde fica?"]
        })
    h1 = seo["h1"].format(cidade=cidade, nome=nome, segmento=seg)
    kw = seo["kw"].format(cidade=cidade, segmento=seg)
    kw_long = seo["kw_long"].format(cidade=cidade, segmento=seg)
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
