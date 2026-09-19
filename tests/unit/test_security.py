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


def test_tokens_invalidate_when_credentials_change(tmp_path, monkeypatch):
    import os

    from src.infrastructure.config.settings import reload_settings

    db_file = tmp_path / "cred.sqlite3"
    monkeypatch.setenv("APP_DATABASE_FILE", str(db_file))
    security.reset_session_secret_cache()

    orig_user = os.environ.get("WEB_USERNAME")
    orig_pass = os.environ.get("WEB_PASSWORD")
    try:
        monkeypatch.setenv("WEB_USERNAME", "admin")
        monkeypatch.setenv("WEB_PASSWORD", "old-password")
        reload_settings()

        token = security.issue_token("admin")
        assert security.verify_token(token) == "admin"

        # 修改密码后，旧 token 应立即失效
        monkeypatch.setenv("WEB_PASSWORD", "new-password")
        reload_settings()
        assert security.verify_token(token) is None

        # 新密码签发的 token 正常有效
        fresh = security.issue_token("admin")
        assert security.verify_token(fresh) == "admin"
    finally:
        # 显式恢复环境并重载，避免污染后续用例的设置单例
        if orig_user is None:
            os.environ.pop("WEB_USERNAME", None)
        else:
            os.environ["WEB_USERNAME"] = orig_user
        if orig_pass is None:
            os.environ.pop("WEB_PASSWORD", None)
        else:
            os.environ["WEB_PASSWORD"] = orig_pass
        reload_settings()
        security.reset_session_secret_cache()


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
