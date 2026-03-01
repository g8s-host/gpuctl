from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import asyncio
import json

from gpuctl.parser.base_parser import BaseParser, ParserError
from gpuctl.kind.training_kind import TrainingKind
from gpuctl.kind.inference_kind import InferenceKind
from gpuctl.kind.notebook_kind import NotebookKind
from gpuctl.kind.compute_kind import ComputeKind
from gpuctl.client.job_client import JobClient
from gpuctl.client.log_client import LogClient

from server.models import (
    JobCreateRequest,
    JobResponse,
    JobListResponse,
    JobItem,
    JobDetailResponse,
    DeleteResponse,
    BatchCreateRequest,
    BatchCreateResponse,
    LogResponse
)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)


# 存储WebSocket连接
active_connections = []


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(request: JobCreateRequest):
    """创建任务"""
    logger.debug(f"开始创建任务，请求内容: {request.yamlContent[:100]}...")
    try:
        # 解析YAML
        logger.debug("正在解析YAML配置")
        parsed_obj = BaseParser.parse_yaml(request.yamlContent)
        logger.debug(f"YAML解析成功，任务类型: {parsed_obj.kind}")

        # 根据任务类型处理
        if parsed_obj.kind == "training":
            logger.debug("处理训练任务")
            handler = TrainingKind()
            result = handler.create_training_job(parsed_obj, namespace="default")
        elif parsed_obj.kind == "inference":
            logger.debug("处理推理服务任务")
            handler = InferenceKind()
            result = handler.create_inference_service(parsed_obj, namespace="default")
        elif parsed_obj.kind == "notebook":
            logger.debug("处理Notebook任务")
            handler = NotebookKind()
            result = handler.create_notebook(parsed_obj, namespace="default")
        elif parsed_obj.kind == "compute":
            logger.debug("处理计算任务")
            handler = ComputeKind()
            result = handler.create_compute_service(parsed_obj, namespace="default")
        else:
            logger.error(f"不支持的任务类型: {parsed_obj.kind}")
            raise HTTPException(status_code=400, detail=f"Unsupported job kind: {parsed_obj.kind}")

        return JobResponse(
            jobId=result["job_id"],
            name=result["name"],
            kind=parsed_obj.kind,
            status="pending",
            createdAt=datetime.utcnow(),
            message="任务已提交至资源池"
        )

    except ParserError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batch", response_model=BatchCreateResponse, status_code=201)
async def create_jobs_batch(request: BatchCreateRequest):
    """批量创建任务"""
    success = []
    failed = []

    for i, yaml_content in enumerate(request.yamlContents):
        try:
            parsed_obj = BaseParser.parse_yaml(yaml_content)

            if parsed_obj.kind == "training":
                handler = TrainingKind()
                result = handler.create_training_job(parsed_obj, namespace="default")
            elif parsed_obj.kind == "inference":
                handler = InferenceKind()
                result = handler.create_inference_service(parsed_obj, namespace="default")
            elif parsed_obj.kind == "notebook":
                handler = NotebookKind()
                result = handler.create_notebook(parsed_obj, namespace="default")
            elif parsed_obj.kind == "compute":
                handler = ComputeKind()
                result = handler.create_compute_service(parsed_obj, namespace="default")
            else:
                failed.append({"index": i, "error": f"Unsupported kind: {parsed_obj.kind}"})
                continue

            success.append({"jobId": result["job_id"], "name": result["name"]})

        except Exception as e:
            failed.append({"index": i, "error": str(e)})

    return BatchCreateResponse(success=success, failed=failed)


def _calculate_age(created_at_str) -> str:
    """计算创建时间到现在的时长"""
    if not created_at_str:
        return "N/A"
    try:
        from datetime import timezone
        created_at = datetime.fromisoformat(str(created_at_str).replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = now - created_at
        seconds = delta.total_seconds()
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m"
        elif seconds < 86400:
            return f"{int(seconds/3600)}h"
        else:
            return f"{int(seconds/86400)}d"
    except Exception:
        return "N/A"


def _get_detailed_status(waiting_reason: str, waiting_message: str) -> str:
    """从容器等待原因获取详细状态"""
    status_mapping = {
        "ImagePullBackOff": "ImagePullBackOff",
        "ErrImagePull": "ErrImagePull",
        "CrashLoopBackOff": "CrashLoopBackOff",
        "CreateContainerConfigError": "CreateContainerConfigError",
        "ContainerCreating": "ContainerCreating",
        "CreateContainerError": "CreateContainerError",
    }
    if waiting_reason in status_mapping:
        return status_mapping[waiting_reason]
    return waiting_reason if waiting_reason else "Waiting"


@router.get("", response_model=JobListResponse)
async def get_jobs(
        kind: Optional[str] = Query(None, description="任务类型过滤"),
        pool: Optional[str] = Query(None, description="资源池过滤"),
        status: Optional[str] = Query(None, description="状态过滤"),
        namespace: Optional[str] = Query(None, description="命名空间过滤"),
        page: int = Query(1, ge=1),
        pageSize: int = Query(20, ge=1, le=100)
):
    """获取任务列表（Pod级别，与CLI gpuctl get jobs 输出一致）"""
    try:
        client = JobClient()

        labels = {}
        if kind:
            labels["g8s.host/job-type"] = kind
        if pool:
            labels["g8s.host/pool"] = pool

        # 使用 include_pods=True 获取 Pod 级别数据，与 CLI 一致
        jobs = client.list_jobs(namespace=namespace, labels=labels, include_pods=True)

        # 状态过滤
        if status:
            status_lower = status.lower()
            filtered_jobs = []
            for job in jobs:
                status_dict = job.get("status", {})
                job_phase = status_dict.get("phase", "Unknown")
                phase_lower = job_phase.lower()
                container_statuses = status_dict.get("container_statuses", [])
                job_status_str = job_phase
                if container_statuses:
                    for cs in container_statuses:
                        if hasattr(cs, 'state') and cs.state and hasattr(cs.state, 'waiting') and cs.state.waiting:
                            job_status_str = _get_detailed_status(
                                getattr(cs.state.waiting, 'reason', '') or '',
                                getattr(cs.state.waiting, 'message', '') or ''
                            )
                            break
                if phase_lower == status_lower or job_status_str.lower() == status_lower:
                    filtered_jobs.append(job)
            jobs = filtered_jobs

        total = len(jobs)
        start_idx = (page - 1) * pageSize
        end_idx = start_idx + pageSize
        paginated_jobs = jobs[start_idx:end_idx]

        items = []
        for job in paginated_jobs:
            labels = job.get("labels", {})
            job_type = labels.get("g8s.host/job-type", "unknown")
            if job_type == "unknown" and "job-name" in labels:
                job_type = "training"

            status_dict = job.get("status", {})
            job_phase = status_dict.get("phase", "Unknown")
            job_status = job_phase

            container_statuses = status_dict.get("container_statuses", [])
            if container_statuses:
                for cs in container_statuses:
                    if hasattr(cs, 'state') and cs.state:
                        if hasattr(cs.state, 'waiting') and cs.state.waiting:
                            job_status = _get_detailed_status(
                                getattr(cs.state.waiting, 'reason', '') or '',
                                getattr(cs.state.waiting, 'message', '') or ''
                            )
                            break
                        if hasattr(cs.state, 'terminated') and cs.state.terminated:
                            reason = getattr(cs.state.terminated, 'reason', '') or ''
                            if reason == "OOMKilled":
                                job_status = "OOMKilled"
                            elif reason == "Error":
                                job_status = "Error"
                            break

            pod_name = job["name"]
            simplified_name = pod_name
            parts = simplified_name.split('-')
            if len(parts) >= 3:
                third_part = parts[2] if len(parts) >= 3 else ''
                if third_part.isalnum() and len(third_part) >= 5:
                    final_name = '-'.join(parts[:2])
                else:
                    final_name = simplified_name
            else:
                final_name = simplified_name

            node_name = job.get("spec", {}).get("node_name") or "N/A"
            pod_ip = status_dict.get("pod_ip") or "N/A"

            total_containers = len(container_statuses)
            ready_containers = 0
            if container_statuses:
                for cs in container_statuses:
                    if hasattr(cs, 'ready') and cs.ready:
                        ready_containers += 1
            ready_str = f"{ready_containers}/{total_containers}" if total_containers > 0 else "0/0"
            age = _calculate_age(job.get("creation_timestamp"))

            job_item = JobItem(
                jobId=pod_name,
                name=final_name,
                namespace=job.get("namespace", "default"),
                kind=job_type,
                status=job_status,
                ready=ready_str,
                node=node_name,
                ip=pod_ip,
                age=age
            )
            items.append(job_item)

        return JobListResponse(total=total, items=items)

    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def _job_detail_calculate_age(created_at_str) -> str:
    """计算 age 字段"""
    if not created_at_str:
        return "N/A"
    try:
        from datetime import timezone
        created_at = datetime.fromisoformat(str(created_at_str).replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = now - created_at
        seconds = delta.total_seconds()
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m"
        elif seconds < 86400:
            return f"{int(seconds/3600)}h"
        else:
            return f"{int(seconds/86400)}d"
    except Exception:
        return "N/A"


def _job_detail_compute_status(job_info: dict) -> str:
    """计算任务状态，与 CLI describe 一致"""
    status_dict = job_info.get("status", {})
    # Pod 有 phase 字段
    if "phase" in status_dict:
        phase = status_dict.get("phase", "Unknown")
        container_statuses = status_dict.get("container_statuses", [])
        if container_statuses:
            for cs in container_statuses:
                if hasattr(cs, 'state') and cs.state:
                    if hasattr(cs.state, 'waiting') and cs.state.waiting:
                        reason = getattr(cs.state.waiting, 'reason', '') or ''
                        return _get_detailed_status(reason, getattr(cs.state.waiting, 'message', '') or '')
                    if hasattr(cs.state, 'terminated') and cs.state.terminated:
                        reason = getattr(cs.state.terminated, 'reason', '') or ''
                        if reason == "OOMKilled":
                            return "OOMKilled"
                        if reason == "Error":
                            return "Error"
        return phase
    # Controller 有 active/succeeded/failed
    if status_dict.get("succeeded", 0) > 0:
        return "Succeeded"
    if status_dict.get("failed", 0) > 0:
        return "Failed"
    if status_dict.get("active", 0) > 0:
        return "Running"
    if status_dict.get("ready_replicas", 0) > 0:
        return "Running"
    return "Pending"


def _compute_resource_type(job_info: dict, job_type: str) -> str:
    """根据 status 字段推断 Kubernetes 资源类型"""
    status_dict = job_info.get("status", {})
    if "phase" in status_dict:
        return "Pod"
    if "ready_replicas" in status_dict:
        return "StatefulSet" if job_type == "notebook" else "Deployment"
    if "active" in status_dict and "succeeded" in status_dict and "failed" in status_dict:
        return "Job"
    # 回退到 kind 推断
    if job_type == "training":
        return "Job"
    if job_type == "notebook":
        return "StatefulSet"
    if job_type in ("inference", "compute"):
        return "Deployment"
    return "Pod"


def _fetch_events(job_name: str, namespace: str, resource_type: str) -> list:
    """从 Kubernetes 获取资源事件列表"""
    try:
        from gpuctl.client.base_client import KubernetesClient
        k8s = KubernetesClient()
        evs = k8s.core_v1.list_namespaced_event(
            namespace=namespace,
            field_selector=f"involvedObject.name={job_name},involvedObject.kind={resource_type}",
            limit=10
        )
        sorted_evs = sorted(
            evs.items,
            key=lambda e: e.last_timestamp or e.first_timestamp or e.event_time or '',
            reverse=True
        )[:10]

        result = []
        for ev in sorted_evs:
            ts = ev.last_timestamp or ev.first_timestamp or ev.event_time
            ts_str = None
            if ts:
                ts_str = ts.isoformat()
                if '.' in ts_str:
                    ts_str = ts_str.split('.')[0] + 'Z'
            # 简单年龄格式化
            age_str = "N/A"
            if ts_str:
                try:
                    from datetime import timezone
                    t = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    delta = datetime.now(timezone.utc) - t
                    s = delta.total_seconds()
                    if s < 60:
                        age_str = f"{int(s)}s"
                    elif s < 3600:
                        age_str = f"{int(s/60)}m"
                    elif s < 86400:
                        age_str = f"{int(s/3600)}h"
                    else:
                        age_str = f"{int(s/86400)}d"
                except Exception:
                    age_str = ts_str
            result.append({
                "age": age_str,
                "type": ev.type or "Normal",
                "reason": ev.reason or "-",
                "from": ev.source.component if ev.source and ev.source.component else "-",
                "object": f"{ev.involved_object.kind}/{ev.involved_object.name}",
                "message": ev.message or "-"
            })
        return result
    except Exception:
        return []


def _fetch_access_methods(job_name: str, namespace: str, job_type: str, resource_type: str) -> Optional[Dict[str, Any]]:
    """获取 inference/compute/notebook 的访问方式"""
    if job_type not in ("inference", "compute", "notebook"):
        return None

    # 计算服务名
    svc_base = job_name
    if job_type == "notebook":
        parts = svc_base.split('-')
        if len(parts) >= 2 and parts[-1].isdigit():
            svc_base = '-'.join(parts[:-1])
    elif resource_type == "Pod":
        parts = svc_base.split('-')
        if len(parts) >= 3 and parts[2].isalnum() and len(parts[2]) >= 5:
            svc_base = '-'.join(parts[:2])

    target_port = None
    service_port = None
    node_port = None
    node_ip = None
    pod_ip = None
    is_running = False

    try:
        from gpuctl.client.base_client import KubernetesClient
        k8s = KubernetesClient()
        svc = k8s.core_v1.read_namespaced_service(
            name=f"svc-{svc_base}", namespace=namespace
        ).to_dict()
        if svc["spec"]["ports"]:
            p = svc["spec"]["ports"][0]
            target_port = p.get("target_port")
            service_port = p.get("port")
            node_port = p.get("node_port")
    except Exception:
        pass

    try:
        from gpuctl.client.base_client import KubernetesClient
        k8s2 = KubernetesClient()
        nodes = k8s2.core_v1.list_node().items
        if nodes:
            for addr in (nodes[0].to_dict().get("status", {}).get("addresses", [])):
                if addr.get("type") == "InternalIP":
                    node_ip = addr.get("address")
                    break
    except Exception:
        pass

    try:
        from gpuctl.client.base_client import KubernetesClient
        k8s3 = KubernetesClient()
        if resource_type == "Pod":
            pod = k8s3.core_v1.read_namespaced_pod(name=job_name, namespace=namespace)
            is_running = pod.status.phase == "Running"
            pod_ip = pod.status.pod_ip
        else:
            pods = k8s3.core_v1.list_namespaced_pod(
                namespace=namespace, label_selector=f"app={job_name}"
            )
            for pod in pods.items:
                if pod.status.phase == "Running":
                    is_running = True
                    pod_ip = pod.status.pod_ip
                    break
    except Exception:
        pass

    port = target_port or service_port
    return {
        "pod_ip_access": {
            "pod_ip": pod_ip if is_running else None,
            "port": port,
            "url": f"http://{pod_ip}:{port}" if (is_running and pod_ip and port) else None
        },
        "node_port_access": {
            "node_ip": node_ip,
            "node_port": node_port,
            "url": f"http://{node_ip}:{node_port}" if (node_ip and node_port) else None
        }
    }


@router.get("/{jobId}", response_model=JobDetailResponse)
async def get_job_detail(
        jobId: str,
        namespace: Optional[str] = Query(None, description="命名空间，不指定时搜索所有 gpuctl 命名空间")
):
    """获取任务详情，与 CLI describe job --json 输出一致（含 events / access_methods）"""
    try:
        client = JobClient()
        ns = namespace or "default"

        # 先尝试按控制器名称查找 (Job/Deployment/StatefulSet)
        job_info = client.get_job(jobId, ns)

        # 若未找到，尝试按 Pod 名称查找（支持跨命名空间搜索）
        if not job_info:
            job_info = client.get_pod(jobId, namespace if namespace else None)

        if not job_info:
            raise HTTPException(status_code=404, detail="Job not found")

        labels = job_info.get("labels", {})
        job_type = labels.get("g8s.host/job-type", "unknown")
        actual_ns = job_info.get("namespace", "default")
        job_name = job_info.get("name", jobId)

        resource_type = _compute_resource_type(job_info, job_type)

        # yaml_content
        try:
            from gpuctl.cli.job_mapper import map_k8s_to_gpuctl
            yaml_content = map_k8s_to_gpuctl(job_info)
        except Exception:
            yaml_content = {}

        events = _fetch_events(job_name, actual_ns, resource_type)
        access_methods = _fetch_access_methods(job_name, actual_ns, job_type, resource_type)

        return JobDetailResponse(
            job_id=job_name,
            name=job_name,
            namespace=actual_ns,
            kind=job_type,
            resource_type=resource_type,
            status=_job_detail_compute_status(job_info),
            age=_job_detail_calculate_age(job_info.get("creation_timestamp")),
            started=job_info.get("start_time"),
            completed=job_info.get("completion_time"),
            priority=labels.get("g8s.host/priority", "medium"),
            pool=labels.get("g8s.host/pool", "default"),
            resources=job_info.get("resources", {}),
            metrics=job_info.get("metrics", {}),
            yaml_content=yaml_content,
            events=events,
            access_methods=access_methods
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job detail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{jobId}", response_model=DeleteResponse)
async def delete_job(jobId: str, force: bool = Query(False, description="是否强制删除")):
    """删除任务"""
    try:
        client = JobClient()
        success = client.delete_job(jobId, force=force)

        if not success:
            raise HTTPException(status_code=404, detail="Job not found")

        return DeleteResponse(
            jobId=jobId,
            status="terminating",
            message="任务删除指令已下发"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete job: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")





@router.get("/{jobId}/logs", response_model=LogResponse)
async def get_job_logs(
        jobId: str,
        follow: bool = False,
        tail: int = Query(100, ge=1),
        pod: Optional[str] = Query(None)
):
    """获取任务日志"""
    try:
        client = LogClient()

        if follow:
            # 对于follow请求，应该使用WebSocket
            raise HTTPException(status_code=400, detail="Use WebSocket for follow mode")

        logs = client.get_job_logs(jobId, tail=tail, pod_name=pod)

        return LogResponse(
            logs=logs,
            lastTimestamp=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"Failed to get job logs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.websocket("/{jobId}/logs/ws")
async def websocket_job_logs(websocket: WebSocket, jobId: str):
    """WebSocket实时日志"""
    await websocket.accept()

    try:
        client = LogClient()

        # 将连接添加到活动连接列表
        connection_info = {"websocket": websocket, "jobId": jobId}
        active_connections.append(connection_info)

        # 发送历史日志
        logs = client.get_job_logs(jobId, tail=100)
        for log in logs:
            await websocket.send_text(json.dumps({"type": "log", "data": log}))

        # 实时推送新日志（简化实现）
        while True:
            await asyncio.sleep(2)  # 每2秒检查新日志

            # 这里应该实现真正的日志流式传输
            # 当前是模拟实现
            new_logs = client.get_job_logs(jobId, tail=5)  # 获取最新5条
            for log in new_logs[-2:]:  # 只发送最新的2条避免重复
                await websocket.send_text(json.dumps({"type": "log", "data": log}))

    except WebSocketDisconnect:
        # 连接断开时移除
        active_connections.remove(connection_info)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
        if connection_info in active_connections:
            active_connections.remove(connection_info)