#!/usr/bin/env python3
"""
Webhook universal para Discord/Slack/Telegram.
Notificacoes do blog, SEO, vendas, erros.
"""

import os
import json
import sys
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

BLOG_DIR = Path(__file__).parent.parent / "frontend" / "blog"

# Configuracao de canais
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def send_discord(message: str, title: str = "FraLib", color: int = 0x00FFB3, fields: List[Dict] = None) -> bool:
    """Envia webhook para Discord."""

    if not DISCORD_WEBHOOK:
        return False

    embed = {
        "title": title,
        "description": message,
        "color": color,
        "timestamp": datetime.now().isoformat(),
        "footer": {"text": "FraLib OS"},
    }

    if fields:
        embed["fields"] = fields

    try:
        resp = requests.post(
            DISCORD_WEBHOOK,
            json={"embeds": [embed]},
            timeout=15,
        )
        return resp.ok
    except Exception as e:
        print(f"  Discord error: {e}", file=sys.stderr)
        return False


def send_slack(message: str, title: str = "FraLib", color: str = "good", fields: List[Dict] = None) -> bool:
    """Envia webhook para Slack."""

    if not SLACK_WEBHOOK:
        return False

    attachment = {
        "color": color,
        "title": title,
        "text": message,
        "ts": int(datetime.now().timestamp()),
    }

    if fields:
        attachment["fields"] = [
            {"title": f["name"], "value": f["value"], "short": f.get("short", True)}
            for f in fields
        ]

    try:
        resp = requests.post(
            SLACK_WEBHOOK,
            json={"attachments": [attachment]},
            timeout=15,
        )
        return resp.ok
    except Exception as e:
        print(f"  Slack error: {e}", file=sys.stderr)
        return False


def send_telegram(message: str) -> bool:
    """Envia mensagem via Telegram bot."""

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
            },
            timeout=15,
        )
        return resp.ok
    except Exception as e:
        print(f"  Telegram error: {e}", file=sys.stderr)
        return False


def notify_all(message: str, title: str = "FraLib OS", level: str = "info", fields: List[Dict] = None) -> Dict:
    """Envia para todos os canais configurados."""

    results = {"discord": False, "slack": False, "telegram": False}

    # Cor por nivel
    colors = {
        "info": 0x00FFB3,
        "success": 0x22C55E,
        "warning": 0xFFB800,
        "error": 0xEF4444,
    }
    color = colors.get(level, 0x00FFB3)

    # Discord
    if DISCORD_WEBHOOK:
        results["discord"] = send_discord(message, title, color, fields)

    # Slack
    if SLACK_WEBHOOK:
        slack_color = "good" if level in ["info", "success"] else "warning" if level == "warning" else "danger"
        results["slack"] = send_slack(message, title, slack_color, fields)

    # Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        formatted = f"<b>{title}</b>\n\n{message}"
        if fields:
            for f in fields:
                formatted += f"\n\n<b>{f['name']}:</b> {f['value']}"
        results["telegram"] = send_telegram(formatted)

    return results


# ============================================================================
# EVENTOS PRE-CONFIGURADOS
# ============================================================================

def notify_blog_generated(posts: List[str], images: int = 0) -> Dict:
    """Notificacao: posts gerados."""

    msg = f"📝 **{len(posts)} posts novos** gerados pelo pipeline\n\n"
    for post in posts[:5]:
        msg += f"• {post[:60]}\n"
    if len(posts) > 5:
        msg += f"• ... e mais {len(posts) - 5}\n"

    return notify_all(
        msg,
        title="📝 Blog Pipeline Executado",
        level="success",
        fields=[
            {"name": "Posts", "value": str(len(posts)), "short": True},
            {"name": "Imagens", "value": str(images), "short": True},
        ],
    )


def notify_seo_score(score: int, total_posts: int) -> Dict:
    """Notificacao: score SEO."""

    level = "success" if score >= 90 else "warning" if score >= 70 else "error"
    return notify_all(
        f"🎯 Score SEO: **{score}/100**\n{total_posts} posts otimizados com 8 tipos de schema.",
        title="🎯 SEO Master Executado",
        level=level,
        fields=[
            {"name": "Score", "value": f"{score}/100", "short": True},
            {"name": "Posts", "value": str(total_posts), "short": True},
        ],
    )


def notify_deploy(success: bool, files_changed: int = 0) -> Dict:
    """Notificacao: deploy."""

    if success:
        msg = f"✅ Deploy concluído com sucesso!\n{files_changed} arquivos atualizados no VPS + GitHub."
        return notify_all(msg, title="🚀 Deploy OK", level="success")
    else:
        msg = f"❌ Deploy falhou!\nVerificar logs em /var/log/fralib/pipeline.log"
        return notify_all(msg, title="🚨 Deploy ERRO", level="error")


def notify_error(error: str, context: str = "") -> Dict:
    """Notificacao: erro."""

    msg = f"❌ {error}\n"
    if context:
        msg += f"\n**Contexto:** {context}"

    return notify_all(msg, title="🚨 ERRO", level="error")


def notify_ranking_change(keyword: str, old_pos: float, new_pos: float) -> Dict:
    """Notificacao: mudança de rankeamento."""

    diff = old_pos - new_pos  # Positivo = subiu
    emoji = "📈" if diff > 0 else "📉" if diff < 0 else "➡️"

    msg = f"{emoji} **{keyword}**\nPosição: {old_pos:.1f} → {new_pos:.1f} ({diff:+.1f})"

    level = "success" if diff > 0 else "warning"
    return notify_all(msg, title="Rankeamento alterado", level=level")


def notify_newsletter_sent(subscribers: int, posts: int) -> Dict:
    """Notificacao: newsletter enviada."""

    msg = f"📧 Newsletter semanal enviada!\n• {subscribers} subscribers\n• {posts} posts no resumo"

    return notify_all(
        msg,
        title="📧 Newsletter Enviada",
        level="success",
        fields=[
            {"name": "Subs", "value": str(subscribers), "short": True},
            {"name": "Posts", "value": str(posts), "short": True},
        ],
    )


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    """CLI para teste."""

    if len(sys.argv) < 2:
        print("Uso: python webhook_notifier.py [test|notify-blog|notify-seo|notify-error] [args]")
        return 1

    cmd = sys.argv[1]

    if cmd == "test":
        result = notify_all("🧪 Teste de webhook FraLib OS", title="Teste", level="info")
        print(f"Resultado: {result}")
    elif cmd == "notify-blog":
        posts = sys.argv[2:] if len(sys.argv) > 2 else ["Teste de post"]
        result = notify_blog_generated(posts, images=len(posts))
        print(f"Resultado: {result}")
    elif cmd == "notify-error":
        error = sys.argv[2] if len(sys.argv) > 2 else "Erro desconhecido"
        result = notify_error(error)
        print(f"Resultado: {result}")
    else:
        print(f"Comando desconhecido: {cmd}")
        return 1

    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
