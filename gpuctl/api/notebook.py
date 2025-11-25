from .common import ResourceRequest, JobMetadata, EnvironmentConfig, StorageConfig
from pydantic import BaseModel, Field

class NotebookJobSpec(BaseModel):
    job: JobMetadata
    environment: EnvironmentConfig
    resources: ResourceRequest
    storage: StorageConfig = Field(default_factory=StorageConfig)

class NotebookJob(BaseModel):
    kind: str = "notebook"
    version: str = "v0.1"
    spec: NotebookJobSpec