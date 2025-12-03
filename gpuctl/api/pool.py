from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from .common import GPUType


class NodeConfig(BaseModel):
    gpu_type: GPUType = Field(..., alias="gpu-type")


class PoolConfig(BaseModel):
    name: str
    description: Optional[str] = None


class ResourcePool(BaseModel):
    kind: str = "resource"
    version: str = "v0.1"
    pool: PoolConfig
    nodes: Dict[str, NodeConfig] = Field(default_factory=dict)

    model_config = {
        "populate_by_name": True
    }