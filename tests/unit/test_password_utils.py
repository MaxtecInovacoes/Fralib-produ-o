"""
test_password_utils.py - Testes unitários para utilitários de senha

Testa as funções de hash e verificação de senha usando bcrypt.
"""
import pytest
import sys
import os

# Adicionar backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from utils.password_utils import hash_password, verify_password, BCRYPT_ROUNDS


@pytest.mark.unit
def test_bcrypt_rounds_configuration():
    """Verifica que bcrypt está configurado com 12 rounds (OWASP)."""
    assert BCRYPT_ROUNDS == 12, "Bcrypt deve usar 12 rounds para segurança adequada"


@pytest.mark.unit
def test_hash_password_generates_valid_hash():
    """Testa que hash_password gera um hash válido."""
    password = "Test123!@#"
    hashed = hash_password(password)

    assert hashed is not None
    assert len(hashed) > 0
    assert hashed != password
    assert hashed.startswith("$2b$")  # Bcrypt hash prefix


@pytest.mark.unit
def test_hash_password_different_hashes():
    """Testa que a mesma senha gera hashes diferentes (salt aleatório)."""
    password = "Test123!@#"
    hash1 = hash_password(password)
    hash2 = hash_password(password)

    assert hash1 != hash2, "Hashes devem ser diferentes devido ao salt aleatório"


@pytest.mark.unit
def test_verify_password_correct():
    """Testa verificação de senha correta."""
    password = "Test123!@#"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


@pytest.mark.unit
def test_verify_password_incorrect():
    """Testa verificação de senha incorreta."""
    password = "Test123!@#"
    wrong_password = "Wrong123!@#"
    hashed = hash_password(password)

    assert verify_password(wrong_password, hashed) is False


@pytest.mark.unit
def test_verify_password_empty():
    """Testa verificação com senha vazia."""
    password = "Test123!@#"
    hashed = hash_password(password)

    assert verify_password("", hashed) is False


@pytest.mark.unit
def test_hash_password_special_characters():
    """Testa hash de senha com caracteres especiais."""
    password = "P@ssw0rd!#$%^&*()"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


@pytest.mark.unit
def test_hash_password_unicode():
    """Testa hash de senha com caracteres unicode."""
    password = "Senha123!çãõ"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


@pytest.mark.unit
def test_hash_password_long():
    """Testa hash de senha longa (até 72 bytes - limite do bcrypt)."""
    password = "A" * 72  # Bcrypt tem limite de 72 bytes
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


@pytest.mark.unit
def test_hash_password_too_long_fails():
    """Testa que senha > 72 bytes lança erro."""
    password = "A" * 100  # Acima do limite do bcrypt

    with pytest.raises(ValueError) as exc_info:
        hash_password(password)

    assert "72 bytes" in str(exc_info.value)


@pytest.mark.unit
def test_verify_password_case_sensitive():
    """Testa que verificação é case-sensitive."""
    password = "Test123!@#"
    hashed = hash_password(password)

    assert verify_password("test123!@#", hashed) is False
    assert verify_password("TEST123!@#", hashed) is False
