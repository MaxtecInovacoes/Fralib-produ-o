"""
Google Local Business Scraper - Parseia resultados do Google Search

Interface compatível com agente1_hunter_v2.py:
  - buscar(query, cidade, limite) -> List[Dict]
  - buscar_negocio(nome, cidade)  -> Dict

Campos: nome, categoria, telefone, rating, total_avaliacoes,
  reviews, fotos, website, endereco, logo,
  horarios, maps_url, atributos, servicos, faixa_preco

Módulos:
  - google_scraper_core: classe GoogleLocalScraper com toda a lógica
  - google_scraper_helpers: utilitários (_env_int, _close_quietly, _playwright_launch_args)
"""
from backend.utils.google_scraper_core import GoogleLocalScraper
from backend.utils.google_scraper_helpers import _env_int, _close_quietly, _playwright_launch_args

__all__ = [
    "GoogleLocalScraper",
    "_env_int",
    "_close_quietly",
    "_playwright_launch_args",
]
