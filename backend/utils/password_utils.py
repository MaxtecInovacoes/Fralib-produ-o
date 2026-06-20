"""
Password Hashing Utilities - FraLib OS

Funções para hash e verificação de senhas usando bcrypt com 12 rounds.
"""
import bcrypt

# Configuração de segurança: 12 rounds (recomendado OWASP)
BCRYPT_ROUNDS = 12
BCRYPT_MAX_BYTES = 72


def _validar_tamanho_bcrypt(plain_password: str) -> bytes:
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > BCRYPT_MAX_BYTES:
        raise ValueError("Senha excede o limite seguro de 72 bytes do bcrypt")
    return password_bytes


def hash_password(plain_password: str) -> str:
    """
    Gera hash de senha usando bcrypt com 12 rounds.

    Args:
        plain_password: Senha em texto plano

    Returns:
        Hash da senha (string)
    """
    password_bytes = _validar_tamanho_bcrypt(plain_password)
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
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
    try:
        password_bytes = _validar_tamanho_bcrypt(plain_password)
    except ValueError:
        return False
    return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
