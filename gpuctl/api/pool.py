from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from .common import GPUType


class NodeConfig(BaseModel):
    gpu_type: GPUType = Field(..., alias="gpu-type")


class ResourcePool(BaseModel):
    kind: str = "pool"
    version: str = "v0.1"
    name: str
    description: Optional[str] = None
    nodes: Dict[str, NodeConfig] = Field(default_factory=dict)

    class Config:
        allow_population_by_field_name = True