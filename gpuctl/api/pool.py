from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class NodeConfig(BaseModel):
    gpu_type: str = Field(..., alias="gpuType")


class PoolInfo(BaseModel):
    name: str
    description: Optional[str] = None


class ResourcePool(BaseModel):
    kind: str = "pool"
    version: str = "v0.1"
    pool: PoolInfo
    nodes: Dict[str, NodeConfig] = Field(default_factory=dict)

    model_config = {
        "populate_by_name": True
    }