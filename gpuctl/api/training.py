from .common import ResourceRequest, JobMetadata, StorageConfig, EnvironmentConfig
from pydantic import BaseModel, Field
from typing import Optional, Literal


class DistributedConfig(BaseModel):
    mode: Literal["standalone", "distributed"] = Field(default="standalone", description="训练模式")
    workers: int = Field(default=1, ge=1, description="Worker 节点数（仅 distributed 模式有意义）")
    master_port: int = Field(default=29500, description="DDP 通信端口")

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