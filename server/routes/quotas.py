from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging

from gpuctl.parser.base_parser import BaseParser, ParserError
from gpuctl.client.quota_client import QuotaClient

from server.models import (
    JobCreateRequest,
    JobResponse,
    DeleteResponse
)

router = APIRouter(prefix="/api/v1/quotas", tags=["quotas"])
logger = logging.getLogger(__name__)


@router.post("", response_model=Dict[str, Any], status_code=201)
async def create_quota(request: JobCreateRequest):
    """创建资源配额"""
    logger.debug(f"开始创建资源配额，请求内容: {request.yamlContent[:100]}...")
    try:
        logger.debug("正在解析YAML配置")
        parsed_obj = BaseParser.parse_yaml(request.yamlContent)
        logger.debug(f"YAML解析成功，配额名称: {parsed_obj.quota.name}")

        if parsed_obj.kind != "quota":
            raise HTTPException(status_code=400, detail=f"Unsupported kind: {parsed_obj.kind}")

        client = QuotaClient()
        quota_config = {
            "name": parsed_obj.quota.name,
            "description": parsed_obj.quota.description,
            "namespace": {}
        }

        if parsed_obj.default:
            quota_config["default"] = {
                "cpu": parsed_obj.default.get_cpu_str(),
                "memory": parsed_obj.default.memory,
                "gpu": parsed_obj.default.get_gpu_str()
            }

        for namespace_name, namespace_quota in parsed_obj.namespace.items():
            quota_config["namespace"][namespace_name] = {
                "cpu": namespace_quota.get_cpu_str(),
                "memory": namespace_quota.memory,
                "gpu": namespace_quota.get_gpu_str()
            }

        results = client.create_quota_config(quota_config)

        return {
            "message": "配额创建成功",
            "name": parsed_obj.quota.name,
            "created": results
        }

    except ParserError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create quota: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=Dict[str, Any])
async def get_quotas(namespace: Optional[str] = Query(None, description="命名空间过滤")):
    """获取资源配额列表"""
    try:
        client = QuotaClient()
        if namespace:
            quota = client.get_quota(namespace)
            if not quota:
                raise HTTPException(status_code=404, detail="Quota not found")
            return quota
        else:
            quotas = client.list_quotas()
            return {
                "total": len(quotas),
                "items": quotas
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quotas: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{namespaceName}", response_model=Dict[str, Any])
async def get_quota_detail(namespaceName: str):
    """获取资源配额详情"""
    try:
        client = QuotaClient()
        quota = client.describe_quota(namespaceName)
        if not quota:
            raise HTTPException(status_code=404, detail="Quota not found")
        return quota

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quota detail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{namespaceName}", response_model=DeleteResponse)
async def delete_quota(namespaceName: str, force: bool = Query(False, description="是否强制删除")):
    """删除资源配额"""
    try:
        client = QuotaClient()
        success = client.delete_quota(namespaceName)

        if not success:
            raise HTTPException(status_code=404, detail="Quota not found")

        return DeleteResponse(
            jobId=namespaceName,
            status="deleted",
            message="配额删除成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete quota: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
