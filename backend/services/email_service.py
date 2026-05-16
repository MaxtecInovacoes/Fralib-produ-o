import httpx
import os
from typing import Optional
from dotenv import load_dotenv

# Garantir que .env está carregado independente de quem importa
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@seunegociofralib.site")
APP_URL = os.getenv("APP_URL", "https://seunegociofralib.site")


# --- Email: Confirmacao de conta ---
async def enviar_email_confirmacao(email: str, nome: str, token: str) -> bool:
    if not RESEND_API_KEY:
        print(f"[Email] RESEND_API_KEY nao configurada - token: {token}")
        return False
    link = f"{APP_URL}/api/auth/confirmar-email?token={token}"
    html = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="color-scheme" content="dark" />
<meta name="supported-color-schemes" content="dark" />
<title>Confirme seu email - FraLib OS</title>
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet" />
</head>
<body style="margin:0;padding:0;background-color:#08080c;font-family:'DM Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#08080c;min-height:100vh;">
<tr>
<td align="center" style="padding:40px 16px;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:520px;">
<tr>
<td align="center" style="padding-bottom:32px;">
<img src="https://seunegociofralib.site/images/Logo%20FraLib.png" alt="FraLib OS" width="140" style="display:block;border:0;outline:none;" />
</td>
</tr>
<tr>
<td>
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#12121a;border-radius:16px;border:1px solid #1e1e2e;box-shadow:0 0 60px rgba(124,58,237,0.08),0 0 120px rgba(168,85,247,0.04);">
<tr>
<td style="padding:48px 40px 16px 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0">
<tr>
<td style="width:64px;height:64px;background:linear-gradient(135deg,#7c3aed,#a855f7);border-radius:50%;text-align:center;vertical-align:middle;font-size:28px;box-shadow:0 0 30px rgba(124,58,237,0.4);">&#9993;</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:24px 40px 0 40px;" align="center">
<h1 style="margin:0;font-family:'Press Start 2P',monospace;font-size:14px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;line-height:1.8;">Confirme seu email</h1>
</td>
</tr>
<tr>
<td style="padding:20px 40px 0 40px;" align="center">
<p style="margin:0;font-size:15px;line-height:24px;color:#a1a1aa;">Ola <span style="color:#e4e4e7;font-weight:500;">{nome}</span>,</p>
<p style="margin:12px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;">Bem-vindo ao FraLib OS! Para comecar a criar sites incriveis para seus clientes, confirme seu endereco de email clicando no botao abaixo.</p>
</td>
</tr>
<tr>
<td style="padding:32px 40px 0 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0">
<tr>
<td align="center" style="border-radius:6px;background:#FFB800;box-shadow:0 4px 0 #b38200, 0 0 20px rgba(255,184,0,0.3);">
<a href="{link}" target="_blank" style="display:inline-block;padding:14px 28px;font-family:'Press Start 2P',monospace;font-size:9px;font-weight:600;color:#08080c;text-decoration:none;letter-spacing:0.5px;">CONFIRMAR EMAIL</a>
</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:20px 40px 0 40px;" align="center">
<p style="margin:0;font-size:12px;color:#71717a;">&#128337; Link valido por 24 horas</p>
</td>
</tr>
<tr>
<td style="padding:24px 40px 0 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr><td style="border-top:1px solid #1e1e2e;font-size:0;line-height:0;">&nbsp;</td></tr></table>
</td>
</tr>
<tr>
<td style="padding:20px 40px 40px 40px;" align="center">
<p style="margin:0;font-size:12px;line-height:18px;color:#52525b;">Se voce nao criou uma conta no FraLib OS, ignore este email.</p>
</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:32px 40px 0 40px;" align="center">
<p style="margin:0;font-family:'Press Start 2P',monospace;font-size:7px;color:#3f3f46;line-height:1.8;">FraLib OS</p>
<p style="margin:8px 0 0 0;font-size:11px;color:#27272a;">Sites com IA para negocios locais</p>
</td>
</tr>
</table>
</td>
</tr>
</table>
</body>
</html>"""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
                json={"from": f"FraLib <{FROM_EMAIL}>", "to": [email], "subject": "Confirme seu email - FraLib", "html": html}
            )
            if r.status_code != 200:
                print(f"[Email] Confirmacao falhou: {r.status_code} {r.text[:200]}")
            return r.status_code == 200
    except Exception as e:
        print(f"[Email] Erro ao enviar: {e}")
        return False


# --- Email: Recuperacao de senha ---
async def enviar_email_recuperacao(email: str, nome: str, token: str) -> bool:
    if not RESEND_API_KEY:
        print(f"[Email] RESEND_API_KEY nao configurada - token recuperacao: {token}")
        return False
    link = f"{APP_URL}/resetar-senha?token={token}"
    html = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="color-scheme" content="dark" />
<meta name="supported-color-schemes" content="dark" />
<title>Recuperar senha - FraLib OS</title>
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet" />
</head>
<body style="margin:0;padding:0;background-color:#08080c;font-family:'DM Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#08080c;min-height:100vh;">
<tr>
<td align="center" style="padding:40px 16px;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:520px;">
<tr>
<td align="center" style="padding-bottom:32px;">
<img src="https://seunegociofralib.site/images/Logo%20FraLib.png" alt="FraLib OS" width="140" style="display:block;border:0;outline:none;" />
</td>
</tr>
<tr>
<td>
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#12121a;border-radius:16px;border:1px solid #1e1e2e;box-shadow:0 0 60px rgba(124,58,237,0.08),0 0 120px rgba(168,85,247,0.04);">
<tr>
<td style="padding:48px 40px 16px 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0">
<tr>
<td style="width:64px;height:64px;background:linear-gradient(135deg,#7c3aed,#a855f7);border-radius:50%;text-align:center;vertical-align:middle;font-size:28px;box-shadow:0 0 30px rgba(124,58,237,0.4);">&#128274;</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:24px 40px 0 40px;" align="center">
<h1 style="margin:0;font-family:'Press Start 2P',monospace;font-size:14px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;line-height:1.8;">Recuperar senha</h1>
</td>
</tr>
<tr>
<td style="padding:20px 40px 0 40px;" align="center">
<p style="margin:0;font-size:15px;line-height:24px;color:#a1a1aa;">Ola <span style="color:#e4e4e7;font-weight:500;">{nome}</span>,</p>
<p style="margin:12px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;">Recebemos uma solicitacao para redefinir a senha da sua conta FraLib OS. Clique no botao abaixo para criar uma nova senha.</p>
</td>
</tr>
<tr>
<td style="padding:32px 40px 0 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0">
<tr>
<td align="center" style="border-radius:6px;background:#FFB800;box-shadow:0 4px 0 #b38200, 0 0 20px rgba(255,184,0,0.3);">
<a href="{link}" target="_blank" style="display:inline-block;padding:14px 28px;font-family:'Press Start 2P',monospace;font-size:9px;font-weight:600;color:#08080c;text-decoration:none;letter-spacing:0.5px;">CRIAR NOVA SENHA</a>
</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:20px 40px 0 40px;" align="center">
<p style="margin:0;font-size:12px;color:#71717a;">&#9889; Link valido por 1 hora</p>
</td>
</tr>
<tr>
<td style="padding:24px 40px 0 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr><td style="border-top:1px solid #1e1e2e;font-size:0;line-height:0;">&nbsp;</td></tr></table>
</td>
</tr>
<tr>
<td style="padding:20px 40px 40px 40px;" align="center">
<p style="margin:0;font-size:12px;line-height:18px;color:#52525b;">Se voce nao solicitou a redefinicao de senha, ignore este email. Sua senha permanecera inalterada.</p>
</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:32px 40px 0 40px;" align="center">
<p style="margin:0;font-family:'Press Start 2P',monospace;font-size:7px;color:#3f3f46;line-height:1.8;">FraLib OS</p>
<p style="margin:8px 0 0 0;font-size:11px;color:#27272a;">Sites com IA para negocios locais</p>
</td>
</tr>
</table>
</td>
</tr>
</table>
</body>
</html>"""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
                json={"from": f"FraLib <{FROM_EMAIL}>", "to": [email], "subject": "Recuperar senha - FraLib", "html": html}
            )
            if r.status_code != 200:
                print(f"[Email] Recuperacao falhou: {r.status_code} {r.text[:200]}")
            return r.status_code == 200
    except Exception as e:
        print(f"[Email] Erro ao enviar: {e}")
        return False


# --- Email: Resumo diario de sites ---
async def enviar_email_resumo_diario(email: str, nome: str, leads: list) -> bool:
    """Envia 1 email/dia com os sites prontos do dia."""
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
        link_html = f'<a href="{url}" style="color:#a855f7;text-decoration:none;font-weight:600;">VER SITE &rarr;</a>' if url else '<span style="color:#6b7280;">em progresso</span>'
        local = f'<p style="margin:2px 0 0 0;font-size:12px;color:#71717a;">{cidade}</p>' if cidade else ''
        linhas += f"""<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="border-bottom:1px solid #1e1e2e;">
<tr>
<td style="padding:14px 16px;">
<p style="margin:0;font-size:14px;font-weight:500;color:#e4e4e7;">{nm}</p>
{local}
</td>
<td style="padding:14px 16px;" align="right">{link_html}</td>
</tr>
</table>"""
    n = len(leads)
    plural = "sites prontos" if n != 1 else "site pronto"
    html = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="color-scheme" content="dark" />
<meta name="supported-color-schemes" content="dark" />
<title>Resumo diario - FraLib OS</title>
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet" />
</head>
<body style="margin:0;padding:0;background-color:#08080c;font-family:'DM Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#08080c;min-height:100vh;">
<tr>
<td align="center" style="padding:40px 16px;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:520px;">
<tr>
<td align="center" style="padding-bottom:32px;">
<img src="https://seunegociofralib.site/images/Logo%20FraLib.png" alt="FraLib OS" width="140" style="display:block;border:0;outline:none;" />
</td>
</tr>
<tr>
<td>
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#12121a;border-radius:16px;border:1px solid #1e1e2e;box-shadow:0 0 60px rgba(124,58,237,0.08),0 0 120px rgba(168,85,247,0.04);">
<tr>
<td style="padding:48px 40px 16px 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0">
<tr>
<td style="width:64px;height:64px;background:linear-gradient(135deg,#7c3aed,#a855f7);border-radius:50%;text-align:center;vertical-align:middle;font-size:28px;box-shadow:0 0 30px rgba(124,58,237,0.4);">&#128640;</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:24px 40px 0 40px;" align="center">
<h1 style="margin:0;font-family:'Press Start 2P',monospace;font-size:14px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;line-height:1.8;">{n} {plural} hoje!</h1>
</td>
</tr>
<tr>
<td style="padding:20px 40px 0 40px;" align="center">
<p style="margin:0;font-size:15px;line-height:24px;color:#a1a1aa;">Ola <span style="color:#e4e4e7;font-weight:500;">{nome}</span>,</p>
<p style="margin:12px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;">Aqui esta o resumo dos sites gerados pela IA nas ultimas 24 horas:</p>
</td>
</tr>
<tr>
<td style="padding:28px 40px 0 40px;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="border:1px solid #1e1e2e;border-radius:10px;overflow:hidden;">
<tr>
<td style="padding:12px 16px;background-color:#0a0a0f;border-bottom:1px solid #1e1e2e;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%">
<tr>
<td style="font-size:11px;font-weight:600;color:#71717a;text-transform:uppercase;letter-spacing:0.5px;">Negocio</td>
<td style="font-size:11px;font-weight:600;color:#71717a;text-transform:uppercase;letter-spacing:0.5px;" align="right">Status</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:0;">{linhas}</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:32px 40px 0 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0">
<tr>
<td align="center" style="border-radius:6px;background:#FFB800;box-shadow:0 4px 0 #b38200, 0 0 20px rgba(255,184,0,0.3);">
<a href="{APP_URL}/dashboard" target="_blank" style="display:inline-block;padding:14px 28px;font-family:'Press Start 2P',monospace;font-size:9px;font-weight:600;color:#08080c;text-decoration:none;letter-spacing:0.5px;">ABRIR DASHBOARD</a>
</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:24px 40px 0 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr><td style="border-top:1px solid #1e1e2e;font-size:0;line-height:0;">&nbsp;</td></tr></table>
</td>
</tr>
<tr>
<td style="padding:20px 40px 40px 40px;" align="center">
<p style="margin:0;font-size:12px;line-height:18px;color:#52525b;">Voce recebe este resumo so quando ha sites novos.</p>
</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:32px 40px 0 40px;" align="center">
<p style="margin:0;font-family:'Press Start 2P',monospace;font-size:7px;color:#3f3f46;line-height:1.8;">FraLib OS</p>
<p style="margin:8px 0 0 0;font-size:11px;color:#27272a;">Sites com IA para negocios locais</p>
</td>
</tr>
</table>
</td>
</tr>
</table>
</body>
</html>"""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
                json={"from": f"FraLib <{FROM_EMAIL}>", "to": [email],
                      "subject": f"\U0001f680 {n} {plural} - FraLib",
                      "html": html}
            )
            if r.status_code != 200:
                print(f"[Email] Resumo falhou: {r.status_code} {r.text[:200]}")
            return r.status_code == 200
    except Exception as e:
        print(f"[Email] resumo diario falhou: {e}")
        return False
