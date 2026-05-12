"""
Cripto simetrica para segredos por tenant (ex: Anthropic API key BYOK do plano Pro).

A FERNET_KEY vem do .env. Se nao existir, geramos uma e logamos um alerta -
mas em prod ela DEVE ser fixa, senao as keys salvas viram lixo no proximo restart.
"""
import os
from cryptography.fernet import Fernet, InvalidToken


_fernet_singleton = None


def _get_fernet() -> Fernet:
    global _fernet_singleton
    if _fernet_singleton is not None:
        return _fernet_singleton
    key = os.getenv('FERNET_KEY', '').strip()
    if not key:
        # Em dev sem FERNET_KEY: gera uma volatil. Falha cedo em prod via flag.
        if os.getenv('FRALIB_ENV', 'dev') == 'prod':
            raise RuntimeError(
                'FERNET_KEY ausente no .env. '
                'Gere uma com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        key = Fernet.generate_key().decode()
        print('[secrets_crypto] AVISO: FERNET_KEY ausente, usando chave volatil (apenas dev).')
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
