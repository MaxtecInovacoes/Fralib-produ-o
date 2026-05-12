import httpx
import os
from typing import Optional

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
APP_URL = os.getenv("APP_URL", "https://seunegociofralib.site")

async def enviar_email_confirmacao(email: str, nome: str, token: str) -> bool:
    if not RESEND_API_KEY:
        print(f"[Email] RESEND_API_KEY nao configurada - token: {token}")
        return False
    link = f"{APP_URL}/api/auth/confirmar-email?token={token}"
    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;padding:32px;background:#0f0f14;color:#e5e7eb;border-radius:16px">
      <div style="text-align:center;margin-bottom:24px">
        <img src="https://seunegociofralib.site/images/Logo%20FraLib.png" alt="FraLib" height="36" style="height:36px">
      </div>
      <h2 style="color:#a855f7;margin:0 0 12px 0;text-align:center">Confirme seu email</h2>
      <p style="color:#e5e7eb;margin:0 0 8px 0">Olá, <strong>{nome}</strong>!</p>
      <p style="color:#9ca3af;margin:0 0 24px 0">Clique no botão abaixo para confirmar seu email e ativar sua conta:</p>
      <div style="text-align:center">
        <a href="{link}" style="display:inline-block;background:#7c3aed;color:#ffffff;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px;letter-spacing:0.5px">CONFIRMAR EMAIL</a>
      </div>
      <p style="color:#6b7280;font-size:12px;margin-top:24px;text-align:center">Link válido por 24 horas. Se não foi você, ignore este email.</p>
      <hr style="border:none;border-top:1px solid #2a2a30;margin:24px 0 16px 0">
      <p style="color:#4b5563;font-size:11px;text-align:center;margin:0">FraLib OS — Geração de sites com IA</p>
    </div>
    """
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
                json={"from": FROM_EMAIL, "to": [email], "subject": "Confirme seu email - FraLib", "html": html}
            )
            return r.status_code == 200
    except Exception as e:
        print(f"[Email] Erro ao enviar: {e}")
        return False

async def enviar_email_resumo_diario(email: str, nome: str, leads: list) -> bool:
    """Envia 1 email/dia com os sites prontos do dia.
    leads = [{"nome": str, "site_url": str, "cidade": str?}, ...]
    """
    if not RESEND_API_KEY:
        print(f"[Email] RESEND_API_KEY ausente - resumo {email} ({len(leads)} sites)")
        return False
    if not leads:
        return False
    linhas = ""
    for ld in leads:
        nm = (ld.get("nome") or "Lead").replace("<", "&lt;").replace(">", "&gt;")
        url = ld.get("site_url") or ld.get("url_site") or ""
        cidade = (ld.get("cidade") or "").replace("<", "&lt;")
        link_html = f'<a href="{url}" style="color:#7c3aed;text-decoration:none;font-weight:600">VER SITE &rarr;</a>' if url else '<span style="color:#9ca3af">sem URL</span>'
        local = f' &middot; {cidade}' if cidade else ''
        linhas += f'<li style="padding:10px 0;border-bottom:1px solid #2a2a30;color:#e5e7eb"><strong>{nm}</strong>{local} &mdash; {link_html}</li>'
    n = len(leads)
    plural = "sites prontos" if n != 1 else "site pronto"
    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;padding:32px;background:#0f0f14;color:#e5e7eb">
      <h2 style="color:#a855f7;margin-top:0">{n} {plural} hoje &#127881;</h2>
      <p>Ola, <strong>{nome}</strong>! Resumo do que o pipeline FraLib produziu hoje:</p>
      <ul style="list-style:none;padding:0;margin:18px 0">{linhas}</ul>
      <p style="margin-top:24px"><a href="{APP_URL}/dashboard" style="display:inline-block;background:#7c3aed;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700">ABRIR DASHBOARD</a></p>
      <p style="color:#6b7280;font-size:12px;margin-top:24px">Voce recebe este resumo so quando ha sites novos. Para desativar, ajuste em /dashboard &rarr; perfil.</p>
    </div>
    """
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
                json={"from": FROM_EMAIL, "to": [email],
                      "subject": f"{n} {plural} - FraLib",
                      "html": html}
            )
            return r.status_code == 200
    except Exception as e:
        print(f"[Email] resumo diario falhou: {e}")
        return False


async def enviar_email_recuperacao(email: str, nome: str, token: str) -> bool:
    if not RESEND_API_KEY:
        print(f"[Email] RESEND_API_KEY nao configurada - token recuperacao: {token}")
        return False
    link = f"{APP_URL}/resetar-senha?token={token}"
    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;padding:32px;background:#0f0f14;color:#e5e7eb;border-radius:16px">
      <div style="text-align:center;margin-bottom:24px">
        <img src="https://seunegociofralib.site/images/Logo%20FraLib.png" alt="FraLib" height="36" style="height:36px">
      </div>
      <h2 style="color:#a855f7;margin:0 0 12px 0;text-align:center">Recuperar senha</h2>
      <p style="color:#e5e7eb;margin:0 0 8px 0">Olá, <strong>{nome}</strong>!</p>
      <p style="color:#9ca3af;margin:0 0 24px 0">Clique no botão abaixo para criar uma nova senha:</p>
      <div style="text-align:center">
        <a href="{link}" style="display:inline-block;background:#7c3aed;color:#ffffff;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px;letter-spacing:0.5px">CRIAR NOVA SENHA</a>
      </div>
      <p style="color:#6b7280;font-size:12px;margin-top:24px;text-align:center">Link válido por 1 hora. Se não foi você, ignore este email.</p>
      <hr style="border:none;border-top:1px solid #2a2a30;margin:24px 0 16px 0">
      <p style="color:#4b5563;font-size:11px;text-align:center;margin:0">FraLib OS — Geração de sites com IA</p>
    </div>
    """
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
                json={"from": FROM_EMAIL, "to": [email], "subject": "Recuperar senha - FraLib", "html": html}
            )
            return r.status_code == 200
    except Exception as e:
        print(f"[Email] Erro ao enviar: {e}")
        return False
