from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum


class ResourceType(str, Enum):
    TRAINING = "training"
    INFERENCE = "inference"
    NOTEBOOK = "notebook"
    POOL = "pool"


class GPUType(str, Enum):
    A100_80G = "a100-80g"
    A100_40G = "a100-40g"
    A10_24G = "a10-24g"
    T4 = "t4"
    V100 = "v100"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResourceRequest(BaseModel):
    pool: Optional[str] = Field(default=None, description="资源池名称")
    gpu: int = Field(..., ge=1, description="GPU数量", alias="accelerator_count")
    gpu_type: Optional[str] = Field(default=None, description="GPU类型", alias="gpu-type")
    cpu: Union[int, str] = Field(..., description="CPU需求，如 8, '8' 或 '8000m'")
    memory: str = Field(..., description="内存需求，如 '32Gi'")
    gpu_share: Optional[str] = Field(default=None, description="GPU共享配置", alias="gpu-share")

    model_config = {
        "populate_by_name": True
    }


class JobMetadata(BaseModel):
    name: str = Field(..., min_length=1, max_length=63)
    description: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    epochs: Optional[int] = Field(default=None, ge=1)
    batch_size: Optional[int] = Field(default=None, ge=1)


class StorageConfig(BaseModel):
    workdirs: List[Dict[str, Any]] = Field(default_factory=list)


class EnvironmentConfig(BaseModel):
    image: str
    image_pull_secret: Optional[str] = Field(default=None, alias="imagePullSecret")
    command: List[str] = Field(default_factory=list)
    args: List[str] = Field(default_factory=list)
    env: List[Dict[str, str]] = Field(default_factory=list)
