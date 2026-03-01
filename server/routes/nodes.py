from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging

from gpuctl.client.pool_client import PoolClient
from gpuctl.constants import Labels, DEFAULT_POOL

from server.models import (
    NodeDetailResponse
)

router = APIRouter(prefix="/api/v1/nodes", tags=["nodes"])
logger = logging.getLogger(__name__)


@router.get("", response_model=Dict[str, Any])
async def get_nodes(
        pool: Optional[str] = Query(None, description="资源池过滤"),
        gpuType: Optional[str] = Query(None, description="GPU类型过滤"),
        status: Optional[str] = Query(None, description="节点状态过滤"),
        page: int = Query(1, ge=1),
        pageSize: int = Query(20, ge=1, le=100)
):
    """获取节点列表"""
    try:
        client = PoolClient.get_instance()
        nodes = client.list_nodes()
        
        node_list = []
        for node in nodes:
            if pool:
                labels = node.get("labels", {})
                if labels.get(Labels.POOL) != pool:
                    continue
            
            if gpuType:
                labels = node.get("labels", {})
                if labels.get("nvidia.com/gpu-type") != gpuType:
                    continue
            
            labels = node.get("labels", {})
            pool_name = labels.get(Labels.POOL, "default")
            
            node_info = {
                "nodeName": node["name"],
                "status": node["status"],
                "gpuTotal": node["gpu_total"],
                "gpuUsed": node["gpu_used"],
                "gpuFree": node["gpu_free"],
                "boundPools": [pool_name],
                "cpu": "unknown",
                "memory": "unknown",
                "gpuType": labels.get("nvidia.com/gpu-type", "unknown"),
                "createdAt": None
            }
            
            node_list.append(node_info)
        
        start_idx = (page - 1) * pageSize
        end_idx = start_idx + pageSize
        paginated_nodes = node_list[start_idx:end_idx]
        
        return {
            "total": len(node_list),
            "items": paginated_nodes
        }

    except Exception as e:
        logger.error(f"Failed to get nodes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/gpu-detail", response_model=Dict[str, Any])
async def get_nodes_gpu_detail(
        page: int = Query(1, ge=1),
        pageSize: int = Query(20, ge=1, le=100)
):
    """获取所有节点的GPU详情"""
    try:
        client = PoolClient.get_instance()
        nodes = client.list_nodes()
        
        gpu_detail_list = []
        for node in nodes:
            gpu_count = node["gpu_total"]
            gpus = []
            for i in range(gpu_count):
                gpus.append({
                    "gpuId": f"gpu-{i}",
                    "type": node["gpu_types"][0] if node["gpu_types"] else "unknown",
                    "status": "free",
                    "utilization": 0.0,
                    "memoryUsage": "0Gi/0Gi"
                })
            
            gpu_detail_list.append({
                "nodeName": node["name"],
                "gpuCount": gpu_count,
                "gpus": gpus
            })
        
        start_idx = (page - 1) * pageSize
        end_idx = start_idx + pageSize
        paginated_gpu_detail = gpu_detail_list[start_idx:end_idx]
        
        return {
            "total": len(gpu_detail_list),
            "items": paginated_gpu_detail
        }

    except Exception as e:
        logger.error(f"Failed to get nodes gpu detail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{nodeName}", response_model=NodeDetailResponse)
async def get_node_detail(nodeName: str):
    """获取节点详情"""
    try:
        client = PoolClient.get_instance()
        node = client.get_node(nodeName)
        
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        
        gpu_detail = []
        gpu_count = node["gpu_total"]
        for i in range(gpu_count):
            gpu_detail.append({
                "gpuId": f"gpu-{i}",
                "type": node["gpu_types"][0] if node["gpu_types"] else "unknown",
                "status": "free",
                "utilization": 0.0,
                "memoryUsage": "0Gi/0Gi"
            })
        
        running_jobs = []
        
        labels = []
        for key, value in node.get("labels", {}).items():
            labels.append({"key": key, "value": value})
        
        bound_pools = []
        if node.get("labels", {}).get(Labels.POOL):
            bound_pools.append(node.get("labels", {}).get(Labels.POOL))
        
        return NodeDetailResponse(
            nodeName=node["name"],
            status=node["status"],
            resources={
                "cpuTotal": 0,
                "cpuUsed": 0,
                "memoryTotal": "0",
                "memoryUsed": "0",
                "gpuTotal": gpu_count,
                "gpuUsed": node["gpu_used"],
                "gpuFree": node["gpu_free"]
            },
            labels=labels,
            boundPools=bound_pools,
            createdAt=None,
            lastUpdatedAt=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node detail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{nodeName}/pools")
async def add_node_to_pool(nodeName: str, request: Dict[str, Any]):
    """将节点添加到资源池"""
    try:
        client = PoolClient.get_instance()
        pool = request.get("pool")
        if not pool:
            raise HTTPException(status_code=400, detail="Pool name is required")
        
        result = client.add_nodes_to_pool(pool, [nodeName])
        
        return {
            "node": nodeName,
            "pool": pool,
            "message": "节点已成功添加到资源池"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add node to pool: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{nodeName}/pools/{poolName}")
async def remove_node_from_pool(nodeName: str, poolName: str):
    """从资源池移除节点"""
    try:
        client = PoolClient.get_instance()
        result = client.remove_nodes_from_pool(poolName, [nodeName])
        
        return {
            "node": nodeName,
            "pool": poolName,
            "message": "节点已成功从资源池移除"
        }

    except Exception as e:
        logger.error(f"Failed to remove node from pool: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{nodeName}/labels")
async def get_node_labels(nodeName: str):
    """获取节点标签"""
    try:
        client = PoolClient.get_instance()
        node = client.get_node(nodeName)
        
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        
        return {
            "node": nodeName,
            "labels": node.get("labels", {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node labels: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
