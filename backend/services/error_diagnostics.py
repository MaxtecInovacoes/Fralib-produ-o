"""
error_diagnostics.py
====================
Dicionario de erros conhecidos com explicacoes didaticas.

Transforma erros tecnicos em mensagens que humanos entendem.
Cada erro tem: titulo, causa, como evitar, acao automatica aplicada.

Uso:
    from backend.services.error_diagnostics import diagnosticar, classificar

    info = diagnosticar("psycopg2.OperationalError: SSL error")
    print(info["titulo"], info["causa"])
"""

import re
from typing import Any

# Categorias possiveis
CATEGORIAS = {
    "transient": "Erro temporario (timeout, rede) - retry resolve",
    "rate_limit": "Limite de requisicao da API externa atingido",
    "data_quality": "Dados do lead incompletos ou invalidos",
    "code_bug": "Bug no codigo do FraLib",
    "external_api": "API externa (Google, Anthropic, etc) falhou",
    "auth": "Falha de autenticacao/autorizacao",
    "resource": "Recurso esgotado (memoria, disco, conexoes)",
    "unknown": "Erro nao classificado",
}


def classificar(erro_tecnico: str) -> str:
    """Classifica um erro em uma categoria.

    Args:
        erro_tecnico: string do erro (stack trace, mensagem)

    Returns:
        Nome da categoria (transient, rate_limit, etc)
    """
    if not erro_tecnico:
        return "unknown"

    e = erro_tecnico.lower()

    # transient - timeout, rede, SSL
    if any(p in e for p in [
        "ssl syscall", "ssl error", "timeout", "timed out",
        "connection refused", "connection reset", "network is unreachable",
        "temporarily unavailable", "try again", "eof detected",
    ]):
        return "transient"

    # rate_limit
    if any(p in e for p in [
        "429", "rate limit", "too many requests", "quota exceeded",
        "rate_limit", "ratelimit", "tps limit",
    ]):
        return "rate_limit"

    # data_quality - Pydantic, validacao
    if any(p in e for p in [
        "validationerror", "validation error", "input should be",
        "field required", "missing", "valueerror",
    ]):
        return "data_quality"

    # code_bug - ImportError, AttributeError, etc
    if any(p in e for p in [
        "importerror", "cannot import", "attributeerror",
        "nameerror", "typeerror", "keyerror", "indentationerror",
    ]):
        return "code_bug"

    # external_api - HTTP 5xx de terceiros
    if any(p in e for p in [
        "anthropic", "openai", "google maps", "hunter",
        "502 bad gateway", "503 service unavailable", "504 gateway",
        "internal server error", "upstream",
    ]):
        return "external_api"

    # auth
    if any(p in e for p in [
        "401", "403", "unauthorized", "forbidden",
        "invalid api key", "authentication",
    ]):
        return "auth"

    # resource
    if any(p in e for p in [
        "out of memory", "disk full", "no space left",
        "too many connections", "max_connections", "memoryerror",
    ]):
        return "resource"

    return "unknown"


# Dicionario didatico por padrao de erro
DIAGNOSTICOS: list[dict[str, Any]] = [
    {
        "match": r"_enqueue_caio",
        "titulo": "Bug conhecido no modulo de leads",
        "causa": "Funcao renomeada mas algum caller usa nome antigo (ImportError)",
        "como_evitar": "Atualizar codigo para usar funcao nova (ja corrigido em producao)",
        "acao_automatica": "Pular para proximo lead - bug nao bloqueia tenant",
        "severidade": "alta",
        "categoria": "code_bug",
        "icone": "bug",
    },
    {
        "match": r"SSL SYSCALL|EOF detected",
        "titulo": "Banco de dados perdeu conexao",
        "causa": "PostgreSQL fechou a conexao SSL inesperadamente",
        "como_evitar": "Conexao sera restabelecida automaticamente em alguns segundos",
        "acao_automatica": "Retry com backoff aplicado (aguarda 5s)",
        "severidade": "media",
        "categoria": "transient",
        "icone": "database",
    },
    {
        "match": r"LeadQualificado.*Input should be a valid",
        "titulo": "Dados do lead incompletos",
        "causa": "Lead sem campos obrigatorios (Pydantic rejeitou)",
        "como_evitar": "Sistema tenta recuperar via fallback antes de desistir",
        "acao_automatica": "Recuperacao automatica via safe_qualificar()",
        "severidade": "baixa",
        "categoria": "data_quality",
        "icone": "data",
    },
    {
        "match": r"timeout|timed out",
        "titulo": "Operacao demorou demais",
        "causa": "LLM ou API externa nao respondeu no tempo limite",
        "como_evitar": "Retry com tempo maior - geralmente resolve",
        "acao_automatica": "Retry agendado com delay de 30s",
        "severidade": "media",
        "categoria": "transient",
        "icone": "clock",
    },
    {
        "match": r"429|rate limit",
        "titulo": "Limite de requisicoes da API externa",
        "causa": "Anthropic/Google/etc atingiu limite por minuto",
        "como_evitar": "Aguardar 1 minuto e tentar novamente",
        "acao_automatica": "Retry com delay de 60s",
        "severidade": "baixa",
        "categoria": "rate_limit",
        "icone": "speedometer",
    },
    {
        "match": r"502|503|504",
        "titulo": "API externa indisponivel",
        "causa": "Google Maps, Anthropic ou outro servico retornou erro de gateway",
        "como_evitar": "Tentar novamente em alguns minutos",
        "acao_automatica": "Retry com backoff exponencial",
        "severidade": "alta",
        "categoria": "external_api",
        "icone": "cloud-off",
    },
    {
        "match": r"401|unauthorized|invalid api key",
        "titulo": "Chave de API invalida ou expirada",
        "causa": "Token da Anthropic/Google/etc expirou ou foi revogado",
        "como_evitar": "Renovar chave no painel /admin/keys",
        "acao_automatica": "Nenhuma - requer intervencao humana",
        "severidade": "critica",
        "categoria": "auth",
        "icone": "key",
    },
    {
        "match": r"out of memory|memoryerror",
        "titulo": "Memoria do worker esgotada",
        "causa": "Worker tentou alocar mais memoria que o limite (2GB)",
        "como_evitar": "Lead muito grande - pular para o proximo",
        "acao_automatica": "systemd reinicia worker automaticamente",
        "severidade": "media",
        "categoria": "resource",
        "icone": "memory",
    },
    {
        "match": r"too many connections|max_connections",
        "titulo": "Limite de conexoes do PostgreSQL atingido",
        "causa": "Mais de 100 conexoes simultaneas no banco",
        "como_evitar": "Aguardar workers terminarem antes de criar novos",
        "acao_automatica": "Retry com delay de 10s",
        "severidade": "alta",
        "categoria": "resource",
        "icone": "database",
    },
    {
        "match": r"disk full|no space left",
        "titulo": "Disco da VPS cheio",
        "causa": "Espaco em disco esgotado (< 1GB livre)",
        "como_evitar": "Limpar backups antigos ou expandir disco",
        "acao_automatica": "Nenhuma - requer limpeza manual",
        "severidade": "critica",
        "categoria": "resource",
        "icone": "hard-drive",
    },
    {
        "match": r"build_renderer|builder_renderer",
        "titulo": "Builder nao gerou site publicavel",
        "causa": "Vite/React nao conseguiu compilar HTML valido",
        "como_evitar": "Reprocessar geralmente resolve (gerador fica melhor com retry)",
        "acao_automatica": "Retry com prompt regenerado",
        "severidade": "media",
        "categoria": "external_api",
        "icone": "code",
    },
    {
        "match": r"hunter.*no leads|google maps",
        "titulo": "Google Maps nao retornou leads",
        "causa": "Nenhum negocio encontrado para o segmento/cidade",
        "como_evitar": "Tentar outro segmento ou cidade maior",
        "acao_automatica": "Nenhuma - requer nova busca",
        "severidade": "baixa",
        "categoria": "external_api",
        "icone": "search",
    },
]


def diagnosticar(erro_tecnico: str, fase: str | None = None) -> dict[str, Any]:
    """Retorna diagnostico didatico para um erro.

    Args:
        erro_tecnico: string do erro
        fase: fase do pipeline (hunter, caio, etc) - opcional

    Returns:
        dict com titulo, causa, como_evitar, acao_automatica, severidade, categoria, icone
    """
    categoria = classificar(erro_tecnico)

    # Procurar match especifico primeiro
    for diag in DIAGNOSTICOS:
        if re.search(diag["match"], erro_tecnico, re.IGNORECASE):
            return diag

    # Fallback por categoria
    return {
        "titulo": _titulo_generico(categoria, fase),
        "causa": f"Erro do tipo '{categoria}'. Detalhes tecnicos: {erro_tecnico[:120]}",
        "como_evitar": "Sistema vai tentar novamente automaticamente",
        "acao_automatica": _acao_generica(categoria),
        "severidade": _severidade_generica(categoria),
        "categoria": categoria,
        "icone": _icone_generico(categoria),
    }


def _titulo_generico(categoria: str, fase: str | None) -> str:
    if fase:
        return f"Erro na fase {fase}"
    return {
        "transient": "Erro temporario",
        "rate_limit": "Limite de requisicoes",
        "data_quality": "Dados invalidos",
        "code_bug": "Bug no codigo",
        "external_api": "API externa falhou",
        "auth": "Erro de autenticacao",
        "resource": "Recurso esgotado",
        "unknown": "Erro desconhecido",
    }.get(categoria, "Erro")


def _acao_generica(categoria: str) -> str:
    return {
        "transient": "Retry automatico em 5-30 segundos",
        "rate_limit": "Retry com espera de 60 segundos",
        "data_quality": "Tenta recuperar dados via fallback",
        "code_bug": "Pula lead - requer investigacao",
        "external_api": "Retry com backoff",
        "auth": "Requer intervencao humana - renovar chave",
        "resource": "Aguardar recursos liberarem",
        "unknown": "Retry padrao",
    }.get(categoria, "Retry")


def _severidade_generica(categoria: str) -> str:
    return {
        "transient": "baixa",
        "rate_limit": "baixa",
        "data_quality": "baixa",
        "code_bug": "alta",
        "external_api": "media",
        "auth": "critica",
        "resource": "media",
        "unknown": "media",
    }.get(categoria, "media")


def _icone_generico(categoria: str) -> str:
    return {
        "transient": "wifi-off",
        "rate_limit": "speedometer",
        "data_quality": "alert-circle",
        "code_bug": "bug",
        "external_api": "cloud-off",
        "auth": "key",
        "resource": "server",
        "unknown": "help-circle",
    }.get(categoria, "help-circle")


def diagnosticar_em_lote(erros: list[dict]) -> list[dict]:
    """Diagnostica varios erros de uma vez.

    Args:
        erros: lista de dicts com pelo menos 'erro_tecnico' e 'fase'

    Returns:
        Lista com diagnostico adicionado a cada erro
    """
    resultado = []
    for erro in erros:
        erro_copy = dict(erro)
        erro_copy["diagnostico"] = diagnosticar(
            erro.get("erro_tecnico", ""),
            erro.get("fase"),
        )
        resultado.append(erro_copy)
    return resultado


if __name__ == "__main__":
    # CLI: python -m backend.services.error_diagnostics "<erro>"
    import sys
    if len(sys.argv) > 1:
        erro = " ".join(sys.argv[1:])
        diag = diagnosticar(erro)
        print(f"Titulo: {diag['titulo']}")
        print(f"Causa: {diag['causa']}")
        print(f"Como evitar: {diag['como_evitar']}")
        print(f"Acao automatica: {diag['acao_automatica']}")
        print(f"Severidade: {diag['severidade']}")
        print(f"Categoria: {diag['categoria']}")
    else:
        print("Uso: python -m backend.services.error_diagnostics <erro>")