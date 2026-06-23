"""HTML sanitizer — fecha tags de bloco abertas mas nao fechadas.

Usa html.parser.HTMLParser da stdlib para detectar tags abertas
(h2, h3, section, div, p, article, main, header, footer, nav, aside)
que ficaram penduradas no HTML gerado pelo LLM OpenUI.

O bug classico: o LLM gera `<h2>Im\nTema.</h2>` mas esquece o
`</h2>`. Depois, o motion_runtime ou LGPD script e injetado antes
do `</h2>` perdido, fazendo o navegador renderizar o `<script>`
dentro do `<h2>` e quebrar o layout.

Esta funcao fecha essas tags orfas antes de qualquer injecao de script.
Idempotente: nao altera HTML ja bem-formado.

Uso:
    from backend.services.html_sanitizer import close_unclosed_block_tags
    cleaned = close_unclosed_block_tags(html)
"""

from __future__ import annotations

import re
from html.parser import HTMLParser


# Tags de bloco que PODEM ficar abertas e quebrar o layout
BLOCK_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "section", "div", "article", "main",
    "header", "footer", "nav", "aside",
    "p", "blockquote", "figure", "details", "summary",
    "ul", "ol", "li",
}

# Tags void (nao precisam fechar)
VOID_TAGS = {
    "br", "hr", "img", "input", "meta", "link",
    "source", "area", "base", "col", "embed", "param", "track", "wbr",
}


class _TagStackParser(HTMLParser):
    """Captura tags de bloco abertas mas nao fechadas ate </body>.

    Tambem detecta self-closing tags (void).
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []  # (tag_lower, position)
        self.last_void_pos: int = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        t = tag.lower()
        if t in VOID_TAGS:
            self.last_void_pos = self.getpos()[0]
            return
        if t in BLOCK_TAGS:
            self.stack.append((t, self.getpos()[0]))

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in BLOCK_TAGS:
            # Pop ate achar tag correspondente
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == t:
                    del self.stack[i:]
                    return

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        # self-closing (XHTML) — ignora
        return


def _find_block_tag_positions(html: str) -> list[tuple[int, int, str]]:
    """Retorna lista de (start_pos, end_pos, tag) para tags de bloco.

    Usado para fechar orfaos antes de </body>.
    """
    parser = _TagStackParser()
    try:
        parser.feed(html)
    except Exception:
        # HTML malformado — retorna lista vazia (fail-safe)
        return []
    return [(pos, pos, tag) for tag, pos in parser.stack]


def close_unclosed_block_tags(html: str) -> str:
    """Fecha tags de bloco abertas mas nao fechadas antes de </body>.

    Estrategia:
    1. Parse com HTMLParser para detectar stack de tags abertas
    2. Em </body>, fecha as tags orfas na ordem inversa (LIFO)
    3. Tambem fecha orfaos imediatamente antes de <script id="fralib-...">
       injetados pelo deploy (defesa especifica para o bug "Im Tema")

    Idempotente: rodar 2x nao quebra HTML bem-formado.
    """
    if not html or "</body>" not in html:
        return html

    # Encontrar tags orfas via parser
    parser = _TagStackParser()
    try:
        parser.feed(html)
    except Exception:
        return html

    orfaos = parser.stack
    if not orfaos:
        return html

    # Mapear tags para seus </tag> correspondentes
    closing_tags = "".join(f"</{tag}>" for tag, _pos in reversed(orfaos))

    # Inserir antes de </body>
    html = html.replace("</body>", closing_tags + "\n</body>", 1)

    return html


def close_unclosed_before_script_injection(html: str, script_ids: list[str] | None = None) -> str:
    """Defesa especifica: fecha tags orfas ANTES de scripts injetados.

    Usado antes de injetar motion_runtime / LGPD runtime.
    """
    if not html:
        return html

    script_ids = script_ids or ["fralib-motion-runtime", "fralib-lgpd-runtime"]
    parser = _TagStackParser()
    try:
        parser.feed(html)
    except Exception:
        return html

    if not parser.stack:
        return html

    # Encontrar posicoes dos scripts injetados
    script_positions: list[int] = []
    for sid in script_ids:
        m = re.search(rf'<script[^>]*id=["\']?{re.escape(sid)}', html)
        if m:
            script_positions.append(m.start())

    if not script_positions:
        # Sem scripts injetados ainda — fecha orfaos antes de </body>
        return close_unclosed_block_tags(html)

    # Encontrar primeiro script injetado
    first_script = min(script_positions)

    # Stack no momento do script = tudo entre parser.last_void_pos e first_script
    # Simplificacao: fecha TODOS os orfaos antes do primeiro script
    orfaos = parser.stack
    closing_tags = "".join(f"</{tag}>" for tag, _pos in reversed(orfaos))

    return html[:first_script] + closing_tags + html[first_script:]


__all__ = [
    "close_unclosed_block_tags",
    "close_unclosed_before_script_injection",
    "BLOCK_TAGS",
]
