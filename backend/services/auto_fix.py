"""
auto_fix.py
============
Sistema de auto-fix inteligente por categoria de erro.

Quando uma falha e registrada, ANTES de desistir, tenta corrigir
baseado no padrao do erro. Cada categoria tem sua estrategia:

- transient (timeout/rede): retry com backoff exponencial
- rate_limit (429/503): espera 60s e tenta de novo
- data_quality (validacao): ja existe safe_qualificar() como fallback
- code_bug (ImportError): pula lead - requer intervencao humana
- external_api (5xx): retry com provider alternativo

LIMITES:
- Max 1 tentativa extra por falha (evita loop infinito)
- Se ja tentou 3x via job_queue, nao tenta mais
- Tudo logado pra auditoria
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

from backend.services.error_diagnostics import classificar

logger = logging.getLogger("uvicorn.auto_fix")

# Configuracao via env vars (para desabilitar em emergencia)
AUTO_FIX_ENABLED = os.getenv("FRALIB_AUTO_FIX_DISABLED", "0") != "1"
MAX_AUTO_FIX_ATTEMPTS = int(os.getenv("FRALIB_AUTO_FIX_MAX_ATTEMPTS", "1"))


@dataclass
class FixResult:
    """Resultado de uma tentativa de auto-fix."""
    sucesso: bool
    categoria: str
    acao: str
    mensagem: str
    proxima_tentativa_em_segundos: Optional[int] = None
    metadata: dict = None

    def to_dict(self) -> dict:
        return {
            "sucesso": self.sucesso,
            "categoria": self.categoria,
            "acao": self.acao,
            "mensagem": self.mensagem,
            "proxima_tentativa_em_segundos": self.proxima_tentativa_em_segundos,
            "metadata": self.metadata or {},
        }


def tentar_auto_fix(
    erro_tecnico: str,
    tentativas_anteriores: int = 0,
    max_tentativas_total: int = 3,
    metadata_extras: Optional[dict] = None,
) -> FixResult:
    """Tenta corrigir uma falha baseado no padrao do erro.

    Args:
        erro_tecnico: mensagem do erro
        tentativas_anteriores: quantas vezes ja tentou via job_queue
        max_tentativas_total: maximo total permitido (job_queue + auto_fix)
        metadata_extras: contexto adicional (lead_id, fase, etc)

    Returns:
        FixResult com decisao do que fazer
    """
    if not AUTO_FIX_ENABLED:
        return FixResult(
            sucesso=False,
            categoria="disabled",
            acao="none",
            mensagem="Auto-fix desabilitado via FRALIB_AUTO_FIX_DISABLED=1",
        )

    categoria = classificar(erro_tecnico)
    total_tentativas = tentativas_anteriores + MAX_AUTO_FIX_ATTEMPTS

    # Se ja tentou maximo, nao tenta mais
    if total_tentativas > max_tentativas_total:
        return FixResult(
            sucesso=False,
            categoria=categoria,
            acao="giveup",
            mensagem=f"Limite de {max_tentativas_total} tentativas atingido (ja tentou {tentativas_anteriores})",
        )

    # Dispatcher por categoria
    handler = _HANDLERS.get(categoria, _handler_unknown)
    return handler(erro_tecnico, tentativas_anteriores, metadata_extras or {})


def _handler_transient(erro: str, tentativas: int, meta: dict) -> FixResult:
    """Erros temporarios: retry com backoff exponencial."""
    delay = 5 * (2 ** tentativas)  # 5s, 10s, 20s
    return FixResult(
        sucesso=True,
        categoria="transient",
        acao="retry_backoff",
        mensagem=f"Erro temporario detectado. Retry em {delay}s (backoff exponencial).",
        proxima_tentativa_em_segundos=delay,
        metadata={"backoff": "exponencial", "delay": delay},
    )


def _handler_rate_limit(erro: str, tentativas: int, meta: dict) -> FixResult:
    """Rate limit: espera 60s e tenta de novo."""
    return FixResult(
        sucesso=True,
        categoria="rate_limit",
        acao="wait_and_retry",
        mensagem="Limite de requisicoes atingido. Retry em 60s.",
        proxima_tentativa_em_segundos=60,
        metadata={"espera": "60s", "motivo": "rate_limit"},
    )


def _handler_data_quality(erro: str, tentativas: int, meta: dict) -> FixResult:
    """Dados invalidos: ja temos safe_qualificar() no codigo."""
    return FixResult(
        sucesso=True,
        categoria="data_quality",
        acao="recuperar_dados",
        mensagem="Tentando recuperar dados via fallback (safe_qualificar).",
        proxima_tentativa_em_segundos=0,  # imediato
        metadata={"fallback": "safe_qualificar", "estrategia": "recuperar"},
    )


def _handler_code_bug(erro: str, tentativas: int, meta: dict) -> FixResult:
    """Bug no codigo: pula lead, nao tenta corrigir."""
    return FixResult(
        sucesso=False,
        categoria="code_bug",
        acao="skip_lead",
        mensagem="Bug no codigo detectado. Lead sera pulado - requer investigacao humana.",
        proxima_tentativa_em_segundos=None,
        metadata={"requer_intervencao": True, "acao_humana": "investigar_bug"},
    )


def _handler_external_api(erro: str, tentativas: int, meta: dict) -> FixResult:
    """API externa falhou: retry com backoff."""
    delay = 30 * (tentativas + 1)  # 30s, 60s, 90s
    return FixResult(
        sucesso=True,
        categoria="external_api",
        acao="retry_provider",
        mensagem=f"API externa indisponivel. Retry em {delay}s com mesmo provider.",
        proxima_tentativa_em_segundos=delay,
        metadata={"provider": meta.get("provider", "unknown"), "delay": delay},
    )


def _handler_auth(erro: str, tentativas: int, meta: dict) -> FixResult:
    """Erro de auth: requer intervencao humana."""
    return FixResult(
        sucesso=False,
        categoria="auth",
        acao="none",
        mensagem="Erro de autenticacao detectado. Renovar chave da API no painel admin.",
        proxima_tentativa_em_segundos=None,
        metadata={"requer_intervencao": True, "acao_humana": "renovar_chave"},
    )


def _handler_resource(erro: str, tentativas: int, meta: dict) -> FixResult:
    """Recurso esgotado: espera e tenta."""
    return FixResult(
        sucesso=True,
        categoria="resource",
        acao="wait_resource",
        mensagem="Recurso (memoria/conexoes) esgotado. Retry em 20s.",
        proxima_tentativa_em_segundos=20,
        metadata={"delay": 20},
    )


def _handler_unknown(erro: str, tentativas: int, meta: dict) -> FixResult:
    """Erro nao classificado: retry conservador."""
    return FixResult(
        sucesso=False,
        categoria="unknown",
        acao="log_only",
        mensagem="Erro nao classificado. Logado para investigacao - sem auto-fix.",
        proxima_tentativa_em_segundos=None,
        metadata={"requer_investigacao": True},
    )


_HANDLERS = {
    "transient": _handler_transient,
    "rate_limit": _handler_rate_limit,
    "data_quality": _handler_data_quality,
    "code_bug": _handler_code_bug,
    "external_api": _handler_external_api,
    "auth": _handler_auth,
    "resource": _handler_resource,
}


def registrar_resultado(falha_id: int, resultado: FixResult) -> None:
    """Registra resultado do auto-fix no log para auditoria."""
    logger.info(
        f"[auto_fix] falha_id={falha_id} categoria={resultado.categoria} "
        f"sucesso={resultado.sucesso} acao={resultado.acao} "
        f"proxima_em={resultado.proxima_tentativa_em_segundos}s"
    )


if __name__ == "__main__":
    # CLI: python -m backend.services.auto_fix "<erro>"
    import sys
    if len(sys.argv) > 1:
        erro = " ".join(sys.argv[1:])
        result = tentar_auto_fix(erro, tentativas_anteriores=0)
        print(f"Sucesso: {result.sucesso}")
        print(f"Categoria: {result.categoria}")
        print(f"Acao: {result.acao}")
        print(f"Mensagem: {result.mensagem}")
        print(f"Proxima tentativa em: {result.proxima_tentativa_em_segundos}s")
    else:
        print("Uso: python -m backend.services.auto_fix <erro>")