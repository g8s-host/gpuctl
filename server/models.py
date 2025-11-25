from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PAUSED = "paused"
    TERMINATING = "terminating"

class JobKind(str, Enum):
    TRAINING = "training"
    INFERENCE = "inference"
    NOTEBOOK = "notebook"

class JobCreateRequest(BaseModel):
    yamlContent: str
    dryRun: bool = False

class JobResponse(BaseModel):
    jobId: str
    name: str
    kind: JobKind
    status: JobStatus
    createdAt: Optional[datetime] = None
    message: Optional[str] = None

class JobListItem(BaseModel):
    jobId: str
    name: str
    kind: JobKind
    pool: str
    status: JobStatus
    gpu: int
    gpuType: Optional[str] = None
    startedAt: Optional[datetime] = None
    progress: Optional[float] = None

class JobListResponse(BaseModel):
    total: int
    items: List[JobListItem]

class JobDetailResponse(BaseModel):
    jobId: str
    name: str
    kind: JobKind
    version: str
    yamlContent: str
    status: JobStatus
    pool: str
    resources: Dict[str, Any]
    metrics: Dict[str, Any]
    createdAt: Optional[datetime] = None
    startedAt: Optional[datetime] = None
    k8sResources: Dict[str, Any]

class BatchCreateRequest(BaseModel):
    yamlContents: List[str]

class BatchCreateItem(BaseModel):
    jobId: str
    name: str

class BatchCreateFailedItem(BaseModel):
    index: int
    error: str

class BatchCreateResponse(BaseModel):
    success: List[BatchCreateItem]
    failed: List[BatchCreateFailedItem]

class PoolResponse(BaseModel):
    name: str
    description: Optional[str] = None
    gpuTotal: int
    gpuUsed: int
    gpuFree: int
    gpuType: List[str]
    status: str

class PoolDetailResponse(BaseModel):
    name: str
    description: Optional[str] = None
    nodes: List[str]
    gpuTotal: int
    gpuUsed: int
    gpuFree: int
    gpuType: Dict[str, int]
    quota: Dict[str, Any]
    jobs: List[Dict[str, Any]]

class LogResponse(BaseModel):
    logs: List[str]
    lastTimestamp: Optional[datetime] = None

class MetricDataPoint(BaseModel):
    timestamp: str
    value: float

class JobMetricsResponse(BaseModel):
    gpuUtilization: List[MetricDataPoint]
    memoryUsage: List[MetricDataPoint]
    networkLatency: Optional[List[MetricDataPoint]] = None
    throughput: Optional[List[MetricDataPoint]] = None

class AuthCheckRequest(BaseModel):
    resource: str
    action: str
    pool: Optional[str] = None

class AuthCheckResponse(BaseModel):
    allowed: bool
    message: str

class NodeListItem(BaseModel):
    nodeName: str
    status: str
    gpuTotal: int
    gpuUsed: int
    gpuFree: int
    boundPools: List[str]
    cpu: str
    memory: str
    gpuType: str
    createdAt: str

class NodeListResponse(BaseModel):
    total: int
    items: List[NodeListItem]

class NodeDetailResponse(BaseModel):
    nodeName: str
    status: str
    k8sStatus: Dict[str, Any]
    resources: Dict[str, Any]
    gpuDetail: List[Dict[str, Any]]
    labels: List[Dict[str, str]]
    boundPools: List[str]
    runningJobs: List[Dict[str, Any]]
    createdAt: str
    lastUpdatedAt: str

class LabelOperationRequest(BaseModel):
    key: str
    value: str
    overwrite: bool = False

class BatchLabelOperationRequest(BaseModel):
    nodeNames: List[str]
    key: str
    value: str
    overwrite: bool = False

class LabelOperationResponse(BaseModel):
    nodeName: str
    label: Dict[str, str]
    message: str

class BatchLabelOperationResponse(BaseModel):
    success: List[str]
    failed: List[Dict[str, Any]]
    message: str