"""API Key 管理路由：POST/GET/DELETE /api/v1/auth/api-keys。

鉴权由 ApiKeyAuthMiddleware 统一负责（本前缀映射为 admin scope；console 会话兜底
让管理员能在 UI 上创建第一把 key，解决冷启动）。GPUCTL_API_AUTH=off 时与其余
/api/v1 一样裸奔 —— 这是 bootstrap 模式，不是生产姿态。

明文 key 只在创建响应里返回一次。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from starlette.concurrency import run_in_threadpool

from gpuctl.apikeys import ApiKeyStore, KNOWN_SCOPES

router = APIRouter(prefix="/api/v1/auth/api-keys", tags=["auth"])
logger = logging.getLogger(__name__)

_store: Optional[ApiKeyStore] = None


def get_store() -> ApiKeyStore:
    global _store
    if _store is None:
        _store = ApiKeyStore()
    return _store


def set_store(store: ApiKeyStore) -> None:
    """由 main/console 注入与中间件同一个 store（共享校验缓存，吊销即时生效）。"""
    global _store
    _store = store


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64,
                      description="给人看的名字，如 claude-code-leon")
    scopes: List[str] = Field(..., min_length=1)
    namespace: str = "*"
    expires_days: Optional[int] = Field(None, ge=1, le=3650)


class ApiKeyInfoResponse(BaseModel):
    key_id: str
    name: str
    namespace: str
    scopes: List[str]
    hint: str = ""
    created_at: str = ""
    expires_at: str = ""


class ApiKeyCreateResponse(ApiKeyInfoResponse):
    key: str  # 明文，仅此一次


@router.get("", response_model=List[ApiKeyInfoResponse])
async def list_api_keys():
    try:
        infos = await run_in_threadpool(get_store().list)
        return [ApiKeyInfoResponse(**vars(i)) for i in infos]
    except Exception as e:
        logger.error(f"Failed to list api keys: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/scopes", response_model=List[str])
async def list_known_scopes():
    """供管理页渲染 scope 勾选框。"""
    return sorted(KNOWN_SCOPES)


@router.post("", response_model=ApiKeyCreateResponse, status_code=201)
async def create_api_key(body: ApiKeyCreateRequest):
    try:
        token, info = await run_in_threadpool(
            get_store().create, body.name, body.scopes,
            body.namespace, body.expires_days)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create api key: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    return ApiKeyCreateResponse(key=token, **vars(info))


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(key_id: str):
    try:
        found = await run_in_threadpool(get_store().revoke, key_id)
    except Exception as e:
        logger.error(f"Failed to revoke api key {key_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not found:
        raise HTTPException(status_code=404, detail="API key not found")
