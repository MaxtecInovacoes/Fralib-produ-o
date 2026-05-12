"""
PR14: Health check pos-deploy.

Valida que o site gerado esta servindo via HTTP e contem os elementos minimos
esperados (titulo, link de contato, schema.org, HTML nao-truncado).

Sem dependencia nova: usa httpx (ja no requirements) e regex.
Sem Playwright/Selenium: nao renderiza JS. Pega ~80% das falhas comuns.
"""
import json
import re
import time
import logging
import httpx

log = logging.getLogger("uvicorn")

TAMANHO_MINIMO_BYTES = 5 * 1024  # 5KB


class HealthCheckError(Exception):
    def __init__(self, motivo: str, detalhe: str = ""):
        self.motivo = motivo
        self.detalhe = detalhe
        super().__init__(f"{motivo}: {detalhe}" if detalhe else motivo)


def _validar_conteudo(html: str) -> None:
    """Levanta HealthCheckError na primeira validacao que falhar."""
    if not html or len(html.encode("utf-8")) < TAMANHO_MINIMO_BYTES:
        raise HealthCheckError(
            "HTML muito pequeno",
            f"tamanho={len(html.encode('utf-8'))} bytes (minimo {TAMANHO_MINIMO_BYTES})",
        )

    html_lower = html.lower()
    if "</body>" not in html_lower or "</html>" not in html_lower:
        raise HealthCheckError("HTML truncado", "faltam tags de fechamento </body> ou </html>")

    if not re.search(r"<h1\b[^>]*>.*?</h1>", html, re.IGNORECASE | re.DOTALL):
        raise HealthCheckError("Sem titulo H1", "site nao tem <h1> visivel")

    tem_tel = bool(re.search(r'href\s*=\s*["\']tel:', html, re.IGNORECASE))
    tem_wpp = bool(re.search(r'href\s*=\s*["\'][^"\']*wa\.me/', html, re.IGNORECASE)) or bool(
        re.search(r'href\s*=\s*["\'][^"\']*api\.whatsapp\.com', html, re.IGNORECASE)
    )
    if not (tem_tel or tem_wpp):
        raise HealthCheckError("Sem contato clicavel", "nenhum link tel: ou wa.me/ encontrado")

    schema_match = re.search(
        r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if not schema_match:
        raise HealthCheckError("Sem schema.org", "nenhum bloco JSON-LD encontrado")
    try:
        json.loads(schema_match.group(1).strip())
    except json.JSONDecodeError as e:
        raise HealthCheckError("Schema.org invalido", f"JSON-LD nao parseia: {e}")


def validar_site(url: str, timeout: float = 10.0, tentativas: int = 3, delay: float = 2.0) -> dict:
    """
    Verifica que `url` responde 200 com HTML valido + campos minimos.

    Faz ate `tentativas` HTTP GETs (com `delay` segundos entre) pra cobrir
    propagacao do nginx servir arquivo recem-escrito.

    Em sucesso retorna {"ok": True, "tamanho": int, "status": int}.
    Em falha levanta HealthCheckError com motivo amigavel e detalhe tecnico.
    """
    if not url or not url.startswith(("http://", "https://")):
        raise HealthCheckError("URL invalida", f"recebido: {url!r}")

    ultimo_erro: Exception = HealthCheckError("nao tentou", "")
    response = None
    for i in range(1, tentativas + 1):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(url)
            if response.status_code == 200:
                break
            ultimo_erro = HealthCheckError(
                "HTTP nao-200", f"tentativa {i}: status {response.status_code}"
            )
        except httpx.HTTPError as e:
            ultimo_erro = HealthCheckError("Falha de conexao", f"tentativa {i}: {e}")
        if i < tentativas:
            time.sleep(delay)
    else:
        raise ultimo_erro

    if response is None or response.status_code != 200:
        raise ultimo_erro

    content_type = (response.headers.get("content-type") or "").lower()
    if "text/html" not in content_type:
        raise HealthCheckError("Content-Type errado", f"esperado text/html, veio {content_type!r}")

    html = response.text
    _validar_conteudo(html)
    log.info(f"[HealthCheck] OK {url} ({len(html)} chars)")
    return {"ok": True, "tamanho": len(html), "status": response.status_code}
