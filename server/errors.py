"""统一错误响应格式(Agent-First PRD §4.8):`{"error": {"code","message","action",["details"]}}`。

设计成**兜底式**——不用逐个改现有的 `raise HTTPException(status_code, detail="...")`
call site(散落在 jobs.py/pools.py/... 几十处)。两个全局 handler(server/main.py、
以及 runwhere-ai 挂载时用的 src/webui/errors.py)统一调用这里的 `error_body()`:
  - `detail` 是普通字符串(现状全部如此)→ 按状态码给合理的默认 code/action。
  - 想给更精确 code/action 的路由,可以改传 `detail={"code": ..., "message": ..., "action": ...}`
    (dict),这里会识别并透传/补全——不用大改,想精确了再逐个升级。

`error.action` 是 Agent 可以直接执行的下一步(如 "provide_api_key"、"retry"),
而不是人话("请检查你的请求")——这是 Agent-First 和普通错误页的关键区别。
"""
from __future__ import annotations

from typing import Any

_DEFAULT_CODE_BY_STATUS: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}

_DEFAULT_ACTION_BY_STATUS: dict[int, str] = {
    400: "fix_request",
    401: "provide_api_key",
    403: "request_scope",
    404: "check_resource_name",
    409: "resolve_conflict",
    422: "fix_request",
    500: "retry",
    503: "retry",
}


def error_body(status_code: int, detail: Any) -> dict:
    """`HTTPException.detail`(字符串或已结构化的 dict)→ 统一错误 body。"""
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        body = {
            "code": detail["code"],
            "message": detail["message"],
            "action": detail.get("action") or _DEFAULT_ACTION_BY_STATUS.get(status_code, "retry"),
        }
        if "details" in detail:
            body["details"] = detail["details"]
        return {"error": body}
    return {
        "error": {
            "code": _DEFAULT_CODE_BY_STATUS.get(status_code, "ERROR"),
            "message": str(detail),
            "action": _DEFAULT_ACTION_BY_STATUS.get(status_code, "retry"),
        }
    }
