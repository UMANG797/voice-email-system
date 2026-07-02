"""
Encrypts/decrypts each user's mail app-password before storing it in SQLite.
Never store SMTP/IMAP passwords in plain text.
"""

from cryptography.fernet import Fernet
from config import Config


def _get_fernet():
    key = Config.FERNET_KEY
    if not key:
        raise RuntimeError(
            "FERNET_KEY is not set in your .env file. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode())


def encrypt_value(plain_text: str) -> str:
    f = _get_fernet()
    return f.encrypt(plain_text.encode()).decode()


def decrypt_value(encrypted_text: str) -> str:
    f = _get_fernet()
    return f.decrypt(encrypted_text.encode()).decode()
