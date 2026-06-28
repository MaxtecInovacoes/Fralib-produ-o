#!/usr/bin/env python3
"""
Newsletter semanal FraLib.
Envia resumo dos melhores posts do blog para a lista.
Mailchimp + Resend como fallback.
"""

import os
import json
import re
import sys
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import List, Dict, Optional

try:
    import requests
except ImportError:
    print("Instale: pip install requests", file=sys.stderr)
    sys.exit(1)


BLOG_DIR = Path(__file__).parent.parent / "frontend" / "blog"
POSTS_DIR = BLOG_DIR / "posts"
SITE_URL = "https://seunegociofralib.site"
SITE_NAME = "FraLib OS"

# Configuracao de envio
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
MAILCHIMP_API_KEY = os.environ.get("MAILCHIMP_API_KEY", "")
MAILCHIMP_LIST_ID = os.environ.get("MAILCHIMP_LIST_ID", "")
MAILCHIMP_SERVER = os.environ.get("MAILCHIMP_SERVER", "us1")

FROM_EMAIL = "newsletter@fralib.site"
FROM_NAME = "FraLib OS"


def get_top_posts(days: int = 7, limit: int = 5) -> List[Dict]:
    """Retorna os melhores posts dos últimos N dias."""

    if not POSTS_DIR.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    posts = []

    for post_file in POSTS_DIR.glob("*.html"):
        mtime = datetime.fromtimestamp(post_file.stat().st_mtime)
        if mtime < cutoff:
            continue

        content = post_file.read_text(encoding="utf-8")
        slug = post_file.stem

        title_match = re.search(r"<title>([^<]+?) — Blog FraLib</title>", content)
        title = title_match.group(1) if title_match else slug

        desc_match = re.search(r'<meta name="description" content="([^"]+)"', content)
        excerpt = desc_match.group(1)[:160] if desc_match else title

        cat_match = re.search(r'<span class="tag">([^<]+)</span>', content)
        category = cat_match.group(1) if cat_match else "Blog"

        has_image = (BLOG_DIR / "images" / f"{slug}.webp").exists()

        word_count = len(re.findall(r"\b\w+\b", content))

        posts.append({
            "slug": slug,
            "title": title,
            "excerpt": excerpt,
            "category": category,
            "date": mtime.strftime("%Y-%m-%d"),
            "has_image": has_image,
            "read_time": max(2, word_count // 200),
            "url": f"{SITE_URL}/blog/posts/{slug}.html",
        })

    # Ordena por data (mais recentes primeiro)
    posts.sort(key=lambda x: x["date"], reverse=True)
    return posts[:limit]


def build_html_email(posts: List[Dict]) -> str:
    """Constroi HTML do email."""

    posts_html = "\n".join([
        f"""
        <div style="background:#12121a;border:1px solid rgba(147,51,234,0.12);padding:20px;margin-bottom:16px">
            <span style="display:inline-block;padding:3px 10px;background:rgba(0,255,179,0.12);color:#00FFB3;font-size:10px;font-family:monospace;letter-spacing:0.5px;margin-bottom:12px">{post['category']}</span>
            <h2 style="font-family:Arial,sans-serif;font-size:18px;font-weight:700;line-height:1.3;color:#f0f0f5;margin:8px 0">
                <a href="{post['url']}?utm_source=newsletter&utm_medium=email&utm_campaign=weekly" style="color:#f0f0f5;text-decoration:none">{post['title']}</a>
            </h2>
            <p style="font-size:14px;line-height:1.6;color:#8888a0;margin:8px 0">{post['excerpt']}</p>
            <div style="font-size:11px;color:#44445a;font-family:monospace;padding-top:8px;border-top:1px solid rgba(147,51,234,0.12)">
                {post['date']} · {post['read_time']} min de leitura
            </div>
        </div>"""
        for post in posts
    ])

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FraLib OS Newsletter - {datetime.now().strftime("%d/%m/%Y")}</title>
</head>
<body style="margin:0;padding:0;background:#0a0714;font-family:Arial,Helvetica,sans-serif;color:#f0f0f5">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#0a0714;padding:32px 0">
<tr>
<td align="center">
<table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%">
    <!-- HEADER -->
    <tr>
    <td style="padding:32px 24px;text-align:center;border-bottom:1px solid rgba(147,51,234,0.25)">
        <h1 style="font-family:'Courier New',monospace;font-size:24px;font-weight:800;margin:0;background:linear-gradient(135deg,#c084fc,#00FFB3);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">FRA LIB OS</h1>
        <p style="color:#8888a0;font-size:13px;margin:8px 0 0">Newsletter Semanal · {datetime.now().strftime("%d de %B de %Y")}</p>
    </td>
    </tr>

    <!-- INTRO -->
    <tr>
    <td style="padding:32px 24px">
        <p style="font-size:15px;line-height:1.7;color:#f0f0f5;margin:0 0 16px">Oi!</p>
        <p style="font-size:15px;line-height:1.7;color:#f0f0f5;margin:0 0 16px">Aqui estão os <strong style="color:#00FFB3">melhores posts desta semana</strong> do FraLib OS.</p>
        <p style="font-size:15px;line-height:1.7;color:#f0f0f5;margin:0 0 24px">Tendemos IA, automacao, vendas e tudo que faz voce <strong>vender mais</strong> sem fazer nada.</p>
    </td>
    </tr>

    <!-- POSTS -->
    <tr>
    <td style="padding:0 24px">
        <h2 style="font-family:'Courier New',monospace;font-size:13px;color:#c084fc;margin:0 0 16px;letter-spacing:1px">TOP 5 DA SEMANA</h2>
        {posts_html}
    </td>
    </tr>

    <!-- CTA -->
    <tr>
    <td style="padding:32px 24px">
        <div style="background:linear-gradient(135deg,rgba(0,255,179,0.08),rgba(147,51,234,0.08));border:1px solid #00FFB3;padding:24px;text-align:center">
            <h3 style="font-family:'Courier New',monospace;font-size:14px;color:#00FFB3;margin:0 0 12px">QUER AUTOMATIZAR SUAS VENDAS?</h3>
            <p style="font-size:14px;line-height:1.6;color:#f0f0f5;margin:0 0 16px">O FraLib acha o cliente, faz o site e vende no WhatsApp. Voce so fica com o lucro.</p>
            <a href="{SITE_URL}/login?signup=1&utm_source=newsletter&utm_medium=email&utm_campaign=weekly_cta" style="display:inline-block;background:#FACC15;color:#000;padding:14px 28px;font-family:'Courier New',monospace;font-size:12px;text-decoration:none;letter-spacing:1px;font-weight:700;box-shadow:inset -3px -3px 0 #A16207,inset 3px 3px 0 #FDE68A,0 4px 0 #713F12">TESTA 7 DIAS GRATIS</a>
        </div>
    </td>
    </tr>

    <!-- FOOTER -->
    <tr>
    <td style="padding:32px 24px;text-align:center;border-top:1px solid rgba(147,51,234,0.12)">
        <p style="color:#8888a0;font-size:12px;margin:0 0 8px">Voce recebeu este email porque se inscreveu no FraLib OS.</p>
        <p style="font-size:11px;color:#44445a;margin:0">
            <a href="{SITE_URL}/unsubscribe?utm_source=newsletter" style="color:#8888a0">Cancelar inscricao</a> ·
            <a href="{SITE_URL}/blog/?utm_source=newsletter" style="color:#8888a0">Ver todos os posts</a> ·
            <a href="{SITE_URL}/" style="color:#8888a0">fralib.site</a>
        </p>
        <p style="color:#44445a;font-size:10px;margin:12px 0 0;font-family:monospace">FRA LIB OS · Feito no Brasil · 2026</p>
    </td>
    </tr>
</table>
</td>
</tr>
</table>
</body>
</html>"""


def build_text_email(posts: List[Dict]) -> str:
    """Versao texto puro (fallback)."""

    lines = [
        f"FraLib OS Newsletter - {datetime.now().strftime('%d/%m/%Y')}",
        "=" * 50,
        "",
        "Oi!",
        "",
        "Aqui estao os melhores posts desta semana:",
        "",
    ]

    for i, post in enumerate(posts, 1):
        lines.extend([
            f"{i}. {post['title']}",
            f"   {post['category']} | {post['date']} | {post['read_time']} min",
            f"   {post['excerpt'][:120]}...",
            f"   Ler: {post['url']}",
            "",
        ])

    lines.extend([
        "---",
        "",
        "Quer automatizar suas vendas?",
        f"Testa 7 dias gratis: {SITE_URL}/login?signup=1",
        "",
        "---",
        f"FraLib OS · 2026 · {SITE_URL}",
        "Cancelar inscricao: " + f"{SITE_URL}/unsubscribe",
    ])

    return "\n".join(lines)


def send_via_resend(subject: str, html: str, text: str, to_email: str) -> bool:
    """Envia via Resend."""

    if not RESEND_API_KEY:
        return False

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "html": html,
                "text": text,
                "tags": [
                    {"name": "category", "value": "newsletter"},
                    {"name": "campaign", "value": "weekly"},
                ],
            },
            timeout=30,
        )

        if resp.ok:
            print(f"  [OK] Enviado via Resend para {to_email}")
            return True
        else:
            print(f"  [ERR] Resend: {resp.status_code} {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"  [ERR] Resend exception: {e}")
        return False


def send_via_mailchimp(subject: str, html: str, to_email: str) -> bool:
    """Envia via Mailchimp API."""

    if not MAILCHIMP_API_KEY or not MAILCHIMP_LIST_ID:
        return False

    try:
        # Cria campaign
        campaign_url = f"https://{MAILCHIMP_SERVER}.api.mailchimp.com/3.0/campaigns"
        auth = ("anystring", MAILCHIMP_API_KEY)

        resp = requests.post(
            campaign_url,
            auth=auth,
            json={
                "type": "regular",
                "recipients": {"list_id": MAILCHIMP_LIST_ID},
                "settings": {
                    "subject_line": subject,
                    "from_name": FROM_NAME,
                    "reply_to": FROM_EMAIL,
                },
            },
            timeout=30,
        )

        if not resp.ok:
            return False

        campaign_id = resp.json()["id"]

        # Define conteudo
        content_url = f"{campaign_url}/{campaign_id}/content"
        requests.put(
            content_url,
            auth=auth,
            json={"html": html},
            timeout=30,
        )

        # Envia
        send_url = f"{campaign_url}/{campaign_id}/actions/send"
        resp = requests.post(send_url, auth=auth, timeout=30)

        return resp.ok
    except Exception as e:
        print(f"  [ERR] Mailchimp: {e}")
        return False


def send_via_smtp(to_email: str, subject: str, html: str, text: str) -> bool:
    """Fallback via SMTP."""

    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    if not smtp_user or not smtp_pass:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["To"] = to_email

        part1 = MIMEText(text, "plain", "utf-8")
        part2 = MIMEText(html, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"  [ERR] SMTP: {e}")
        return False


def get_subscribers() -> List[str]:
    """Carrega lista de subscribers (mock + arquivo)."""

    subs_file = BLOG_DIR / "subscribers.json"
    if subs_file.exists():
        data = json.loads(subs_file.read_text(encoding="utf-8"))
        return data.get("emails", [])

    # Fallback: email admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@fralib.site")
    return [admin_email]


def main() -> int:
    """Envia newsletter semanal."""

    print(f"[{datetime.now()}] Iniciando newsletter semanal...")

    # Busca top posts
    posts = get_top_posts(days=7, limit=5)
    if not posts:
        print("  Nenhum post novo esta semana")
        return 0

    print(f"  {len(posts)} posts encontrados")

    # Constroi email
    subject = f"Newsletter FraLib · {len(posts)} posts novos · {datetime.now().strftime('%d/%m')}"
    html = build_html_email(posts)
    text = build_text_email(posts)

    # Salva preview
    preview_file = BLOG_DIR / "newsletter-preview.html"
    preview_file.write_text(html, encoding="utf-8")
    print(f"  [OK] Preview: {preview_file}")

    # Carrega subscribers
    subscribers = get_subscribers()
    print(f"  {len(subscribers)} subscribers")

    # Envia para cada subscriber
    sent = 0
    for email in subscribers:
        # Tenta Resend primeiro
        if send_via_resend(subject, html, text, email):
            sent += 1
        elif send_via_mailchimp(subject, html, email):
            sent += 1
        elif send_via_smtp(email, subject, html, text):
            sent += 1
        else:
            print(f"  [SKIP] Nenhum provider disponivel para {email}")

    # Log
    log_file = BLOG_DIR / "newsletter-log.json"
    log_entry = {
        "sent_at": datetime.now().isoformat(),
        "subject": subject,
        "posts_count": len(posts),
        "recipients": len(subscribers),
        "sent_ok": sent,
    }

    logs = []
    if log_file.exists():
        logs = json.loads(log_file.read_text(encoding="utf-8"))
    logs.append(log_entry)
    log_file.write_text(json.dumps(logs[-50:], indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n[OK] {sent}/{len(subscribers)} emails enviados")
    print(f"   Log: {log_file}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
