"""API Key 核心：生成 / 校验 / 吊销，状态寄存在 K8s Secret（零数据库）。

设计要点（对齐 Agent-First PRD Phase 0）：
  - 每个 key 一个 Secret，命名 ``rw-apikey-<key_id>``，带 ``runwhere.ai/api-key=true`` 标签；
    console 重启无状态，list 一遍即重建视图。
  - Secret 只存 sha256 哈希，明文仅在创建响应里出现一次。
  - ``key_id`` = sha256(明文) 前 16 位 hex —— 校验时可按名字直接 GET，无需遍历。
  - 校验结果带 TTL 缓存（默认 30s），吊销最迟一个 TTL 后生效。

本模块只依赖 kubernetes 包，CLI 与 HTTP server 共用；FastAPI 中间件在
``server/auth.py``，管理路由在 ``server/routes/apikeys.py``。
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

KEY_PREFIX = "rw_"
SECRET_NAME_PREFIX = "rw-apikey-"
LABEL_APIKEY = "runwhere.ai/api-key"

# 已知 scope 全集。``admin`` 通配一切；資源 scope 命名 = /api/v1 后首段 + :read|:write。
# gpu / inferences 为 Agent PRD 预留，路由落地前先允许创建。
KNOWN_SCOPES = frozenset({
    "admin",
    "jobs:read", "jobs:write",
    "pools:read", "pools:write",
    "nodes:read", "nodes:write",
    "quotas:read", "quotas:write",
    "namespaces:read", "namespaces:write",
    "clusters:read", "clusters:write",
    "labels:read", "labels:write",
    "gpu:read",
    "inferences:read", "inferences:write",
})


class ApiKeyInvalid(Exception):
    """校验失败。code ∈ {KEY_UNKNOWN, KEY_EXPIRED, KEY_MALFORMED}。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ApiKeyIdentity:
    """一次成功校验得到的调用方身份。"""

    key_id: str
    name: str
    namespace: str  # 绑定的命名空间，"*" = 不限（v1 仅记录，按 scope 鉴权）
    scopes: Tuple[str, ...] = ()

    def allows(self, scope: str) -> bool:
        return "admin" in self.scopes or scope in self.scopes


@dataclass
class ApiKeyInfo:
    """管理视图（list/create 返回），不含哈希。"""

    key_id: str
    name: str
    namespace: str
    scopes: List[str] = field(default_factory=list)
    hint: str = ""          # 明文前 7 位 + "…"，帮用户对上是哪把 key
    created_at: str = ""
    expires_at: str = ""    # 空串 = 永不过期


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_store_namespace() -> str:
    ns = os.getenv("GPUCTL_APIKEY_NAMESPACE")
    if ns:
        return ns
    sa_ns = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
    try:
        with open(sa_ns) as f:
            return f.read().strip() or "default"
    except OSError:
        return "default"


class ApiKeyStore:
    """K8s Secret 后端的 API Key 存取。线程安全（缓存加锁；K8s 调用无共享状态）。"""

    def __init__(self, namespace: Optional[str] = None, core_v1=None,
                 cache_ttl: Optional[float] = None):
        self.namespace = namespace or _resolve_store_namespace()
        self._core_v1 = core_v1
        self._cache: dict = {}  # sha256hex -> (expire_ts, ApiKeyIdentity)
        self._cache_lock = threading.Lock()
        self._cache_ttl = (
            cache_ttl if cache_ttl is not None
            else float(os.getenv("GPUCTL_APIKEY_CACHE_SECONDS", "30"))
        )

    # ── K8s client（惰性，测试可注入）────────────────────────────────────────
    @property
    def core_v1(self):
        if self._core_v1 is None:
            from kubernetes import client, config
            if os.getenv("KUBERNETES_SERVICE_HOST"):
                config.load_incluster_config()
            else:
                config.load_kube_config()
            self._core_v1 = client.CoreV1Api()
        return self._core_v1

    # ── 创建 ────────────────────────────────────────────────────────────────
    def create(self, name: str, scopes: List[str], namespace: str = "*",
               expires_days: Optional[int] = None) -> Tuple[str, ApiKeyInfo]:
        """生成新 key。返回 (明文, info)；明文此后不再可取。"""
        if not name or not name.strip():
            raise ValueError("api key needs a non-empty name")
        scopes = sorted(set(scopes or []))
        if not scopes:
            raise ValueError("api key needs at least one scope")
        unknown = [s for s in scopes if s not in KNOWN_SCOPES]
        if unknown:
            raise ValueError(f"unknown scopes: {', '.join(unknown)}")

        token = KEY_PREFIX + secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        key_id = digest[:16]
        expires_at = ""
        if expires_days is not None and expires_days > 0:
            expires_at = (_now() + timedelta(days=expires_days)).isoformat()

        info = ApiKeyInfo(
            key_id=key_id, name=name.strip(), namespace=namespace or "*",
            scopes=scopes, hint=token[:7] + "…",
            created_at=_now().isoformat(), expires_at=expires_at,
        )

        from kubernetes import client
        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=SECRET_NAME_PREFIX + key_id,
                labels={LABEL_APIKEY: "true",
                        "app.kubernetes.io/managed-by": "runwhere"},
            ),
            type="Opaque",
            string_data={
                "hash": digest,
                "name": info.name,
                "namespace": info.namespace,
                "scopes": ",".join(scopes),
                "hint": info.hint,
                "created_at": info.created_at,
                "expires_at": expires_at,
            },
        )
        self.core_v1.create_namespaced_secret(self.namespace, secret)
        return token, info

    # ── 列表 / 吊销 ─────────────────────────────────────────────────────────
    def list(self) -> List[ApiKeyInfo]:
        result = self.core_v1.list_namespaced_secret(
            self.namespace, label_selector=f"{LABEL_APIKEY}=true")
        infos = []
        for item in result.items or []:
            data = _decode_secret_data(item)
            infos.append(ApiKeyInfo(
                key_id=(item.metadata.name or "")[len(SECRET_NAME_PREFIX):],
                name=data.get("name", ""),
                namespace=data.get("namespace", "*"),
                scopes=[s for s in data.get("scopes", "").split(",") if s],
                hint=data.get("hint", ""),
                created_at=data.get("created_at", ""),
                expires_at=data.get("expires_at", ""),
            ))
        infos.sort(key=lambda i: i.created_at)
        return infos

    def revoke(self, key_id: str) -> bool:
        """删除 Secret 即吊销。返回是否真的存在。缓存立即驱逐（本进程）。"""
        from kubernetes.client.rest import ApiException
        try:
            self.core_v1.delete_namespaced_secret(
                SECRET_NAME_PREFIX + key_id, self.namespace)
        except ApiException as e:
            if e.status == 404:
                return False
            raise
        with self._cache_lock:
            for h, (_, ident) in list(self._cache.items()):
                if ident.key_id == key_id:
                    self._cache.pop(h, None)
        return True

    # ── 校验 ────────────────────────────────────────────────────────────────
    def verify(self, token: str) -> ApiKeyIdentity:
        """明文 token → 身份；失败抛 ApiKeyInvalid。"""
        if not token or not token.startswith(KEY_PREFIX):
            raise ApiKeyInvalid("KEY_MALFORMED", "API key must start with 'rw_'")
        digest = hashlib.sha256(token.encode()).hexdigest()

        with self._cache_lock:
            hit = self._cache.get(digest)
        if hit is not None:
            expire_ts, ident = hit
            if time.time() < expire_ts:
                return ident
            with self._cache_lock:
                self._cache.pop(digest, None)

        from kubernetes.client.rest import ApiException
        try:
            secret = self.core_v1.read_namespaced_secret(
                SECRET_NAME_PREFIX + digest[:16], self.namespace)
        except ApiException as e:
            if e.status == 404:
                raise ApiKeyInvalid("KEY_UNKNOWN", "unknown API key")
            raise

        data = _decode_secret_data(secret)
        stored_hash = data.get("hash", "")
        if not hmac.compare_digest(stored_hash, digest):
            raise ApiKeyInvalid("KEY_UNKNOWN", "unknown API key")

        expires_at = data.get("expires_at", "")
        if expires_at:
            try:
                expiry = datetime.fromisoformat(expires_at)
            except ValueError:
                expiry = None
            if expiry is not None and _now() > expiry:
                raise ApiKeyInvalid("KEY_EXPIRED", "API key expired")

        ident = ApiKeyIdentity(
            key_id=digest[:16],
            name=data.get("name", ""),
            namespace=data.get("namespace", "*"),
            scopes=tuple(s for s in data.get("scopes", "").split(",") if s),
        )
        with self._cache_lock:
            self._cache[digest] = (time.time() + self._cache_ttl, ident)
        return ident


def _decode_secret_data(secret) -> dict:
    """V1Secret.data 是 base64；string_data 只在写入时存在。"""
    import base64
    out = {}
    for k, v in (secret.data or {}).items():
        try:
            out[k] = base64.b64decode(v).decode()
        except Exception:  # noqa: BLE001 — 单字段坏了不拖垮整把 key 的解析
            out[k] = ""
    return out
