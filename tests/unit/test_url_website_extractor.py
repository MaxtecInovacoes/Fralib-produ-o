"""Testes para extrair_url_website (whatsapp/interactions.py).

Funcao pura — sem I/O. Cobre os casos do ticket da Carolina Ragugnetti
(URL propria via WhatsApp) e os guard-rails (redes sociais, links Google).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from whatsapp.interactions import extrair_url_website


def test_extrai_url_simples_sem_scheme():
    """URL sem scheme e sem www deve ser normalizada para https://."""
    assert (
        extrair_url_website("Meu site é carolinaragugnetti.com.br")
        == "https://carolinaragugnetti.com.br"
    )


def test_extrai_url_com_https():
    """URL com https://www. deve retornar apenas o dominio."""
    assert (
        extrair_url_website("veja https://exemplo.com/portfolio")
        == "https://exemplo.com"
    )


def test_extrai_url_com_www():
    """URL com www. mas sem scheme deve perder o www."""
    assert extrair_url_website("www.acme.com.br") == "https://acme.com.br"


def test_extrai_url_com_path_e_query():
    """Path e query sao descartados; retorna apenas o dominio."""
    assert (
        extrair_url_website("https://exemplo.com.br/pagina?x=1#ancora")
        == "https://exemplo.com.br"
    )


def test_ignora_instagram():
    """Redes sociais nao contam como site proprio."""
    assert extrair_url_website("me segue @fulano no instagram.com/fulano") is None
    assert extrair_url_website("https://instagram.com/empresa") is None


def test_ignora_facebook():
    assert extrair_url_website("https://facebook.com/empresa") is None
    assert extrair_url_website("https://fb.com/x") is None


def test_ignora_x_twitter():
    assert extrair_url_website("https://x.com/fulano") is None
    assert extrair_url_website("https://twitter.com/fulano") is None


def test_ignora_tiktok():
    assert extrair_url_website("https://tiktok.com/@nutri") is None


def test_ignora_linktr_ee():
    """Agregadores de link (linktr.ee, bio.me, beacons.ai) NAO sao site proprio."""
    assert extrair_url_website("https://linktr.ee/empresa") is None


def test_ignora_texto_sem_url():
    """Texto comum sem URL retorna None."""
    assert extrair_url_website("oi, quero saber mais sobre o servico") is None
    assert extrair_url_website("") is None


def test_ignora_link_google():
    """URLs do Google (assets, Maps) nao sao site proprio."""
    assert extrair_url_website("https://lh3.googleusercontent.com/foo") is None
    assert extrair_url_website("https://maps.google.com/maps?q=abc") is None
    assert extrair_url_website("https://schema.org/Thing") is None


def test_primeira_url_valida_em_mensagem_longa():
    """Quando ha multiplas URLs, retorna a primeira que seja site proprio."""
    texto = (
        "Oi! segue meu insta instagram.com/foo e meu site "
        "https://carolinaragugnetti.com.br/contato"
    )
    assert extrair_url_website(texto) == "https://carolinaragugnetti.com.br"


def test_case_insensitive():
    """Dominio em CAIXA ALTA ainda funciona."""
    assert (
        extrair_url_website("veja CAROLINARAGUGNETTI.COM.BR").lower()
        == "https://carolinaragugnetti.com.br"
    )


def test_dominio_curto_com_hifen():
    """Hifens no dominio sao aceitos (ate 61 chars)."""
    assert extrair_url_website("meu-site-legal.com") == "https://meu-site-legal.com"


def test_input_none():
    """Defensivo: None nao quebra a funcao."""
    assert extrair_url_website(None) is None  # type: ignore[arg-type]