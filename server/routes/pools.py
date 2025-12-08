from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
import logging

from gpuctl.client.pool_client import PoolClient

from server.models import (
    PoolResponse,
    PoolCreateRequest,
    PoolUpdateRequest
)
from server.auth import AuthValidator, security

router = APIRouter(prefix="/api/v1/pools", tags=["pools"])
logger = logging.getLogger(__name__)


@router.get("", response_model=List[PoolResponse])
async def get_pools(token: str = Depends(AuthValidator.validate_token)):
    """获取资源池列表"""
    try:
        client = PoolClient.get_instance()
        pools = client.list_pools()

        response = []
        for pool in pools:
            response.append(PoolResponse(
                name=pool["name"],
                description=pool.get("description"),
                gpuTotal=pool["gpu_total"],
                gpuUsed=pool["gpu_used"],
                gpuFree=pool["gpu_free"],
                gpuType=pool["gpu_types"],
                status=pool["status"]
            ))

        return response

    except Exception as e:
        logger.error(f"Failed to get pools: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{poolName}", response_model=Dict[str, Any])
async def get_pool_detail(poolName: str, token: str = Depends(AuthValidator.validate_token)):
    """获取资源池详情"""
    try:
        client = PoolClient.get_instance()
        pool_info = client.get_pool(poolName)

        if not pool_info:
            raise HTTPException(status_code=404, detail="Pool not found")

        return pool_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pool detail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", status_code=201)
async def create_pool(request: PoolCreateRequest, token: str = Depends(AuthValidator.validate_token)):
    """创建资源池"""
    try:
        client = PoolClient.get_instance()
        # 构建资源池配置
        pool_config = {
            "name": request.name,
            "description": request.description,
            "nodes": request.nodes,
            "gpu_type": request.gpuType,
            "quota": request.quota
        }
        
        result = client.create_pool(pool_config)
        
        return {
            "name": request.name,
            "status": "created",
            "message": "资源池创建成功"
        }

    except Exception as e:
        logger.error(f"Failed to create pool: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{poolName}")
async def update_pool(poolName: str, request: PoolUpdateRequest, token: str = Depends(AuthValidator.validate_token)):
    """更新资源池"""
    try:
        # 这里需要实现资源池更新逻辑
        return {
            "name": poolName,
            "status": "updated",
            "message": "资源池更新成功"
        }

    except Exception as e:
        logger.error(f"Failed to update pool: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{poolName}")
async def delete_pool(poolName: str, token: str = Depends(AuthValidator.validate_token)):
    """删除资源池"""
    try:
        client = PoolClient.get_instance()
        success = client.delete_pool(poolName)
        
        if not success:
            raise HTTPException(status_code=404, detail="Pool not found")
        
        return {
            "name": poolName,
            "status": "deleted",
            "message": "资源池删除成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete pool: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")