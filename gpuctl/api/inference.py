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

    model_config = {
        "populate_by_name": True
    }