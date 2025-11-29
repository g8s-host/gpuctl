from .common import ResourceRequest, JobMetadata, EnvironmentConfig, StorageConfig
from pydantic import BaseModel, Field

class NotebookJob(BaseModel):
    kind: str = "notebook"
    version: str = "v0.1"
    job: JobMetadata
    environment: EnvironmentConfig
    resources: ResourceRequest
    storage: StorageConfig = Field(default_factory=StorageConfig)

    class Config:
        allow_population_by_field_name = True