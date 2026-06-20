"""
Criptografia simétrica para segredos por tenant (ex: Anthropic API key BYOK do plano Pro).

A FERNET_KEY é OBRIGATÓRIA em produção. Nunca use fallback derivado do JWT_SECRET_KEY
em produção - isso compromete a segurança de todas as chaves criptografadas.
"""
import os
import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken


_fernet_singleton = None


def _get_fernet() -> Fernet:
    global _fernet_singleton
    if _fernet_singleton is not None:
        return _fernet_singleton

    key = os.getenv('FERNET_KEY', '').strip()
    if not key:
        env = os.getenv('FRALIB_ENV', 'dev')
        if env == 'prod':
            # PRODUÇÃO: FERNET_KEY é obrigatório
            raise RuntimeError(
                'FERNET_KEY ausente no .env (PRODUÇÃO). '
                'Gere uma com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        # DEV: Usa chave volátil (avisa no log)
        key = Fernet.generate_key().decode()
        print('[secrets_crypto] AVISO: FERNET_KEY ausente em DEV, usando chave volátil.')

    _fernet_singleton = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet_singleton


def encriptar(plaintext: str) -> str:
    if not plaintext:
        return ''
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decriptar(ciphertext: str) -> str:
    if not ciphertext:
        return ''
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        # FERNET_KEY trocada ou dado corrompido. Nao vaza nada.
        return ''


def mascarar_key(plaintext: str) -> str:
    """Mostra os ultimos 4 chars para o cliente confirmar visualmente."""
    if not plaintext or len(plaintext) < 8:
        return ''
    return plaintext[:4] + '...' + plaintext[-4:]
