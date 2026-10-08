"""Bounded authentication security audit: failing-first tests.

Scope: real registration/password login, hashes, session minting,
unknown-user timing, malformed stored hashes, logout token consistency.
Preserves hash format, session contracts, rate limits, Google behavior.
"""
from __future__ import annotations

import hashlib

from core.store import hash_password, verify_password

PW = "password123"


def _anon_client(data_dir, monkeypatch):
    monkeypatch.setenv("RESEARCH_DATA_DIR", str(data_dir))
    from fastapi.testclient import TestClient

    from api.main import app

    return TestClient(app)


def test_verify_rejects_wrong_algorithm_prefix():
    """Envelope algo must be pbkdf2; a swapped prefix must not verify."""
    _, iters, salt_hex, digest_hex = hash_password(PW).split("$")
    forged = f"md5${iters}${salt_hex}${digest_hex}"
    assert verify_password(PW, forged) is False


def test_verify_rejects_unbounded_iterations():
    """Stored iteration counts above the cap must not be honored."""
    salt_hex = "ab" * 16
    big_iters = 2_000_000
    digest_hex = hashlib.pbkdf2_hmac(
        "sha256", PW.encode(), bytes.fromhex(salt_hex), big_iters
    ).hex()
    forged = f"pbkdf2${big_iters}${salt_hex}${digest_hex}"
    assert verify_password(PW, forged) is False


def test_verify_malformed_hash_still_costs_pbkdf2(monkeypatch):
    """Unusable envelopes (google-only, garbage) must cost one dummy KDF."""
    import core.store as store_mod

    calls = []
    real = hashlib.pbkdf2_hmac

    def counting(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(store_mod.hashlib, "pbkdf2_hmac", counting)
    assert verify_password(PW, "google$abc123") is False
    assert verify_password(PW, "not-a-hash") is False
    assert calls, "malformed stored hash must still run a dummy PBKDF2"


def test_login_unknown_user_still_costs_hashing(data_dir, monkeypatch):
    """Unknown email must still burn one KDF (no enumeration shortcut)."""
    import core.store as store_mod

    client = _anon_client(data_dir, monkeypatch)
    with client:
        client.post(
            "/api/auth/register",
            json={"email": "known@example.com", "password": PW},
        )
        real = hashlib.pbkdf2_hmac
        calls = []

        def counting(*args, **kwargs):
            calls.append(1)
            return real(*args, **kwargs)

        monkeypatch.setattr(store_mod.hashlib, "pbkdf2_hmac", counting)
        r = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": PW},
        )
        assert r.status_code == 401
        assert calls, "unknown-user login must still run a dummy PBKDF2"


def test_login_google_only_user_still_costs_hashing(data_dir, monkeypatch):
    """Google-only rows (google$ hash) must cost one KDF, still 401."""
    import core.store as store_mod
    from core.store import Store

    monkeypatch.setenv("RESEARCH_DATA_DIR", str(data_dir))
    Store(root=data_dir).create_google_user("gonly@example.com", "sub-123")
    client = _anon_client(data_dir, monkeypatch)
    with client:
        real = hashlib.pbkdf2_hmac
        calls = []

        def counting(*args, **kwargs):
            calls.append(1)
            return real(*args, **kwargs)

        monkeypatch.setattr(store_mod.hashlib, "pbkdf2_hmac", counting)
        r = client.post(
            "/api/auth/login",
            json={"email": "gonly@example.com", "password": PW},
        )
        assert r.status_code == 401
        assert calls, "google-only password login must still run a dummy PBKDF2"


def test_logout_token_parsing_matches_auth(data_dir, monkeypatch):
    """Logout must delete the same token auth validated (whitespace)."""
    client = _anon_client(data_dir, monkeypatch)
    with client:
        token = client.post(
            "/api/auth/register",
            json={"email": "w@example.com", "password": PW},
        ).json()["token"]
        # Extra spaces after Bearer: get_current_user strips, logout must too.
        r = client.post(
            "/api/auth/logout", headers={"Authorization": f"Bearer  {token}"}
        )
        assert r.status_code == 204
        me = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me.status_code == 401


def test_backend_persists_only_salted_password_and_session_hashes(data_dir, monkeypatch):
    """Exercise real HTTP credentials and inspect only this synthetic test DB."""
    client = _anon_client(data_dir, monkeypatch)
    with client:
        bodies = [client.post("/api/auth/register", json={
            "email": email, "password": PW,
        }).json() for email in ("first@example.test", "second@example.test")]
        from core.store import Store

        store = Store(root=data_dir)
        first = store.get_user_by_email("first@example.test")
        second = store.get_user_by_email("second@example.test")
        assert first is not None and second is not None
        assert first[1] != second[1]
        assert first[1].startswith("pbkdf2$600000$")
        assert PW not in first[1]
        with store._connect() as con:
            hashes = {row[0] for row in con.execute("SELECT token_hash FROM sessions")}
        for body in bodies:
            assert body["token"] not in hashes
            assert hashlib.sha256(body["token"].encode()).hexdigest() in hashes
        wrong = client.post("/api/auth/login", json={"email": "first@example.test", "password": "wrong"})
        assert wrong.status_code == 401 and "token" not in wrong.json()
        login = client.post("/api/auth/login", json={"email": "first@example.test", "password": PW})
        assert login.status_code == 200
        assert login.json()["user"]["id"] == first[0].id
        bearer = {"Authorization": f"Bearer {login.json()['token']}"}
        assert client.get("/api/auth/me", headers=bearer).json()["id"] == first[0].id
        assert client.post("/api/auth/logout", headers=bearer).status_code == 204
        assert client.get("/api/auth/me", headers=bearer).status_code == 401
