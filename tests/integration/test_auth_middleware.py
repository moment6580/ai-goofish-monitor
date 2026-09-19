import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.api import security
from src.api.routes import accounts, websocket as websocket_router


@pytest.fixture()
def protected_app(monkeypatch, tmp_path):
    """带鉴权中间件的最小应用，用于验证保护行为。"""
    db_file = tmp_path / "app.sqlite3"
    monkeypatch.setenv("APP_DATABASE_FILE", str(db_file))
    security.reset_session_secret_cache()
    security.login_rate_limiter.reset_all()

    app = FastAPI()
    app.include_router(accounts.router)
    app.include_router(websocket_router.router)
    app.middleware("http")(security.auth_middleware)

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.post("/auth/status")
    async def auth_status(payload: dict):
        if payload.get("username") == "admin" and payload.get("password") == "pw":
            return {
                "authenticated": True,
                "username": "admin",
                "token": security.issue_token("admin"),
                "expires_in": security.TOKEN_TTL_SECONDS,
            }
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="认证失败")

    yield app
    security.reset_session_secret_cache()
    security.login_rate_limiter.reset_all()


@pytest.fixture()
def client(protected_app):
    return TestClient(protected_app)


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_api_without_token_rejected(client):
    assert client.get("/api/accounts").status_code == 401
    assert client.get("/api/tasks").status_code == 401
    assert client.post("/api/accounts", json={}).status_code == 401


def test_api_with_invalid_token_rejected(client):
    assert (
        client.get("/api/accounts", headers=_auth_header("bad.token")).status_code
        == 401
    )
    assert (
        client.get(
            "/api/accounts", headers={"Authorization": "Basic dXNlcjpwYXNz"}
        ).status_code
        == 401
    )


def test_api_with_valid_token_allowed(client):
    token = security.issue_token("admin")
    response = client.get("/api/accounts", headers=_auth_header(token))
    assert response.status_code == 200
    assert response.json() == []


def test_api_with_token_via_query_param(client):
    token = security.issue_token("admin")
    assert client.get(f"/api/accounts?token={token}").status_code == 200


def test_health_exempt_from_auth(client):
    assert client.get("/health").status_code == 200


def test_login_success_returns_token(client):
    response = client.post(
        "/auth/status", json={"username": "admin", "password": "pw"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert security.verify_token(body["token"]) == "admin"
    assert body["expires_in"] > 0


def test_login_failure_returns_401(client):
    response = client.post(
        "/auth/status", json={"username": "admin", "password": "wrong"}
    )
    assert response.status_code == 401


def test_login_rate_limited_on_real_app(monkeypatch, tmp_path):
    """使用真实 src.app 验证登录端点确实应用了限速。"""
    monkeypatch.setenv("APP_DATABASE_FILE", str(tmp_path / "app.sqlite3"))
    security.reset_session_secret_cache()
    security.login_rate_limiter.reset_all()

    from src.app import app as real_app

    with TestClient(real_app) as client:
        for _ in range(5):
            client.post(
                "/auth/status", json={"username": "admin", "password": "wrong"}
            )
        # 窗口期内即使凭据正确也会被限速
        response = client.post(
            "/auth/status", json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 429

        # 限速只按客户端计数：窗口过期后恢复
        security.login_rate_limiter.reset_all()
        ok = client.post(
            "/auth/status", json={"username": "admin", "password": "admin123"}
        )
        assert ok.status_code == 200
        body = ok.json()
        assert body["authenticated"] is True
        assert security.verify_token(body["token"]) == "admin"

    security.reset_session_secret_cache()
    security.login_rate_limiter.reset_all()


def test_ws_rejected_without_token(protected_app):
    client = TestClient(protected_app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws") as ws:
            ws.receive_text()
    assert exc_info.value.code == security.WS_REJECTED_CLOSE_CODE


def test_ws_rejected_with_invalid_token(protected_app):
    client = TestClient(protected_app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws?token=forged.token") as ws:
            ws.receive_text()
    assert exc_info.value.code == security.WS_REJECTED_CLOSE_CODE


def test_ws_accepts_valid_token(protected_app):
    client = TestClient(protected_app)
    token = security.issue_token("admin")
    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.send_text("ping")
