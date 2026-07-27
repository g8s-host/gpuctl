"""ApiKeyAuthMiddleware + required_scope 测试（store 用真实 ApiKeyStore + 内存 K8s）。"""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from gpuctl.apikeys import ApiKeyStore
from server.auth import ApiKeyAuthMiddleware, required_scope
from fake_k8s import FakeCoreV1


@pytest.mark.parametrize("path,method,scope", [
    ("/api/v1/jobs", "GET", "jobs:read"),
    ("/api/v1/jobs/x/logs", "GET", "jobs:read"),
    ("/api/v1/jobs", "POST", "jobs:write"),
    ("/api/v1/pools/p1", "DELETE", "pools:write"),
    ("/api/v1/auth/api-keys", "GET", "admin"),
    ("/api/v1/auth/api-keys/abc", "DELETE", "admin"),
])
def test_required_scope_mapping(path, method, scope):
    assert required_scope(path, method) == scope


def _build_app(session_fallback=None):
    store = ApiKeyStore(namespace="rw-system", core_v1=FakeCoreV1(), cache_ttl=30)
    app = FastAPI()
    app.add_middleware(ApiKeyAuthMiddleware, store=store,
                       session_fallback=session_fallback)

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/api/v1/jobs")
    async def list_jobs(request: Request):
        ident = request.state.api_key
        return {"caller": ident.name if ident else "session"}

    @app.post("/api/v1/jobs")
    async def create_job():
        return {"created": True}

    return app, store


def test_non_api_paths_pass_without_auth():
    app, _ = _build_app()
    assert TestClient(app).get("/health").status_code == 200


def test_missing_key_gets_structured_401():
    app, _ = _build_app()
    r = TestClient(app).get("/api/v1/jobs")
    assert r.status_code == 401
    err = r.json()["error"]
    assert err["code"] == "UNAUTHENTICATED"
    assert err["action"] == "provide_api_key"
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_key_401():
    app, _ = _build_app()
    r = TestClient(app).get("/api/v1/jobs",
                            headers={"Authorization": "Bearer rw_nope"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "KEY_UNKNOWN"


def test_valid_key_with_scope_passes_and_sets_identity():
    app, store = _build_app()
    token, _ = store.create("agent-1", ["jobs:read"])
    r = TestClient(app).get("/api/v1/jobs",
                            headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == {"caller": "agent-1"}


def test_valid_key_missing_scope_403_with_details():
    app, store = _build_app()
    token, _ = store.create("reader", ["jobs:read"])
    r = TestClient(app).post("/api/v1/jobs",
                             headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    err = r.json()["error"]
    assert err["code"] == "FORBIDDEN"
    assert err["details"]["required_scope"] == "jobs:write"
    assert err["details"]["granted_scopes"] == ["jobs:read"]


def test_session_fallback_allows_browser_requests():
    async def fallback(request, scope):
        return object()  # 已认证的 console 会话

    app, _ = _build_app(session_fallback=fallback)
    r = TestClient(app).get("/api/v1/jobs")
    assert r.status_code == 200
    assert r.json() == {"caller": "session"}


def test_session_fallback_failure_still_401():
    async def fallback(request, scope):
        raise RuntimeError("no session")

    app, _ = _build_app(session_fallback=fallback)
    assert TestClient(app).get("/api/v1/jobs").status_code == 401


def test_non_rw_bearer_token_falls_through_to_session():
    """K8s bearer token（console 的 bearer provider 场景）不该被当成坏 API key。"""
    async def fallback(request, scope):
        auth = request.headers.get("Authorization", "")
        return object() if auth == "Bearer k8s-sa-token" else None

    app, _ = _build_app(session_fallback=fallback)
    r = TestClient(app).get("/api/v1/jobs",
                            headers={"Authorization": "Bearer k8s-sa-token"})
    assert r.status_code == 200


def test_session_fallback_receives_required_scope_and_can_veto():
    """非 admin 会话不该靠会话兜底就通过 admin-only 端点(如 key 管理)。"""
    async def fallback(request, scope):
        return None if scope == "admin" else object()

    app, store = _build_app(session_fallback=fallback)

    @app.get("/api/v1/auth/api-keys")
    async def list_keys():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/api/v1/jobs").status_code == 200          # jobs:read → 放行
    assert client.get("/api/v1/auth/api-keys").status_code == 401  # admin → 拒绝
