import os, json, re, time, hashlib

import requests
from urllib.parse import quote

def clean_json_response(text: str) -> str:
    import re as _rcj

    bt = chr(96)
    text = text.replace(bt * 3 + "json", "").replace(bt * 3, "").strip()
    text = _rcj.sub(
        r"["
        + chr(0)
        + "-"
        + chr(8)
        + chr(11)
        + chr(12)
        + chr(14)
        + "-"
        + chr(31)
        + chr(127)
        + "]",
        "",
        text,
    )
    candidates = []
    i = 0
    while i < len(text):
        if text[i] != "{":
            i += 1
            continue
        depth = 0
        j = i
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[i : j + 1])
                    break
            j += 1
        i = j + 1
    return max(candidates, key=len) if candidates else text

def pesquisar_referencias_jina(segmento: str, cidade: str = "") -> str:
    _cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jina_cache")
    os.makedirs(_cache_dir, exist_ok=True)
    _cache_key = hashlib.md5((segmento.lower() + cidade.lower()).encode()).hexdigest()[
        :12
    ]
    _cache_file = os.path.join(_cache_dir, f"jina_{_cache_key}.txt")
    _TTL = 48 * 3600
    if (
        os.path.exists(_cache_file)
        and (time.time() - os.path.getmtime(_cache_file)) < _TTL
    ):
        print("[Jina AI] Cache HIT para segmento: " + segmento)
        with open(_cache_file, "r", encoding="utf-8") as _f:
            return _f.read()

    QUERIES_DESIGN_NICHO = {
        "academia": "academia independente site design premium UI UX moderno brasil",
        "crossfit": "crossfit box site design premium dark energetico UI UX",
        "gym": "gym fitness studio site design premium moderno UI UX brasil",
        "fitness": "personal trainer studio fitness site design premium UI UX",
        "musculacao": "musculacao studio site design premium dark energetico UI UX",
        "barbearia": "barbearia premium site design moderno masculino UI UX brasil",
        "salao": "salao de beleza premium site design elegante UI UX brasil",
        "clinica": "clinica medica site design premium clean profissional UI UX",
        "odontologica": "clinica odontologica site design premium clean UI UX brasil",
        "dentista": "dentista consultorio site design premium moderno UI UX",
        "estetica": "clinica estetica site design premium luxuoso UI UX brasil",
        "restaurante": "restaurante local site design premium gastronomia UI UX brasil",
        "lanchonete": "lanchonete artesanal site design premium moderno UI UX",
        "pizzaria": "pizzaria artesanal site design premium gastronomia UI UX brasil",
        "padaria": "padaria artesanal site design premium aconchegante UI UX",
        "confeitaria": "confeitaria artesanal site design premium elegante UI UX",
        "cafe": "cafeteria independente site design premium aconchegante UI UX",
        "advocacia": "escritorio advocacia site design premium sober UI UX brasil",
        "imobiliaria": "imobiliaria boutique site design premium moderno UI UX",
        "escola": "escola curso site design premium moderno educacao UI UX",
        "farmacia": "farmacia manipulacao site design premium clean UI UX brasil",
        "pet": "petshop veterinaria site design premium moderno UI UX brasil",
        "auto": "oficina mecanica site design premium moderno UI UX brasil",
        "nutricionista": "nutricionista site design premium clean saude UI UX brasil",
        "psicologia": "psicologo clinica site design premium acolhedor UI UX brasil",
        "arquitetura": "escritorio arquitetura site design premium portfolio UI UX",
        "fotografia": "fotografo site design premium portfolio visual UI UX brasil",
    }
    seg_lower = segmento.lower()
    query = None
    for key, q in QUERIES_DESIGN_NICHO.items():
        if key in seg_lower:
            query = q
            break
    if not query:
        query = segmento + " site design premium UI UX moderno brasil"
    if cidade:
        query = query + " " + cidade
    print("[Jina AI] Query de design: " + query)

    sites_ref = []
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
        "outback",
        "giraffas",
        "subway",
        "burger",
        "sorridents",
        "odontoprev",
        "drogasil",
        "drogaraia",
        "cobasi",
        "petz",
        "petlove",
        "kumon",
        "wizard",
        "ccaa",
        "quintoandar",
        "vivareal",
        "zapimoveis",
        "localiza",
        "movida",
        "unidas",
        "wix.com",
        "wordpress.com",
        "blogspot",
        "squarespace",
        "webflow.io",
        "maps",
        "wikipedia",
        "amazon",
        "mercadolivre",
        "ifood",
    ]
    try:
        search_url = "https://r.jina.ai/https://www.google.com/search?q=" + quote(query)
        headers_search = {"X-Return-Format": "markdown", "X-Timeout": "15"}
        if jina_key := os.getenv("JINA_API_KEY"):
            headers_search["Authorization"] = f"Bearer {jina_key}"
        response = requests.get(search_url, headers=headers_search, timeout=20)
        if response.status_code == 200:
            for line in response.text.split(chr(10)):
                if "http" in line:
                    url_match = re.search(r"https?://[^\s\)\"\x27]+", line)
                    if url_match:
                        url = url_match.group(0).rstrip(".,)")
                        url_lower = url.lower()
                        if not any(exc in url_lower for exc in EXCLUIR):
                            if url not in sites_ref and len(url) > 15:
                                sites_ref.append(url)
                                if len(sites_ref) >= 3:
                                    break
    except Exception as e:
        print("[Jina AI] Erro busca Google: " + str(e))

    if not sites_ref:
        return (
            "Jina AI: Sem referencias. Usar padroes premium do segmento "
            + segmento
            + "."
        )

    print(
        "[Jina AI] Analisando " + str(len(sites_ref)) + " referencias para " + segmento
    )

    insights = []
    headers_site = {"X-Return-Format": "markdown", "X-Timeout": "15"}
    if jina_key := os.getenv("JINA_API_KEY"):
        headers_site["Authorization"] = f"Bearer {jina_key}"

    for i, site_url in enumerate(sites_ref, 1):
        try:
            print("[Jina AI] Referencia " + str(i) + ": " + site_url)
            resp = requests.get(
                "https://r.jina.ai/" + site_url, headers=headers_site, timeout=15
            )
            if resp.status_code == 200:
                content = resp.text[:3000]
                insights.append(
                    "**Referencia "
                    + str(i)
                    + " ("
                    + site_url
                    + "):**"
                    + chr(10)
                    + content
                    + chr(10)
                )
                print("[Jina AI] OK: " + str(len(content)) + " chars")
        except Exception as e:
            print("[Jina AI] Erro " + site_url + ": " + str(e))

    if not insights:
        return "Jina AI: Sem referencias. Usar padroes premium do segmento."

    header = (
        "INTELIGENCIA DE MERCADO - NICHO: "
        + segmento.upper()
        + " | CIDADE: "
        + (cidade or "Brasil").upper()
        + chr(10)
        + chr(10)
        + "## 1. CONCORRENTES PRINCIPAIS"
        + chr(10)
        + "## 2. PALAVRAS-CHAVE"
        + chr(10)
        + "## 3. VOLUME E TENDENCIA"
        + chr(10)
        + "## 4. COPY E CONVERSAO"
        + chr(10)
        + "## 5. DESIGN E VIBE VISUAL"
        + chr(10)
        + chr(10)
    )

    result = header + chr(10).join(insights)

    try:
        from llm_direct import call_claude as _call_claude

        _faq_prompt = (
            "Analise o conteudo abaixo de sites do nicho '"
            + segmento
            + "' e extraia:\n"
            "1. FAQ_QUESTIONS: lista de 6 perguntas frequentes reais (JSON array)\n"
            "2. SEO_KEYWORDS: lista de 10 termos de busca reais (JSON array)\n"
            "3. VALUE_PROPS: lista de 4 diferenciais que convertem (JSON array)\n"
            'Retorne APENAS JSON valido: {"faq_questions": [...], "seo_keywords": [...], "value_props": [...]}\n\n'
            + chr(10).join(insights)[:4000]
        )
        _faq_resp = _call_claude(
            system=(
                "You extract structured data from web content. Return ONLY valid JSON.\n"
                "All user-facing copy MUST be in Brazilian Portuguese (pt-BR)."
            ),
            user=_faq_prompt,
            model="sonnet",
            max_tokens=1000,
            temperature=0.1,
        )
        _faq_data = json.loads(_faq_resp.strip())
        result += chr(10) + chr(10) + "=== DADOS ESTRUTURADOS PARA SEO ===" + chr(10)
        result += (
            "FAQ_QUESTIONS: "
            + json.dumps(_faq_data.get("faq_questions", []), ensure_ascii=False)
            + chr(10)
        )
        result += (
            "SEO_KEYWORDS: "
            + json.dumps(_faq_data.get("seo_keywords", []), ensure_ascii=False)
            + chr(10)
        )
        result += (
            "VALUE_PROPS: "
            + json.dumps(_faq_data.get("value_props", []), ensure_ascii=False)
            + chr(10)
        )
        print(
            "[Jina AI] FAQ/keywords extraidos: "
            + str(len(_faq_data.get("faq_questions", [])))
            + " FAQs, "
            + str(len(_faq_data.get("seo_keywords", [])))
            + " keywords"
        )
    except Exception as _fe:
        print("[Jina AI] Aviso: extracao FAQ falhou: " + str(_fe))

    print("[Jina AI] Analise concluida: " + str(len(result)) + " chars")
    try:
        with open(_cache_file, "w", encoding="utf-8") as _f:
            _f.write(result)
        print("[Jina AI] Cache salvo: " + _cache_file)
    except Exception as _ce:
        print("[Jina AI] Aviso: nao foi possivel salvar cache: " + str(_ce))
    return result
