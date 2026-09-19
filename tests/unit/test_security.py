import time

import pytest

from src.api import security


@pytest.fixture(autouse=True)
def isolated_secret(tmp_path, monkeypatch):
    db_file = tmp_path / "app.sqlite3"
    monkeypatch.setenv("APP_DATABASE_FILE", str(db_file))
    security.reset_session_secret_cache()
    yield
    security.reset_session_secret_cache()


def test_token_roundtrip():
    token = security.issue_token("admin")
    assert security.verify_token(token) == "admin"


def test_token_rejects_tampered_payload():
    token = security.issue_token("admin")
    payload, signature = token.split(".", 1)
    forged_payload = security._b64encode(
        b'{"u":"attacker","exp":9999999999}'
    )
    tampered = f"{forged_payload}.{signature}"
    assert security.verify_token(tampered) is None
    # 原始 token 仍然有效
    assert security.verify_token(token) == "admin"


def test_token_rejects_expired():
    token = security.issue_token("admin", ttl_seconds=-10)
    assert security.verify_token(token) is None


def test_token_rejects_garbage():
    assert security.verify_token(None) is None
    assert security.verify_token("") is None
    assert security.verify_token("not-a-token") is None
    assert security.verify_token("a.b.c") is None


def test_session_secret_persists_across_instances(tmp_path, monkeypatch):
    db_file = tmp_path / "persist.sqlite3"
    monkeypatch.setenv("APP_DATABASE_FILE", str(db_file))

    security.reset_session_secret_cache()
    token = security.issue_token("admin")
    assert security.verify_token(token) == "admin"

    # 模拟进程重启：清空内存缓存后重新从 SQLite 加载密钥
    security.reset_session_secret_cache()
    assert security.verify_token(token) == "admin"


def test_rate_limiter_allows_burst_then_blocks():
    limiter = security.SlidingWindowRateLimiter(max_events=3, window_seconds=60)
    assert limiter.allow("1.2.3.4")
    assert limiter.allow("1.2.3.4")
    assert limiter.allow("1.2.3.4")
    assert not limiter.allow("1.2.3.4")
    # 其他 IP 不受影响
    assert limiter.allow("5.6.7.8")


def test_rate_limiter_window_expiry():
    limiter = security.SlidingWindowRateLimiter(max_events=1, window_seconds=0.05)
    assert limiter.allow("1.2.3.4")
    assert not limiter.allow("1.2.3.4")
    time.sleep(0.06)
    assert limiter.allow("1.2.3.4")


def test_rate_limiter_reset():
    limiter = security.SlidingWindowRateLimiter(max_events=1, window_seconds=60)
    assert limiter.allow("1.2.3.4")
    assert not limiter.allow("1.2.3.4")
    limiter.reset("1.2.3.4")
    assert limiter.allow("1.2.3.4")


def test_is_protected_path():
    assert security.is_protected_path("/api")
    assert security.is_protected_path("/api/tasks")
    assert security.is_protected_path("/ws")
    assert not security.is_protected_path("/apiwiki")
    assert not security.is_protected_path("/health")
    assert not security.is_protected_path("/auth/status")
    assert not security.is_protected_path("/")
    assert not security.is_protected_path("/assets/app.js")
