from __future__ import annotations


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"


def test_index_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"OpenKeepr" in r.data


def test_security_txt(client):
    r = client.get("/.well-known/security.txt")
    assert r.status_code == 200
    text = r.data.decode()
    assert "Contact:" in text and "Expires:" in text


def test_api_docs_render(client):
    r = client.get("/docs/api")
    assert r.status_code == 200
    assert b"OpenKeepr REST API" in r.data


def test_release_notes_render(client):
    r = client.get("/release-notes")
    assert r.status_code == 200
    assert b"Changelog" in r.data or b"1.0.0" in r.data


def test_404(client):
    r = client.get("/this-route-does-not-exist")
    assert r.status_code == 404
