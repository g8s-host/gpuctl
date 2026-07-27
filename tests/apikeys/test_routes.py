"""/api/v1/auth/api-keys 管理路由测试（不挂鉴权中间件，专注路由行为本身）。"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gpuctl.apikeys import ApiKeyStore
from server.routes.apikeys import router, set_store
from fake_k8s import FakeCoreV1


@pytest.fixture
def client():
    store = ApiKeyStore(namespace="rw-system", core_v1=FakeCoreV1(), cache_ttl=30)
    set_store(store)
    app = FastAPI()
    app.include_router(router)
    yield TestClient(app)
    set_store(None)


def test_create_list_revoke_lifecycle(client):
    r = client.post("/api/v1/auth/api-keys", json={
        "name": "claude-code-leon",
        "scopes": ["jobs:read", "jobs:write"],
        "namespace": "leon",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["key"].startswith("rw_")
    key_id = body["key_id"]

    r = client.get("/api/v1/auth/api-keys")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["name"] == "claude-code-leon"
    assert "key" not in items[0]            # 明文只出现在创建响应

    assert client.delete(f"/api/v1/auth/api-keys/{key_id}").status_code == 204
    assert client.get("/api/v1/auth/api-keys").json() == []
    assert client.delete(f"/api/v1/auth/api-keys/{key_id}").status_code == 404


def test_create_validates_scopes(client):
    r = client.post("/api/v1/auth/api-keys", json={
        "name": "bad", "scopes": ["not-a-scope"],
    })
    assert r.status_code == 422


def test_scopes_endpoint_lists_known_scopes(client):
    r = client.get("/api/v1/auth/api-keys/scopes")
    assert r.status_code == 200
    scopes = r.json()
    assert "admin" in scopes and "jobs:write" in scopes
