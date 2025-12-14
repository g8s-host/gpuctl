from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
import logging

from gpuctl.client.pool_client import PoolClient

from server.models import (
    LabelRequest,
    LabelResponse
)
from server.auth import AuthValidator, security

# 节点标签相关路由
router = APIRouter(prefix="/api/v1/nodes", tags=["labels"])

# 全局标签相关路由
global_labels_router = APIRouter(prefix="/api/v1", tags=["labels"])

logger = logging.getLogger(__name__)


@router.post("/{nodeName}/labels", response_model=LabelResponse)
async def add_node_label(nodeName: str, request: LabelRequest, token: str = Depends(AuthValidator.validate_token)):
    """给指定节点添加Label"""
    try:
        client = PoolClient()
        
        # 添加Label
        client._label_node(nodeName, request.key, request.value)
        
        return {
            "nodeName": nodeName,
            "label": {request.key: request.value},
            "message": "标签添加成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add node label: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/labels/batch")
async def batch_add_node_labels(
        nodeNames: List[str] = Query(..., description="节点名称列表"),
        key: str = Query(..., description="Label键"),
        value: str = Query(..., description="Label值"),
        overwrite: bool = Query(False, description="是否覆盖已有同键Label"),
        token: str = Depends(AuthValidator.validate_token)
):
    """批量给多个节点添加Label"""
    try:
        client = PoolClient()
        
        success = []
        failed = []
        
        for node_name in nodeNames:
            try:
                # 检查节点是否存在
                node = client.core_v1.read_node(node_name)
                
                # 检查Label是否已存在
                existing_labels = node.metadata.labels or {}
                if key in existing_labels and not overwrite:
                    failed.append({"nodeName": node_name, "error": f"Label {key} already exists"})
                    continue
                
                # 添加Label
                client._label_node(node_name, key, value)
                success.append(node_name)
            except Exception as e:
                failed.append({"nodeName": node_name, "error": str(e)})
        
        return {
            "success": success,
            "failed": failed,
            "message": "批量标记节点 Label 完成"
        }

    except Exception as e:
        logger.error(f"Failed to batch add node labels: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{nodeName}/labels/{key}", response_model=Dict[str, Any])
async def get_node_label(nodeName: str, key: str, token: str = Depends(AuthValidator.validate_token)):
    """查询指定节点的指定Label"""
    try:
        client = PoolClient()
        
        # 获取节点信息
        node = client.core_v1.read_node(nodeName)
        
        # 获取Label值
        labels = node.metadata.labels or {}
        if key not in labels:
            raise HTTPException(status_code=404, detail=f"节点 {nodeName} 未找到键为 {key} 的 Label")
        
        return {
            "nodeName": nodeName,
            "label": {
                "key": key,
                "value": labels[key],
                "createdAt": node.metadata.creation_timestamp,
                "lastUpdatedAt": node.metadata.creation_timestamp
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node label: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{nodeName}/labels", response_model=Dict[str, Any])
async def get_node_labels(nodeName: str, token: str = Depends(AuthValidator.validate_token)):
    """查询指定节点的所有Label"""
    try:
        client = PoolClient()
        
        # 获取节点信息
        node = client.get_node(nodeName)
        
        # 获取所有Label
        labels = node.get("labels", {})
        
        return {
            "node": nodeName,
            "labels": labels
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node labels: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/labels", response_model=Dict[str, Any])
async def get_nodes_labels(
        key: str = Query(..., description="要查询的Label键"),
        page: int = Query(1, ge=1),
        pageSize: int = Query(20, ge=1, le=100),
        token: str = Depends(AuthValidator.validate_token)
):
    """查询所有节点的指定Label"""
    try:
        client = PoolClient()
        
        # 获取所有节点
        nodes = client.core_v1.list_node()
        
        # 构建Label列表
        label_list = []
        for node in nodes.items:
            labels = node.metadata.labels or {}
            if key in labels:
                label_list.append({
                    "nodeName": node.metadata.name,
                    "labelKey": key,
                    "labelValue": labels[key]
                })
        
        # 分页
        start_idx = (page - 1) * pageSize
        end_idx = start_idx + pageSize
        paginated_labels = label_list[start_idx:end_idx]
        
        return {
            "total": len(label_list),
            "items": paginated_labels
        }

    except Exception as e:
        logger.error(f"Failed to get nodes labels: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/labels/all", response_model=Dict[str, Any])
async def get_all_nodes_labels(
        page: int = Query(1, ge=1),
        pageSize: int = Query(20, ge=1, le=100),
        token: str = Depends(AuthValidator.validate_token)
):
    """列出所有节点的GPU相关Label及绑定资源池"""
    try:
        client = PoolClient()
        
        # 获取所有节点
        nodes = client.core_v1.list_node()
        
        # 构建节点Label列表
        node_label_list = []
        for node in nodes.items:
            labels = node.metadata.labels or {}
            gpu_labels = []
            bound_pools = []
            
            # 提取GPU相关Label
            for key, value in labels.items():
                if key.startswith("nvidia.com/gpu-") or key.endswith("gpu-type") or key.endswith("gpu-model"):
                    gpu_labels.append({"key": key, "value": value})
                
            # 提取绑定的资源池
            if "g8s.host/pool" in labels:
                bound_pools.append(labels["g8s.host/pool"])
            
            node_label_list.append({
                "nodeName": node.metadata.name,
                "gpuLabels": gpu_labels,
                "boundPools": bound_pools
            })
        
        # 分页
        start_idx = (page - 1) * pageSize
        end_idx = start_idx + pageSize
        paginated_node_labels = node_label_list[start_idx:end_idx]
        
        return {
            "total": len(node_label_list),
            "items": paginated_node_labels
        }

    except Exception as e:
        logger.error(f"Failed to get all nodes labels: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{nodeName}/labels/{key}")
async def delete_node_label(nodeName: str, key: str, token: str = Depends(AuthValidator.validate_token)):
    """删除指定节点的指定Label"""
    try:
        client = PoolClient()
        
        # 删除Label
        client._remove_node_label(nodeName, key)
        
        return {
            "node": nodeName,
            "label": key,
            "message": "标签删除成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete node label: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{nodeName}/labels/{key}")
async def update_node_label(nodeName: str, key: str, request: Dict[str, Any], token: str = Depends(AuthValidator.validate_token)):
    """更新指定节点的指定Label"""
    try:
        client = PoolClient()
        
        # 更新Label
        value = request.get("value")
        if not value:
            raise HTTPException(status_code=400, detail="Label值不能为空")
        
        client._label_node(nodeName, key, value)
        
        return {
            "node": nodeName,
            "label": f"{key}={value}",
            "message": "标签更新成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update node label: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@global_labels_router.get("/labels")
async def list_all_node_labels(token: str = Depends(AuthValidator.validate_token)):
    """获取所有节点标签"""
    try:
        client = PoolClient()
        
        # 获取所有节点
        nodes = client.list_nodes()
        
        # 构建标签统计
        label_stats = {}
        for node in nodes:
            labels = node.get("labels", {})
            for key, value in labels.items():
                if key not in label_stats:
                    label_stats[key] = set()
                label_stats[key].add(value)
        
        # 转换为列表格式
        result = {}
        for key, values in label_stats.items():
            result[key] = list(values)
        
        return result

    except Exception as e:
        logger.error(f"Failed to list all node labels: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# 导出路由
__all__ = ["router", "global_labels_router"]