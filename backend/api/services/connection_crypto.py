"""Optional Fernet encryption for database connection strings at rest."""
from __future__ import annotations

import os


def _fernet():
    key = os.getenv("FERNET_KEY", "").strip()
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        return None


def encrypt_credentials(plain: str) -> str:
    if not plain:
        return plain
    f = _fernet()
    if not f:
        return plain
    return "enc:" + f.encrypt(plain.encode()).decode()


def decrypt_credentials(stored: str) -> str:
    if not stored or not str(stored).startswith("enc:"):
        return stored or ""
    f = _fernet()
    if not f:
        raise ValueError("Connection is encrypted but FERNET_KEY is not configured on the server.")
    return f.decrypt(stored[4:].encode()).decode()


def maybe_decrypt_connection_row(row: dict) -> dict:
    if not row:
        return row
    out = dict(row)
    cred = out.get("credentials")
    if cred:
        out["credentials"] = decrypt_credentials(cred)
    return out
