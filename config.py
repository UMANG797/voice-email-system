"""
Configuration for the Voice-Based Email System.
All secrets are read from environment variables (.env file) — nothing is hardcoded.
"""

import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY") or Fernet.generate_key().decode()
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes

    # Database
    DATABASE_PATH = os.path.join(BASE_DIR, "database", "voice_email.db")

    # Encryption key used to encrypt each user's stored app-password (IMAP/SMTP)
    # Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    FERNET_KEY = os.environ.get("FERNET_KEY")
    RESEND_API_KEY = os.environment.get("RESEND_API_KEY")

    # Default mail servers (Gmail). Users can override per-account if needed.
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
    IMAP_PORT = int(os.environ.get("IMAP_PORT", 993))

    # Rate limiting for login attempts
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_SECONDS = 300
