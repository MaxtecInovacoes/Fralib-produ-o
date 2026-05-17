"""
Google Local Business Scraper - Parseia resultados do Google Search

Interface compatível com agente1_hunter_v2.py:
  - buscar(query, cidade, limite) -> List[Dict]
  - buscar_negocio(nome, cidade)  -> Dict

Campos: nome, categoria, telefone, rating, total_avaliacoes,
  reviews, fotos, website, endereco, logo,
  horarios, maps_url, atributos, servicos, faixa_preco
"""
from playwright.async_api import async_playwright
import asyncio
import re
import random
from typing import List, Dict, Optional

class GoogleLocalScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless

    async def _human_delay(self, min_ms=800, max_ms=2500):
        await asyncio.sleep(random.uniform(min_ms/1000, max_ms/1000))

    async def buscar(self, query: str, cidade: str, limite: int = 10) -> List[Dict]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="pt-BR",
                timezone_id="America/Sao_Paulo",
                extra_http_headers={"Accept-Language": "pt-BR,pt;q=0.9"}
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
            )
            page = await context.new_page()

            try:
                maps_query = f"{query} {cidade}"
                maps_url = f"https://www.google.com/maps/search/{maps_query.replace(' ', '+')}?hl=pt-BR"
                print(f"[Scraper] Abrindo Maps: {maps_query}")
                await page.goto(maps_url, timeout=30000)
                await self._human_delay(3000, 5000)

                estabelecimentos_maps = await self._capturar_painel_maps(page, limite)

                if estabelecimentos_maps:
                    import asyncio as _asyncio
                    _sem = _asyncio.Semaphore(4)  # max 4 tabs simultâneas

                    async def _buscar_com_sem(est):
                        async with _sem:
                            try:
                                detalhes = await self._buscar_detalhes(context, est["nome"], cidade)
                                if detalhes:
                                    est["logo"] = detalhes.get("logo", "")
                                    est["fotos"] = detalhes.get("fotos", [])
                                    est["depoimentos"] = detalhes.get("depoimentos", [])
                                    est["horarios"] = detalhes.get("horarios", [])
                                    est["maps_url"] = detalhes.get("maps_url", "")
                                    est["atributos"] = detalhes.get("atributos", [])
                                    est["servicos"] = detalhes.get("servicos", [])
                                    est["faixa_preco"] = detalhes.get("faixa_preco", "")
                                    if detalhes.get("website"):
                                        est["website"] = detalhes["website"]
                                    if detalhes.get("telefone"):
                                        est["telefone"] = detalhes["telefone"]
                            except Exception as e_det:
                                print(f"[Scraper] detalhe {est['nome']}: {e_det}")

                    await _asyncio.gather(*[_buscar_com_sem(est) for est in estabelecimentos_maps])
                    print(f"\n[Scraper] Total: {len(estabelecimentos_maps)} estabelecimentos capturados")
                    await browser.close()
                    return estabelecimentos_maps

                # Fallback: Google Search texto
                await page.goto("https://www.google.com.br", timeout=30000)
                await self._human_delay(1500, 3000)
                try:
                    btn = await page.query_selector("button[id='L2AGLb']")
                    if btn:
                        await btn.click()
                        await self._human_delay(500, 1000)
                except:
                    pass

                search_query = f"{query} {cidade}"
                search_box = await page.query_selector("textarea[name='q'], input[name='q']")
                if search_box:
                    await search_box.click()
                    await self._human_delay(300, 600)
                    for char in search_query:
                        await search_box.type(char, delay=random.randint(40, 120))
                    await self._human_delay(400, 800)
                    await page.keyboard.press("Enter")
                else:
                    url = f"https://www.google.com.br/search?q={search_query.replace(' ', '+')}&hl=pt-BR"
                    await page.goto(url, timeout=30000)

                await self._human_delay(3000, 5000)
                texto = await page.inner_text("body")
                estabelecimentos = self._parsear_resultados(texto, limite)

                import asyncio as _asyncio2
                _sem2 = _asyncio2.Semaphore(4)

                async def _buscar_com_sem2(est):
                    async with _sem2:
                        try:
                            detalhes = await self._buscar_detalhes(context, est["nome"], cidade)
                            if detalhes:
                                est["logo"] = detalhes.get("logo", "")
                                est["fotos"] = detalhes.get("fotos", [])
                                est["depoimentos"] = detalhes.get("depoimentos", [])
                                est["horarios"] = detalhes.get("horarios", [])
                                est["maps_url"] = detalhes.get("maps_url", "")
                                est["atributos"] = detalhes.get("atributos", [])
                                est["servicos"] = detalhes.get("servicos", [])
                                est["faixa_preco"] = detalhes.get("faixa_preco", "")
                        except:
                            pass

                await _asyncio2.gather(*[_buscar_com_sem2(est) for est in estabelecimentos])

                print(f"\n[Scraper] Total: {len(estabelecimentos)} estabelecimentos capturados")
                await browser.close()
                return estabelecimentos

            except Exception as e:
                print(f"[Scraper] ERRO: {e}")
                await browser.close()
                return []

    async def _capturar_painel_maps(self, page, limite: int) -> List[Dict]:
        """Captura resultados do painel lateral do Google Maps com scroll."""
        estabelecimentos = []
        try:
            await page.wait_for_selector(
                "div[role='feed'], div.Nv2PK, a[href*='/maps/place/']",
                timeout=10000
            )
            await self._human_delay(1000, 2000)

            painel = await page.query_selector("div[role='feed']")
            if painel:
                rodadas = max(3, (limite // 5) + 2)
                for _ in range(rodadas):
                    await painel.evaluate("el => el.scrollTop += 1200")
                    await self._human_delay(1200, 2000)
                    fim = await page.query_selector("span.HlvSq")
                    if fim:
                        break

            cards = await page.query_selector_all("div.Nv2PK")
            print(f"[Scraper] Painel Maps: {len(cards)} cards encontrados")

            for card in cards[:limite]:
                try:
                    nome_el = await card.query_selector("div.qBF1Pd, span.fontHeadlineSmall")
                    nome = (await nome_el.inner_text()).strip() if nome_el else ""
                    if not nome or len(nome) < 3:
                        continue

                    rating_el = await card.query_selector("span.MW4etd")
                    rating_txt = (await rating_el.inner_text()).strip() if rating_el else "0"
                    try:
                        rating = float(rating_txt.replace(",", "."))
                    except:
                        rating = 0.0

                    # Reviews: extrair do texto completo do card via regex (span.UY7F9 foi removido pelo Google)
                    card_text = await card.inner_text()
                    reviews_match = re.search(r"\(([\d\.]+)\)", card_text)
                    reviews_num = int(re.sub(r"\D", "", reviews_match.group(1))) if reviews_match else 0

                    # Tipo e endereço: extrair do texto do card
                    linhas = [l.strip() for l in card_text.split("\n") if l.strip()]
                    tipo = ""
                    endereco = ""
                    for linha in linhas:
                        if linha in [nome, rating_txt]:
                            continue
                        if re.search(r"(Academia|Sala de fitness|Gym|Fitness|Pilates|Crossfit)", linha, re.I) and not tipo:
                            tipo = linha.split("·")[0].strip()
                        if re.search(r"(Rua|R\.|Av\.|Avenida|Rodovia|Al\.|Alameda)", linha) and not endereco:
                            endereco = re.sub(r"^.*?·\s*", "", linha).strip()

                    est = {
                        "nome": nome, "tipo": tipo or "", "endereco": endereco,
                        "telefone": "", "rating": rating, "reviews": reviews_num,
                        "website": "", "logo": "", "fotos": [], "depoimentos": [],
                        "horarios": [], "maps_url": "", "atributos": [],
                        "servicos": [], "faixa_preco": "",
                    }
                    estabelecimentos.append(est)
                    print(f"[Scraper] Maps OK {nome} | {rating} ({reviews_num} reviews)")
                except Exception as e_card:
                    print(f"[Scraper] card erro: {e_card}")
                    continue

        except Exception as e:
            print(f"[Scraper] Painel Maps erro (usando fallback): {e}")

        return estabelecimentos

    def _parsear_resultados(self, texto: str, limite: int) -> List[Dict]:
        estabelecimentos = []
        linhas = [l.strip() for l in texto.split("\n") if l.strip()]
        i = 0
        while i < len(linhas) and len(estabelecimentos) < limite:
            linha = linhas[i]
            match_rating_tipo = re.match(r"^([0-9],[0-9])\(([0-9]+)\)\s*[·•]\s*(.+)$", linha)
            if match_rating_tipo:
                nome = linhas[i-1] if i > 0 else "Sem nome"
                if any(x in nome.lower() for x in ["resultados", "empresas", "mais empresas", "mapa", "abrir"]):
                    i += 1
                    continue
                rating = float(match_rating_tipo.group(1).replace(",", "."))
                reviews = int(match_rating_tipo.group(2))
                tipo = match_rating_tipo.group(3).strip()
                endereco = ""
                telefone = ""
                depoimento_rapido = ""
                website = ""
                for j in range(i+1, min(i+8, len(linhas))):
                    prox = linhas[j]
                    if any(x in prox for x in ["R. ", "Av. ", "Rua ", "Avenida ", "Rodovia ", "Al. "]):
                        endereco = re.sub(r"^.*?[·•]\s*", "", prox).strip()
                    elif re.search(r"\(\d{2}\)\s*\d{4,5}", prox):
                        telefone = re.search(r"\(\d{2}\)\s*[\d\s-]+", prox).group(0).strip()
                    elif prox.startswith('"') and prox.endswith('"') and len(prox) > 5:
                        depoimento_rapido = prox.strip('"')
                    elif prox.lower() in ["site", "website"]:
                        website = "disponivel"
                    elif re.match(r"^[0-9],[0-9]\([0-9]+\)", prox):
                        break
                est = {
                    "nome": nome, "tipo": tipo, "endereco": endereco,
                    "telefone": telefone, "rating": rating, "reviews": reviews,
                    "website": website, "logo": "", "fotos": [], "depoimentos": [],
                    "horarios": [], "maps_url": "", "atributos": [],
                    "servicos": [], "faixa_preco": "",
                }
                if depoimento_rapido:
                    est["depoimentos"] = [{"autor": "Cliente", "rating": 5, "texto": depoimento_rapido, "data": ""}]
                estabelecimentos.append(est)
                print(f"[Scraper] OK {nome} | {rating} ({reviews} reviews) | {telefone}")
            i += 1
        return estabelecimentos

    async def _extrair_reviews_de_blocos(self, page) -> List[Dict]:
        """Extrai reviews dos blocos na aba de reviews (camada 1)."""
        depoimentos = []
        _textos_vistos = set()  # dedup por texto
        review_blocks = await page.query_selector_all(
            "div[data-review-id], div.jftiEf"
        )
        if not review_blocks:
            review_blocks = await page.query_selector_all("div.GHT2ce, div[class*='review']")
        for block in review_blocks[:25]:
            try:
                # Autor: pegar apenas o nome, sem metadata
                autor = "Cliente"
                autor_el = await block.query_selector(
                    "div.d4r55, span.X43Kjb, div.WNxzHc a, button.WEBjve div"
                )
                if autor_el:
                    _autor_raw = (await autor_el.inner_text()).strip()
                    # Limpar metadata do autor (ex: "Juliana Ferrari\n7 avaliações · 13 fotos")
                    _autor_lines = _autor_raw.split("\n")
                    autor = _autor_lines[0].strip()
                    # Remover sufixos como "7 avaliações" ou "Local Guide"
                    if "avalia" in autor.lower() or "foto" in autor.lower():
                        autor = "Cliente"
                    elif len(autor) > 40:
                        autor = autor[:40]

                # Texto do review
                texto_el = await block.query_selector(
                    "span.wiI7pd, div.MyEned span, span[data-expandable-section]"
                )
                texto = (await texto_el.inner_text()).strip() if texto_el else ""
                if not texto:
                    # Fallback: buscar span com texto longo
                    all_spans = await block.query_selector_all("span")
                    for sp in all_spans:
                        t = (await sp.inner_text()).strip()
                        if len(t) > 20 and not re.match(r"^[0-9,.\s]+$", t) and "avalia" not in t.lower():
                            texto = t
                            break

                # Limpar texto: remover metadata misturada
                if texto:
                    # Cortar em "Gostei", "Útil", "Compartilhar" que são botões
                    for _corte in ["\nGostei", "\nÚtil", "\nCompartilhar", "\n(Traduzido"]:
                        if _corte in texto:
                            texto = texto[:texto.index(_corte)]
                    texto = texto.strip()

                # Rating
                rating_val = 5
                rating_el = await block.query_selector("[aria-label*='estrela'], [aria-label*='star'], span[role='img']")
                if rating_el:
                    lbl = await rating_el.get_attribute("aria-label") or ""
                    m = re.search(r"([0-9])", lbl)
                    if m:
                        rating_val = int(m.group(1))

                # Data
                data_el = await block.query_selector("span.rsqaWe, span[class*='dehysf']")
                data_str = (await data_el.inner_text()).strip() if data_el else ""

                # Validar e dedup
                if texto and len(texto) > 10 and rating_val >= 4:
                    _texto_key = texto[:50].lower()
                    if _texto_key not in _textos_vistos:
                        _textos_vistos.add(_texto_key)
                        depoimentos.append({"autor": autor, "rating": rating_val, "texto": texto, "data": data_str})
                        if len(depoimentos) >= 8:
                            break
            except:
                continue
        return depoimentos

    async def _extrair_reviews_de_blocos_raw(self, review_blocks) -> List[Dict]:
        """Extrai reviews de blocos já selecionados (camada 2 - destaque)."""
        depoimentos = []
        for block in review_blocks[:15]:
            try:
                autor_el = await block.query_selector(
                    "div.d4r55, span.X43Kjb, div.WNxzHc, span.SubCsc, "
                    "a[data-review-id] div, button div[class]"
                )
                autor = (await autor_el.inner_text()).strip() if autor_el else "Cliente"
                texto_el = await block.query_selector(
                    "span.wiI7pd, div.MyEned span, span[data-expandable-section], "
                    "div.Jtu6Td span, span.review-full-text"
                )
                texto = ""
                if texto_el:
                    texto = (await texto_el.inner_text()).strip()
                if not texto:
                    all_spans = await block.query_selector_all("span")
                    for sp in all_spans:
                        t = (await sp.inner_text()).strip()
                        if len(t) > 15 and not re.match(r"^[0-9,.\s]+$", t):
                            texto = t
                            break
                rating_val = 5
                rating_el = await block.query_selector("[aria-label*='estrela'], [aria-label*='star'], span[role='img']")
                if rating_el:
                    lbl = await rating_el.get_attribute("aria-label") or ""
                    m = re.search(r"([0-9])", lbl)
                    if m:
                        rating_val = int(m.group(1))
                if texto and len(texto) > 3 and rating_val >= 4:
                    if not any(d["texto"] == texto for d in depoimentos):
                        depoimentos.append({"autor": autor, "rating": rating_val, "texto": texto, "data": ""})
                        if len(depoimentos) >= 10:
                            break
            except:
                continue
        return depoimentos

    async def _buscar_detalhes(self, context, nome: str, cidade: str) -> Optional[Dict]:
        """Busca detalhes no Google Maps: fotos, reviews, horarios, atributos, servicos, website."""
        detail_page = None
        try:
            detail_page = await context.new_page()
            search = f"{nome} {cidade}"
            url = f"https://www.google.com/maps/search/{search.replace(' ', '+')}?hl=pt-BR"
            await detail_page.goto(url, timeout=20000)
            await asyncio.sleep(3)

            maps_url_final = detail_page.url

            # Se Maps redirecionou direto para a página do negócio, já está no lugar certo
            # Se ficou na lista de resultados, clicar no primeiro link
            if "/maps/place/" not in detail_page.url:
                primeiro = await detail_page.query_selector("a[href*='/maps/place/']")
                if primeiro:
                    href = await primeiro.get_attribute("href")
                    await detail_page.goto(href, timeout=20000)
                    await asyncio.sleep(3)
                    maps_url_final = detail_page.url

            page = detail_page

            # Aguardar carregamento completo da pagina de detalhes
            try:
                await page.wait_for_selector("img[src*='googleusercontent']", timeout=8000)
                await asyncio.sleep(1.5)
            except:
                await asyncio.sleep(2)

            # Fotos — DESATIVADO: usamos Unsplash, não fotos do Google Maps
            logo = ""
            fotos = []

            # Website real
            website_real = ""
            try:
                site_el = await page.query_selector("a[data-item-id='authority']")
                if site_el:
                    website_real = await site_el.get_attribute("href") or ""
                    if website_real and "google.com" in website_real:
                        website_real = ""
            except:
                pass

            # Telefone real
            telefone_real = ""
            try:
                tel_el = await page.query_selector("[data-item-id*='phone'], button[aria-label*='Ligar']")
                if tel_el:
                    lbl = await tel_el.get_attribute("aria-label") or await tel_el.inner_text() or ""
                    m = re.search(r"[\(\d][\d\s\(\)\-]+", lbl)
                    if m:
                        telefone_real = m.group(0).strip()
            except:
                pass

            # Horarios
            horarios = []
            try:
                # Tentar clicar no botão de horários (vários seletores)
                btn_horarios = None
                for sel_h in [
                    "div[aria-label*='orário']",
                    "div[aria-label*='orario']",
                    "button[aria-label*='orário']",
                    "button[aria-label*='orario']",
                    "div[aria-label*='ours']",
                    "button[data-item-id='oh']",
                    "[data-hide-tooltip-on-mouse-move] img[src*='schedule']",
                    "div[class*='OqCZI'] span",
                ]:
                    btn_horarios = await page.query_selector(sel_h)
                    if btn_horarios:
                        break
                if btn_horarios:
                    try:
                        await btn_horarios.click(force=True, timeout=3000)
                        await asyncio.sleep(1.5)
                    except:
                        pass
                # Extrair tabela de horários
                horario_els = await page.query_selector_all("table.eK4R0e tr, table.WgFkxc tr, table[class*='fontBody'] tr")
                for el in horario_els[:14]:
                    txt = (await el.inner_text()).strip()
                    if txt and len(txt) > 3:
                        # Limpar: remover unicode Private Use Area e adicionar espaco entre dia e hora
                        txt = re.sub(r'[-￿]', '', txt)
                        txt = re.sub(r'([a-záéíóúãõç])(\d)', r'\1 \2', txt)  # "sábado10:00" → "sábado 10:00"
                        txt = txt.strip()
                        if txt:
                            horarios.append(txt)
                # Fallback: div com horários em texto
                if not horarios:
                    for sel_div in ["div[class*='t39EBf']", "div[class*='OqCZI']", "div[aria-label*='orário']", "div[aria-label*='orario']"]:
                        horario_div = await page.query_selector(sel_div)
                        if horario_div:
                            txt = (await horario_div.inner_text()).strip()
                            lines = [l.strip() for l in txt.split("\n") if l.strip() and len(l.strip()) > 3]
                            if lines:
                                horarios = lines[:14]
                                break
                # Fallback 2: aria-label do botão contém horários resumidos
                if not horarios and btn_horarios:
                    lbl = await btn_horarios.get_attribute("aria-label") or ""
                    if lbl and len(lbl) > 10:
                        horarios = [l.strip() for l in lbl.replace(". ", "\n").split("\n") if l.strip() and len(l.strip()) > 3][:14]
            except:
                pass

            # Atributos
            atributos = []
            try:
                attr_els = await page.query_selector_all("div.RcCsl span, li[class*='hpLkke']")
                for el in attr_els[:20]:
                    txt = (await el.inner_text()).strip()
                    if txt and 2 < len(txt) < 60:
                        atributos.append(txt)
                atributos = list(dict.fromkeys(atributos))[:15]
            except:
                pass

            # Servicos
            servicos = []
            try:
                serv_els = await page.query_selector_all("div.qty3Ue span")
                for el in serv_els[:20]:
                    txt = (await el.inner_text()).strip()
                    if txt and 2 < len(txt) < 80:
                        servicos.append(txt)
                servicos = list(dict.fromkeys(servicos))[:15]
            except:
                pass


            # Endereco completo
            endereco_completo = ""
            try:
                addr_el = await page.query_selector("button[data-item-id='address'], [data-item-id='address']")
                if addr_el:
                    addr_label = await addr_el.get_attribute("aria-label") or ""
                    if addr_label:
                        # aria-label formato: "Endereco: Rua X, 123 - Bairro, Cidade - UF"
                        endereco_completo = addr_label.replace("Endereço: ", "").replace("Endereco: ", "").strip()
                    if not endereco_completo:
                        endereco_completo = (await addr_el.inner_text()).strip()
                if not endereco_completo:
                    # Fallback: buscar no texto geral da pagina
                    addr_divs = await page.query_selector_all("div[class*='Io6YTe'], div[class*='rogA2c']")
                    for div in addr_divs[:5]:
                        txt = (await div.inner_text()).strip()
                        if re.search(r"(Rua|R\.|Av\.|Avenida|Rodovia|Al\.|Alameda|Estr\.|Estrada)", txt) and len(txt) > 10:
                            endereco_completo = txt
                            break
            except:
                pass

            # Faixa de preco
            faixa_preco = ""
            try:
                preco_el = await page.query_selector("span[aria-label*='Preco'], span.mgr77e")
                if preco_el:
                    faixa_preco = (await preco_el.get_attribute("aria-label") or await preco_el.inner_text() or "").strip()
            except:
                pass

            # Reviews reais — 3 camadas de fallback
            depoimentos = []

            # Fechar modais/overlays que bloqueiam clicks (Google Maps review prompt)
            try:
                for modal_sel in [
                    "div.goog-reviews-write-widget-modal-bg",
                    "div[class*='modal-bg']",
                    "button[aria-label='Fechar']",
                    "button[aria-label='Close']",
                    "div[class*='VIpgJd']",
                ]:
                    modals = await page.query_selector_all(modal_sel)
                    for modal in modals:
                        await modal.evaluate("el => el.remove()")
                await asyncio.sleep(0.5)
            except:
                pass

            # CAMADA 1: Clicar na aba de reviews e extrair
            try:
                aba_reviews = None
                for sel in [
                    "button[aria-label*='valiac']",
                    "button[aria-label*='valia']",
                    "button[aria-label*='eview']",
                    "button[aria-label*='Review']",
                    "[data-tab-index='1']",
                    "button[jsaction*='review']",
                    "button[jsaction*='pane.rating']",
                    "a[href*='reviews']",
                ]:
                    aba_reviews = await page.query_selector(sel)
                    if aba_reviews:
                        break

                if aba_reviews:
                    # Remover modais novamente antes do click (podem reaparecer)
                    await page.evaluate("document.querySelectorAll('.goog-reviews-write-widget-modal-bg, [class*=VIpgJd]').forEach(e => e.remove())")
                    await aba_reviews.click(force=True, timeout=5000)
                    try:
                        await page.wait_for_selector("div[data-review-id], div.jftiEf, div[jscontroller] span.wiI7pd", timeout=8000)
                    except:
                        pass
                    await asyncio.sleep(2)
                    painel = await page.query_selector("div[aria-label*='valiac'], div[aria-label*='valia'], div[role='main']")
                    if painel:
                        for _ in range(6):
                            await painel.evaluate("el => el.scrollTop += 800")
                            await asyncio.sleep(0.8)
                    botoes_mais = await page.query_selector_all("button[aria-label*='mais'], button[aria-label*='Mais'], button.w8nwRe, button[aria-expanded='false']")
                    for btn in botoes_mais[:10]:
                        try:
                            await btn.click()
                            await asyncio.sleep(0.3)
                        except:
                            pass
                    depoimentos = await self._extrair_reviews_de_blocos(page)
                    if depoimentos:
                        print(f"[Scraper] {nome}: {len(depoimentos)} reviews (camada 1 - aba)")
            except Exception as e_rev:
                print(f"[Scraper] reviews camada 1 erro: {e_rev}")

            # CAMADA 2: Reviews em destaque na visão geral (mesma página, sem clicar aba)
            if not depoimentos:
                try:
                    # Fechar modais/overlays que possam bloquear clicks
                    for modal_sel in [
                        "div.goog-reviews-write-widget-modal-bg",
                        "div[class*='modal-bg']",
                        "button[aria-label='Fechar']",
                        "button[aria-label='Close']",
                    ]:
                        modal = await page.query_selector(modal_sel)
                        if modal:
                            await modal.evaluate("el => el.remove()")
                    await asyncio.sleep(0.5)

                    # Voltar pra visão geral se estávamos na aba de reviews
                    overview_btn = await page.query_selector("[data-tab-index='0'], button[aria-label*='Visão geral'], button[aria-label*='Geral']")
                    if overview_btn:
                        try:
                            await overview_btn.click(force=True, timeout=5000)
                            await asyncio.sleep(1.5)
                        except:
                            pass
                    destaque_sels = [
                        "div.GHT2ce",
                        "div[data-review-id]",
                        "div.jftiEf",
                        "div[jscontroller][class*='review']",
                        "div.WMbnJf",
                        "div[class*='fontBodyMedium'][data-review-id]",
                    ]
                    review_blocks = []
                    for sel in destaque_sels:
                        review_blocks = await page.query_selector_all(sel)
                        if review_blocks:
                            break
                    if review_blocks:
                        depoimentos = await self._extrair_reviews_de_blocos_raw(review_blocks)
                        if depoimentos:
                            print(f"[Scraper] {nome}: {len(depoimentos)} reviews (camada 2 - destaque)")
                except Exception as e_rev2:
                    print(f"[Scraper] reviews camada 2 erro: {e_rev2}")

            # CAMADA 3: Heurística — qualquer bloco com estrelas + texto perto
            if not depoimentos:
                _lixo_patterns = re.compile(
                    r"(^Aberto|^Fechado|^Fecha\b|^Abre\b|^horário|"
                    r"^Sala de fitness$|^Academia$|^Gym$|^Centro de treinamento$|"
                    r"^\d{1,2}:\d{2}|·|^Avalia|estrela|^Enviar|^Escrever|"
                    r"^Rua |^R\. |^Av\.|^Rodovia|^Endere|"
                    r"^Ligar$|^Rotas$|^Salvar$|^Compartilhar$|^Site$|"
                    r"^Mais info|^Sugerir|^Editar|^Adicionar|"
                    r"^\(\d+\)$|^[0-9,.\s]+$)", re.I
                )
                try:
                    all_blocks = await page.query_selector_all("[aria-label*='estrela'], [aria-label*='star'], span[role='img'][aria-label]")
                    for block in all_blocks[:20]:
                        try:
                            lbl = await block.get_attribute("aria-label") or ""
                            m = re.search(r"([0-9])", lbl)
                            rating_val = int(m.group(1)) if m else 5
                            parent = await block.evaluate_handle("el => el.closest('div[class]') || el.parentElement?.parentElement")
                            if not parent:
                                continue
                            parent_text = await parent.evaluate("el => el.innerText || ''")
                            linhas = [l.strip() for l in parent_text.split("\n") if l.strip() and len(l.strip()) > 3]
                            texto_candidatos = [l for l in linhas if len(l) > 15 and not _lixo_patterns.search(l)]
                            if texto_candidatos:
                                texto = texto_candidatos[0][:500]
                                autor_candidatos = [l for l in linhas if 2 < len(l) < 40 and l != texto and not re.search(r"[0-9]{2}", l) and not _lixo_patterns.search(l)]
                                autor = autor_candidatos[0] if autor_candidatos else "Cliente"
                                if not any(d["texto"] == texto for d in depoimentos):
                                    depoimentos.append({"autor": autor, "rating": rating_val, "texto": texto, "data": ""})
                                    if len(depoimentos) >= 10:
                                        break
                        except:
                            continue
                    if depoimentos:
                        print(f"[Scraper] {nome}: {len(depoimentos)} reviews (camada 3 - heuristica)")
                except Exception as e_rev3:
                    print(f"[Scraper] reviews camada 3 erro: {e_rev3}")

            if not depoimentos:
                print(f"[Scraper] {nome}: 0 reviews em todas as 3 camadas")

            # Gerar embed Google Maps por coordenadas ou nome+cidade
            google_maps_embed = ""
            try:
                import urllib.parse as _up
                _q = _up.quote(f"{nome}, {cidade}")
                coord_match = re.search(r'@(-?[0-9]+\.[0-9]+),(-?[0-9]+\.[0-9]+)', maps_url_final)
                if coord_match:
                    lat, lng = coord_match.group(1), coord_match.group(2)
                    google_maps_embed = (f'<iframe width="100%" height="450" style="border:0;" '
                        f'loading="lazy" allowfullscreen="" referrerpolicy="no-referrer-when-downgrade" '
                        f'src="https://maps.google.com/maps?q={lat},{lng}&output=embed&z=16"></iframe>')
                else:
                    google_maps_embed = (f'<iframe width="100%" height="450" style="border:0;" '
                        f'loading="lazy" allowfullscreen="" referrerpolicy="no-referrer-when-downgrade" '
                        f'src="https://maps.google.com/maps?q={_q}&output=embed&z=16"></iframe>')
                print(f"[Scraper] maps_embed gerado: {len(google_maps_embed)} chars")
            except Exception as e_maps:
                print(f"[Scraper] maps_embed erro: {e_maps}")

            # Separar logo (primeira imagem) das fotos do estabelecimento
            logo_url = fotos[0] if fotos else ""
            fotos_sem_logo = fotos[1:] if len(fotos) > 1 else fotos

            print(f"[Scraper] {nome}: {len(fotos)} fotos, {len(depoimentos)} reviews, {len(horarios)} horarios, {len(atributos)} atributos, endereco={endereco_completo[:50]}")
            return {
                "logo": logo_url, "fotos": fotos_sem_logo, "depoimentos": depoimentos,
                "horarios": horarios, "maps_url": maps_url_final,
                "website": website_real, "telefone": telefone_real,
                "atributos": atributos, "servicos": servicos, "faixa_preco": faixa_preco,
                "google_maps_embed": google_maps_embed,
                "endereco_completo": endereco_completo,
            }

        except Exception as e:
            print(f"[Scraper] detalhe erro: {e}")
            return None
        finally:
            if detail_page:
                try:
                    await detail_page.close()
                except:
                    pass

    async def buscar_negocio(self, nome: str, cidade: str) -> Optional[Dict]:
        resultados = await self.buscar(nome, cidade, limite=1)
        if resultados:
            r = resultados[0]
            return {
                "nome": r.get("nome", nome), "categoria": r.get("tipo", ""),
                "telefone": r.get("telefone", ""), "rating": r.get("rating", 0),
                "total_avaliacoes": r.get("reviews", 0), "reviews": r.get("depoimentos", []),
                "fotos": r.get("fotos", []), "logo": r.get("logo", ""),
                "website": r.get("website", ""), "endereco": r.get("endereco_completo", "") or r.get("endereco", ""),
                "horarios": r.get("horarios", []), "maps_url": r.get("maps_url", ""),
                "atributos": r.get("atributos", []), "servicos": r.get("servicos", []),
                "faixa_preco": r.get("faixa_preco", ""),
            }
        return None

    async def buscar_detalhe_unico(self, nome: str, cidade: str):
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, args=["--no-sandbox"])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1366, "height": 768}, locale="pt-BR", timezone_id="America/Sao_Paulo",
            )
            try:
                return await self._buscar_detalhes(context, nome, cidade)
            finally:
                await browser.close()

    async def buscar_somente_cards(self, query: str, cidade: str, limite: int = 10):
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, args=["--no-sandbox"])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1366, "height": 768}, locale="pt-BR", timezone_id="America/Sao_Paulo",
                extra_http_headers={"Accept-Language": "pt-BR,pt;q=0.9"},
            )
            page = await context.new_page()
            try:
                url = f"https://www.google.com/maps/search/{query.replace(chr(32), chr(43))}+{cidade.replace(chr(32), chr(43))}?hl=pt-BR"
                await page.goto(url, timeout=30000)
                await self._human_delay(3000, 5000)
                return await self._capturar_painel_maps(page, limite)
            finally:
                await browser.close()

