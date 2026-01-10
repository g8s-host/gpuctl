from .common import ResourceRequest, JobMetadata, StorageConfig, EnvironmentConfig, ServiceConfig
from pydantic import BaseModel, Field
from typing import Optional


class ComputeJob(BaseModel):
    kind: str = "compute"
    version: str = "v0.1"
    job: JobMetadata
    environment: EnvironmentConfig
    resources: ResourceRequest
    service: Optional[ServiceConfig] = Field(default_factory=ServiceConfig)
    storage: Optional[StorageConfig] = Field(default_factory=StorageConfig)

    model_config = {
        "populate_by_name": True
    }