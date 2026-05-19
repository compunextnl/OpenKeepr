from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _make_payload(plaintext: bytes = b"hello secret"):
    key = AESGCM.generate_key(bit_length=256)
    iv = os.urandom(12)
    salt = os.urandom(16)
    ct = AESGCM(key).encrypt(iv, plaintext, None)
    return key, {
        "ciphertext_b64": base64.b64encode(ct).decode(),
        "iv_b64": base64.b64encode(iv).decode(),
        "salt_b64": base64.b64encode(salt).decode(),
    }


def test_create_anonymous_returns_security_code(client):
    _, payload = _make_payload()
    payload.update({"expires_in_hours": 1, "max_opens": 1, "use_security_code": True})
    r = client.post("/m/create", json=payload)
    assert r.status_code == 201, r.data
    body = r.get_json()
    assert "public_id" in body
    assert "url" in body
    assert body["security_code"] is not None
    assert len(body["security_code"]) == 6


def test_create_with_recipients_no_code(client):
    _, payload = _make_payload()
    payload.update({"recipients": ["alice@example.com"], "expires_in_hours": 1})
    r = client.post("/m/create", json=payload)
    body = r.get_json()
    assert r.status_code == 201, body
    assert body["security_code"] is None
    assert body["requires_email"] is True


def test_reveal_with_security_code(client):
    _, payload = _make_payload(b"top secret")
    payload.update({"expires_in_hours": 1, "use_security_code": True})
    r = client.post("/m/create", json=payload)
    body = r.get_json()
    pid = body["public_id"]
    code = body["security_code"]

    # Wrong code → 403
    r = client.post(f"/m/{pid}/reveal", json={"code": "000000"})
    assert r.status_code == 403

    # Correct code → ciphertext returned
    r = client.post(f"/m/{pid}/reveal", json={"code": code})
    assert r.status_code == 200
    rev = r.get_json()
    assert "ciphertext_b64" in rev and "iv_b64" in rev


def test_view_404_when_missing(client):
    r = client.get("/m/does-not-exist")
    assert r.status_code == 404


def test_oversize_rejected(client):
    # 1 MB ciphertext — way over the 256KB default cap
    _, payload = _make_payload(b"x" * (300 * 1024))
    payload.update({"expires_in_hours": 1, "use_security_code": True})
    r = client.post("/m/create", json=payload)
    assert r.status_code == 413
