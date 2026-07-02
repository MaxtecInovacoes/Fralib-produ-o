"""Testes estáticos para a migration 2026_07_phone_health.sql.

Não precisa de DB rodando — valida estrutura, idempotência, e conformidade
com convenções do projeto (PT-BR em comentários, IF NOT EXISTS, índices).
"""

from __future__ import annotations

from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
SQL_PATH = _ROOT / "backend" / "migrations" / "2026_07_phone_health.sql"


@pytest.fixture(scope="module")
def sql_text() -> str:
    return SQL_PATH.read_text(encoding="utf-8")


@pytest.mark.unit
class TestMigrationStructure:
    """Estrutura básica: arquivo existe, tem 3 CREATE TABLE, IF NOT EXISTS, índices."""

    def test_file_exists(self) -> None:
        assert SQL_PATH.is_file(), f"migration não encontrada em {SQL_PATH}"

    def test_has_3_create_tables(self, sql_text: str) -> None:
        n = sql_text.count("CREATE TABLE IF NOT EXISTS")
        assert n == 3, f"esperado 3 CREATE TABLE, encontrado {n}"

    def test_rate_limit_counters_table(self, sql_text: str) -> None:
        assert "CREATE TABLE IF NOT EXISTS rate_limit_counters" in sql_text

    def test_phone_health_score_table(self, sql_text: str) -> None:
        assert "CREATE TABLE IF NOT EXISTS phone_health_score" in sql_text

    def test_phone_health_events_table(self, sql_text: str) -> None:
        assert "CREATE TABLE IF NOT EXISTS phone_health_events" in sql_text

    def test_all_create_index_uses_if_not_exists(self, sql_text: str) -> None:
        # Cada CREATE INDEX deve ter IF NOT EXISTS para idempotência
        creates = [
            line.strip() for line in sql_text.split("\n")
            if line.strip().upper().startswith("CREATE INDEX")
        ]
        assert len(creates) >= 4, f"esperado ≥4 CREATE INDEX, encontrado {len(creates)}"
        for line in creates:
            assert "IF NOT EXISTS" in line.upper(), f"índice sem IF NOT EXISTS: {line}"


@pytest.mark.unit
class TestMigrationConstraints:
    """Constraints CHECK e FK devem estar presentes."""

    def test_rate_limit_kind_check(self, sql_text: str) -> None:
        assert "'flood'" in sql_text
        assert "'daily'" in sql_text
        assert "'cooldown'" in sql_text
        assert "'human_pause'" in sql_text

    def test_phone_health_status_check(self, sql_text: str) -> None:
        for status in ("'healthy'", "'degraded'", "'restricted'", "'banned'"):
            assert status in sql_text, f"status {status} não encontrado no CHECK"

    def test_phone_event_severity_check(self, sql_text: str) -> None:
        for sev in ("'info'", "'warn'", "'error'", "'critical'"):
            assert sev in sql_text, f"severity {sev} não encontrada no CHECK"

    def test_score_range_check(self, sql_text: str) -> None:
        assert "BETWEEN 0 AND 100" in sql_text

    def test_fk_users_referenced(self, sql_text: str) -> None:
        # Todas as 3 tabelas devem referenciar users(id)
        fk_count = sql_text.count("REFERENCES users(id)")
        assert fk_count >= 3, f"esperado ≥3 REFERENCES users(id), encontrado {fk_count}"

    def test_on_delete_cascade(self, sql_text: str) -> None:
        assert "ON DELETE CASCADE" in sql_text


@pytest.mark.unit
class TestMigrationSeedAndTrigger:
    """Seed inicial e trigger de atualizado_em devem existir."""

    def test_seed_insert_phone_health_score(self, sql_text: str) -> None:
        # Seed em phone_health_score para todos os users existentes
        assert "INSERT INTO phone_health_score" in sql_text
        assert "ON CONFLICT (user_id) DO NOTHING" in sql_text

    def test_updated_at_trigger(self, sql_text: str) -> None:
        assert "CREATE OR REPLACE FUNCTION trg_phone_health_updated_at" in sql_text
        assert "CREATE TRIGGER trg_phone_health_updated" in sql_text

    def test_trigger_attaches_to_phone_health_score(self, sql_text: str) -> None:
        assert "BEFORE UPDATE ON phone_health_score" in sql_text


@pytest.mark.unit
class TestMigrationIdempotency:
    """Idempotência: rodar 2x não deve falhar (todas as operações usam IF NOT EXISTS)."""

    def test_no_drop_table_or_view(self, sql_text: str) -> None:
        # Não deve dropar nada (só em testes/reset)
        for forbidden in ("DROP TABLE", "DROP SCHEMA", "DROP VIEW"):
            assert forbidden not in sql_text.upper(), (
                f"{forbidden} não deve aparecer na migration (apenas reset/test fixtures)"
            )

    def test_no_truncate(self, sql_text: str) -> None:
        assert "TRUNCATE" not in sql_text.upper()


@pytest.mark.unit
class TestMigrationPortugueseComments:
    """Convenção do projeto: comentários em PT-BR."""

    def test_has_portuguese_header(self, sql_text: str) -> None:
        # Primeiro bloco de comentário — pode ser /* */ ou -- linhas
        first_lines = "\n".join(line.lstrip() for line in sql_text.split("\n")[:20])
        assert any(
            word in first_lines.lower()
            for word in ("trilha", "saúde", "saude", "migra", "anti-ban", "observabilidad", "substitui", "whatsapp")
        ), f"comentário header não está em PT-BR: {first_lines[:300]}"


@pytest.mark.unit
def test_migration_path_matches_convention() -> None:
    """Arquivo deve estar em backend/migrations/ e seguir naming YYYY_MM_DD_*.sql ou YYYY_MM_*.sql."""
    name = SQL_PATH.name
    assert name.endswith(".sql")
    # Aceita 2026_07_*.sql ou 2026_07_15_*.sql
    assert name.startswith("2026_07"), f"convenção de data não seguida: {name}"