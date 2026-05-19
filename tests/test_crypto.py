from __future__ import annotations


def test_password_hash_and_verify(app):
    with app.app_context():
        from app.services.crypto import hash_password, verify_password

        h = hash_password("correct-horse-battery-staple")
        assert verify_password(h, "correct-horse-battery-staple") is True
        assert verify_password(h, "wrong") is False


def test_hash_email_is_deterministic_and_keyed(app):
    with app.app_context():
        from app.services.crypto import hash_email

        a = hash_email("alice@example.com")
        b = hash_email("ALICE@example.com  ")  # normalisation
        c = hash_email("bob@example.com")
        assert a == b
        assert a != c
        assert len(a) == 64  # hex sha256


def test_aead_round_trip(app):
    with app.app_context():
        from app.services.crypto import aead_decrypt, aead_encrypt

        token = aead_encrypt(b"hello world", associated_data=b"v1")
        assert aead_decrypt(token, associated_data=b"v1") == b"hello world"


def test_random_6digit_code_format(app):
    with app.app_context():
        from app.services.crypto import random_6digit_code

        for _ in range(50):
            code = random_6digit_code()
            assert len(code) == 6 and code.isdigit()
