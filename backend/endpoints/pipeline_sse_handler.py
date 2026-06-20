"""
Handler SSE para redirecionamento de logs do pipeline.

Redireciona logs do logger Python para o terminal mágico via SSE,
classificando cada mensagem por tipo (info, error, warning, success, etc.).
"""
import logging


class SSEHandler(logging.Handler):
    """Redireciona logs do logger para o terminal magico via SSE."""

    def emit(self, record):
        msg = self.format(record)
        nivel = record.levelname.lower()
        if nivel == "error":
            tipo = "error"
        elif nivel == "warning":
            tipo = "warning"
        elif (
            "success" in msg.lower()
            or "ok" in msg.lower()
            or "concluido" in msg.lower()
        ):
            tipo = "success"
        elif "caio" in msg.lower() or "qualif" in msg.lower():
            tipo = "caio"
        elif "lead" in msg.lower() or "hunter" in msg.lower():
            tipo = "leads"
        elif "pipeline" in msg.lower():
            tipo = "pipeline"
        else:
            tipo = "info"
        try:
            from backend.endpoints.sse_endpoints import adicionar_log
            adicionar_log(msg, tipo)
        except Exception:
            pass


# Instância global do handler SSE
_sse_handler = SSEHandler()
_sse_handler.setFormatter(logging.Formatter("%(message)s"))
