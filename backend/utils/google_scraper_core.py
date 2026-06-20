"""
Google Local Scraper - Core
"""
import asyncio
import os
import random
import re
from typing import Any, Callable, List, Dict, Optional

from playwright.async_api import async_playwright

from backend.utils.google_scraper_helpers import _env_int, _close_quietly, _playwright_launch_args
from backend.utils.google_scraper_parse import _capturar_painel_maps, _parsear_resultados, _extrair_reviews_de_blocos, _extrair_reviews_de_blocos_raw, _buscar_detalhes


class GoogleLocalScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless

    async def _human_delay(self, min_ms=800, max_ms=2500):
        await asyncio.sleep(random.uniform(min_ms/1000, max_ms/1000))

    async def buscar(
        self,
        query: str,
        cidade: str,
        limite: int = 10,
        leads_existentes: set = None,
        candidate_acceptor: Optional[Callable[[List[Dict[str, Any]]], bool]] = None,
        max_duration_secs: Optional[float] = None,
    ) -> List[Dict]:
        _existentes = leads_existentes or set()
        _loop = asyncio.get_running_loop()
        _budget = (
            float(max_duration_secs)
            if max_duration_secs is not None
            else float(_env_int("FRALIB_MAPS_CAPTURE_TIMEOUT_SECS", 135, 30, 180))
        )
        _deadline = _loop.time() + max(10.0, _budget)

        def _remaining_secs() -> float:
            return max(0.0, _deadline - _loop.time())

        def _timeout_ms(default_ms: int, floor_ms: int = 1000) -> int:
            remaining_ms = int(_remaining_secs() * 1000)
            return max(floor_ms, min(default_ms, remaining_ms))

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=_playwright_launch_args(),
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
                if _remaining_secs() <= 5:
                    print("[Scraper] Deadline de captura atingido antes de abrir Maps")
                    await _close_quietly(browser)
                    return []
                await page.goto(
                    maps_url,
                    timeout=_timeout_ms(30000, 5000),
                    wait_until="domcontentloaded",
                )
                await self._human_delay(3000, 5000)

                estabelecimentos_maps = await _capturar_painel_maps(page, limite)

                if estabelecimentos_maps:
                    import asyncio as _asyncio
                    _sem = _asyncio.Semaphore(4)  # max 4 tabs simultâneas

                    # Filtrar duplicatas ANTES de buscar detalhes (economiza tempo)
                    _novos = [e for e in estabelecimentos_maps if e.get("nome", "").lower().strip() not in _existentes]
                    _dupes = len(estabelecimentos_maps) - len(_novos)
                    if _dupes > 0:
                        print(f"[Scraper] {_dupes} duplicatas filtradas antes de buscar detalhes")
                    # Detalhar um pool real: muitos cards têm site válido, telefone fixo
                    # ou dados incompletos e ainda serão descartados pelo Caio.
                    _detail_limit = max(
                        5,
                        min(_env_int("FRALIB_MAPS_DETAIL_LIMIT", 8, 5, 30), 30),
                    )
                    _alvo_detalhes = min(_detail_limit, max(limite, 5))
                    # Mistura relevancia local do Maps com prova publica do painel.
                    # A decisao comercial continua exclusiva do Caio.
                    _por_reviews = sorted(
                        _novos,
                        key=lambda item: int(item.get("reviews") or 0),
                        reverse=True,
                    )
                    _metade_local = (_alvo_detalhes + 1) // 2
                    _para_detalhar = list(_novos[:_metade_local])
                    for _item in _por_reviews:
                        if _item not in _para_detalhar:
                            _para_detalhar.append(_item)
                        if len(_para_detalhar) >= _alvo_detalhes:
                            break

                    async def _buscar_com_sem(est):
                        async with _sem:
                            try:
                                remaining = _remaining_secs()
                                if remaining <= 3:
                                    return
                                detalhes = await self._buscar_detalhes(
                                    context,
                                    est["nome"],
                                    cidade,
                                    fast=bool(candidate_acceptor),
                                )
                                if detalhes:
                                    est["logo"] = detalhes.get("logo", "")
                                    est["fotos"] = detalhes.get("fotos", [])
                                    est["depoimentos"] = detalhes.get("depoimentos", [])
                                    est["horarios"] = detalhes.get("horarios", [])
                                    est["maps_url"] = detalhes.get("maps_url", "")
                                    est["atributos"] = detalhes.get("atributos", [])
                                    est["servicos"] = detalhes.get("servicos", [])
                                    est["faixa_preco"] = detalhes.get("faixa_preco", "")
                                    est["endereco"] = detalhes.get("endereco_completo", "") or est.get("endereco", "")
                                    est["google_maps_embed"] = detalhes.get("google_maps_embed", "")
                                    if detalhes.get("website"):
                                        est["website"] = detalhes["website"]
                                    if detalhes.get("telefone"):
                                        est["telefone"] = detalhes["telefone"]
                            except Exception as e_det:
                                print(f"[Scraper] detalhe {est['nome']}: {e_det}")

                    _detalhados = []
                    _batch_size = max(
                        1,
                        min(int(os.getenv("FRALIB_MAPS_DETAIL_BATCH", "4")), 8),
                    )
                    for _inicio in range(0, len(_para_detalhar), _batch_size):
                        if _remaining_secs() <= 5:
                            print("[Scraper] Deadline de captura atingido; interrompendo detalhes")
                            break
                        _lote = _para_detalhar[_inicio:_inicio + _batch_size]
                        await _asyncio.gather(
                            *[_buscar_com_sem(est) for est in _lote],
                            return_exceptions=True,
                        )
                        _detalhados.extend(_lote)
                        if candidate_acceptor and candidate_acceptor(_lote):
                            print(
                                f"[Scraper] Caio aprovou candidato no lote "
                                f"{(_inicio // _batch_size) + 1}; interrompendo detalhes"
                            )
                            _detalhados = [
                                est for est in _detalhados if est.get("_caio_resultado")
                            ]
                            break
                    print(f"\n[Scraper] Total: {len(_detalhados)} estabelecimentos capturados")
                    await _close_quietly(browser)
                    return _detalhados

                # Fallback: Google Search texto
                await page.goto("https://www.google.com.br", timeout=30000)
                await self._human_delay(1500, 3000)
                try:
                    btn = await page.query_selector("button[id='L2AGLb']")
                    if btn:
                        await btn.click()
                        await self._human_delay(500, 1000)
                except Exception:
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
                estabelecimentos = _parsear_resultados(texto, limite)

                import asyncio as _asyncio2
                _sem2 = _asyncio2.Semaphore(4)

                async def _buscar_com_sem2(est):
                    async with _sem2:
                        try:
                            remaining = _remaining_secs()
                            if remaining <= 3:
                                return
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
                        except Exception as e_det:
                            # IMPORTANTE: falha silenciosa pode perder dados de detalhes
                            # Logamos para detectar problemas de scraping
                            print(f"[Scraper][WARN] detalhe {est['nome']}: {e_det}")

                await _asyncio2.gather(
                    *[_buscar_com_sem2(est) for est in estabelecimentos],
                    return_exceptions=True,
                )

                print(f"\n[Scraper] Total: {len(estabelecimentos)} estabelecimentos capturados")
                await _close_quietly(browser)
                return estabelecimentos

            except Exception as e:
                print(f"[Scraper] ERRO: {e}")
                await _close_quietly(browser)
                return []

    async def _buscar_detalhes(
        self,
        context,
        nome: str,
        cidade: str,
        fast: bool = False,
    ) -> Optional[Dict]:
        """Busca detalhes no Google Maps: fotos, reviews, horarios, atributos, servicos, website."""
        detail_page = None
        try:
            detail_page = await context.new_page()
            goto_timeout = _env_int("FRALIB_MAPS_DETAIL_GOTO_TIMEOUT_MS", 8000, 3000, 20000)
            search = f"{nome} {cidade}"
            url = f"https://www.google.com/maps/search/{search.replace(' ', '+')}?hl=pt-BR"
            await detail_page.goto(
                url,
                timeout=goto_timeout,
                wait_until="domcontentloaded",
            )
            await asyncio.sleep(0.7 if fast else 1.5)

            result = await _buscar_detalhes(detail_page, nome, cidade, fast)
            return result

        except Exception as e:
            print(f"[Scraper] detalhe erro: {e}")
            return None
        finally:
            if detail_page:
                await _close_quietly(detail_page)

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
            browser = await p.chromium.launch(headless=self.headless, args=_playwright_launch_args())
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1366, "height": 768}, locale="pt-BR", timezone_id="America/Sao_Paulo",
            )
            page = None
            try:
                page = await context.new_page()
                goto_timeout = _env_int("FRALIB_MAPS_DETAIL_GOTO_TIMEOUT_MS", 8000, 3000, 20000)
                search = f"{nome} {cidade}"
                url = f"https://www.google.com/maps/search/{search.replace(' ', '+')}?hl=pt-BR"
                await page.goto(
                    url,
                    timeout=goto_timeout,
                    wait_until="domcontentloaded",
                )
                await asyncio.sleep(1.5)
                return await _buscar_detalhes(page, nome, cidade)
            finally:
                if page:
                    await _close_quietly(page)
                await browser.close()

    async def buscar_somente_cards(self, query: str, cidade: str, limite: int = 10):
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, args=_playwright_launch_args())
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1366, "height": 768}, locale="pt-BR", timezone_id="America/Sao_Paulo",
                extra_http_headers={"Accept-Language": "pt-BR,pt;q=0.9"},
            )
            page = None
            try:
                page = await context.new_page()
                url = f"https://www.google.com/maps/search/{query.replace(chr(32), chr(43))}+{cidade.replace(chr(32), chr(43))}?hl=pt-BR"
                await page.goto(url, timeout=30000)
                await self._human_delay(3000, 5000)
                return await _capturar_painel_maps(page, limite)
            finally:
                if page:
                    await _close_quietly(page)
                await browser.close()
