from .common import ResourceRequest, JobMetadata, EnvironmentConfig, ServiceConfig
from pydantic import BaseModel, Field
from typing import Optional


class ModelConfig(BaseModel):
    source: str = Field(default="model-registry")
    name: str
    version: str
    format: str = Field(default="safetensors")
    cache: bool = Field(default=True)


class InferenceJob(BaseModel):
    kind: str = "inference"
    version: str = "v0.1"
    job: JobMetadata
    model: Optional[ModelConfig] = None
    environment: EnvironmentConfig
    resources: ResourceRequest
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    # 多机/模型并行 serving 的开关在 resources.nodes(与 pool/gpu/cpu/memory 并列)。
    # nodes>1:StatefulSet + Headless + head-only Service;此时 service.replicas 不生效
    # (StatefulSet 副本数 = resources.nodes = 这一个逻辑副本)。

    model_config = {
        "populate_by_name": True
    }