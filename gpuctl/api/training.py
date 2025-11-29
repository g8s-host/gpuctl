from .common import ResourceRequest, JobMetadata, StorageConfig, EnvironmentConfig
from pydantic import BaseModel, Field
from typing import Optional


class TrainingJob(BaseModel):
    kind: str = "training"
    version: str = "v0.1"
    job: JobMetadata
    environment: EnvironmentConfig
    resources: ResourceRequest
    storage: StorageConfig = Field(default_factory=StorageConfig)

    class Config:
        allow_population_by_field_name = True