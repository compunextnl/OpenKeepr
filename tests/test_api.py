from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _seed_user_with_key(app):
    """Create a user + API key directly via the ORM."""
    from app.extensions import db
    from app.models.api_key import ApiKey, generate_api_key
    from app.models.user import User
    from app.services.crypto import hash_password

    with app.app_context():
        u = User(email="apiuser@example.com", password_hash=hash_password("x" * 12))
        db.session.add(u)
        db.session.flush()
        plain, prefix, h = generate_api_key()
        key = ApiKey(
            user_id=u.id, label="test", prefix=prefix, key_hash=h,
            scopes="messages:write messages:read feedback:write",
        )
        db.session.add(key)
        db.session.commit()
        return plain, u.id


def test_api_create_and_get_message(app, client):
    plain_key, _ = _seed_user_with_key(app)
    headers = {"Authorization": f"Bearer {plain_key}"}

    key = AESGCM.generate_key(bit_length=256)
    iv = os.urandom(12); salt = os.urandom(16)
    ct = AESGCM(key).encrypt(iv, b"hello api", None)
    payload = {
        "ciphertext_b64": base64.b64encode(ct).decode(),
        "iv_b64": base64.b64encode(iv).decode(),
        "salt_b64": base64.b64encode(salt).decode(),
        "expires_in_hours": 2,
        "max_opens": 1,
        "use_security_code": True,
    }
    r = client.post("/api/v1/messages", json=payload, headers=headers)
    assert r.status_code == 201, r.data
    body = r.get_json()
    pid = body["id"]
    assert body["security_code"] is not None

    r = client.get(f"/api/v1/messages/{pid}", headers=headers)
    assert r.status_code == 200
    meta = r.get_json()
    assert meta["id"] == pid
    assert meta["opens"] == 0


def test_api_requires_key(client):
    r = client.post("/api/v1/messages", json={})
    assert r.status_code == 401
