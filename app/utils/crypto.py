from cryptography.fernet import Fernet
from app.core.config import settings

FERNET_KEY = settings.credential_encryption_key

try:
    fernet = Fernet(FERNET_KEY.encode())
except Exception as e:
    raise RuntimeError("Invalid Fernet key format") from e


def encrypt_token(token: str) -> str:
    """
    Encrypt a plaintext token and return base64 string
    """
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(token: str) -> str:
    """
    Decrypt an encrypted token back to plaintext
    """
    return fernet.decrypt(token.encode()).decode()
