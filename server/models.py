from pydantic import BaseModel, Field
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


class JobItem(BaseModel):
    jobId: str
    name: str
    namespace: str
    kind: str
    status: str
    ready: str
    node: str
    ip: str
    age: str


class JobListResponse(BaseModel):
    total: int
    items: List[JobItem]


class BatchCreateRequest(BaseModel):
    yamlContents: List[str]


class BatchCreateResponse(BaseModel):
    success: List[Dict[str, str]]
    failed: List[Dict[str, str]]


class JobDetailResponse(BaseModel):
    """任务详情响应，与 CLI describe job --json 输出一致"""
    job_id: str
    name: str
    namespace: str
    kind: str
    resource_type: str = "Unknown"
    status: str
    age: str
    started: Optional[str] = None
    completed: Optional[str] = None
    priority: str = "medium"
    pool: str = "default"
    resources: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    yaml_content: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    access_methods: Optional[Dict[str, Any]] = None


class DeleteResponse(BaseModel):
    jobId: str
    status: str
    message: str


class PoolResponse(BaseModel):
    name: str
    description: Optional[str]
    gpuTotal: int
    gpuUsed: int
    gpuFree: int
    gpuType: List[str]
    status: str


class PoolDetailResponse(BaseModel):
    name: str
    description: Optional[str]
    nodes: List[str]
    gpuTotal: int
    gpuUsed: int
    gpuFree: int
    gpuType: Dict[str, int]
    jobs: List[Dict[str, Any]]


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
    resources: Dict[str, Any]
    labels: List[Dict[str, str]]
    boundPools: List[str]
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