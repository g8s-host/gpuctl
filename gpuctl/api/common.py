import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from enum import Enum

from gpuctl.constants import Kind, Priority


_DURATION_RE = re.compile(r"^([0-9]+)([smh]?)$")


def parse_duration_seconds(value) -> int:
    """把 '600' / '600s' / '10m' / '1h' 解析成秒；无单位按秒。非法格式抛 ValueError。"""
    m = _DURATION_RE.match(str(value).strip())
    if not m:
        raise ValueError(f"无效的时长 {value!r}，请用如 '600'、'600s'、'10m'、'1h'")
    return int(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600}[m.group(2)]


class ResourceType(str, Enum):
    TRAINING = Kind.TRAINING
    INFERENCE = Kind.INFERENCE
    NOTEBOOK = Kind.NOTEBOOK
    POOL = "pool"


class GPUType(str, Enum):
    A100_80G = "a100-80g"
    A100_40G = "a100-40g"
    A10_24G = "a10-24g"
    T4 = "t4"
    V100 = "v100"


class ResourceRequest(BaseModel):
    pool: Optional[str] = Field(default=None, description="资源池名称")
    # 一个逻辑副本横跨的节点数。1(默认)= 单 Pod;>1 仅推理(inference)启用多机/模型并行
    # serving(StatefulSet + Headless + head-only Service)。与 pool/gpu/cpu/memory 并列:
    # resources 描述"一个节点的形状",nodes 描述"几个这样的节点"(总卡 = nodes × gpu)。
    nodes: int = Field(default=1, ge=1, description="副本横跨的节点数;>1 启用多机推理")
    gpu: int = Field(default=0, ge=0, description="GPU数量", alias="accelerator_count")
    gpu_type: Optional[str] = Field(default=None, description="GPU类型", alias="gpuType")
    cpu: Union[int, str] = Field(..., description="CPU需求，如 8, '8' 或 '8000m'")
    memory: str = Field(..., description="内存需求，如 '32Gi'")
    gpu_share: Optional[str] = Field(default=None, description="GPU共享配置", alias="gpuShare")
    cluster: Optional[str] = Field(default=None, description="目标集群名称（如 dev/prod）")

    model_config = {
        "populate_by_name": True
    }


class JobMetadata(BaseModel):
    name: str = Field(..., min_length=1, max_length=63)
    description: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    epochs: Optional[int] = Field(default=None, ge=1)
    batch_size: Optional[int] = Field(default=None, ge=1)
    namespace: Optional[str] = None


class StorageConfig(BaseModel):
    workdirs: List[Dict[str, Any]] = Field(default_factory=list)


class ServiceConfig(BaseModel):
    replicas: int = Field(default=1, ge=1)
    port: int = Field(default=8000, ge=1, le=65535)
    health_check: Optional[str] = Field(default=None, alias="healthCheck")
    # 服务从「启动」到「健康检查通过」允许的最长时间（如 '10m'、'600s'）。映射为 K8s startupProbe：
    # 这段时间内即使 /health 还没通也不会被存活探针杀掉——适配「先下载/加载模型、暖数据再服务」的慢启动。
    # 不设则默认 10m（见 inference_builder）。这是唯一暴露的探针旋钮；检查周期/单次超时/失败阈值等
    # 都走 builder 的合理默认，不向用户暴露 K8s 细节。
    startup_timeout: Optional[str] = Field(default=None, alias="startupTimeout")

    model_config = {"populate_by_name": True}

    @field_validator("startup_timeout")
    @classmethod
    def _check_startup_timeout(cls, v):
        if v is not None:
            parse_duration_seconds(v)  # 仅校验格式，非法即报错
        return v


class EnvironmentConfig(BaseModel):
    notebook: Optional[str] = Field(default=None, description="引用 Notebook 名称，用于确定 NFS home 路径")
    image: str
    conda: Optional[str] = Field(default=None, description="conda 环境名，未指定时直接执行 command")
    image_pull_secret: Optional[str] = Field(default=None, alias="imagePullSecret")
    command: Union[str, List[str]] = Field(default_factory=list)
    args: List[str] = Field(default_factory=list)
    env: List[Dict[str, str]] = Field(default_factory=list)

    @field_validator("command", mode="before")
    @classmethod
    def normalize_command(cls, v):
        if isinstance(v, str):
            return ["bash", "-c", v]
        return v
