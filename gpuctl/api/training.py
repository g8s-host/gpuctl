from .common import ResourceRequest, JobMetadata, StorageConfig, EnvironmentConfig
from pydantic import BaseModel, Field
from typing import Optional, Literal


class DistributedConfig(BaseModel):
    """已弃用:节点数统一用 resources.nodes 声明(与推理一致)。

    保留本段仅为向后兼容旧 YAML(distributed.workers)与暴露 master_port 这一高级旋钮。
    mode 字段已忽略(nodes>1 即多机)。
    """
    mode: Literal["standalone", "multi-node"] = Field(default="standalone", description="已弃用,忽略")
    workers: int = Field(default=1, ge=1, description="已弃用,请用 resources.nodes;旧 YAML 仍兼容")
    master_port: int = Field(default=29500, description="DDP 通信端口(高级,通常无需改)")

    model_config = {
        "populate_by_name": True
    }


class TrainingJob(BaseModel):
    kind: str = "training"
    version: str = "v0.1"
    job: JobMetadata
    environment: EnvironmentConfig
    resources: ResourceRequest
    distributed: DistributedConfig = Field(default_factory=DistributedConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    model_config = {
        "populate_by_name": True
    }


def resolve_training_nodes(job: "TrainingJob") -> int:
    """统一解析训练节点数:优先 resources.nodes;旧 YAML 的 distributed.workers 作兼容回退。

    nodes>1 即多机(Indexed Job + Headless + DDP env);1 即单机。
    """
    nodes = getattr(job.resources, "nodes", 1) or 1
    d = getattr(job, "distributed", None)
    if nodes <= 1 and d is not None and (d.workers or 1) > 1:
        nodes = d.workers
    return nodes