from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
import logging

from gpuctl.client.pool_client import PoolClient

from server.models import (
    PoolResponse,
    PoolCreateRequest,
    PoolUpdateRequest
)

router = APIRouter(prefix="/api/v1/pools", tags=["pools"])
logger = logging.getLogger(__name__)


@router.get("", response_model=List[PoolResponse])
async def get_pools():
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
async def get_pool_detail(poolName: str):
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
async def create_pool(request: PoolCreateRequest):
    """创建资源池。

    资源池在 gpuctl 里就是「打了 runwhere.ai/pool=<name> 标签的一组节点」——没有节点的空池
    无处持久化(list_pools 按节点标签聚合得来),故至少要绑定一个节点。

    PoolClient.create_pool 期望 nodes 为 {node_name: {gpuType}} 字典(与 YAML/CLI apply 路径
    一致),这里把请求里的 nodes(列表)+ gpuType(按下标对齐的列表)归一成该字典再下传。
    """
    if not request.nodes:
        raise HTTPException(status_code=400, detail="至少需要绑定一个节点（资源池由节点标签构成，空池无法持久化）")

    gpu_types = request.gpuType or []
    nodes_config = {}
    for i, node_name in enumerate(request.nodes):
        cfg = {}
        gpu_type = gpu_types[i] if i < len(gpu_types) else None
        if gpu_type:
            cfg["gpuType"] = gpu_type
        nodes_config[node_name] = cfg

    try:
        client = PoolClient.get_instance()
        client.create_pool({
            "name": request.name,
            "description": request.description,
            "nodes": nodes_config,
        })

        return {
            "name": request.name,
            "status": "created",
            "message": "资源池创建成功"
        }

    except ValueError as e:
        # 节点不存在等校验错误(create_pool → _validate_nodes_exist 抛 ValueError) → 400 透出原因
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create pool: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{poolName}")
async def update_pool(poolName: str, request: PoolUpdateRequest):
    """更新资源池（暂未实现）"""
    raise HTTPException(status_code=501, detail="update_pool is not yet implemented")


@router.delete("/{poolName}")
async def delete_pool(poolName: str):
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

    except ValueError as e:
        # 池内仍有关联任务(delete_pool 抛 ValueError) → 409 透出原因(前端提示先删任务)
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete pool: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
