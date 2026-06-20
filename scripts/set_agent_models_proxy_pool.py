"""Set FraLib agents to the canonical LiteLLM proxy pool aliases."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]

AGENT_CONFIGS: dict[str, tuple[str, float, int]] = {
    "agente_nicho": ("fralib-fast-cheap", 0.30, 4000),
    "agente_variacao": ("fralib-json-repair", 0.35, 1500),
    "validador": ("fralib-json-repair", 0.20, 2000),
    "arquiteto_mestre": ("fralib-agent-balanced", 0.35, 6000),
    "designer_prd": ("fralib-agent-balanced", 0.35, 6000),
    "curadoria": ("fralib-agent-balanced", 0.40, 3000),
    "jina_intel": ("fralib-research", 0.30, 3500),
    "franz": ("fralib-agent-balanced", 0.45, 1200),
    "builder_renderer": ("fralib-builder-strong", 0.55, 36000),
}


def _load_env() -> None:
    for candidate in (ROOT / ".env", ROOT / "backend" / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=True)
            return
    load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplica aliases canonicos LiteLLM aos agentes")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    _load_env()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL nao configurado")

    if not args.apply:
        print("DRY RUN: aplicaria agent_model_configs:")
        for agent, (model, temp, max_tokens) in AGENT_CONFIGS.items():
            print(f"- {agent}: provider=anthropic model={model} temp={temp} max_tokens={max_tokens}")
        return

    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS agent_model_configs (
                    agent_name VARCHAR(80) PRIMARY KEY,
                    provider VARCHAR(50) NOT NULL DEFAULT 'anthropic',
                    model_id VARCHAR(120) NOT NULL,
                    fallback_provider VARCHAR(50),
                    fallback_model_id VARCHAR(120),
                    temperature NUMERIC(4,2),
                    top_p NUMERIC(4,2),
                    max_tokens INTEGER,
                    enabled BOOLEAN DEFAULT TRUE,
                    atualizado_em TIMESTAMP DEFAULT NOW(),
                    atualizado_por INTEGER
                )
                """
            )
        )
        for agent_name, (model_id, temperature, max_tokens) in AGENT_CONFIGS.items():
            conn.execute(
                text(
                    """
                    INSERT INTO agent_model_configs (
                        agent_name, provider, model_id, fallback_provider,
                        fallback_model_id, temperature, max_tokens, enabled,
                        atualizado_em
                    )
                    VALUES (
                        :agent_name, 'anthropic', :model_id,
                        NULL, NULL, :temperature, :max_tokens, TRUE, NOW()
                    )
                    ON CONFLICT (agent_name) DO UPDATE SET
                        provider = EXCLUDED.provider,
                        model_id = EXCLUDED.model_id,
                        fallback_provider = NULL,
                        fallback_model_id = NULL,
                        temperature = EXCLUDED.temperature,
                        max_tokens = EXCLUDED.max_tokens,
                        enabled = TRUE,
                        atualizado_em = NOW()
                    """
                ),
                {
                    "agent_name": agent_name,
                    "model_id": model_id,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
        conn.execute(text("DELETE FROM agent_model_configs WHERE lower(agent_name) = 'bryan'"))

    print(f"agent_model_configs atualizado: {len(AGENT_CONFIGS)} agente(s)")


if __name__ == "__main__":
    main()
