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
    link = f"{APP_URL}/confirmar-email?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">
      <h2 style="color:#7c3aed">Confirme seu email</h2>
      <p>Olá, <strong>{nome}</strong>!</p>
      <p>Clique no botão abaixo para confirmar seu email e ativar sua conta:</p>
      <a href="{link}" style="display:inline-block;background:#7c3aed;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:700;margin:16px 0">
        CONFIRMAR EMAIL
      </a>
      <p style="color:#6b7280;font-size:13px">Link válido por 24 horas. Se não foi você, ignore este email.</p>
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

async def enviar_email_recuperacao(email: str, nome: str, token: str) -> bool:
    if not RESEND_API_KEY:
        print(f"[Email] RESEND_API_KEY nao configurada - token recuperacao: {token}")
        return False
    link = f"{APP_URL}/resetar-senha?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">
      <h2 style="color:#7c3aed">Recuperar senha</h2>
      <p>Olá, <strong>{nome}</strong>!</p>
      <p>Clique no botão abaixo para criar uma nova senha:</p>
      <a href="{link}" style="display:inline-block;background:#7c3aed;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:700;margin:16px 0">
        CRIAR NOVA SENHA
      </a>
      <p style="color:#6b7280;font-size:13px">Link válido por 1 hora. Se não foi você, ignore este email.</p>
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
