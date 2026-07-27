"""ApiKeyStore 单元测试（K8s 用内存 fake）。"""
import base64
from datetime import datetime, timedelta, timezone

import pytest

from gpuctl.apikeys import (
    SECRET_NAME_PREFIX,
    ApiKeyInvalid,
    ApiKeyStore,
)
from fake_k8s import FakeCoreV1


@pytest.fixture
def fake():
    return FakeCoreV1()


@pytest.fixture
def store(fake):
    return ApiKeyStore(namespace="rw-system", core_v1=fake, cache_ttl=30)


def test_create_returns_plaintext_once_and_persists_hash_only(store, fake):
    token, info = store.create("claude-code", ["jobs:read", "jobs:write"])
    assert token.startswith("rw_")
    assert info.key_id and len(info.key_id) == 16
    assert info.scopes == ["jobs:read", "jobs:write"]
    assert info.hint.startswith("rw_")

    secret = fake.secrets[("rw-system", SECRET_NAME_PREFIX + info.key_id)]
    stored = {k: base64.b64decode(v).decode() for k, v in secret.data.items()}
    assert token not in stored.values()          # 明文绝不落盘
    assert len(stored["hash"]) == 64


@pytest.mark.parametrize("name,scopes,err", [
    ("", ["jobs:read"], "name"),
    ("k", [], "scope"),
    ("k", ["jobs:read", "bogus:write"], "unknown scopes"),
])
def test_create_rejects_bad_input(store, name, scopes, err):
    with pytest.raises(ValueError, match=err):
        store.create(name, scopes)


def test_verify_roundtrip(store):
    token, info = store.create("agent", ["gpu:read"], namespace="leon")
    ident = store.verify(token)
    assert ident.key_id == info.key_id
    assert ident.name == "agent"
    assert ident.namespace == "leon"
    assert ident.allows("gpu:read")
    assert not ident.allows("jobs:write")


def test_admin_scope_allows_everything(store):
    token, _ = store.create("root", ["admin"])
    ident = store.verify(token)
    assert ident.allows("jobs:write")
    assert ident.allows("admin")


def test_verify_unknown_and_malformed(store):
    with pytest.raises(ApiKeyInvalid) as e:
        store.verify("rw_definitely-not-a-real-key-aaaaaaaaaaaa")
    assert e.value.code == "KEY_UNKNOWN"

    with pytest.raises(ApiKeyInvalid) as e:
        store.verify("sk-openai-style-key")
    assert e.value.code == "KEY_MALFORMED"


def test_verify_expired(store, fake):
    token, info = store.create("old", ["jobs:read"], expires_days=1)
    secret = fake.secrets[("rw-system", SECRET_NAME_PREFIX + info.key_id)]
    past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    secret.data["expires_at"] = base64.b64encode(past.encode()).decode()

    with pytest.raises(ApiKeyInvalid) as e:
        store.verify(token)
    assert e.value.code == "KEY_EXPIRED"


def test_verify_uses_cache(store, fake):
    token, _ = store.create("cached", ["jobs:read"])
    store.verify(token)
    store.verify(token)
    assert fake.read_calls == 1


def test_revoke_evicts_cache_and_deletes(store, fake):
    token, info = store.create("gone", ["jobs:read"])
    store.verify(token)                      # 进缓存
    assert store.revoke(info.key_id) is True
    with pytest.raises(ApiKeyInvalid):
        store.verify(token)                  # 缓存已被驱逐，K8s 404
    assert store.revoke(info.key_id) is False


def test_list_shows_all_keys_without_hash(store):
    store.create("a", ["jobs:read"])
    store.create("b", ["admin"], namespace="team-x")
    infos = store.list()
    assert [i.name for i in infos] == ["a", "b"]
    assert infos[1].namespace == "team-x"
    assert all(not hasattr(i, "hash") for i in infos)
