"""
认证与登录限速。

- Token 采用 HMAC-SHA256 签名的 JSON payload（Base64URL 编码），自带过期时间。
- 签名密钥首次生成后持久化到 SQLite app_metadata，应用重启后已签发的 token 仍然有效。
- 登录接口按客户端 IP 做滑动窗口限速。
- 纯标准库实现，不引入第三方依赖。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

from starlette.requests import Request
from starlette.responses import JSONResponse

from src.infrastructure.persistence.storage_names import DEFAULT_DATABASE_PATH

SESSION_SECRET_METADATA_KEY = "security:session_secret"
TOKEN_TTL_SECONDS = 7 * 24 * 3600
WS_REJECTED_CLOSE_CODE = 4401

PROTECTED_API_PREFIX = "/api"
PROTECTED_WS_PATH = "/ws"

_secret_cache: Optional[str] = None
_secret_lock = threading.Lock()


def get_database_path() -> str:
    import os

    return os.getenv("APP_DATABASE_FILE", DEFAULT_DATABASE_PATH)


def _load_or_create_session_secret() -> str:
    """从 SQLite app_metadata 读取签名密钥，不存在则生成并持久化。"""
    global _secret_cache
    with _secret_lock:
        if _secret_cache:
            return _secret_cache

        db_path = get_database_path()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS app_metadata ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            row = conn.execute(
                "SELECT value FROM app_metadata WHERE key = ?",
                (SESSION_SECRET_METADATA_KEY,),
            ).fetchone()
            if row is not None:
                secret = str(row[0])
            else:
                secret = secrets.token_hex(32)
                conn.execute(
                    "INSERT OR REPLACE INTO app_metadata(key, value) VALUES (?, ?)",
                    (SESSION_SECRET_METADATA_KEY, secret),
                )
                conn.commit()
        finally:
            conn.close()

        _secret_cache = secret
        return secret


def reset_session_secret_cache() -> None:
    """清空内存中的密钥缓存（测试用）。"""
    global _secret_cache
    with _secret_lock:
        _secret_cache = None


def _credential_fingerprint() -> str:
    """当前登录凭据的指纹，混入签名密钥。

    修改 WEB_USERNAME/WEB_PASSWORD 后（无需重启），所有旧 token 自动失效。
    """
    from src.infrastructure.config.settings import get_app_settings

    app_settings = get_app_settings()
    payload = f"{app_settings.web_username}:{app_settings.web_password}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _effective_signing_secret() -> str:
    """签名密钥 = 持久化随机密钥 + 凭据指纹。"""
    return f"{_load_or_create_session_secret()}:{_credential_fingerprint()}"


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _sign(message: bytes, secret: str) -> bytes:
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()


def issue_token(username: str, *, ttl_seconds: int = TOKEN_TTL_SECONDS) -> str:
    """签发带过期时间的 HMAC 签名 token。"""
    payload = json.dumps(
        {"u": username, "exp": int(time.time()) + ttl_seconds},
        separators=(",", ":"),
    ).encode("utf-8")
    encoded_payload = _b64encode(payload)
    secret = _effective_signing_secret()
    signature = _b64encode(_sign(encoded_payload.encode("ascii"), secret))
    return f"{encoded_payload}.{signature}"


def verify_token(token: Optional[str]) -> Optional[str]:
    """校验 token，有效时返回用户名，无效或过期返回 None。"""
    if not token or token.count(".") != 1:
        return None

    encoded_payload, signature = token.split(".", 1)
    secret = _effective_signing_secret()
    expected = _sign(encoded_payload.encode("ascii"), secret)
    try:
        actual = _b64decode(signature)
    except Exception:
        return None
    if not hmac.compare_digest(expected, actual):
        return None

    try:
        payload = json.loads(_b64decode(encoded_payload))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    if not isinstance(payload.get("exp"), int):
        return None
    if payload["exp"] < time.time():
        return None
    username = payload.get("u")
    if not isinstance(username, str) or not username:
        return None
    return username


def extract_token(request: Request) -> Optional[str]:
    """从 Authorization 头（Bearer）或查询参数 token 中提取令牌。"""
    auth_header = request.headers.get("authorization") or ""
    if auth_header.lower().startswith("bearer "):
        candidate = auth_header[7:].strip()
        if candidate:
            return candidate
    return request.query_params.get("token")


def authenticate_request(request: Request) -> Optional[str]:
    """综合校验请求凭证，成功返回用户名。"""
    return verify_token(extract_token(request))


def is_protected_path(path: str) -> bool:
    if path == PROTECTED_API_PREFIX or path.startswith(PROTECTED_API_PREFIX + "/"):
        return True
    return path == PROTECTED_WS_PATH


async def auth_middleware(request: Request, call_next):
    """保护 /api 与 /ws 的 HTTP 请求；/health、/auth/status 与静态资源豁免。"""
    if is_protected_path(request.url.path):
        username = authenticate_request(request)
        if username is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "未认证或凭证已失效"},
                headers={"WWW-Authenticate": "Bearer"},
            )
    return await call_next(request)


class SlidingWindowRateLimiter:
    """线程安全的滑动窗口限速器（进程内）。"""

    def __init__(self, max_events: int, window_seconds: float):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._events: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = [t for t in self._events.get(key, []) if now - t < self.window_seconds]
            if len(bucket) >= self.max_events:
                self._events[key] = bucket
                return False
            bucket.append(now)
            self._events[key] = bucket
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def reset_all(self) -> None:
        """清空所有限速状态（测试用）。"""
        with self._lock:
            self._events.clear()


login_rate_limiter = SlidingWindowRateLimiter(max_events=5, window_seconds=60.0)


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"
