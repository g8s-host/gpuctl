from .common import ResourceRequest, JobMetadata, EnvironmentConfig
from pydantic import BaseModel, Field
from typing import Optional


class ModelConfig(BaseModel):
    source: str = Field(default="model-registry")
    name: str
    version: str
    format: str = Field(default="safetensors")
    cache: bool = Field(default=True)


class ServiceConfig(BaseModel):
    replicas: int = Field(default=1, ge=1)
    port: int = Field(default=8000, ge=1, le=65535)
    health_check: Optional[str] = Field(default=None, alias="health_check")
    timeout: Optional[str] = Field(default=None)


class AutoScalingConfig(BaseModel):
    enabled: bool = Field(default=False)
    min_replicas: int = Field(default=1, ge=1)
    max_replicas: int = Field(default=10, ge=1)
    target_gpu_utilization: int = Field(default=70, ge=1, le=100, alias="targetGPUUtilization")
    target_memory_utilization: Optional[int] = Field(default=None, ge=1, le=100, alias="targetMemoryUtilization")


class InferenceJobSpec(BaseModel):
    job: JobMetadata
    model: Optional[ModelConfig] = None
    environment: EnvironmentConfig
    resources: ResourceRequest
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    autoscaling: AutoScalingConfig = Field(default_factory=AutoScalingConfig)

    class Config:
        allow_population_by_field_name = True


class InferenceJob(BaseModel):
    kind: str = "inference"
    version: str = "v0.1"
    spec: InferenceJobSpec