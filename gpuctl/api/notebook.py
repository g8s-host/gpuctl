from .common import ResourceRequest, JobMetadata, EnvironmentConfig, StorageConfig, ServiceConfig
from pydantic import BaseModel, Field

class NotebookJob(BaseModel):
    kind: str = "notebook"
    version: str = "v0.1"
    job: JobMetadata
    environment: EnvironmentConfig
    resources: ResourceRequest
    storage: StorageConfig = Field(default_factory=StorageConfig)
    service: ServiceConfig = Field(default_factory=ServiceConfig)

    model_config = {
        "populate_by_name": True
    }