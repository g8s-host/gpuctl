"""/api/v1 的 API Key 鉴权中间件（gpuctl 独立 server 与 runwhere-ai console 共用）。

开关：env ``GPUCTL_API_AUTH``
  - ``apikey``：强制 —— /api/v1/* 需要有效的 ``Authorization: Bearer rw_...``；
    console 场景可传 ``session_fallback``，让已通过控制台会话认证的浏览器请求放行。
  - 其他值 / 未设（默认 ``off``）：不鉴权，仅在启动时打警告。默认关闭是为兼容
    存量部署与测试；生产部署应显式设 ``apikey``。

scope 规则：``/api/v1/<seg>/...`` → GET/HEAD/OPTIONS 要 ``<seg>:read``，否则 ``<seg>:write``；
``/api/v1/auth/*``（key 管理）一律要 ``admin``。

已知边界（v1）：BaseHTTPMiddleware 不拦 WebSocket（如 jobs 的日志 WS）；
key 的 namespace 绑定只记录、未按请求强制 —— 均留待 Agent-First Phase 1。

错误响应用 Agent 可解析的统一结构（error.code / error.action），是 PRD §4.8 的雏形。
"""
from __future__ import annotations

import logging
import os
from typing import Awaitable, Callable, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

from gpuctl.apikeys import ApiKeyInvalid, ApiKeyStore, KEY_PREFIX

logger = logging.getLogger(__name__)

GUARDED_PREFIX = "/api/v1/"

# 会话兜底：async (request, required_scope) -> 任意真值（该 scope 下已授权）/ None（拒绝）。
# required_scope 让调用方（console）能拒绝"已登录但角色不够"的会话——例如非 admin 的
# namespace_user 会话不该走会话兜底就通过 admin scope（/api/v1/auth/* key 管理）。
# 异常按未认证处理。
SessionFallback = Callable[[Request, str], Awaitable[Optional[object]]]


def auth_mode() -> str:
    return (os.getenv("GPUCTL_API_AUTH") or "off").strip().lower()


def required_scope(path: str, method: str) -> str:
    seg = path[len(GUARDED_PREFIX):].split("/", 1)[0].split("?", 1)[0]
    if seg == "auth":
        return "admin"
    if method.upper() in ("GET", "HEAD", "OPTIONS"):
        return f"{seg}:read"
    return f"{seg}:write"


def _error(status: int, code: str, message: str, action: str, **details) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "action": action}}
    if details:
        body["error"]["details"] = details
    resp = JSONResponse(status_code=status, content=body)
    if status == 401:
        resp.headers["WWW-Authenticate"] = "Bearer"
    return resp


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, store: ApiKeyStore,
                 session_fallback: Optional[SessionFallback] = None):
        super().__init__(app)
        self.store = store
        self.session_fallback = session_fallback

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith(GUARDED_PREFIX):
            return await call_next(request)

        header = request.headers.get("Authorization", "")
        token = header[7:].strip() if header.startswith("Bearer ") else ""

        if token.startswith(KEY_PREFIX):
            try:
                # store.verify 是同步 K8s 调用，扔线程池避免卡事件循环
                ident = await run_in_threadpool(self.store.verify, token)
            except ApiKeyInvalid as exc:
                return _error(401, exc.code, exc.message, "check_api_key")
            except Exception:  # noqa: BLE001 — 存储后端故障不能伪装成 key 无效
                logger.exception("api key verification backend error")
                return _error(503, "AUTH_BACKEND_ERROR",
                              "API key verification temporarily unavailable",
                              "retry", retry_after=10)
            scope = required_scope(request.url.path, request.method)
            if not ident.allows(scope):
                return _error(403, "FORBIDDEN",
                              f"API key '{ident.name}' lacks scope '{scope}'",
                              "request_scope", required_scope=scope,
                              granted_scopes=list(ident.scopes))
            request.state.api_key = ident
            return await call_next(request)

        # 无 API key：console 会话兜底（浏览器同源 fetch 带 cookie 的场景）
        if self.session_fallback is not None:
            scope = required_scope(request.url.path, request.method)
            try:
                user = await self.session_fallback(request, scope)
            except Exception:  # noqa: BLE001 — 兜底认证失败即未认证
                user = None
            if user is not None:
                request.state.api_key = None
                return await call_next(request)

        return _error(401, "UNAUTHENTICATED",
                      "This endpoint requires an API key "
                      "(Authorization: Bearer rw_...)",
                      "provide_api_key")


def install_api_auth(app: FastAPI,
                     session_fallback: Optional[SessionFallback] = None,
                     store: Optional[ApiKeyStore] = None) -> Optional[ApiKeyStore]:
    """按 env 决定是否启用鉴权。返回启用时的 store（供管理路由复用），未启用返回 None。"""
    mode = auth_mode()
    if mode != "apikey":
        logger.warning(
            "GPUCTL_API_AUTH=%s — /api/v1 未启用鉴权（生产部署请设 GPUCTL_API_AUTH=apikey）",
            mode or "off")
        return None
    store = store or ApiKeyStore()
    app.add_middleware(ApiKeyAuthMiddleware, store=store,
                       session_fallback=session_fallback)
    logger.info("API key auth enabled for /api/v1 (secrets namespace=%s)",
                store.namespace)
    return store
