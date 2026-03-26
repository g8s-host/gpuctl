"""集群管理 REST API 路由"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from gpuctl.multicloud.config import (
    ClusterExistsError,
    ClusterNotFoundError,
    add_cluster,
    get_cluster,
    load_config,
    remove_cluster,
    set_default_cluster,
)
from gpuctl.multicloud.models import ClusterConfig, ClusterHealth
from gpuctl.multicloud.validator import check_cluster_health, get_cluster_health

router = APIRouter(prefix="/clusters", tags=["clusters"])


# 请求/响应模型

class ClusterCreateRequest(BaseModel):
    name: str = Field(..., description="集群名称")
    provider: str = Field(..., description="云厂商: ack/tke/cce")
    region: Optional[str] = Field(None, description="区域代码")
    kubeconfig_path: str = Field(..., description="kubeconfig 文件路径")


class ClusterResponse(BaseModel):
    name: str
    provider: str
    region: Optional[str]
    status: str
    message: str
    node_count: Optional[int]
    is_default: bool
    created_at: str


class ClusterListResponse(BaseModel):
    clusters: List[ClusterResponse]
    default_cluster: Optional[str]
    total: int


class SetDefaultRequest(BaseModel):
    name: str


class ValidateKubeconfigRequest(BaseModel):
    kubeconfig_path: str


class ValidateKubeconfigResponse(BaseModel):
    valid: bool
    message: str
    node_count: Optional[int] = None


# API 端点

@router.get("", response_model=ClusterListResponse)
async def list_clusters():
    """列出所有集群"""
    registry = load_config()
    
    clusters = []
    for cluster in registry.clusters:
        health = get_cluster_health(cluster.name, cluster.kubeconfig_path)
        clusters.append(ClusterResponse(
            name=cluster.name,
            provider=cluster.provider,
            region=cluster.region,
            status=health.status.value,
            message=health.message,
            node_count=health.node_count,
            is_default=registry.default_cluster == cluster.name,
            created_at=cluster.created_at.isoformat()
        ))
    
    return ClusterListResponse(
        clusters=clusters,
        default_cluster=registry.default_cluster,
        total=len(clusters)
    )


@router.post("", response_model=ClusterResponse, status_code=201)
async def create_cluster(request: ClusterCreateRequest):
    """添加集群"""
    # 验证 kubeconfig
    is_valid, message, node_count = check_cluster_health(request.kubeconfig_path)
    
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid kubeconfig: {message}")
    
    # 创建集群配置
    from datetime import datetime
    cluster = ClusterConfig(
        name=request.name,
        provider=request.provider,
        region=request.region,
        kubeconfig_path=request.kubeconfig_path,
        created_at=datetime.utcnow()
    )
    
    try:
        add_cluster(cluster)
    except ClusterExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    
    # 如果是第一个集群，设为默认
    registry = load_config()
    if len(registry.clusters) == 1:
        set_default_cluster(request.name)
    
    health = get_cluster_health(cluster.name, cluster.kubeconfig_path)
    return ClusterResponse(
        name=cluster.name,
        provider=cluster.provider,
        region=cluster.region,
        status=health.status.value,
        message=health.message,
        node_count=health.node_count,
        is_default=registry.default_cluster == cluster.name,
        created_at=cluster.created_at.isoformat()
    )


@router.get("/{name}", response_model=ClusterResponse)
async def get_cluster_info(name: str):
    """获取集群详情"""
    cluster = get_cluster(name)
    if not cluster:
        raise HTTPException(status_code=404, detail=f"Cluster '{name}' not found")
    
    registry = load_config()
    health = get_cluster_health(name, cluster.kubeconfig_path)
    
    return ClusterResponse(
        name=cluster.name,
        provider=cluster.provider,
        region=cluster.region,
        status=health.status.value,
        message=health.message,
        node_count=health.node_count,
        is_default=registry.default_cluster == name,
        created_at=cluster.created_at.isoformat()
    )


@router.put("/default")
async def set_default(request: SetDefaultRequest):
    """设置默认集群"""
    try:
        set_default_cluster(request.name)
        return {"message": f"Default cluster set to '{request.name}'"}
    except ClusterNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{name}")
async def delete_cluster(name: str):
    """删除集群"""
    try:
        remove_cluster(name)
        return {"message": f"Cluster '{name}' removed successfully"}
    except ClusterNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/validate", response_model=ValidateKubeconfigResponse)
async def validate_kubeconfig_endpoint(request: ValidateKubeconfigRequest):
    """验证 kubeconfig 文件"""
    is_valid, message, node_count = check_cluster_health(request.kubeconfig_path)
    return ValidateKubeconfigResponse(
        valid=is_valid,
        message=message,
        node_count=node_count if node_count > 0 else None
    )


@router.get("/{name}/health", response_model=ClusterResponse)
async def get_cluster_health_endpoint(name: str):
    """获取集群健康状态"""
    cluster = get_cluster(name)
    if not cluster:
        raise HTTPException(status_code=404, detail=f"Cluster '{name}' not found")
    
    registry = load_config()
    health = get_cluster_health(name, cluster.kubeconfig_path)
    
    return ClusterResponse(
        name=cluster.name,
        provider=cluster.provider,
        region=cluster.region,
        status=health.status.value,
        message=health.message,
        node_count=health.node_count,
        is_default=registry.default_cluster == name,
        created_at=cluster.created_at.isoformat()
    )
