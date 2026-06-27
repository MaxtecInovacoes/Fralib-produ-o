import httpx
import os
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


# --- Email: Reativacao de cliente inativo (Sprint 14.3) ---
async def enviar_email_reativacao(
    email: str,
    nome: str,
    dias_cadastrado: int,
    plano: str,
    creditos: int,
) -> bool:
    """Email leve e consultivo para clientes que cadastraram mas nunca usaram.

    Tom: oferecer ajuda, nao pressionar. CTA primario = responder email.
    CTA secundario = ir direto pro painel.
    """
    if not RESEND_API_KEY:
        print(f"[Email] RESEND_API_KEY nao configurada - reativacao {email}")
        return False

    # Primeiro nome para o assunto (tom pessoal)
    primeiro_nome = (nome or email.split("@")[0]).split()[0]
    plural_dias = "dia" if dias_cadastrado == 1 else "dias"
    plural_creditos = "credito" if creditos == 1 else "creditos"
    link_dashboard = f"{APP_URL}/dashboard"

    html = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="color-scheme" content="dark" />
<meta name="supported-color-schemes" content="dark" />
<title>Oi {primeiro_nome}, ficou com duvida?</title>
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
<td style="width:64px;height:64px;background:linear-gradient(135deg,#7c3aed,#a855f7);border-radius:50%;text-align:center;vertical-align:middle;font-size:28px;box-shadow:0 0 30px rgba(124,58,237,0.4);">&#128172;</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:24px 40px 0 40px;" align="center">
<h1 style="margin:0;font-family:'Press Start 2P',monospace;font-size:13px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;line-height:1.8;">Oi {primeiro_nome}, ficou com duvida?</h1>
</td>
</tr>
<tr>
<td style="padding:20px 40px 0 40px;">
<p style="margin:0;font-size:15px;line-height:24px;color:#a1a1aa;">Ola <span style="color:#e4e4e7;font-weight:500;">{nome}</span>,</p>
<p style="margin:12px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;">Voce criou sua conta na FraLib ha <strong style="color:#e4e4e7;">{dias_cadastrado} {plural_dias}</strong>, e eu queria saber: <strong style="color:#e4e4e7;">ficou com alguma duvida?</strong> Travou em alguma parte? Sentiu falta de alguma coisa?</p>
<p style="margin:16px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;">As vezes o primeiro site da uma travada - o briefing tem umas perguntas sobre seu negocio (segmento, cidade, servicos) e eu sei que nao e obvio pra todo mundo.</p>
</td>
</tr>
<tr>
<td style="padding:20px 40px 0 40px;" align="center">
<p style="margin:0;font-size:14px;line-height:22px;color:#a1a1aa;font-style:italic;">"Me conta seu tipo de negocio que eu te ajudo a configurar."</p>
</td>
</tr>
<tr>
<td style="padding:32px 40px 0 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0">
<tr>
<td align="center" style="border-radius:6px;background:#FFB800;box-shadow:0 4px 0 #b38200, 0 0 20px rgba(255,184,0,0.3);">
<a href="mailto:contato@seunegociofralib.site?subject=Reativacao%20-%20Quero%20gerar%20meu%20site" style="display:inline-block;padding:14px 28px;font-family:'Press Start 2P',monospace;font-size:9px;font-weight:600;color:#08080c;text-decoration:none;letter-spacing:0.5px;">RESPONDER ESTE EMAIL</a>
</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:16px 40px 0 40px;" align="center">
<p style="margin:0;font-size:12px;color:#71717a;">ou entao va direto pro painel:</p>
</td>
</tr>
<tr>
<td style="padding:14px 40px 0 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0">
<tr>
<td align="center" style="border-radius:6px;background:transparent;border:1px solid #7c3aed;">
<a href="{link_dashboard}" target="_blank" style="display:inline-block;padding:12px 24px;font-family:'Press Start 2P',monospace;font-size:8px;font-weight:600;color:#a855f7;text-decoration:none;letter-spacing:0.5px;">ABRIR PAINEL</a>
</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:24px 40px 0 40px;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#0a0a0f;border:1px solid #1e1e2e;border-radius:10px;">
<tr>
<td style="padding:16px 20px;">
<p style="margin:0;font-size:12px;color:#71717a;text-transform:uppercase;letter-spacing:0.5px;">Sua conta</p>
<p style="margin:8px 0 0 0;font-size:14px;color:#e4e4e7;"><strong>{creditos}</strong> {plural_creditos} {plano} esperando</p>
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
<p style="margin:0;font-size:12px;line-height:18px;color:#52525b;">Se nao quiser mais receber emails da gente, <a href="mailto:contato@seunegociofralib.site?subject=Cancelar%20inscricao" style="color:#71717a;text-decoration:underline;">cancele sua inscricao</a>.</p>
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
                json={
                    "from": f"FraLib <{FROM_EMAIL}>",
                    "to": [email],
                    "subject": f"Oi {primeiro_nome}, ficou com alguma duvida sobre a FraLib?",
                    "html": html,
                    "reply_to": "contato@seunegociofralib.site",
                },
            )
            if r.status_code != 200:
                print(f"[Email] Reativacao falhou: {r.status_code} {r.text[:200]}")
                return False
            return True
    except Exception as e:
        print(f"[Email] reativacao erro: {e}")
        return False


# Alias para compatibilidade com o drip campaign (step 1)
# A funcao enviar_email_reativacao original e a step 1 do drip.
# Criamos um alias explicito para clareza no admin endpoint.
async def enviar_email_reativacao_step1(
    email: str, nome: str, dias_cadastrado: int, plano: str, creditos: int,
) -> bool:
    """Step 1 do drip: Ajuda 1-a-1. Mesmo template da funcao original."""
    return await enviar_email_reativacao(
        email=email, nome=nome,
        dias_cadastrado=dias_cadastrado, plano=plano, creditos=creditos,
    )


# --- Helpers compartilhados pelos emails do drip ---
# Numero de WhatsApp para resposta direta. Configuravel via .env (REATIVACAO_WPP).
# Padrao: placeholder. Trocar no .env antes de disparar para os clientes.
REATIVACAO_WPP = os.getenv("REATIVACAO_WPP", "5541999999999")
REATIVACAO_WPP_MSG = os.getenv(
    "REATIVACAO_WPP_MSG",
    "Ola! Vi o email da FraLib e quero ajuda com meu site.",
)


def _rodape_wpp() -> str:
    """Bloco HTML do rodape com WhatsApp. Reusado nos 5 emails."""
    wpp_link = f"https://wa.me/{REATIVACAO_WPP}?text={REATIVACAO_WPP_MSG.replace(' ', '%20')}"
    return f"""
<tr>
<td style="padding:24px 40px 0 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr><td style="border-top:1px solid #1e1e2e;font-size:0;line-height:0;">&nbsp;</td></tr></table>
</td>
</tr>
<tr>
<td style="padding:20px 40px 12px 40px;" align="center">
<p style="margin:0;font-size:13px;color:#a1a1aa;">Prefere responder por WhatsApp?</p>
</td>
</tr>
<tr>
<td style="padding:0 40px 32px 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0">
<tr>
<td align="center" style="border-radius:6px;background:#25D366;box-shadow:0 4px 0 #128C7E, 0 0 20px rgba(37,211,102,0.3);">
<a href="{wpp_link}" target="_blank" style="display:inline-block;padding:12px 24px;font-family:'Press Start 2P',monospace;font-size:9px;font-weight:600;color:#ffffff;text-decoration:none;letter-spacing:0.5px;">&#128172; FALAR NO WHATSAPP</a>
</td>
</tr>
</table>
</td>
</tr>"""


def _base_layout(titulo: str, primeiro_nome: str, icone: str, inner_html: str) -> str:
    """Template base reutilizado pelos 5 emails do drip."""
    return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="color-scheme" content="dark" />
<meta name="supported-color-schemes" content="dark" />
<title>{titulo}</title>
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
<td style="width:64px;height:64px;background:linear-gradient(135deg,#7c3aed,#a855f7);border-radius:50%;text-align:center;vertical-align:middle;font-size:28px;box-shadow:0 0 30px rgba(124,58,237,0.4);">{icone}</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:24px 40px 0 40px;" align="center">
<h1 style="margin:0;font-family:'Press Start 2P',monospace;font-size:13px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;line-height:1.8;">{titulo}</h1>
</td>
</tr>
{inner_html}
{_rodape_wpp()}
<tr>
<td style="padding:20px 40px 40px 40px;" align="center">
<p style="margin:0;font-size:12px;line-height:18px;color:#52525b;">Se nao quiser mais receber emails da gente, <a href="mailto:contato@seunegociofralib.site?subject=Cancelar%20inscricao" style="color:#71717a;text-decoration:underline;">cancele sua inscricao</a>.</p>
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


async def _enviar_drip(email: str, primeiro_nome: str, assunto: str, html: str) -> bool:
    """Helper interno: POST ao Resend com reply_to configurado."""
    if not RESEND_API_KEY:
        print(f"[Email] RESEND_API_KEY nao configurada - drip {email}")
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
                json={
                    "from": f"FraLib <{FROM_EMAIL}>",
                    "to": [email],
                    "subject": assunto,
                    "html": html,
                    "reply_to": "contato@seunegociofralib.site",
                },
            )
            if r.status_code != 200:
                print(f"[Email] Drip falhou ({assunto[:30]}): {r.status_code} {r.text[:200]}")
                return False
            return True
    except Exception as e:
        print(f"[Email] drip erro: {e}")
        return False


# --- Email Step 2 (D3): Case de sucesso ---
async def enviar_email_reativacao_step2(email: str, nome: str) -> bool:
    """Case real: como um cliente saiu de 0 a 12 sites em 30 dias."""
    primeiro_nome = (nome or email.split("@")[0]).split()[0]
    inner = f"""
<tr>
<td style="padding:20px 40px 0 40px;">
<p style="margin:0;font-size:15px;line-height:24px;color:#a1a1aa;">Ola <span style="color:#e4e4e7;font-weight:500;">{nome}</span>,</p>
<p style="margin:12px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;">Voce sabe o que aconteceu com o <strong style="color:#e4e4e7;">Lucas, dono de uma barbearia em Pinhais</strong>, ha 2 meses atras?</p>
<p style="margin:12px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;">Ele tava na mesma situacao que voce: conta criada, sem usar. Ate que um dia ele resolveu testar.</p>
</td>
</tr>
<tr>
<td style="padding:24px 40px 0 40px;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#0a0a0f;border:1px solid #1e1e2e;border-left:3px solid #a855f7;border-radius:10px;">
<tr>
<td style="padding:20px 24px;">
<p style="margin:0;font-size:13px;color:#71717a;font-style:italic;">"Em 30 dias gerei 12 sites para clientes diferentes. Cada um me pagou entre R$500 e R$1500. A IA faz o trabalho pesado, eu so fecho o negocio e reviso o resultado."</p>
<p style="margin:14px 0 0 0;font-size:12px;color:#a1a1aa;"><strong style="color:#e4e4e7;">Lucas M.</strong> &middot; Barbearia Premium &middot; Pinhais/PR</p>
</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:20px 40px 0 40px;">
<p style="margin:0;font-size:15px;line-height:24px;color:#a1a1aa;">O segredo nao foi a ferramenta. Foi <strong style="color:#e4e4e7;">comecar com um unico cliente</strong> - o dele mesmo - e depois replicar.</p>
<p style="margin:12px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;">Quer que eu te ajude a fazer o mesmo? Posso te ligar 5min ou guiar por aqui mesmo.</p>
</td>
</tr>
<tr>
<td style="padding:28px 40px 0 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0">
<tr>
<td align="center" style="border-radius:6px;background:#FFB800;box-shadow:0 4px 0 #b38200, 0 0 20px rgba(255,184,0,0.3);">
<a href="mailto:contato@seunegociofralib.site?subject=Quero%20ver%20o%20case%20completo&body=Oi!%20Quero%20saber%20mais%20sobre%20como%20gerar%20sites%20para%20clientes" style="display:inline-block;padding:14px 28px;font-family:'Press Start 2P',monospace;font-size:9px;font-weight:600;color:#08080c;text-decoration:none;letter-spacing:0.5px;">QUERO VER O CASE</a>
</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:14px 40px 0 40px;" align="center">
<p style="margin:0;font-size:12px;color:#71717a;">ou tente voce mesmo:</p>
</td>
</tr>
<tr>
<td style="padding:10px 40px 0 40px;" align="center">
<a href="{APP_URL}/dashboard" style="color:#a855f7;font-size:13px;font-weight:600;text-decoration:none">ABRIR PAINEL &rarr;</a>
</td>
</tr>"""
    html = _base_layout(
        titulo=f"{primeiro_nome}, um caso real",
        primeiro_nome=primeiro_nome,
        icone="&#128161;",
        inner_html=inner,
    )
    return await _enviar_drip(email, primeiro_nome, f"{primeiro_nome}, o caso do Lucas (12 sites em 30 dias)", html)


# --- Email Step 3 (D6): Monetização direta ---
async def enviar_email_reativacao_step3(email: str, nome: str) -> bool:
    """Quanto cobrar pelo primeiro site. Tabela de precos e ROI."""
    primeiro_nome = (nome or email.split("@")[0]).split()[0]
    inner = f"""
<tr>
<td style="padding:20px 40px 0 40px;">
<p style="margin:0;font-size:15px;line-height:24px;color:#a1a1aa;">Ola <span style="color:#e4e4e7;font-weight:500;">{nome}</span>,</p>
<p style="margin:12px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;">Uma duvida que todo mundo tem: <strong style="color:#e4e4e7;">quanto eu cobro por um site?</strong></p>
<p style="margin:12px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;">A verdade: <strong style="color:#e4e4e7;">depende do cliente</strong>. Mas a FaixA que funciona:</p>
</td>
</tr>
<tr>
<td style="padding:20px 40px 0 40px;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#0a0a0f;border:1px solid #1e1e2e;border-radius:10px;overflow:hidden;">
<tr style="background:#12121a">
<td style="padding:12px 16px;font-size:11px;font-weight:600;color:#71717a;text-transform:uppercase;letter-spacing:0.5px;">Tipo</td>
<td style="padding:12px 16px;font-size:11px;font-weight:600;color:#71717a;text-transform:uppercase;letter-spacing:0.5px;text-align:right;">Preco medio</td>
</tr>
<tr>
<td style="padding:14px 16px;font-size:13px;color:#e4e4e7;border-top:1px solid #1e1e2e;">Landing page simples</td>
<td style="padding:14px 16px;font-size:13px;color:#FFB800;border-top:1px solid #1e1e2e;text-align:right;font-weight:600;">R$ 500 - R$ 800</td>
</tr>
<tr>
<td style="padding:14px 16px;font-size:13px;color:#e4e4e7;border-top:1px solid #1e1e2e;">Site institucional completo</td>
<td style="padding:14px 16px;font-size:13px;color:#FFB800;border-top:1px solid #1e1e2e;text-align:right;font-weight:600;">R$ 1.000 - R$ 2.500</td>
</tr>
<tr>
<td style="padding:14px 16px;font-size:13px;color:#e4e4e7;border-top:1px solid #1e1e2e;">Site premium + manutencao</td>
<td style="padding:14px 16px;font-size:13px;color:#FFB800;border-top:1px solid #1e1e2e;text-align:right;font-weight:600;">R$ 3.000 - R$ 5.000+</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:20px 40px 0 40px;">
<p style="margin:0;font-size:15px;line-height:24px;color:#a1a1aa;">Com a FraLib, o tempo de geracao cai de <strong style="color:#e4e4e7;">dias para minutos</strong>. Isso significa que voce pode cobrar o mesmo (ou mais) e ter lucro muito maior.</p>
<p style="margin:12px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;"><strong style="color:#FFB800;">Calculo rapido:</strong> 5 sites/mes x R$1.000 = R$5.000/mes. Ja e mais que o salario minimo, com IA fazendo 80% do trabalho.</p>
</td>
</tr>
<tr>
<td style="padding:28px 40px 0 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0">
<tr>
<td align="center" style="border-radius:6px;background:#FFB800;box-shadow:0 4px 0 #b38200, 0 0 20px rgba(255,184,0,0.3);">
<a href="mailto:contato@seunegociofralib.site?subject=Quero%20saber%20quanto%20cobrar&body=Oi!%20Quero%20entender%20melhor%20como%20precificar" style="display:inline-block;padding:14px 28px;font-family:'Press Start 2P',monospace;font-size:9px;font-weight:600;color:#08080c;text-decoration:none;letter-spacing:0.5px;">QUERO A PLANILHA</a>
</td>
</tr>
</table>
</td>
</tr>"""
    html = _base_layout(
        titulo="Quanto cobrar pelo seu 1o site",
        primeiro_nome=primeiro_nome,
        icone="&#128176;",
        inner_html=inner,
    )
    return await _enviar_drip(email, primeiro_nome, f"Quanto cobrar pelo seu primeiro site, {primeiro_nome}?", html)


# --- Email Step 4 (D9): Tour de recursos ---
async def enviar_email_reativacao_step4(email: str, nome: str) -> bool:
    """3 coisas que talvez voce nao saiba que a FraLib faz."""
    primeiro_nome = (nome or email.split("@")[0]).split()[0]
    inner = f"""
<tr>
<td style="padding:20px 40px 0 40px;">
<p style="margin:0;font-size:15px;line-height:24px;color:#a1a1aa;">Ola <span style="color:#e4e4e7;font-weight:500;">{nome}</span>,</p>
<p style="margin:12px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;">Talvez voce nao conheca <strong style="color:#e4e4e7;">3 coisas</strong> que a FraLib ja faz por voce:</p>
</td>
</tr>
<tr>
<td style="padding:20px 40px 0 40px;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%">
<tr>
<td style="padding:12px 0;border-bottom:1px solid #1e1e2e;">
<p style="margin:0;font-size:18px;color:#a855f7;">&#128231;</p>
<p style="margin:6px 0 0 0;font-size:14px;color:#e4e4e7;font-weight:600;">Briefing automatico</p>
<p style="margin:4px 0 0 0;font-size:13px;color:#a1a1aa;line-height:20px;">Voce so fala o segmento e cidade. A IA pergunta o resto e ja gera o site. Em 5min.</p>
</td>
</tr>
<tr>
<td style="padding:12px 0;border-bottom:1px solid #1e1e2e;">
<p style="margin:0;font-size:18px;color:#a855f7;">&#128241;</p>
<p style="margin:6px 0 0 0;font-size:14px;color:#e4e4e7;font-weight:600;">Design premium por segmento</p>
<p style="margin:4px 0 0 0;font-size:13px;color:#a1a1aa;line-height:20px;">Cada nicho (barbearia, academia, restaurante) tem paleta, fotos e copy proprios. Nada generico.</p>
</td>
</tr>
<tr>
<td style="padding:12px 0;">
<p style="margin:0;font-size:18px;color:#a855f7;">&#128640;</p>
<p style="margin:6px 0 0 0;font-size:14px;color:#e4e4e7;font-weight:600;">Publicacao 1-click</p>
<p style="margin:4px 0 0 0;font-size:13px;color:#a1a1aa;line-height:20px;">Site pronto = no ar no seu subdominio FraLib instantaneamente. Sem FTP, sem DNS, sem dor de cabeca.</p>
</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:20px 40px 0 40px;">
<p style="margin:0;font-size:15px;line-height:24px;color:#a1a1aa;"><strong style="color:#e4e4e7;">E o melhor:</strong> cada site que voce gera para um cliente conta como 1 credito. Plano Pro = 360 creditos. Da pra fazer 1 site por dia por quase 1 ano.</p>
</td>
</tr>
<tr>
<td style="padding:28px 40px 0 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0">
<tr>
<td align="center" style="border-radius:6px;background:#FFB800;box-shadow:0 4px 0 #b38200, 0 0 20px rgba(255,184,0,0.3);">
<a href="{APP_URL}/dashboard" style="display:inline-block;padding:14px 28px;font-family:'Press Start 2P',monospace;font-size:9px;font-weight:600;color:#08080c;text-decoration:none;letter-spacing:0.5px;">EXPLORAR O PAINEL</a>
</td>
</tr>
</table>
</td>
</tr>"""
    html = _base_layout(
        titulo="3 coisas que talvez voce nao saiba",
        primeiro_nome=primeiro_nome,
        icone="&#128269;",
        inner_html=inner,
    )
    return await _enviar_drip(email, primeiro_nome, f"{primeiro_nome}, 3 coisas que voce talvez nao conheca da FraLib", html)


# --- Email Step 5 (D12): Ultima chance / urgencia ---
async def enviar_email_reativacao_step5(email: str, nome: str, plano: str, creditos: int) -> bool:
    """Ultima chance: creditos vao expirar. Posso estender se precisar."""
    primeiro_nome = (nome or email.split("@")[0]).split()[0]
    plural_creditos = "credito" if creditos == 1 else "creditos"
    inner = f"""
<tr>
<td style="padding:20px 40px 0 40px;">
<p style="margin:0;font-size:15px;line-height:24px;color:#a1a1aa;">Ola <span style="color:#e4e4e7;font-weight:500;">{nome}</span>,</p>
<p style="margin:12px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;">Voce recebeu alguns emails meus nas ultimas semanas. <strong style="color:#e4e4e7;">Este e o ultimo.</strong></p>
</td>
</tr>
<tr>
<td style="padding:24px 40px 0 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#0a0a0f;border:1px solid #ef4444;border-radius:10px;">
<tr>
<td style="padding:20px 24px;text-align:center;">
<p style="margin:0;font-size:13px;color:#71717a;text-transform:uppercase;letter-spacing:0.5px;">Seus creditos</p>
<p style="margin:10px 0 0 0;font-size:28px;color:#FFB800;font-weight:700;font-family:'Press Start 2P',monospace;">{creditos}</p>
<p style="margin:6px 0 0 0;font-size:13px;color:#a1a1aa;">{plural_creditos} {plano} esperando</p>
</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:24px 40px 0 40px;">
<p style="margin:0;font-size:15px;line-height:24px;color:#a1a1aa;">Eles vao expirar em breve. Se voce quiser testar a ferramenta de verdade (sem compromisso), <strong style="color:#e4e4e7;">posso estender seus creditos em +30 dias</strong>.</p>
<p style="margin:12px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;">So me responde "sim, quero estender" e eu estendo na hora. Sem pegadinha, sem cobranca.</p>
<p style="margin:12px 0 0 0;font-size:15px;line-height:24px;color:#a1a1aa;">Se preferir, tambem posso te ligar 5min para entender qual e a sua duvida e tentar resolver.</p>
</td>
</tr>
<tr>
<td style="padding:28px 40px 0 40px;" align="center">
<table role="presentation" cellpadding="0" cellspacing="0">
<tr>
<td align="center" style="border-radius:6px;background:#FFB800;box-shadow:0 4px 0 #b38200, 0 0 20px rgba(255,184,0,0.3);">
<a href="mailto:contato@seunegociofralib.site?subject=Sim,%20quero%20estender%20meus%20creditos" style="display:inline-block;padding:14px 28px;font-family:'Press Start 2P',monospace;font-size:9px;font-weight:600;color:#08080c;text-decoration:none;letter-spacing:0.5px;">SIM, QUERO ESTENDER</a>
</td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:14px 40px 0 40px;" align="center">
<p style="margin:0;font-size:13px;color:#a1a1aa;">ou se preferir:</p>
</td>
</tr>
<tr>
<td style="padding:10px 40px 0 40px;" align="center">
<a href="{APP_URL}/dashboard" style="color:#a855f7;font-size:13px;font-weight:600;text-decoration:none">GERAR MEU PRIMEIRO SITE &rarr;</a>
</td>
</tr>"""
    html = _base_layout(
        titulo="Ultima mensagem (prometo)",
        primeiro_nome=primeiro_nome,
        icone="&#9200;",
        inner_html=inner,
    )
    return await _enviar_drip(email, primeiro_nome, f"{primeiro_nome}, este e meu ultimo email (mas posso estender seus creditos)", html)


# --- Email: Relatorio paralelo ao admin apos cada step ---
ADMIN_EMAIL = os.getenv("REATIVACAO_ADMIN_EMAIL", "")


async def enviar_relatorio_drip_admin(
    campaign: str,
    step: int,
    enviados: int,
    pulados: int,
    erros: int,
    total_candidatos: int,
) -> bool:
    """Manda email paralelo ao admin (Franz) resumindo o que foi disparado.

    Disparado automaticamente apos cada step do drip campaign.
    NAO conta como outreach_attempt (e separado).
    """
    if not ADMIN_EMAIL:
        print("[Relatorio admin] REATIVACAO_ADMIN_EMAIL nao configurado - pulando")
        return False
    if not RESEND_API_KEY:
        return False

    # Buscar contadores por status
    try:
        from backend.core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'sent') AS sent,
                    COUNT(*) FILTER (WHERE status = 'replied') AS replied,
                    COUNT(*) FILTER (WHERE status = 'converted') AS converted,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed
                FROM outreach_attempts
                WHERE campaign = :camp
            """), {"camp": campaign}).fetchone()
            counts = {
                'sent': int(row[0] or 0),
                'replied': int(row[1] or 0),
                'converted': int(row[2] or 0),
                'completed': int(row[3] or 0),
            }
    except Exception as e:
        print(f"[Relatorio admin] erro ao buscar contadores: {e}")
        counts = {'sent': 0, 'replied': 0, 'converted': 0, 'completed': 0}

    taxa_geral = (counts['replied'] + counts['converted']) / max(counts['sent'], 1) * 100

    # Proxima execucao do cron (sempre proximo dia 14h UTC = 11h BRT)
    from datetime import datetime, timedelta
    amanha = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d 11:00 BRT")

    subject = f"Drip {campaign} step {step}: {enviados} enviados, {pulados} pulados, {erros} erros"

    html = f"""<!DOCTYPE html>
<html><body style="font-family:system-ui,sans-serif;background:#0a0a0f;color:#e5e7eb;padding:24px;margin:0">
<table cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;background:#12121a;border:1px solid #1e1e2e;border-radius:12px;padding:32px">
<tr><td>
<h2 style="margin:0 0 16px 0;font-size:18px;color:#a855f7">Drip Campaign · Relatorio</h2>
<p style="margin:0 0 8px 0;font-size:14px;color:#a1a1aa"><strong>Campaign:</strong> {campaign}</p>
<p style="margin:0 0 8px 0;font-size:14px;color:#a1a1aa"><strong>Step:</strong> {step} de 5</p>
<hr style="border:0;border-top:1px solid #1e1e2e;margin:16px 0">
<h3 style="margin:0 0 12px 0;font-size:14px;color:#FFB800">Este disparo</h3>
<p style="margin:0 0 4px 0;font-size:14px">Enviados: <strong style="color:#10b981">{enviados}</strong> de {total_candidatos} candidatos</p>
<p style="margin:0 0 4px 0;font-size:14px">Pulados (ja enviados): {pulados}</p>
<p style="margin:0 0 16px 0;font-size:14px">Erros: <strong style="color:#ef4444">{erros}</strong></p>
<h3 style="margin:0 0 12px 0;font-size:14px;color:#FFB800">Total da campanha</h3>
<p style="margin:0 0 4px 0;font-size:14px">Total enviados: <strong>{counts['sent']}</strong></p>
<p style="margin:0 0 4px 0;font-size:14px">Replied: <strong style="color:#FFB800">{counts['replied']}</strong></p>
<p style="margin:0 0 4px 0;font-size:14px">Convertidos: <strong style="color:#10b981">{counts['converted']}</strong></p>
<p style="margin:0 0 16px 0;font-size:14px">Completaram 5 steps: {counts['completed']}</p>
<p style="margin:0 0 16px 0;font-size:14px">Taxa de resposta/conv. ate agora: <strong style="color:#a855f7">{taxa_geral:.1f}%</strong></p>
<hr style="border:0;border-top:1px solid #1e1e2e;margin:16px 0">
<p style="margin:0 0 4px 0;font-size:13px;color:#a1a1aa"><strong>Proximo step:</strong> step {step + 1} (se step &lt; 5)</p>
<p style="margin:0;font-size:13px;color:#a1a1aa">Proxima execucao automatica: <strong>{amanha}</strong> via cron 0 14 * * *</p>
<p style="margin:8px 0 0 0;font-size:12px;color:#71717a">Para parar o proximo step, marque todos como replied/converted no dashboard.</p>
</td></tr>
</table>
</body></html>"""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
                json={
                    "from": f"FraLib OS <{FROM_EMAIL}>",
                    "to": [ADMIN_EMAIL],
                    "subject": subject,
                    "html": html,
                },
            )
            if r.status_code != 200:
                print(f"[Relatorio admin] Resend falhou: {r.status_code} {r.text[:200]}")
                return False
            return True
    except Exception as e:
        print(f"[Relatorio admin] erro: {e}")
        return False
