from cryptography.fernet import Fernet
from app.config import settings

# Fernet guarantees that encrypted data cannot be read or manipulated without the key [citation:4][citation:18]
fernet = Fernet(settings.fernet_key.encode())


def encrypt_url(url: str) -> bytes:
    """Encrypt a database connection URL for storage at rest."""
    return fernet.encrypt(url.encode())


def decrypt_url(encrypted: bytes) -> str:
    """Decrypt a stored connection URL."""
    return fernet.decrypt(encrypted).decode()
