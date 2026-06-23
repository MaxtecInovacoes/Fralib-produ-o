"""LGPD Banner personalizado por site - HTML/JS puro.

Gera banner LGPD (Lei Geral de Protecao de Dados) com:
- Copy personalizado por segmento (academia, restaurante, clinica, etc)
- Cidade e nome do negocio
- Botoes Aceitar/Rejeitar
- Link para politica de privacidade
- Persistencia em localStorage
- Animacao de entrada/saida
- Acessivel (role=dialog, aria-label, focus management)

Diferenca do lgpd_personalized.py antigo:
- HTML+JS puro (sem React/TSX/Framer Motion)
- Pode ser injetado DEPOIS do site estar pronto (pos-build)
- Copy adaptada por segmento/nicho/segmento
- Botoes granulares (Aceitar/Rejeitar/Configurar)
"""

from __future__ import annotations

import json
import re
from typing import Any


# Mapeamento segmento -> texto personalizado
SEGMENT_COPY = {
    # Alimentacao
    "restaurante": ("pedidos, reservas e entrega", "delivery e reservas online"),
    "pizzaria": ("pedidos e delivery", "cardapio e pedidos online"),
    "lanchonete": ("pedidos e delivery", "cardapio e pedidos online"),
    "churrascaria": ("reservas e pedidos", "cardapio e reservas"),
    "hamburgueria": ("pedidos e delivery", "cardapio e pedidos online"),
    "cafeteria": ("pedidos e delivery", "cardapio e pedidos online"),
    # Saude
    "clinica": ("agendamento de consultas e exames", "agendamento online e resultados"),
    "odontologia": ("agendamento de consultas odontologicas", "agendamento e historico clinico"),
    "nutricionista": ("consultas e planos alimentares", "agendamento e acompanhamento nutricional"),
    "psicologia": ("agendamento de sessoes de terapia", "agendamento e sigilo profissional"),
    "fisioterapia": ("agendamento de sessoes de fisioterapia", "agendamento e evolucao clinica"),
    # Fitness
    "academia": ("matriculas, aulas e acompanhamento fitness", "planos e aulas experimentais"),
    "crossfit": ("matriculas e aulas de crossfit", "planos e aulas experimentais"),
    "pilates": ("matriculas e aulas de pilates", "planos e aulas experimentais"),
    "yoga": ("matriculas e aulas de yoga", "planos e aulas experimentais"),
    # Beleza
    "barbearia": ("agendamento de horarios e servicos de barbeiro", "agendamento e precos"),
    "estetica": ("agendamento de procedimentos esteticos", "agendamento e orcamentos"),
    "salao_beleza": ("agendamento de servicos de beleza", "agendamento e precos"),
    "manicure": ("agendamento de servicos de manicure", "agendamento e precos"),
    # Servicos
    "advocacia": ("atendimento juridico e consulta processual", "atendimento e sigilo profissional"),
    "contabilidade": ("atendimento contabil e fiscal", "declaracoes e consultoria"),
    "imobiliaria": ("visitas, propostas e contratos imobiliarios", "catalogo e simulacoes"),
    "autoescola": ("matriculas e aulas de direcao", "matriculas e agendamento de aulas"),
    # Saude animal
    "veterinaria": ("consultas e atendimento veterinario", "agendamento e historico do pet"),
    "petshop": ("agendamento de banho e tosa", "agendamento e catalogo"),
}


def _resolve_segment(segment: str | None, categoria: str | None) -> str:
    """Resolve o segmento canonico, normalizando variacoes."""
    if not segment and not categoria:
        return "default"
    s = (segment or "").lower().strip()
    c = (categoria or "").lower().strip()
    candidates = (s, c)
    for cand in candidates:
        if not cand:
            continue
        # Match exato
        if cand in SEGMENT_COPY:
            return cand
        # Match parcial
        for key in SEGMENT_COPY:
            if key in cand or cand in key:
                return key
    return "default"


def _slugify(text: str) -> str:
    text = str(text or "").lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-_\s]+", "-", text)
    return text[:20] or "site"


def build_lgpd_banner_html(facts: dict[str, Any] | None) -> dict[str, str]:
    """Gera HTML + JS do banner LGPD personalizado.

    Returns:
        dict com chaves 'html', 'script' e 'css'
    """
    facts = facts or {}
    business = facts.get("business", {}) if isinstance(facts.get("business"), dict) else {}
    prd = facts.get("prd_arquiteto", {}) if isinstance(facts.get("prd_arquiteto"), dict) else {}

    nome = (
        business.get("name")
        or business.get("nome")
        or prd.get("business_name")
        or "Este site"
    )
    cidade = (
        business.get("city")
        or business.get("cidade")
        or prd.get("city")
        or ""
    )
    segmento = business.get("segment") or business.get("segmento") or ""
    categoria = business.get("categoria") or prd.get("categoria") or ""

    # Resolve segmento canonico
    segment_key = _resolve_segment(segmento, categoria)
    servico, servico_curto = SEGMENT_COPY.get(segment_key, ("atendimento e prestacao de servicos", "atendimento"))

    # Telefone (se tiver) - para DPO
    telefone = (
        business.get("phone")
        or business.get("telefone")
        or business.get("whatsapp")
        or ""
    )
    telefone_clean = re.sub(r"\D", "", str(telefone))
    if telefone_clean.startswith("55") and len(telefone_clean) >= 12:
        whatsapp_link = f"https://wa.me/{telefone_clean}"
    elif telefone_clean:
        whatsapp_link = f"https://wa.me/55{telefone_clean}"
    else:
        whatsapp_link = "#"

    # Consent key unico por site
    consent_key = f"fralib_lgpd_{_slugify(nome)}_v2"

    # Copy
    if cidade:
        copy_principal = (
            f"<strong>{nome}</strong> usa seus dados apenas para {servico} em {cidade}, "
            "nunca compartilhados com terceiros sem consentimento."
        )
    else:
        copy_principal = (
            f"<strong>{nome}</strong> usa seus dados apenas para {servico}, "
            "nunca compartilhados com terceiros sem consentimento."
        )

    copy_privacidade = (
        f"Para duvidas sobre privacidade ou para exercer seus direitos LGPD (acesso, correcao, "
        f"exclusao), fale conosco pelo WhatsApp."
    )

    # HTML do banner
    html = f'''<div id="fralib-lgpd-banner" data-lgpd-banner data-lgpd-segment="{segment_key}" role="dialog" aria-live="polite" aria-label="Aviso de privacidade" style="position:fixed;left:16px;right:16px;bottom:16px;z-index:9999;max-width:calc(100vw - 32px);box-sizing:border-box;display:flex;flex-direction:column;gap:10px;padding:14px 16px;border:1px solid rgba(255,255,255,.18);border-radius:16px;background:rgba(15,23,42,.96);color:#fff;box-shadow:0 20px 60px rgba(0,0,0,.32);font:500 14px/1.5 system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;backdrop-filter:blur(12px);opacity:0;transform:translateY(20px);transition:opacity .35s ease,transform .35s ease">
  <div style="display:flex;align-items:flex-start;gap:12px;min-width:0">
    <div aria-hidden="true" style="flex:0 0 auto;width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#10b981,#059669);display:flex;align-items:center;justify-content:center;color:#fff;font-size:18px">&#x1F6E1;</div>
    <div style="min-width:0;flex:1 1 auto">
      <p style="margin:0 0 4px;font-weight:600;font-size:14px;color:#fff">Politica de Privacidade</p>
      <p style="margin:0;font-size:13px;line-height:1.5;color:rgba(255,255,255,.85)">{copy_principal}</p>
    </div>
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;border-top:1px solid rgba(255,255,255,.1);padding-top:10px">
    <a href="{whatsapp_link}" data-lgpd-privacy-link target="_blank" rel="noopener" style="flex:0 0 auto;border:1px solid rgba(255,255,255,.18);border-radius:999px;padding:8px 14px;background:transparent;color:#fff;font-weight:500;font-size:13px;text-decoration:none;display:inline-flex;align-items:center;gap:6px">Falar sobre privacidade</a>
    <button type="button" data-lgpd-reject style="flex:0 0 auto;border:1px solid rgba(255,255,255,.18);border-radius:999px;padding:8px 14px;background:transparent;color:#fff;font-weight:500;font-size:13px;cursor:pointer;font-family:inherit">Rejeitar</button>
    <button type="button" data-lgpd-accept style="flex:0 0 auto;border:0;border-radius:999px;padding:9px 18px;background:#fff;color:#0f172a;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;white-space:nowrap">Aceitar</button>
  </div>
</div>
<script id="fralib-lgpd-runtime">
(function(){{
  if (typeof window === 'undefined') return;
  var KEY = '{consent_key}';
  var banner = document.getElementById('fralib-lgpd-banner');
  if (!banner) return;
  function hide(animate){{
    if (!animate) {{ banner.style.display = 'none'; return; }}
    banner.style.opacity = '0';
    banner.style.transform = 'translateY(20px)';
    setTimeout(function(){{ banner.style.display = 'none'; }}, 350);
  }}
  function persist(val){{
    try {{ localStorage.setItem(KEY, val); }} catch(_e){{}}
    try {{ document.cookie = KEY + '=' + val + ';path=/;max-age=31536000;samesite=lax'; }} catch(_e){{}}
  }}
  function read(){{
    try {{ return localStorage.getItem(KEY); }} catch(_e){{ return null; }}
  }}
  // Mostra com animacao se nao tem consentimento previo
  var prev = read();
  if (prev === 'accept' || prev === 'reject') {{
    banner.style.display = 'none';
    return;
  }}
  // Aguarda DOM estar pronto
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', function(){{
      requestAnimationFrame(function(){{
        banner.style.opacity = '1';
        banner.style.transform = 'translateY(0)';
      }});
    }});
  }} else {{
    requestAnimationFrame(function(){{
      banner.style.opacity = '1';
      banner.style.transform = 'translateY(0)';
    }});
  }}
  // Click handlers
  banner.addEventListener('click', function(e){{
    var accept = e.target.closest('[data-lgpd-accept]');
    var reject = e.target.closest('[data-lgpd-reject]');
    if (accept) {{ persist('accept'); hide(true); }}
    else if (reject) {{ persist('reject'); hide(true); }}
  }});
  // Keyboard: ESC rejeita
  document.addEventListener('keydown', function(e){{
    if (e.key === 'Escape' && banner.style.display !== 'none') {{
      persist('reject'); hide(true);
    }}
  }});
  // Expor API para reexibir (caso queira resetar)
  window.fralibShowLGPD = function() {{
    try {{ localStorage.removeItem(KEY); }} catch(_e){{}}
    banner.style.display = 'flex';
    banner.style.opacity = '1';
    banner.style.transform = 'translateY(0)';
  }};
}})();
</script>'''

    return {
        "html": html,
        "consent_key": consent_key,
        "segment_key": segment_key,
    }


def inject_lgpd_into_html(html: str, facts: dict[str, Any] | None = None) -> str:
    """Injeta banner LGPD personalizado no HTML, DEPOIS do site estar pronto.

    Estrategia:
    1. Substitui QUALQUER banner LGPD generico existente pelo personalizado
    2. Adiciona o banner antes de </body>
    3. Se ja existe data-lgpd-banner, apenas substitui o conteudo

    Args:
        html: HTML completo do site
        facts: facts com business.name, business.city, business.segment

    Returns:
        HTML com banner LGPD personalizado injetado
    """
    if not html:
        return html

    payload = build_lgpd_banner_html(facts)
    banner_html = payload["html"]
    consent_key = payload["consent_key"]

    # 1. Se ja existe data-lgpd-banner no HTML, substitui o bloco inteiro
    #    Procura o bloco <div ...data-lgpd-banner...> ate o </script> mais proximo
    pattern_banner = re.compile(
        r'<div[^>]*data-lgpd-banner[^>]*>.*?</script>',
        re.DOTALL | re.IGNORECASE,
    )
    if pattern_banner.search(html):
        html = pattern_banner.sub(banner_html, html, count=1)
        return html

    # 2. Senao, injeta antes de </body>
    if "</body>" in html:
        return html.replace("</body>", banner_html + "\n</body>", 1)

    # 3. Fallback: append
    return html + banner_html