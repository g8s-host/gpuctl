"""POST /api/v1/inferences —— Agent 友好的推理部署入口(Agent-First PRD §4.5)。

`kind: inference` 的部署能力早就有(YAML -> POST /api/v1/jobs),这里补的缺口是
**JSON 原生**入口:Agent 不用现学 gpuctl 的 YAML schema,传一个干净的 JSON body 就行。
底层不重复造轮子——请求体在这里翻译成 gpuctl 已有的 `InferenceJob` 模型,然后原样
调用已有的 `InferenceKind().create_inference_service()`(同一条路径 CLI/YAML 也在走)。

查询 / 日志 / 删除**刻意不在这里重复**:`GET /api/v1/jobs?kind=inference`、
`GET /api/v1/jobs/{name}`、`DELETE /api/v1/jobs/{name}` 已经通用地覆盖所有 kind
(见 server/routes/jobs.py),重开一套会重蹈 2026-06 架构评审点名的
"跨前端 dispatch 逻辑重复"覆辙。这里只补 v1 路线图明确要的:手动部署 API。
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from gpuctl.api.common import EnvironmentConfig, JobMetadata, ResourceRequest, ServiceConfig
from gpuctl.api.inference import InferenceJob
from gpuctl.constants import DEFAULT_NAMESPACE, Priority, svc_name
from gpuctl.kind.inference_kind import InferenceKind

router = APIRouter(prefix="/api/v1/inferences", tags=["inferences"])
logger = logging.getLogger(__name__)


class GpuSpec(BaseModel):
    count: int = Field(default=1, ge=0)
    # 保留字段,对齐 Agent-First PRD 的 gpu.type("any"/"A100"...);v1 尚未按类型择卡,仅记录。
    type: Optional[str] = None


class InferenceCreateRequest(BaseModel):
    """PRD §4.5 的 JSON 形状,补了 cpu/memory 的友好默认值(内部 ResourceRequest 要求必填,
    但 Agent 提交推理服务时通常不关心这两个数字)。"""

    name: str = Field(..., min_length=1, max_length=63)
    image: str
    command: Union[str, List[str], None] = None
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    gpu: Union[int, GpuSpec] = Field(default_factory=lambda: GpuSpec(count=1))
    cpu: Union[int, str] = "4"
    memory: str = "16Gi"
    port: int = Field(default=8000, ge=1, le=65535)
    replicas: int = Field(default=1, ge=1)
    pool: Optional[str] = None
    namespace: Optional[str] = None
    priority: Priority = Priority.MEDIUM

    model_config = {"populate_by_name": True}

    @field_validator("gpu", mode="before")
    @classmethod
    def _normalize_gpu(cls, v):
        if isinstance(v, int):
            return GpuSpec(count=v)
        return v

    def to_inference_job(self) -> InferenceJob:
        gpu = self.gpu if isinstance(self.gpu, GpuSpec) else GpuSpec(count=int(self.gpu))
        return InferenceJob(
            job=JobMetadata(name=self.name, priority=self.priority),
            environment=EnvironmentConfig(
                image=self.image,
                command=self.command or [],
                args=self.args,
                env=[self.env] if self.env else [],
            ),
            resources=ResourceRequest(
                pool=self.pool,
                gpu=gpu.count,
                cpu=self.cpu,
                memory=self.memory,
            ),
            service=ServiceConfig(port=self.port, replicas=self.replicas),
        )


class InferenceResponse(BaseModel):
    name: str
    namespace: str
    status: str
    replicas: int
    gpu: int
    port: int
    internal_endpoint: str
    node_port: Optional[int] = None


def _node_port(name: str, namespace: str) -> Optional[int]:
    """服务创建后读一次 NodePort;拿不到就返回 None,不阻断创建结果。"""
    try:
        from kubernetes import client

        svc = client.CoreV1Api().read_namespaced_service(svc_name(name), namespace)
        ports = svc.spec.ports or []
        return ports[0].node_port if ports else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("read nodePort for %s/%s failed: %s", namespace, name, exc)
        return None


@router.post("", response_model=InferenceResponse, status_code=201)
async def create_inference(request: InferenceCreateRequest):
    namespace = request.namespace or DEFAULT_NAMESPACE
    try:
        inference_job = request.to_inference_job()
        InferenceKind().create_inference_service(inference_job, namespace=namespace)
    except ValueError as e:
        # 用户输入类错误(如多机+多副本冲突、命名空间无配额)→ 400,而非 500
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to create inference service: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    gpu_count = request.gpu.count if isinstance(request.gpu, GpuSpec) else int(request.gpu)
    return InferenceResponse(
        name=request.name,
        namespace=namespace,
        status="Starting",
        replicas=request.replicas,
        gpu=gpu_count,
        port=request.port,
        internal_endpoint=f"http://{svc_name(request.name)}.{namespace}.svc.cluster.local:{request.port}",
        node_port=_node_port(request.name, namespace),
    )
