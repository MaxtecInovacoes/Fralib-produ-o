"""
Módulo de Inteligência — Espionagem de Concorrência via Playwright

Busca top 3 concorrentes no Google, extrai dados visuais/técnicos,
People Also Ask, e padrões de mercado. 100% grátis (sem API).

Roda em paralelo com Jina e Maps no pipeline.
"""
import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright


# Domínios a ignorar nos resultados do Google
_IGNORAR_DOMINIOS = frozenset([
    "yelp.com", "tripadvisor.com", "ifood.com.br", "rappi.com.br",
    "google.com/maps", "facebook.com", "instagram.com", "youtube.com",
    "linkedin.com", "twitter.com", "tiktok.com", "reclameaqui.com",
    "guiamais.com", "apontador.com", "kekanto.com", "foursquare.com",
    "yellowpages", "paginas-amarelas", "wikipedia.org",
])


async def espionar_concorrencia(nicho: str, cidade: str, max_concorrentes: int = 3) -> dict:
    """
    Usa Playwright pra buscar e analisar concorrentes no Google.
    Retorna dados visuais, padrões de mercado e People Also Ask.

    Args:
        nicho: segmento do negócio (ex: "hamburgueria")
        cidade: cidade alvo (ex: "Gramado")
        max_concorrentes: quantos sites analisar (default 3)

    Returns:
        dict com concorrentes, padroes_mercado, people_also_ask
    """
    resultados = []
    paa = []
    query = f"{nicho} {cidade}"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="pt-BR",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # 1. Busca no Google
            try:
                await page.goto(
                    f"https://www.google.com/search?q={query}&hl=pt-BR&gl=br",
                    timeout=15000, wait_until="domcontentloaded"
                )
                await asyncio.sleep(2)

                # Aceitar cookies se aparecer
                try:
                    accept_btn = await page.query_selector("button:has-text('Aceitar'), button:has-text('Accept')")
                    if accept_btn:
                        await accept_btn.click()
                        await asyncio.sleep(1)
                except Exception:
                    pass

                # Extrair links orgânicos
                links = await page.evaluate("""
                    () => {
                        const ignorar = %s;
                        return [...document.querySelectorAll('div.g a[href^="http"], div[data-sokoban-container] a[href^="http"]')]
                            .map(a => a.href)
                            .filter(url => !ignorar.some(d => url.includes(d)))
                            .filter(url => !url.includes('google.com'))
                            .filter((url, i, arr) => arr.indexOf(url) === i)
                            .slice(0, 8);
                    }
                """ % str(list(_IGNORAR_DOMINIOS)))

                # Extrair People Also Ask
                paa = await page.evaluate("""
                    () => {
                        const perguntas = [];
                        document.querySelectorAll('[data-q], [aria-expanded] span').forEach(el => {
                            const q = el.getAttribute('data-q') || el.textContent;
                            if (q && q.includes('?') && q.length > 10 && q.length < 150) {
                                perguntas.push(q.trim());
                            }
                        });
                        // Fallback: divs com role=heading dentro de "As pessoas também perguntam"
                        if (perguntas.length === 0) {
                            document.querySelectorAll('[role="heading"][aria-level="3"]').forEach(el => {
                                const t = el.textContent.trim();
                                if (t.includes('?')) perguntas.push(t);
                            });
                        }
                        return [...new Set(perguntas)].slice(0, 8);
                    }
                """)

                print(f"[Inteligência] Google: {len(links)} links, {len(paa)} PAA")

            except Exception as e:
                print(f"[Inteligência] Erro na busca Google: {e}")
                links = []

            # 2. Analisar cada concorrente
            for url in links[:max_concorrentes]:
                dados = await _analisar_site(page, url)
                if dados:
                    resultados.append(dados)

            await browser.close()

    except Exception as e:
        print(f"[Inteligência] Erro geral Playwright: {e}")

    # 3. Identificar padrões de mercado
    padroes = _identificar_padroes(resultados)

    return {
        "concorrentes": resultados,
        "padroes_mercado": padroes,
        "people_also_ask": paa,
        "query": query,
        "total_analisados": len(resultados),
    }


async def _analisar_site(page, url: str) -> Optional[dict]:
    """Abre um site concorrente e extrai dados visuais/técnicos."""
    try:
        await page.goto(url, timeout=12000, wait_until="domcontentloaded")
        await asyncio.sleep(1.5)

        dados = await page.evaluate("""
            () => {
                try {
                    const cs = getComputedStyle(document.body);
                    const h1 = document.querySelector('h1');
                    const h1cs = h1 ? getComputedStyle(h1) : null;

                    // Detectar CTA principal
                    const ctaSels = [
                        'a[href*="whatsapp"]', 'a[href*="wa.me"]',
                        'a.btn', 'button.btn', '.cta', '[class*="cta"]',
                        'a[class*="button"]', 'button[class*="primary"]',
                        'header a[href]', 'nav a[href]:last-child'
                    ];
                    let ctaText = '';
                    for (const sel of ctaSels) {
                        const el = document.querySelector(sel);
                        if (el && el.textContent.trim().length > 2 && el.textContent.trim().length < 40) {
                            ctaText = el.textContent.trim();
                            break;
                        }
                    }

                    // Detectar tema (dark/light)
                    const bg = cs.backgroundColor;
                    const rgb = bg.match(/\\d+/g) || [255, 255, 255];
                    const luminance = (parseInt(rgb[0]) * 299 + parseInt(rgb[1]) * 587 + parseInt(rgb[2]) * 114) / 1000;
                    const tema = luminance < 128 ? 'dark' : 'light';

                    // Detectar seções visíveis
                    const secoes = [];
                    document.querySelectorAll('section, [id]').forEach(el => {
                        const id = el.id || el.className.split(' ')[0] || '';
                        if (id && id.length < 30) secoes.push(id.toLowerCase());
                    });

                    // Meta description
                    const metaDesc = document.querySelector('meta[name="description"]');

                    return {
                        title: document.title || '',
                        meta_desc: metaDesc ? metaDesc.content : '',
                        tema: tema,
                        cores: {
                            bg: bg,
                            text: cs.color,
                            accent: '' // detectado abaixo
                        },
                        fonte_h1: h1cs ? h1cs.fontFamily.split(',')[0].replace(/["']/g, '').trim() : '',
                        fonte_body: cs.fontFamily.split(',')[0].replace(/["']/g, '').trim(),
                        cta_principal: ctaText,
                        secoes_visiveis: [...new Set(secoes)].slice(0, 10),
                        h1_text: h1 ? h1.textContent.trim().slice(0, 100) : ''
                    };
                } catch(e) {
                    return null;
                }
            }
        """)

        if not dados:
            return None

        # Detectar cor accent (botões/links coloridos)
        accent = await page.evaluate("""
            () => {
                const btns = document.querySelectorAll('a.btn, button, [class*="cta"], [class*="primary"]');
                for (const btn of btns) {
                    const bg = getComputedStyle(btn).backgroundColor;
                    const rgb = bg.match(/\\d+/g);
                    if (rgb && !(rgb[0] === rgb[1] && rgb[1] === rgb[2])) {
                        return bg; // Cor não-cinza = provavelmente accent
                    }
                }
                // Fallback: cor dos links
                const link = document.querySelector('a[href]:not([class])');
                if (link) return getComputedStyle(link).color;
                return '';
            }
        """)
        dados["cores"]["accent"] = accent or ""
        dados["url"] = url
        dados["nome"] = (dados.get("title", "").split("—")[0].split("-")[0].split("|")[0].strip())[:60]

        print(f"[Inteligência] Analisado: {dados['nome']} ({dados['tema']})")
        return dados

    except Exception as e:
        print(f"[Inteligência] Erro ao analisar {url}: {e}")
        return None


def _identificar_padroes(concorrentes: list) -> dict:
    """Identifica padrões dominantes entre os concorrentes analisados."""
    if not concorrentes:
        return {"tema_dominante": "dark", "total_analisados": 0}

    temas = [c.get("tema", "dark") for c in concorrentes]
    fontes_h1 = [c.get("fonte_h1", "") for c in concorrentes if c.get("fonte_h1")]
    fontes_body = [c.get("fonte_body", "") for c in concorrentes if c.get("fonte_body")]
    ctas = [c.get("cta_principal", "") for c in concorrentes if c.get("cta_principal")]

    tema_dominante = max(set(temas), key=temas.count) if temas else "dark"
    fonte_h1_dom = max(set(fontes_h1), key=fontes_h1.count) if fontes_h1 else ""
    fonte_body_dom = max(set(fontes_body), key=fontes_body.count) if fontes_body else ""

    return {
        "tema_dominante": f"{tema_dominante} ({temas.count(tema_dominante)}/{len(temas)} concorrentes)",
        "fonte_h1_dominante": fonte_h1_dom,
        "fonte_body_dominante": fonte_body_dom,
        "ctas_encontrados": ctas[:5],
        "total_analisados": len(concorrentes),
    }


def extrair_insights_reviews(reviews: list) -> dict:
    """
    Analisa reviews reais e extrai padrões pra alimentar a copy.
    Roda localmente (sem LLM), baseado em frequência de palavras.
    """
    if not reviews:
        return {"elogios": [], "reclamacoes": [], "palavras_frequentes": [],
                "sentimento_geral": "neutro", "total_reviews": 0, "diferencial_detectado": ""}

    elogios = []
    reclamacoes = []
    palavras_freq = {}

    # Stopwords PT-BR básicas
    _stop = frozenset(["para", "como", "mais", "muito", "esse", "essa", "este", "esta",
        "aqui", "onde", "quando", "porque", "porém", "também", "ainda", "depois",
        "antes", "sobre", "entre", "desde", "cada", "outro", "outra", "todos",
        "todas", "mesmo", "mesma", "nosso", "nossa", "vocês", "eles", "elas",
        "dele", "dela", "nele", "nela", "pelo", "pela", "pelos", "pelas",
        "lugar", "vezes", "coisa", "gente", "super", "legal", "bom", "boa"])

    for review in reviews:
        texto = (review.get("texto") or review.get("text") or "").strip()
        if not texto or len(texto) < 10:
            continue
        nota = float(review.get("rating") or review.get("nota") or review.get("stars") or 3)

        if nota >= 4:
            elogios.append(texto[:200])
        elif nota <= 2:
            reclamacoes.append(texto[:200])

        # Conta palavras relevantes (>4 chars, não stopword)
        for palavra in re.findall(r'[a-záàâãéèêíïóôõúüç]+', texto.lower()):
            if len(palavra) > 4 and palavra not in _stop:
                palavras_freq[palavra] = palavras_freq.get(palavra, 0) + 1

    # Top palavras
    top_palavras = sorted(palavras_freq.items(), key=lambda x: x[1], reverse=True)[:15]

    # Detectar diferencial (palavra frequente que não é genérica)
    _genericas = {"atendimento", "comida", "lugar", "ambiente", "preço", "serviço", "qualidade"}
    diferencial = ""
    for palavra, freq in top_palavras:
        if palavra not in _genericas and freq >= 2:
            diferencial = palavra
            break

    sentimento = "positivo" if len(elogios) > len(reclamacoes) * 2 else (
        "misto" if elogios else "negativo")

    return {
        "elogios": elogios[:5],
        "reclamacoes": reclamacoes[:3],
        "palavras_frequentes": [p[0] for p in top_palavras[:10]],
        "sentimento_geral": sentimento,
        "total_reviews": len(reviews),
        "diferencial_detectado": diferencial,
    }


def mapear_atributos_para_servicos(atributos: list, nicho: str = "") -> list:
    """
    Converte atributos reais do Google Maps em serviços confirmados.
    NUNCA inventa serviço que o negócio não tem.
    """
    _MAPA = {
        "dine_in": {"titulo": "Refeição no Local", "icone": "fork-knife"},
        "delivery": {"titulo": "Entrega", "icone": "package"},
        "takeout": {"titulo": "Para Viagem", "icone": "bag"},
        "reservable": {"titulo": "Reservas", "icone": "calendar"},
        "outdoor_seating": {"titulo": "Área Externa", "icone": "sun"},
        "live_music": {"titulo": "Música ao Vivo", "icone": "music-notes"},
        "wheelchair_accessible": {"titulo": "Acessibilidade", "icone": "wheelchair"},
        "wifi": {"titulo": "Wi-Fi Grátis", "icone": "wifi-high"},
        "parking": {"titulo": "Estacionamento", "icone": "car"},
        "accepts_credit_cards": {"titulo": "Cartão de Crédito", "icone": "credit-card"},
        "good_for_kids": {"titulo": "Espaço Kids", "icone": "baby"},
        "good_for_groups": {"titulo": "Grupos", "icone": "users-three"},
        "serves_beer": {"titulo": "Cerveja", "icone": "beer-bottle"},
        "serves_wine": {"titulo": "Vinhos", "icone": "wine"},
        "serves_vegetarian": {"titulo": "Opções Vegetarianas", "icone": "leaf"},
        "serves_breakfast": {"titulo": "Café da Manhã", "icone": "coffee"},
        "serves_lunch": {"titulo": "Almoço", "icone": "fork-knife"},
        "serves_dinner": {"titulo": "Jantar", "icone": "moon"},
        "pet_friendly": {"titulo": "Pet Friendly", "icone": "paw-print"},
        "air_conditioning": {"titulo": "Ar Condicionado", "icone": "thermometer-cold"},
    }

    servicos = []

    if isinstance(atributos, dict):
        for key, val in atributos.items():
            key_lower = key.lower().replace(" ", "_").replace("-", "_")
            if val and key_lower in _MAPA:
                servicos.append({**_MAPA[key_lower], "confirmado": True})
    elif isinstance(atributos, list):
        for attr in atributos:
            attr_lower = (attr if isinstance(attr, str) else "").lower().replace(" ", "_").replace("-", "_")
            # Match parcial
            for key, val in _MAPA.items():
                if key in attr_lower or attr_lower in key:
                    servicos.append({**val, "confirmado": True})
                    break

    return servicos[:8]  # Max 8 serviços


def _extrair_keywords_reais(keyword_research_text: str) -> list:
    """Extrai keywords reais do texto de pesquisa de keywords (Jina + Google Suggest)."""
    if not keyword_research_text:
        return []

    keywords = []
    lines = keyword_research_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Pular títulos, seções e instruções
        if line.startswith('===') or line.startswith('INSTR') or line.isupper() or line.endswith(':'):
            continue
        # Pular linhas de seção (palavras-chave específicas)
        titulos_secao = ['BUSCAS REAIS', 'INTEN', 'CONCORR', 'Atualizado', 'Pesquisando', 'Cache']
        if any(line.startswith(t) for t in titulos_secao):
            continue

        # Stripar bullet "  - " ou "  -" no início
        if line.startswith('  - '):
            kw = line[4:].strip()
        elif line.startswith('  -'):
            kw = line[3:].strip()
        elif line.startswith('- '):
            kw = line[2:].strip()
        else:
            kw = None

        if kw:
            # Validar: 3-100 chars, 2+ palavras, sem caracteres especiais demais
            if 3 <= len(kw) <= 100 and len(kw.split()) >= 2:
                if not any(c in kw for c in ['#', '`', '?', '!', '|', '—', '>>']):
                    keywords.append(kw)

    return list(dict.fromkeys(keywords))  # dedup


def _extrair_keywords_jina(jina_insights: str) -> list:
    """Extrai keywords e insights do jina_insights."""
    if not jina_insights:
        return []

    keywords = []
    # Tentar extrair do bloco de keywords se existir
    lines = jina_insights.split('\n')
    for line in lines:
        line = line.strip()
        if len(line) > 5 and len(line) < 80:
            words = line.split()
            if 2 <= len(words) <= 6:
                # Filtrar linhas que parecem keywords (não são perguntas, não começam com maiúscula isolada)
                if not line.endswith('?') and not line.startswith('#'):
                    keywords.append(line)
    return list(dict.fromkeys(keywords))[:5]  # Máximo 5 do Jina


def gerar_seo_context(nicho: str, cidade: str, nome: str, paa: list = None,
                      rating: float = 0, total_reviews: int = 0,
                      keyword_research: str = "", jina_insights: str = "") -> dict:
    """
    Gera contexto SEO local usando dados REAIS de pesquisa (Jina + Google Suggest).
    Se keyword_research vier vazio, pesquisa agora via pesquisar_keywords_nicho().
    """
    # Se não tiver keyword_research, pesquisar agora
    if not keyword_research:
        try:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'agents'))
            from keyword_research import pesquisar_keywords_nicho
            keyword_research = pesquisar_keywords_nicho(nicho, cidade)
        except Exception as e:
            print(f"[SEO] Erro ao pesquisar keywords: {e}")
            keyword_research = ""

    # Extrair keywords reais do texto de pesquisa
    keywords_reais = _extrair_keywords_reais(keyword_research)

    # Se tiver jina_insights, extrair mais keywords
    if jina_insights:
        keywords_jina = _extrair_keywords_jina(jina_insights)
        for kw in keywords_jina:
            if kw not in keywords_reais:
                keywords_reais.append(kw)

    # Usar keyword primária real ou fallback
    keyword_primaria = keywords_reais[0] if keywords_reais else f"{nicho} {cidade}".lower()

    # Gerar H1 baseado no nome real
    h1_sugerido = f"{nome} — {nicho.title()} em {cidade}"
    if len(h1_sugerido) > 60:
        h1_sugerido = f"{nome} | {nicho.title()} {cidade}"

    # Meta description com dados reais
    meta_desc = f"{nome}: {nicho} em {cidade}."
    if rating:
        meta_desc += f" Nota {rating}/5"
        if total_reviews:
            meta_desc += f" ({total_reviews} avaliações)"
    meta_desc += ". Confira horários e contato."
    if len(meta_desc) > 155:
        meta_desc = meta_desc[:152] + "..."

    return {
        "keyword_primaria": keyword_primaria,
        "keywords_longtail": keywords_reais[:8] if keywords_reais else [
            f"{nicho} {cidade} perto de mim",
            f"melhor {nicho} {cidade}",
            f"{nicho} {cidade} aberto agora",
        ],
        "people_also_ask": paa or [],
        "h1_sugerido": h1_sugerido,
        "meta_desc_sugerida": meta_desc,
        "title_sugerido": f"{nome} — {nicho.title()} em {cidade}"[:60],
        "keyword_research_raw": keyword_research,
    }
