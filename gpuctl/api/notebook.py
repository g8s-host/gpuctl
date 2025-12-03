from .common import ResourceRequest, JobMetadata, EnvironmentConfig, StorageConfig
from pydantic import BaseModel, Field

class NotebookJob(BaseModel):
    kind: str = "notebook"
    version: str = "v0.1"
    job: JobMetadata
    environment: EnvironmentConfig
    resources: ResourceRequest
    storage: StorageConfig = Field(default_factory=StorageConfig)

    model_config = {
        "populate_by_name": True
    }