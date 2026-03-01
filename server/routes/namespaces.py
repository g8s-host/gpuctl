from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, Optional
import logging

from gpuctl.client.quota_client import QuotaClient
from gpuctl.constants import Labels, NS_LABEL_SELECTOR

router = APIRouter(prefix="/api/v1/namespaces", tags=["namespaces"])
logger = logging.getLogger(__name__)


@router.get("", response_model=Dict[str, Any])
async def list_namespaces():
    """获取所有 gpuctl 管理的命名空间列表（含 default 命名空间）"""
    try:
        client = QuotaClient()

        namespaces = client.core_v1.list_namespace(
            label_selector=NS_LABEL_SELECTOR
        )

        result = []
        for ns in namespaces.items:
            result.append({
                "name": ns.metadata.name,
                "status": ns.status.phase,
                "age": str(ns.metadata.creation_timestamp)
            })

        # 补充 default 命名空间
        try:
            default_ns = client.core_v1.read_namespace("default")
            if not any(n["name"] == "default" for n in result):
                result.append({
                    "name": default_ns.metadata.name,
                    "status": default_ns.status.phase,
                    "age": str(default_ns.metadata.creation_timestamp)
                })
        except Exception:
            pass

        return {"total": len(result), "items": result}

    except Exception as e:
        logger.error(f"Failed to list namespaces: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{namespaceName}", response_model=Dict[str, Any])
async def get_namespace_detail(namespaceName: str):
    """获取命名空间详情（含配额信息）"""
    try:
        client = QuotaClient()

        try:
            ns = client.core_v1.read_namespace(namespaceName)
        except Exception:
            raise HTTPException(status_code=404, detail="Namespace not found")

        labels = ns.metadata.labels or {}
        quota = client.get_quota(namespaceName)

        return {
            "name": ns.metadata.name,
            "status": ns.status.phase,
            "age": str(ns.metadata.creation_timestamp),
            "labels": labels,
            "quota": quota
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get namespace detail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{namespaceName}", response_model=Dict[str, Any])
async def delete_namespace(
    namespaceName: str,
    force: bool = Query(False, description="是否强制删除（含命名空间内所有资源）")
):
    """删除命名空间（仅限由 gpuctl 创建的命名空间）"""
    try:
        client = QuotaClient()

        try:
            ns = client.core_v1.read_namespace(namespaceName)
        except Exception:
            raise HTTPException(status_code=404, detail="Namespace not found")

        labels = ns.metadata.labels or {}
        if not labels.get(Labels.NS_MARKER) == "true":
            raise HTTPException(
                status_code=403,
                detail=f"Namespace '{namespaceName}' was not created by gpuctl and cannot be deleted via this API"
            )

        client.core_v1.delete_namespace(namespaceName)

        return {
            "name": namespaceName,
            "status": "deleted",
            "message": f"命名空间 {namespaceName} 已成功删除"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete namespace: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
