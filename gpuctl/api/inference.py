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


class InferenceJob(BaseModel):
    kind: str = "inference"
    version: str = "v0.1"
    job: JobMetadata
    model: Optional[ModelConfig] = None
    environment: EnvironmentConfig
    resources: ResourceRequest
    service: ServiceConfig = Field(default_factory=ServiceConfig)

    model_config = {
        "populate_by_name": True
    }