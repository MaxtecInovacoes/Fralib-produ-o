"""Fail when deploy paths can republish stale or non-canonical frontend."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    hook = (ROOT / "scripts" / "post-receive").read_text(encoding="utf-8")
    build = (ROOT / "frontend" / "build.py").read_text(encoding="utf-8")
    nginx = (ROOT / "deploy" / "nginx" / "seunegociofralib.conf").read_text(
        encoding="utf-8"
    )
    problems = []

    required_hook_tokens = (
        'if [ "$refname" = "refs/heads/master" ]',
        "Push sem alteracao em master; deploy ignorado",
        "scripts/verify_frontend_canonical.py",
        "Builder OpenUI: sem etapa Node",
        'cd "$FRALIB_DIR"\n\n# 4. Publicar frontend',
        'frontend/llms.txt',
        '$WEB_DIR/llms.txt',
        "landing2.html",
        "landing_backup.html",
    )
    for token in required_hook_tokens:
        if token not in hook:
            problems.append(f"post-receive sem contrato obrigatorio: {token}")

    if 'frontend/*.html' in hook:
        problems.append("post-receive ainda publica frontend/*.html por glob")
    if "dashboard.html landing.html" in hook or "admin.html dashboard.html" in hook:
        problems.append("post-receive ainda publica dashboard.html")
    if "dashboard.html" not in hook or "rm -f" not in hook:
        problems.append("post-receive nao remove dashboard.html legado")
    if "HTML legado ainda publicado" not in hook:
        problems.append("post-receive nao falha fechado se HTML legado sobreviver")
    if "/etc/cron.d/fralib-frontend-sync" not in hook:
        problems.append("post-receive nao remove cron legado que republica frontend/*.html")
    if 'location = /dashboard {' not in nginx or 'return 302 /admin.html$is_args$args;' not in nginx:
        problems.append("Nginx nao redireciona /dashboard para admin.html")
    if 'location = /dashboard.html {' not in nginx or 'return 302 /admin.html$is_args$args;' not in nginx:
        problems.append("Nginx nao redireciona /dashboard.html para admin.html")
    if 'location = /admin {' not in nginx or 'return 302 /admin.html;' not in nginx:
        problems.append("Nginx nao preserva a rota operacional /admin")
    if 'location = /login.html {' not in nginx or 'return 302 /login$is_args$args;' not in nginx:
        problems.append("Nginx nao redireciona /login.html para /login")
    if 'location = /planos.html {' not in nginx or 'return 302 /planos$is_args$args;' not in nginx:
        problems.append("Nginx nao redireciona /planos.html para /planos")
    if 'return 301 /admin;' in nginx or 'return 302 /admin;' in nginx:
        problems.append("Nginx redireciona outra superficie para /admin")
    for token in ('nginx -t', 'systemctl reload nginx', 'deploy/nginx/seunegociofralib.conf'):
        if token not in hook:
            problems.append(f"post-receive nao aplica contrato Nginx: {token}")
    if "/var/www/fralib" in build:
        problems.append("frontend/build.py ainda tenta publicar direto em /var/www/fralib")

    if problems:
        print("Deploy contract failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("deploy contract ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
