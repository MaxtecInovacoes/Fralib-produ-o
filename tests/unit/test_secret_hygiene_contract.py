from scripts import check_secret_hygiene


def _matches_any_secret_pattern(text: str) -> bool:
    return any(pattern.search(text) for pattern in check_secret_hygiene.SECRET_PATTERNS)


def test_secret_hygiene_blocks_database_urls_with_passwords():
    assert _matches_any_secret_pattern(
        "DATABASE_URL=postgresql://user" + ":password@localhost:5433/fralib_db"
    )


def test_secret_hygiene_blocks_jwt_secrets():
    assert _matches_any_secret_pattern("JWT_SECRET_KEY=" + "c" * 32)


def test_secret_hygiene_blocks_local_env_backups():
    assert "**/.env.backup*" in check_secret_hygiene.SENSITIVE_BACKUP_GLOBS


def test_secret_hygiene_blocks_tracked_database_suffixes():
    assert ".db" in check_secret_hygiene.BLOCKED_TRACKED_SUFFIXES


def test_secret_hygiene_allows_known_templates_but_not_real_files():
    text = "JWT_SECRET_KEY=" + "sua_chave_super_secreta_aqui_minimo_32_bytes"
    match = check_secret_hygiene.SECRET_PATTERNS[-2].search(text)

    assert check_secret_hygiene._allowed_placeholder(".env.example", text, match)
    assert not check_secret_hygiene._allowed_placeholder("backend/config.py", text, match)
