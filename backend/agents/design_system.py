"""
Design System FraLib - Carregador e Validador
Versão: 2.0 (52 itens)
Data: 2026-04-27
"""
from pathlib import Path
from typing import Dict, List

DESIGN_SYSTEM_PATH = Path(__file__).parent / "DESIGN-SYSTEM.md"

def carregar_design_system() -> str:
    """Carrega Design System completo"""

    if not DESIGN_SYSTEM_PATH.exists():
        print(f"[Design System] ⚠️ Arquivo não encontrado em {DESIGN_SYSTEM_PATH}")
        return ""

    try:
        with open(DESIGN_SYSTEM_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"[Design System] ✅ Carregado ({len(content)} chars, 52 itens)")
        return content

    except Exception as e:
        print(f"[Design System] ❌ Erro ao carregar: {e}")
        return ""


def extrair_checklist_liz() -> Dict[str, bool]:
    """Extrai checklist binário para Liz validar (52 itens)"""

    checklist = {
        # SEO Local (10 itens)
        "title_com_cidade": False,
        "meta_description_com_cidade": False,
        "schema_local_business": False,
        "google_business_profile_link": False,
        "backlinks_diretorios_locais": False,
        "faq_schema": False,
        "long_tail_keywords": False,
        "alt_text_com_cidade": False,
        "nap_consistency": False,
        "google_maps_embed": False,

        # LGPD (5 itens)
        "banner_cookies": False,
        "politica_privacidade": False,
        "termos_uso": False,
        "opt_in_explicito": False,
        "botao_rejeitar_cookies": False,

        # Conversão (8 itens)
        "prova_social": False,
        "urgencia_escassez": False,
        "lead_magnet": False,
        "cta_primario_hero": False,
        "cta_repetido_3x": False,
        "whatsapp_flutuante": False,
        "notificacoes_conversao": False,
        "visto_por_x_pessoas": False,

        # Performance (10 itens)
        "imagens_webp": False,
        "lazy_loading": False,
        "preconnect_fontes": False,
        "css_critico_inline": False,
        "minificacao": False,
        "lcp_menor_2_5s": False,
        "prefetch_paginas": False,
        "srcset_responsivo": False,
        "aspect_ratio": False,
        "placeholder_blur": False,

        # Acessibilidade (6 itens)
        "contraste_wcag_aa": False,
        "alt_text_todas_imagens": False,
        "navegacao_teclado": False,
        "aria_labels": False,
        "prefers_reduced_motion": False,
        "skip_links": False,

        # Mobile (4 itens)
        "mobile_first": False,
        "touch_targets_48px": False,
        "menu_hamburger": False,
        "viewport_meta_tag": False,

        # Analytics (5 itens)
        "google_analytics_4": False,
        "facebook_pixel": False,
        "event_tracking": False,
        "conversoes_configuradas": False,
        "retargeting_ativo": False,

        # Segurança (4 itens)
        "https_ssl": False,
        "content_security_policy": False,
        "x_frame_options": False,
        "x_content_type_options": False
    }

    return checklist


def validar_html_design_system(html: str) -> Dict[str, any]:
    """
    Valida HTML contra Design System (52 itens)

    Returns:
        {
            "score": 0-100,
            "aprovado": bool (>= 96%),
            "checklist": {...},
            "falhas": [...],
            "itens_aprovados": int,
            "total_itens": int
        }
    """
    checklist = extrair_checklist_liz()
    falhas = []

    html_lower = html.lower()

    # SEO Local (10 itens)
    if "<title>" in html_lower and ("em " in html_lower or " | " in html_lower):
        checklist["title_com_cidade"] = True
    else:
        falhas.append("Title sem cidade ou separador |")

    if 'name="description"' in html_lower:
        checklist["meta_description_com_cidade"] = True

    if "application/ld+json" in html and "LocalBusiness" in html:
        checklist["schema_local_business"] = True
    else:
        falhas.append("Falta Schema.org LocalBusiness")

    if "g.page" in html or "google.com/maps" in html:
        checklist["google_business_profile_link"] = True

    if "guiamais" in html_lower or "apontador" in html_lower:
        checklist["backlinks_diretorios_locais"] = True

    if "FAQPage" in html:
        checklist["faq_schema"] = True

    # LGPD (5 itens)
    if "cookie" in html_lower and ("aceitar" in html_lower or "accept" in html_lower):
        checklist["banner_cookies"] = True
    else:
        falhas.append("Falta banner de cookies")

    if "politica" in html_lower or "privacy" in html_lower:
        checklist["politica_privacidade"] = True

    if "termos" in html_lower or "terms" in html_lower:
        checklist["termos_uso"] = True

    if 'type="checkbox"' in html and "consent" in html_lower:
        checklist["opt_in_explicito"] = True

    if "rejeitar" in html_lower or "reject" in html_lower:
        checklist["botao_rejeitar_cookies"] = True

    # Conversão (8 itens)
    if "whatsapp" in html_lower or "wa.me" in html:
        checklist["whatsapp_flutuante"] = True
    else:
        falhas.append("Falta botão WhatsApp")

    cta_count = html_lower.count("agende") + html_lower.count("solicite") + html_lower.count("garanta")
    if cta_count >= 3:
        checklist["cta_repetido_3x"] = True

    # Performance (10 itens)
    if ".webp" in html_lower:
        checklist["imagens_webp"] = True
    else:
        falhas.append("Imagens não estão em WebP")

    if 'loading="lazy"' in html:
        checklist["lazy_loading"] = True
    else:
        falhas.append("Falta lazy loading")

    if "srcset" in html:
        checklist["srcset_responsivo"] = True
    else:
        falhas.append("Falta srcset responsivo")

    if "aspect-ratio" in html:
        checklist["aspect_ratio"] = True

    # Segurança (4 itens)
    if "Content-Security-Policy" in html:
        checklist["content_security_policy"] = True
    else:
        falhas.append("Falta Content Security Policy")

    if "X-Frame-Options" in html:
        checklist["x_frame_options"] = True

    if "X-Content-Type-Options" in html:
        checklist["x_content_type_options"] = True

    # Analytics (5 itens)
    if "gtag" in html or "google-analytics" in html_lower:
        checklist["google_analytics_4"] = True

    if "fbq" in html or "facebook" in html_lower:
        checklist["facebook_pixel"] = True

    # Calcular score
    total_itens = len(checklist)
    itens_aprovados = sum(1 for v in checklist.values() if v)
    score = int((itens_aprovados / total_itens) * 100)

    return {
        "score": score,
        "aprovado": score >= 96,  # 50/52 itens
        "checklist": checklist,
        "falhas": falhas,
        "itens_aprovados": itens_aprovados,
        "total_itens": total_itens
    }
