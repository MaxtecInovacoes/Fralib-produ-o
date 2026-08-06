"""
Validação de variáveis de ambiente na inicialização.
Dispara erro claro se faltar qualquer variável essencial.
"""

import os
import sys
from typing import List, Tuple

# Variáveis obrigatórias (nome, descrição, required)
REQUIRED_ENV_VARS: List[Tuple[str, str, bool]] = [
    ("DATABASE_URL", "URL de conexão com PostgreSQL", True),
    ("JWT_SECRET_KEY", "Chave secreta para assinar JWTs", True),
    ("FRALIB_SITES_DIR", "Diretório para salvar sites gerados", True),
    ("REDIS_URL", "URL do Redis (cache/rate-limit)", False),  # opcional mas recomendado
    ("OPENAI_API_KEY", "API key da OpenAI (ou ANTHROPIC_API_KEY)", False),
    ("ANTHROPIC_API_KEY", "API key da Anthropic", False),
    ("SENTRY_DSN", "DSN do Sentry para captura de erros", False),
]

# Variáveis opcionais com defaults seguros
OPTIONAL_ENV_VARS = {
    "LOG_LEVEL": ("INFO", "Nível de log: DEBUG, INFO, WARNING, ERROR"),
    "LOG_FILE": ("", "Caminho para arquivo de log (vazio = console apenas)"),
    "ENVIRONMENT": ("development", "Ambiente: development, staging, production"),
    "SENTRY_ENVIRONMENT": ("", "Override do ambiente no Sentry"),
    "SENTRY_TRACES_SAMPLE_RATE": ("0.1", "Taxa de amostragem de traces (0.0 a 1.0)"),
    "FRALIB_SKIP_HTML_QUALITY_GATE": ("0", "0=pula QA HTML, 1=executa QA"),
    "FRALIB_BUILDER_AUTO_APPROVE": ("0", "1=auto-aprova HTML, 0=requer aprovação manual"),
    "FRALIB_BUILDER_ENGINE": ("openui", "Engine builder: openui, liam"),
    "MAX_PIPELINES_GLOBAL": ("4", "Máximo de pipelines paralelas"),
    "WORKER_POLL_INTERVAL": ("2", "Intervalo de poll do worker (segundos)"),
}


def validate_env() -> List[str]:
    """
    Valida variáveis de ambiente.
    Retorna lista de erros (vazia = tudo OK).
    """
    errors = []
    warnings = []

    for var_name, description, required in REQUIRED_ENV_VARS:
        value = os.getenv(var_name, "").strip()
        if required and not value:
            errors.append(f"VARIÁVEL OBRIGATÓRIA AUSENTE: {var_name} — {description}")
        elif not value and not required:
            warnings.append(f"Opcional não definida: {var_name} — {description}")

    # Validar que pelo menos uma LLM key está presente
    has_llm = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not has_llm:
        errors.append("Nenhuma LLM configurada: defina OPENAI_API_KEY ou ANTHROPIC_API_KEY")

    # Log warnings
    for w in warnings:
        print(f"[EnvValidator] ⚠️  {w}")

    # Log errors
    for e in errors:
        print(f"[EnvValidator] ❌ {e}")

    return errors


def print_env_summary() -> None:
    """Imprime resumo do ambiente (para logs de inicialização)."""
    env = os.getenv("ENVIRONMENT", "development")
    print(f"\n{'='*60}")
    print(f"  Fralib — Inicialização do Sistema")
    print(f"  Ambiente: {env}")
    print(f"  Host: {os.uname().nodename if hasattr(os, 'uname') else 'unknown'}")
    print(f"  PID: {os.getpid()}")
    print(f"{'='*60}")

    for var_name, (default, description) in OPTIONAL_ENV_VARS.items():
        value = os.getenv(var_name, default)
        # Mascarar valores sensíveis
        display = value if not any(s in var_name.upper() for s in ["SECRET", "KEY", "PASSWORD", "DSN"]) else "***"
        print(f"  {var_name}={display}  # {description}")

    print(f"{'='*60}\n")


def check_and_fail() -> None:
    """
    Executa validação e falha se houver erros críticos.
    Chamado na inicialização do servidor.
    """
    errors = validate_env()
    if errors:
        print("\n" + "=" * 60)
        print("  FALHA NA INICIALIZAÇÃO — Variáveis de ambiente faltando")
        print("=" * 60)
        for e in errors:
            print(f"  ❌ {e}")
        print("=" * 60)
        print("\nCorrija o arquivo .env e reinicie o servidor.\n")
        sys.exit(1)

    print_env_summary()
