from .common import ResourceRequest, JobMetadata, StorageConfig, EnvironmentConfig
from pydantic import BaseModel, Field
from typing import Optional


class TrainingJobSpec(BaseModel):
    job: JobMetadata
    environment: EnvironmentConfig
    resources: ResourceRequest
    storage: StorageConfig = Field(default_factory=StorageConfig)
    epochs: Optional[int] = Field(default=None, ge=1)
    batch_size: Optional[int] = Field(default=None, ge=1)

    class Config:
        allow_population_by_field_name = True


class TrainingJob(BaseModel):
    kind: str = "training"
    version: str = "v0.1"
    spec: TrainingJobSpec