"""Server-side cryptographic primitives.

NOTE: message encryption itself happens in the BROWSER. This module provides:
  - argon2id password hashing (User, security codes)
  - HMAC-SHA256 keyed hashing for recipient e-mails (privacy-preserving lookup)
  - AES-256-GCM helpers for at-rest encryption of small server-side secrets
    (e.g. TOTP secrets, backup codes) — keyed with SERVER_ENCRYPTION_KEY
  - constant-time comparisons & secure random helpers
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Optional

from argon2 import PasswordHasher, exceptions
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import current_app

_hasher = PasswordHasher(time_cost=3, memory_cost=64_000, parallelism=2)


# ---------------------------------------------------------------------------
# Password / code hashing
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Argon2id hash of a password (or 6-digit code). Includes salt + params."""
    return _hasher.hash(plain)


def verify_password(stored_hash: str, plain: str) -> bool:
    """Constant-time verify. Returns False (not raises) on any mismatch."""
    try:
        return _hasher.verify(stored_hash, plain)
    except exceptions.VerifyMismatchError:
        return False
    except exceptions.InvalidHash:
        return False
    except exceptions.VerificationError:
        return False


def password_needs_rehash(stored_hash: str) -> bool:
    """Argon2 params change over time; rehash on next login if so."""
    return _hasher.check_needs_rehash(stored_hash)


# ---------------------------------------------------------------------------
# Recipient e-mail hashing — keyed HMAC so leaks can't be cracked offline
# ---------------------------------------------------------------------------


def hash_email(email: str) -> str:
    """Normalize and HMAC an e-mail address.

    Normalization: strip + lowercase. We do NOT do Gmail-style dot-stripping,
    because that subtly changes identity. Operators who want that should layer
    it on top.
    """
    key: bytes = current_app.config["RECIPIENT_HASH_SECRET"]
    normalized = email.strip().lower().encode("utf-8")
    return hmac.new(key, normalized, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Random helpers
# ---------------------------------------------------------------------------


def random_6digit_code() -> str:
    """Cryptographically-random 6-digit numeric code. Returned with leading zeros."""
    return f"{secrets.randbelow(1_000_000):06d}"


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


# ---------------------------------------------------------------------------
# AES-GCM for at-rest server secrets (TOTP secret, backup codes)
# ---------------------------------------------------------------------------


def _derive_key() -> bytes:
    raw: str = current_app.config["SERVER_ENCRYPTION_KEY"]
    # Derive a stable 32-byte key from whatever the operator put in .env.
    return hashlib.sha256(raw.encode()).digest()


def aead_encrypt(plaintext: bytes, *, associated_data: bytes = b"") -> str:
    """Encrypt and return urlsafe-base64(nonce || ciphertext)."""
    aes = AESGCM(_derive_key())
    nonce = secrets.token_bytes(12)
    ct = aes.encrypt(nonce, plaintext, associated_data or None)
    return base64.urlsafe_b64encode(nonce + ct).decode("ascii")


def aead_decrypt(token: str, *, associated_data: bytes = b"") -> bytes:
    """Reverse of aead_encrypt(). Raises cryptography.exceptions.InvalidTag on tamper."""
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    nonce, ct = raw[:12], raw[12:]
    aes = AESGCM(_derive_key())
    return aes.decrypt(nonce, ct, associated_data or None)


# ---------------------------------------------------------------------------
# API-key hashing (separate from passwords — keys have high entropy so SHA-256
# is enough, and we don't want the cost of argon2 on every API request)
# ---------------------------------------------------------------------------


def hash_api_key(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()


# ---------------------------------------------------------------------------
# IP hashing (when we choose to log it for abuse mitigation)
# ---------------------------------------------------------------------------


def hash_ip(ip: Optional[str]) -> Optional[str]:
    if not ip:
        return None
    key: bytes = current_app.config["RECIPIENT_HASH_SECRET"]
    return hmac.new(key, ip.encode(), hashlib.sha256).hexdigest()[:32]
