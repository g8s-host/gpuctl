"""多云集群管理的数据模型"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ClusterStatus(str, Enum):
    """集群健康状态"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ClusterConfig(BaseModel):
    """单个集群配置"""
    
    name: str = Field(
        ..., 
        description="集群名称（用户定义，如 dev/prod）",
        pattern=r"^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=32
    )
    
    provider: str = Field(
        ...,
        description="云厂商类型: ack/tke/cce"
    )
    
    region: Optional[str] = Field(
        default=None,
        description="区域代码（如 cn-hangzhou）",
        max_length=32
    )
    
    kubeconfig_path: str = Field(
        ...,
        description="kubeconfig 文件绝对路径"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="创建时间"
    )
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """验证云厂商类型"""
        allowed = ['ack', 'tke', 'cce']
        if v not in allowed:
            raise ValueError(f"provider must be one of {allowed}")
        return v
    
    @field_validator('kubeconfig_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """验证路径格式"""
        import os
        v = os.path.expanduser(v)
        if not os.path.isabs(v):
            raise ValueError("kubeconfig_path must be absolute path")
        return v


class ClusterRegistry(BaseModel):
    """集群注册表（整个配置文件）"""
    
    version: str = Field(
        default="1.0",
        description="配置文件版本"
    )
    
    default_cluster: Optional[str] = Field(
        default=None,
        description="默认集群名称"
    )
    
    clusters: List[ClusterConfig] = Field(
        default_factory=list,
        description="集群配置列表"
    )
    
    def get_cluster(self, name: str) -> Optional[ClusterConfig]:
        """按名称获取集群配置"""
        for cluster in self.clusters:
            if cluster.name == name:
                return cluster
        return None
    
    def cluster_exists(self, name: str) -> bool:
        """检查集群是否存在"""
        return any(c.name == name for c in self.clusters)
    
    def add_cluster(self, cluster: ClusterConfig) -> None:
        """添加集群（如存在则报错）"""
        if self.cluster_exists(cluster.name):
            raise ValueError(f"Cluster '{cluster.name}' already exists")
        self.clusters.append(cluster)
    
    def remove_cluster(self, name: str) -> bool:
        """删除集群，返回是否成功"""
        for i, cluster in enumerate(self.clusters):
            if cluster.name == name:
                self.clusters.pop(i)
                # 如果删除的是默认集群，清空默认设置
                if self.default_cluster == name:
                    self.default_cluster = None
                return True
        return False
    
    def set_default(self, name: str) -> None:
        """设置默认集群"""
        if not self.cluster_exists(name):
            raise ValueError(f"Cluster '{name}' not found")
        self.default_cluster = name


class ClusterHealth(BaseModel):
    """集群健康状态（运行时检测，不存储）"""
    name: str
    status: ClusterStatus
    message: str
    checked_at: datetime
    node_count: Optional[int] = None
