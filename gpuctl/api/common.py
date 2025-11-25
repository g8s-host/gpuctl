from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
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
    accelerator_count: int = Field(..., ge=1, description="加速器数量")
    gpu_type: Optional[GPUType] = Field(default=None, description="GPU类型")
    cpu: str = Field(..., description="CPU需求，如 '8' 或 '8000m'")
    memory: str = Field(..., description="内存需求，如 '32Gi'")
    gpu_share: Optional[str] = Field(default=None, description="GPU共享配置")


class JobMetadata(BaseModel):
    name: str = Field(..., min_length=1, max_length=63)
    description: Optional[str] = None
    priority: Priority = Priority.MEDIUM


class StorageConfig(BaseModel):
    workdirs: List[Dict[str, Any]] = Field(default_factory=list)


class EnvironmentConfig(BaseModel):
    image: str
    image_pull_secret: Optional[str] = Field(default=None, alias="imagePullSecret")
    command: List[str] = Field(default_factory=list)
    args: List[str] = Field(default_factory=list)
    env: List[Dict[str, str]] = Field(default_factory=list)
