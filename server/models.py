from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


# API数据模型
class JobCreateRequest(BaseModel):
    yamlContent: str
    dryRun: bool = False


class JobResponse(BaseModel):
    jobId: str
    name: str
    kind: str
    status: str
    createdAt: Optional[datetime] = None
    message: Optional[str] = None


class JobListResponse(BaseModel):
    total: int
    items: List[Dict[str, Any]]


class BatchCreateRequest(BaseModel):
    yamlContents: List[str]


class BatchCreateResponse(BaseModel):
    success: List[Dict[str, str]]
    failed: List[Dict[str, str]]


class PoolResponse(BaseModel):
    name: str
    description: Optional[str]
    gpuTotal: int
    gpuUsed: int
    gpuFree: int
    gpuType: List[str]
    status: str


class PoolCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    nodes: List[str] = []
    gpuType: Optional[List[str]] = None
    quota: Optional[Dict[str, Any]] = None


class PoolUpdateRequest(BaseModel):
    description: Optional[str] = None
    nodes: Optional[List[str]] = None
    gpuType: Optional[List[str]] = None
    quota: Optional[Dict[str, Any]] = None


class NodeResponse(BaseModel):
    nodeName: str
    status: str
    gpuTotal: int
    gpuUsed: int
    gpuFree: int
    boundPools: List[str]
    cpu: str
    memory: str
    gpuType: Optional[str] = None
    createdAt: Optional[datetime] = None


class NodeDetailResponse(BaseModel):
    nodeName: str
    status: str
    k8sStatus: Dict[str, Any]
    resources: Dict[str, Any]
    gpuDetail: List[Dict[str, Any]]
    labels: List[Dict[str, str]]
    boundPools: List[str]
    runningJobs: List[Dict[str, Any]]
    createdAt: Optional[datetime] = None
    lastUpdatedAt: Optional[datetime] = None


class GPUDetailResponse(BaseModel):
    nodeName: str
    gpuCount: int
    gpus: List[Dict[str, Any]]


class LabelRequest(BaseModel):
    key: str
    value: str
    overwrite: bool = False


class LabelResponse(BaseModel):
    nodeName: str
    label: Dict[str, str]
    message: str


class LogResponse(BaseModel):
    logs: List[str]
    lastTimestamp: Optional[datetime] = None


class AuthCheckRequest(BaseModel):
    resource: str
    action: str
    pool: Optional[str] = None


class AuthCheckResponse(BaseModel):
    allowed: bool
    message: str