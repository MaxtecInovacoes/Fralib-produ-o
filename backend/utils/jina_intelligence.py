"""
Jina Intelligence — Inteligência de mercado estruturada.
Substitui a Jina antiga (68 chars genéricos) por dados reais:
- Tom de voz do mercado
- Palavras que vendem
- Frases genéricas observadas
- Headlines/CTAs de referência
- Estilo visual dominante
- Diferencial disponível

Fallbacks por nicho quando Jina Reader falha.
"""

import os
import re
import json
import hashlib
import time
import sys

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents"),
)

JINA_API_KEY = os.getenv("JINA_API_KEY", "")

# Sites modelo por nicho (fallback quando não acha concorrente local)
REFERENCIAS_NICHO = {
    "academia": "https://www.smartfit.com.br",
    "crossfit": "https://www.crossfitbrasil.com.br",
    "hamburgueria": "https://www.bullguer.com.br",
    "pizzaria": "https://www.pizzariabatepapo.com.br",
    "dentista": "https://www.odontocompany.com",
    "nutricionista": "https://www.nutricionistaadrianalauffer.com.br",
    "barbearia": "https://www.barbeariadonjuan.com.br",
    "salao": "https://www.jacquesjanine.com.br",
    "clinica": "https://www.dfrancisco.com.br",
    "pet": "https://www.petlove.com.br",
    "restaurante": "https://www.madero.com.br",
    "pilates": "https://www.pilatesstudiobrasil.com.br",
    "estetica": "https://www.espacolaser.com.br",
    "advocacia": "https://www.mattosfilho.com.br",
    "contabilidade": "https://www.contabilizei.com.br",
    "imobiliaria": "https://www.quintoandar.com.br",
    "escola": "https://www.kumon.com.br",
    "mecanica": "https://www.dpaschoal.com.br",
}

# Frases genéricas comuns do mercado. São contexto, não regra para o Builder.
FRASES_GENERICAS_PADRAO = [
    "atendimento personalizado",
    "qualidade e compromisso",
    "resultados reais",
    "os melhores profissionais",
    "pronto para começar",
    "excelência em atendimento",
    "sua satisfação é nossa prioridade",
    "venha nos conhecer",
    "entre em contato",
]


def buscar_inteligencia_jina(
    nicho: str, cidade: str, nome_negocio: str, concorrentes_urls: list = None
) -> dict:
    """
    Busca inteligência real de mercado via Jina Reader.
    Retorna dict estruturado. Síncrono (compatível com pipeline atual).
    Cache de 48h por nicho+cidade.
    """

    # Cache
    _cache_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "agents",
        "jina_cache",
    )
    os.makedirs(_cache_dir, exist_ok=True)
    _cache_key = hashlib.md5(
        (nicho.lower() + cidade.lower() + "v2").encode()
    ).hexdigest()[:12]
    _cache_file = os.path.join(_cache_dir, f"jina_intel_{_cache_key}.json")
    _TTL = 48 * 3600

    if (
        os.path.exists(_cache_file)
        and (time.time() - os.path.getmtime(_cache_file)) < _TTL
    ):
        try:
            with open(_cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            print(
                f"[Jina Intel] Cache HIT: {nicho} em {cidade} ({len(json.dumps(cached))} chars)"
            )
            return cached
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
            pass

    # Tentar buscar inteligência real via Jina
    resultado = None
    try:
        resultado = _buscar_real(nicho, cidade, nome_negocio, concorrentes_urls)
    except Exception as e:
        print(f"[Jina Intel] Erro busca real: {e}")

    # Fallback se busca real falhou
    if not resultado or not resultado.get("palavras_poder"):
        print(f"[Jina Intel] Usando fallback por nicho: {nicho}")
        resultado = _fallback_inteligencia(nicho)

    # Salvar cache
    try:
        with open(_cache_file, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False)
    except (OSError, IOError):
        pass

    total = len(json.dumps(resultado, ensure_ascii=False))
    print(
        f"[Jina Intel] OK: {total} chars, {len(resultado.get('palavras_poder', []))} palavras-poder"
    )
    return resultado


def _buscar_real(
    nicho: str, cidade: str, nome_negocio: str, concorrentes_urls: list = None
) -> dict:
    """Busca real via Jina Reader — lê sites concorrentes e analisa."""
    import requests

    urls_analisar = []

    # Prioridade 1: URLs de concorrentes já encontrados
    if concorrentes_urls:
        urls_analisar = [u for u in concorrentes_urls[:2] if u and u.startswith("http")]

    # Prioridade 2: Buscar via Google
    if not urls_analisar:
        urls_analisar = _buscar_concorrentes_google(nicho, cidade)

    # Prioridade 3: Site modelo do nicho
    if not urls_analisar:
        nicho_lower = nicho.lower()
        for key, url in REFERENCIAS_NICHO.items():
            if key in nicho_lower or nicho_lower in key:
                urls_analisar = [url]
                break

    if not urls_analisar:
        return None

    # Ler e analisar cada site
    resultados = []
    headers = {"X-Return-Format": "text", "X-Timeout": "15"}
    if JINA_API_KEY:
        headers["Authorization"] = f"Bearer {JINA_API_KEY}"

    for url in urls_analisar[:2]:
        try:
            print(f"[Jina Intel] Lendo: {url}")
            resp = requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=20)
            if resp.status_code == 200 and len(resp.text) > 200:
                conteudo = resp.text[:5000]
                analise = _analisar_conteudo_llm(conteudo, nicho, cidade, nome_negocio)
                if analise:
                    analise["url_fonte"] = url
                    resultados.append(analise)
                    print(f"[Jina Intel] Análise OK: {url}")
        except Exception as e:
            print(f"[Jina Intel] Erro lendo {url}: {e}")

    if not resultados:
        return None

    return _consolidar_inteligencia(resultados, nicho, cidade, nome_negocio)


def _buscar_concorrentes_google(nicho: str, cidade: str) -> list:
    """Busca URLs de concorrentes via Jina Search."""
    import requests

    query = f"melhor {nicho} {cidade} site oficial"
    headers = {"X-Return-Format": "markdown", "X-Timeout": "15"}
    if JINA_API_KEY:
        headers["Authorization"] = f"Bearer {JINA_API_KEY}"

    EXCLUIR = [
        "google",
        "facebook",
        "instagram",
        "youtube",
        "linkedin",
        "twitter",
        "smartfit",
        "bodytech",
        "bluefit",
        "mcdonalds",
        "starbucks",
        "yelp",
        "tripadvisor",
        "ifood",
        "rappi",
        "reclameaqui",
        "guiamais",
        "apontador",
        "telelistas",
        "wikipedia",
        "amazon",
        "mercadolivre",
        "wix.com",
        "wordpress.com",
        "blogspot",
    ]

    try:
        search_url = f"https://r.jina.ai/https://www.google.com/search?q={requests.utils.quote(query)}"
        resp = requests.get(search_url, headers=headers, timeout=20)
        if resp.status_code != 200:
            return []

        urls = []
        for line in resp.text.split("\n"):
            if "http" in line:
                url_match = re.search(r"https?://[^\s\)\"\x27]+", line)
                if url_match:
                    url = url_match.group(0).rstrip(".,)")
                    if not any(exc in url.lower() for exc in EXCLUIR) and len(url) > 15:
                        urls.append(url)
                        if len(urls) >= 2:
                            break
        return urls
    except Exception as e:
        print(f"[Jina Intel] Erro busca Google: {e}")
        return []


def _analisar_conteudo_llm(
    conteudo: str, nicho: str, cidade: str, nome_negocio: str
) -> dict:
    """Analisa conteúdo extraído via Haiku (barato)."""
    from llm_direct import call_claude

    prompt = f"""Analise este site de {nicho} e extraia APENAS este JSON (sem texto extra):

{{
  "tom_de_voz": "como eles falam (formal/casual/premium/popular/técnico/emocional)",
  "palavras_poder": ["10 palavras/expressões que usam pra vender"],
  "frases_genericas": ["frases comuns ou clichês observados no mercado"],
  "headlines": ["3 headlines eficazes encontradas no site"],
  "ctas": ["os CTAs mais fortes (texto dos botões)"],
  "proposta_valor": "em 1 frase, o que esse negócio promete",
  "estilo_visual": "dark/light, cores dominantes, tipografia, sensação geral",
  "secoes_presentes": ["lista das seções do site na ordem"],
  "diferencial_comunicado": "o que eles dizem que os torna únicos",
  "publico_alvo": "pra quem o site fala (idade, perfil, dor)"
}}

CONTEÚDO DO SITE:
{conteudo[:4000]}

Retorne APENAS o JSON."""

    try:
        resp = call_claude(
            system="Você extrai inteligência de marketing de sites. Retorne APENAS JSON válido.",
            user=prompt,
            model="haiku",
            max_tokens=800,
            temperature=0.1,
            agent_name="jina_intel",
        )
        json_match = re.search(r"\{[\s\S]*\}", resp)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"[Jina Intel] Erro análise LLM: {e}")

    return None


def _consolidar_inteligencia(
    resultados: list, nicho: str, cidade: str, nome_negocio: str
) -> dict:
    """Consolida análises de múltiplos concorrentes."""
    palavras_poder = []
    frases_genericas = list(FRASES_GENERICAS_PADRAO)
    headlines = []
    ctas = []
    estilos = []

    for r in resultados:
        palavras_poder.extend(r.get("palavras_poder", []))
        frases_genericas.extend(r.get("frases_genericas", []))
        headlines.extend(r.get("headlines", []))
        ctas.extend(r.get("ctas", []))
        estilos.append(r.get("estilo_visual", ""))

    # Deduplica
    palavras_poder = list(dict.fromkeys(palavras_poder))[:12]
    frases_genericas = list(dict.fromkeys(frases_genericas))[:15]
    headlines = list(dict.fromkeys(headlines))[:5]
    ctas = list(dict.fromkeys(ctas))[:5]

    return {
        "tom_de_voz": resultados[0].get("tom_de_voz", "profissional-direto"),
        "palavras_poder": palavras_poder,
        "frases_genericas": frases_genericas,
        "headlines_referencia": headlines,
        "ctas_referencia": ctas,
        "estilo_visual": estilos[0] if estilos else "moderno, clean",
        "proposta_valor_concorrentes": [
            r.get("proposta_valor", "") for r in resultados if r.get("proposta_valor")
        ],
        "secoes_comuns": resultados[0].get("secoes_presentes", []),
        "diferencial_ausente": _detectar_diferencial(resultados, nome_negocio),
        "publico_alvo": resultados[0].get("publico_alvo", ""),
        "fontes_analisadas": [r.get("url_fonte", "") for r in resultados],
    }


def _detectar_diferencial(resultados: list, nome_negocio: str) -> str:
    """Identifica o que NENHUM concorrente menciona — oportunidade."""
    todos_textos = " ".join(
        json.dumps(r, ensure_ascii=False) for r in resultados
    ).lower()

    diferenciais_possiveis = [
        ("horário estendido", "horário"),
        ("aula experimental grátis", "experimental"),
        ("estacionamento", "estacionamento"),
        ("ar condicionado", "ar condicionado"),
        ("sem matrícula", "matrícula"),
        ("plano sem fidelidade", "fidelidade"),
        ("personal incluso", "personal"),
        ("avaliação física", "avaliação"),
        ("primeira consulta grátis", "primeira consulta"),
        ("atendimento 24h", "24h"),
    ]

    temas_ausentes = []
    for diferencial, keyword in diferenciais_possiveis:
        if keyword not in todos_textos:
            temas_ausentes.append(diferencial)

    if temas_ausentes:
        return f"Nenhum concorrente menciona: {', '.join(temas_ausentes[:3])}. Oportunidade."
    return "Mercado saturado — diferenciar por experiência e tom de voz."


def _fallback_inteligencia(nicho: str) -> dict:
    """Fallback por nicho quando Jina falha. Melhor que 68 chars."""
    fallbacks = {
        "academia": {
            "tom_de_voz": "motivacional-direto, frases curtas, verbos de ação",
            "palavras_poder": [
                "supere",
                "transforme",
                "resultado",
                "evolução",
                "limite",
                "força",
                "disciplina",
                "conquista",
                "treino",
                "performance",
            ],
            "frases_genericas": list(FRASES_GENERICAS_PADRAO),
            "headlines_referencia": [
                "Seu corpo. Suas regras. Seu ritmo.",
                "Treino que transforma — não só o corpo.",
                "Aqui ninguém treina sozinho.",
            ],
            "ctas_referencia": [
                "Agende sua aula grátis",
                "Comece hoje",
                "Quero conhecer",
                "Ver planos",
            ],
            "estilo_visual": "dark, cores intensas (vermelho/amarelo), tipografia bold, fotos de ação",
            "secoes_comuns": [
                "hero",
                "sobre",
                "modalidades",
                "planos",
                "depoimentos",
                "contato",
            ],
            "diferencial_ausente": "Explorar: comunidade, resultados reais de alunos, sem fidelidade",
            "publico_alvo": "25-45 anos, busca saúde e estética, quer motivação e acompanhamento",
        },
        "crossfit": {
            "tom_de_voz": "intenso-tribal, comunidade, desafio",
            "palavras_poder": [
                "WOD",
                "comunidade",
                "superação",
                "box",
                "atleta",
                "funcional",
                "intensidade",
                "evolução",
                "PR",
                "squad",
            ],
            "frases_genericas": list(FRASES_GENERICAS_PADRAO),
            "headlines_referencia": [
                "Seu limite é só o começo.",
                "Treine com quem entende de verdade.",
                "Mais que treino — família.",
            ],
            "ctas_referencia": [
                "Agende seu trial",
                "Primeira aula grátis",
                "Conheça o box",
                "Quero começar",
            ],
            "estilo_visual": "dark, vermelho/preto, tipografia bold condensed, fotos de grupo",
            "secoes_comuns": [
                "hero",
                "modalidades",
                "coaches",
                "horarios",
                "depoimentos",
                "contato",
            ],
            "diferencial_ausente": "Explorar: programação individualizada, acompanhamento nutricional",
            "publico_alvo": "22-40 anos, busca desafio e comunidade, não quer academia convencional",
        },
        "hamburgueria": {
            "tom_de_voz": "casual-premium, sensorial, direto",
            "palavras_poder": [
                "artesanal",
                "defumado",
                "suculento",
                "na brasa",
                "premium",
                "blend",
                "smash",
                "sabor",
                "receita",
                "ingredientes",
            ],
            "frases_genericas": list(FRASES_GENERICAS_PADRAO),
            "headlines_referencia": [
                "Carne nobre, fogo de verdade.",
                "Hambúrguer que fala por si.",
                "Feito na hora. Sem atalhos.",
            ],
            "ctas_referencia": [
                "Ver cardápio",
                "Peça agora",
                "Reserve sua mesa",
                "Faça seu pedido",
            ],
            "estilo_visual": "dark, vermelho/dourado, tipografia bold, fotos close-up de comida",
            "secoes_comuns": [
                "hero",
                "cardapio",
                "sobre",
                "depoimentos",
                "delivery",
                "contato",
            ],
            "diferencial_ausente": "Explorar: ingredientes locais, processo artesanal, história do fundador",
            "publico_alvo": "20-40 anos, foodie, valoriza experiência gastronômica",
        },
        "pizzaria": {
            "tom_de_voz": "gastronômico-acolhedor, sensorial, familiar-premium",
            "palavras_poder": [
                "massa",
                "fornada",
                "sabor",
                "artesanal",
                "ingredientes",
                "tradição",
                "família",
                "pedido",
                "mesa",
                "experiência",
            ],
            "frases_genericas": list(FRASES_GENERICAS_PADRAO),
            "headlines_referencia": [
                "Pizza feita para reunir gente em volta da mesa.",
                "Sabor de pizzaria local com cuidado em cada fornada.",
                "Peça pelo WhatsApp e escolha sua próxima pizza.",
            ],
            "ctas_referencia": [
                "Fazer pedido",
                "Chamar no WhatsApp",
                "Ver opções",
                "Como chegar",
            ],
            "estilo_visual": "gastronomia premium, fotos de comida em destaque, alto contraste, detalhes quentes",
            "secoes_comuns": [
                "hero",
                "prova social",
                "sobre",
                "opcoes",
                "localizacao",
                "pedido",
                "footer",
            ],
            "diferencial_ausente": "Explorar experiência local e facilidade de pedido sem declarar cardápio, preços ou horário não informados.",
            "publico_alvo": "moradores locais, famílias e clientes buscando pizza para jantar, retirada ou pedido rápido",
        },
        "dentista": {
            "tom_de_voz": "profissional-acolhedor, confiável, sem jargão",
            "palavras_poder": [
                "sorriso",
                "confiança",
                "cuidado",
                "tecnologia",
                "conforto",
                "resultado",
                "especialista",
                "transformação",
                "indolor",
                "moderno",
            ],
            "frases_genericas": list(FRASES_GENERICAS_PADRAO),
            "headlines_referencia": [
                "Seu sorriso merece especialistas.",
                "Odontologia moderna. Sem medo.",
                "Cuide do seu sorriso com quem entende.",
            ],
            "ctas_referencia": [
                "Agende sua avaliação",
                "Marcar consulta",
                "Fale com a gente",
                "Quero agendar",
            ],
            "estilo_visual": "light, azul/verde-menta, clean, fotos de sorrisos reais",
            "secoes_comuns": [
                "hero",
                "tratamentos",
                "equipe",
                "estrutura",
                "depoimentos",
                "contato",
            ],
            "diferencial_ausente": "Explorar: antes/depois, tecnologia específica, atendimento humanizado",
            "publico_alvo": "25-55 anos, medo de dentista, busca confiança e resultado estético",
        },
        "barbearia": {
            "tom_de_voz": "masculino-casual, confiante, sem frescura",
            "palavras_poder": [
                "estilo",
                "corte",
                "barba",
                "navalha",
                "tradição",
                "precisão",
                "experiência",
                "cerveja",
                "relaxe",
                "identidade",
            ],
            "frases_genericas": list(FRASES_GENERICAS_PADRAO),
            "headlines_referencia": [
                "Corte certo. Sem enrolação.",
                "Sua barba, nossa especialidade.",
                "Mais que um corte — uma experiência.",
            ],
            "ctas_referencia": [
                "Agendar horário",
                "Reserve agora",
                "Ver serviços",
                "Marcar meu horário",
            ],
            "estilo_visual": "dark, dourado/preto, vintage-moderno, tipografia serif bold",
            "secoes_comuns": [
                "hero",
                "servicos",
                "barbeiros",
                "galeria",
                "depoimentos",
                "contato",
            ],
            "diferencial_ausente": "Explorar: ambiente exclusivo, cerveja artesanal, clube de assinatura",
            "publico_alvo": "20-45 anos, masculino, valoriza aparência e experiência",
        },
        "nutricionista": {
            "tom_de_voz": "acolhedor-científico, empático, sem terrorismo alimentar",
            "palavras_poder": [
                "equilíbrio",
                "saúde",
                "hábito",
                "resultado",
                "acompanhamento",
                "personalizado",
                "ciência",
                "bem-estar",
                "rotina",
                "evolução",
            ],
            "frases_genericas": list(FRASES_GENERICAS_PADRAO)
            + ["dieta restritiva", "emagreça rápido", "perca peso"],
            "headlines_referencia": [
                "Nutrição que respeita sua rotina.",
                "Comer bem não precisa ser difícil.",
                "Resultados que duram — sem sofrimento.",
            ],
            "ctas_referencia": [
                "Agende sua consulta",
                "Quero começar",
                "Fale comigo",
                "Marcar avaliação",
            ],
            "estilo_visual": "light, verde/bege, clean, fotos de alimentos reais",
            "secoes_comuns": [
                "hero",
                "sobre",
                "servicos",
                "como-funciona",
                "depoimentos",
                "contato",
            ],
            "diferencial_ausente": "Explorar: atendimento online, plano flexível, sem dieta pronta",
            "publico_alvo": "25-50 anos, feminino majoritário, busca saúde sem radicalismo",
        },
        "estetica": {
            "tom_de_voz": "premium-acolhedor, resultado, autoestima",
            "palavras_poder": [
                "rejuvenescimento",
                "resultado",
                "tecnologia",
                "autoestima",
                "cuidado",
                "protocolo",
                "transformação",
                "natural",
                "harmonização",
                "bem-estar",
            ],
            "frases_genericas": list(FRASES_GENERICAS_PADRAO) + ["milagre", "sem cirurgia"],
            "headlines_referencia": [
                "Sua melhor versão começa aqui.",
                "Tecnologia a favor da sua beleza.",
                "Resultados reais. Sem exagero.",
            ],
            "ctas_referencia": [
                "Agende sua avaliação",
                "Quero conhecer",
                "Ver tratamentos",
                "Fale conosco",
            ],
            "estilo_visual": "light/rosé, dourado, clean premium, fotos de antes/depois",
            "secoes_comuns": [
                "hero",
                "tratamentos",
                "sobre",
                "estrutura",
                "depoimentos",
                "contato",
            ],
            "diferencial_ausente": "Explorar: protocolos exclusivos, tecnologia de ponta, avaliação gratuita",
            "publico_alvo": "28-55 anos, feminino, busca autoestima e resultado natural",
        },
        "pet": {
            "tom_de_voz": "carinhoso-profissional, emocional, confiável",
            "palavras_poder": [
                "amor",
                "cuidado",
                "família",
                "saúde",
                "confiança",
                "carinho",
                "bem-estar",
                "segurança",
                "especialista",
                "peludo",
            ],
            "frases_genericas": list(FRASES_GENERICAS_PADRAO),
            "headlines_referencia": [
                "Seu pet merece o melhor.",
                "Cuidamos como se fosse nosso.",
                "Saúde e carinho pro seu melhor amigo.",
            ],
            "ctas_referencia": [
                "Agendar consulta",
                "Fale conosco",
                "Ver serviços",
                "Marcar banho",
            ],
            "estilo_visual": "light, verde/azul, fotos de pets felizes, tipografia rounded",
            "secoes_comuns": [
                "hero",
                "servicos",
                "equipe",
                "estrutura",
                "depoimentos",
                "contato",
            ],
            "diferencial_ausente": "Explorar: atendimento 24h, transporte pet, câmera ao vivo",
            "publico_alvo": "25-50 anos, tutores apaixonados, tratam pet como filho",
        },
    }

    nicho_lower = nicho.lower()
    for key, data in fallbacks.items():
        if key in nicho_lower or nicho_lower in key:
            return data

    # Fallback genérico
    return {
        "tom_de_voz": "profissional-direto, confiável",
        "palavras_poder": [
            "resultado",
            "confiança",
            "experiência",
            "qualidade",
            "especialista",
            "solução",
            "transformação",
            "compromisso real",
        ],
        "frases_genericas": list(FRASES_GENERICAS_PADRAO),
        "headlines_referencia": [],
        "ctas_referencia": ["Fale conosco", "Agende agora", "Quero conhecer"],
        "estilo_visual": "moderno, clean",
        "secoes_comuns": ["hero", "sobre", "servicos", "depoimentos", "contato"],
        "diferencial_ausente": "",
        "publico_alvo": "",
    }


def formatar_inteligencia_para_arquiteto(intel: dict) -> str:
    """Formata o dict de inteligência como texto pro prompt do ArquitetoMestre."""
    if not intel:
        return ""

    partes = [
        "=== INTELIGÊNCIA DE MERCADO (Jina AI) ===",
        "",
        f"TOM DE VOZ DO MERCADO: {intel.get('tom_de_voz', '')}",
        "",
        "LINGUAGEM COMERCIAL OBSERVADA:",
        f"  {', '.join(intel.get('palavras_poder', []))}",
        "",
    ]

    headlines = intel.get("headlines_referencia", [])
    if headlines:
        partes.append("HEADLINES DE REFERÊNCIA (inspiração, não copiar):")
        for h in headlines:
            partes.append(f"  - {h}")
        partes.append("")

    ctas = intel.get("ctas_referencia", [])
    if ctas:
        partes.append("CTAs QUE CONVERTEM:")
        for c in ctas:
            partes.append(f"  - {c}")
        partes.append("")

    partes.append(f"ESTILO VISUAL DO MERCADO: {intel.get('estilo_visual', '')}")
    partes.append(f"PÚBLICO-ALVO: {intel.get('publico_alvo', '')}")

    diferencial = intel.get("diferencial_ausente", "")
    if diferencial:
        partes.append(f"DIFERENCIAL DISPONÍVEL: {diferencial}")

    partes.append("")
    partes.append("Esta inteligência é referência de mercado para o próximo agente.")
    partes.append("=== FIM INTELIGÊNCIA ===")

    return "\n".join(partes)
