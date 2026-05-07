"""
Password Hashing Utilities - FraLib OS

Funções para hash e verificação de senhas usando bcrypt com 12 rounds.
"""
import bcrypt

# Configuração de segurança: 12 rounds (recomendado OWASP)
BCRYPT_ROUNDS = 12


def hash_password(plain_password: str) -> str:
    """
    Gera hash de senha usando bcrypt com 12 rounds.

    Args:
        plain_password: Senha em texto plano

    Returns:
        Hash da senha (string)
    """
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha em texto plano corresponde ao hash.

    Args:
        plain_password: Senha em texto plano
        hashed_password: Hash da senha

    Returns:
        True se a senha está correta, False caso contrário
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )
