"""Symmetric encryption for secrets that must live in the database.

Live payment credentials (a tenant's Pagopar private key, a consuming app's
callback secret) cannot be read from process env — they are per tenant and
operators add them at runtime. They must therefore be stored, and storing a
live payment secret in plaintext is not acceptable.

Fernet (AES-128-CBC + HMAC-SHA256, from `cryptography`) gives authenticated
encryption with a single symmetric key held ONLY in the deployment
environment as `CREDENTIALS_ENCRYPTION_KEY`. A database dump therefore
leaks ciphertext, not merchant credentials.

Fails LOUDLY (`ImproperlyConfigured`) when the key is unset: a service that
cannot encrypt must not silently fall back to plaintext.

Key rotation: Fernet tokens are self-describing, so rotation means
re-encrypting every stored secret with the new key (decrypt with the old,
encrypt with the new) in a one-off management step. There is no key-id
embedded here on purpose — a second key would be a second thing to leak.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _fernet():
    from cryptography.fernet import Fernet

    key = getattr(settings, "CREDENTIALS_ENCRYPTION_KEY", "") or ""
    if not key:
        raise ImproperlyConfigured(
            "CREDENTIALS_ENCRYPTION_KEY is not set; refusing to handle stored secrets. "
            "Generate one with: python -c "
            "'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    try:
        return Fernet(key.encode("utf-8") if isinstance(key, str) else key)
    except Exception as exc:  # malformed key is a deployment error, not a runtime one
        raise ImproperlyConfigured(
            f"CREDENTIALS_ENCRYPTION_KEY is not a valid Fernet key: {exc}"
        ) from exc

def encrypt_secret(plaintext: str) -> str:
    """Return a Fernet token for `plaintext`. Empty input stays empty (means "unset")."""
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")

def decrypt_secret(ciphertext: str) -> str:
    """Return the plaintext behind a Fernet token. Empty input stays empty."""
    if not ciphertext:
        return ""
    return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
