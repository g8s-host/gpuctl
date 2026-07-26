from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import asyncio
import json
import threading

from gpuctl.parser.base_parser import BaseParser, ParserError
from gpuctl.kind.training_kind import TrainingKind
from gpuctl.kind.inference_kind import InferenceKind
from gpuctl.kind.notebook_kind import NotebookKind
from gpuctl.kind.compute_kind import ComputeKind
from gpuctl.client.job_client import JobClient
from gpuctl.client.log_client import LogClient
from gpuctl.constants import (
    Kind, Labels, KINDS_WITH_SERVICE, DEFAULT_NAMESPACE, DEFAULT_POOL,
    CONTAINER_WAITING_REASONS, get_detailed_status, infer_resource_type,
    svc_name, DEFAULT_PRIORITY,
)

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


# 进程内只需确保一次:首个任务创建前建好所需 PriorityClass(与 CLI create 路径一致,
# 见 gpuctl/cli/job.py)。新集群从未跑过 CLI 时,UI/API 建的任务会因缺 PriorityClass
# 报 "pods ... is forbidden: no PriorityClass named gpuctl-medium" 而调度不出。
_priority_classes_ensured = False


def _ensure_priority_classes_once():
    """幂等地确保 gpuctl 优先级类存在;失败不阻断建任务(仅告警),下次再试。"""
    global _priority_classes_ensured
    if _priority_classes_ensured:
        return
    try:
        from gpuctl.client.priority_client import PriorityClient
        PriorityClient().ensure_priority_classes()
        _priority_classes_ensured = True
        logger.info("PriorityClasses ensured (gpuctl-high/medium/low)")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"ensure_priority_classes failed (任务可能因缺 PriorityClass 调度不出): {e}")


def _create_by_kind(parsed_obj, namespace: str) -> Dict[str, Any]:
    """kind -> handler().create_x(parsed_obj, namespace=...)。

    create_job 和 create_jobs_batch 此前各写一遍完全相同的 if/elif kind 分支
    (2026-06 架构评审 P1-5:跨前端 dispatch 逻辑重复)。表建在函数体内(不是模块级
    常量)是刻意的——现有测试用 `@patch('server.routes.jobs.TrainingKind')` 这类
    补丁替换类引用，模块级常量在 import 时就把类绑死了，测试的补丁会失效；
    函数体内的裸名字查找在**调用时**才解析，能看到补丁后的值。
    """
    handlers = {
        Kind.TRAINING: (TrainingKind, "create_training_job"),
        Kind.INFERENCE: (InferenceKind, "create_inference_service"),
        Kind.NOTEBOOK: (NotebookKind, "create_notebook"),
        Kind.COMPUTE: (ComputeKind, "create_compute_service"),
    }
    if parsed_obj.kind not in handlers:
        raise ValueError(f"Unsupported job kind: {parsed_obj.kind}")
    handler_cls, method_name = handlers[parsed_obj.kind]
    handler = handler_cls()
    return getattr(handler, method_name)(parsed_obj, namespace=namespace)


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(request: JobCreateRequest):
    """创建任务"""
    logger.debug(f"开始创建任务，请求内容: {request.yamlContent[:100]}...")
    try:
        # 确保优先级类存在(否则带 priority 的任务 Pod 会被 forbidden)
        _ensure_priority_classes_once()
        # 解析YAML
        logger.debug("正在解析YAML配置")
        parsed_obj = BaseParser.parse_yaml(request.yamlContent)
        logger.debug(f"YAML解析成功，任务类型: {parsed_obj.kind}")

        result = _create_by_kind(parsed_obj, DEFAULT_NAMESPACE)

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
    except ValueError as e:
        # 用户输入类错误(如多机+多副本不支持、命名空间无配额)→ 400 + 明确信息,而非 500
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batch", response_model=BatchCreateResponse, status_code=201)
async def create_jobs_batch(request: BatchCreateRequest):
    """批量创建任务"""
    _ensure_priority_classes_once()
    success = []
    failed = []

    for i, yaml_content in enumerate(request.yamlContents):
        try:
            parsed_obj = BaseParser.parse_yaml(yaml_content)
            result = _create_by_kind(parsed_obj, DEFAULT_NAMESPACE)
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
    """从容器等待原因获取详细状态 (delegates to constants module)"""
    return get_detailed_status(waiting_reason, waiting_message)


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
            labels[Labels.JOB_TYPE] = kind
        if pool:
            labels[Labels.POOL] = pool

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
            job_type = labels.get(Labels.JOB_TYPE, "unknown")
            if job_type == "unknown" and Labels.JOB_NAME in labels:
                job_type = Kind.TRAINING

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
            # NAME = 真实作业名(YAML job.name),从 pod 标签读:inference/notebook/compute
            # 是 app=<name>,training(K8s Job)是 job-name=<name>——与 CLI `gpuctl get jobs`
            # 的 _get_job_name 一致。不再按 '-' 切 pod 名:对单段名(sttest)和含连字符的名
            # (pping-lang)都会切错。无标签才回退完整 pod 名。
            final_name = labels.get(Labels.APP) or labels.get(Labels.JOB_NAME) or pod_name

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


def _job_detail_status_with_pods(job_info: dict, job_name: str, namespace: str,
                                 resource_type: str) -> str:
    """详情页状态:控制器(Job/Deployment/StatefulSet)的 status.active 把【Pending 的
    Pod】也计入,会把"调度中"误显成 Running。这里对控制器类型改看真实 Pod 相,优先
    暴露非 Running 的相(调度中/拉镜像失败/OOM 等),与任务列表保持一致。
    """
    base = _job_detail_compute_status(job_info)
    if resource_type not in ("Job", "Deployment", "StatefulSet"):
        return base  # Pod 等已是真实相
    try:
        pods = [p for p in JobClient().list_pods(namespace)
                if (p.get("name") or "").startswith(f"{job_name}-")]
        if not pods:
            return base
        statuses = [_job_detail_compute_status(p) for p in pods]
        for s in statuses:               # 任一非 Running/Succeeded → 暴露该相
            if s not in ("Running", "Succeeded"):
                return s
        return statuses[0]
    except Exception:
        return base


def _compute_resource_type(job_info: dict, job_type: str) -> str:
    """根据 status 字段推断 Kubernetes 资源类型 (delegates to constants module)"""
    return infer_resource_type(job_info.get("status", {}), job_type)


def _fetch_events(job_name: str, namespace: str, resource_type: str) -> list:
    """从 Kubernetes 获取资源事件列表"""
    try:
        from gpuctl.client.base_client import KubernetesClient
        k8s = KubernetesClient()
        # 关键:调度/拉镜像/OOM 等事件挂在 Pod 上,而不在工作负载对象(Job/Deployment/
        # StatefulSet)上。只按 involvedObject.name=<workload>,kind=<resource_type> 过滤
        # 会漏掉它们——Pending 任务的 FailedScheduling 就永远看不到(用户因此"不知道
        # 卡在哪")。改为列命名空间事件,保留 involvedObject 名等于工作负载名、或以
        # "<workload>-" 开头(即其 Pod / ReplicaSet)的事件。
        evs = k8s.core_v1.list_namespaced_event(namespace=namespace, limit=200)
        prefix = f"{job_name}-"
        related = [
            ev for ev in evs.items
            if ev.involved_object and ev.involved_object.name
            and (ev.involved_object.name == job_name
                 or ev.involved_object.name.startswith(prefix))
        ]
        sorted_evs = sorted(
            related,
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
    if job_type not in KINDS_WITH_SERVICE:
        return None

    svc_base = job_name
    if job_type == Kind.NOTEBOOK:
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
            name=svc_name(svc_base), namespace=namespace
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
        job_type = labels.get(Labels.JOB_TYPE, "unknown")
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
            status=_job_detail_status_with_pods(job_info, job_name, actual_ns, resource_type),
            age=_job_detail_calculate_age(job_info.get("creation_timestamp")),
            started=job_info.get("start_time"),
            completed=job_info.get("completion_time"),
            priority=labels.get(Labels.PRIORITY, "medium"),
            pool=labels.get(Labels.POOL, "default"),
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
async def delete_job(
        jobId: str,
        namespace: Optional[str] = Query(None, description="命名空间，不指定时默认 default"),
        force: bool = Query(False, description="是否强制删除")
):
    """删除任务"""
    try:
        client = JobClient()
        success = client.delete_job(jobId, namespace=namespace or "default", force=force)

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job logs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.websocket("/{jobId}/logs/ws")
async def websocket_job_logs(websocket: WebSocket, jobId: str):
    """WebSocket 实时日志 —— 真流式 follow，不丢行、不重复。

    底层用 LogClient.stream_job_logs（K8s read_namespaced_pod_log(follow=True)）。
    它是同步阻塞生成器，故放后台线程跑，经 asyncio.Queue 交回事件循环推送，
    避免阻塞事件循环。消息格式保持 {"type": "log", "data": <line>} 不变（向后兼容）。

    （旧实现是「每 2s 取 tail=5、固定发最后 2 条」的模拟轮询：空闲时重复刷屏、
      繁忙时丢行，已替换。）
    """
    await websocket.accept()

    connection_info = {"websocket": websocket, "jobId": jobId}
    active_connections.append(connection_info)

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue(maxsize=2000)
    stop = threading.Event()

    def _push(item):
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            pass

    def _producer():
        try:
            for line in LogClient().stream_job_logs(jobId):
                if stop.is_set():
                    break
                loop.call_soon_threadsafe(_push, line)
        except Exception as exc:  # noqa: BLE001
            loop.call_soon_threadsafe(_push, f"[stream error] {exc}")
        finally:
            loop.call_soon_threadsafe(_push, None)  # 哨兵：流结束

    threading.Thread(target=_producer, daemon=True).start()

    try:
        while True:
            line = await queue.get()
            if line is None:
                break
            await websocket.send_text(json.dumps({"type": "log", "data": line}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        stop.set()
        if connection_info in active_connections:
            active_connections.remove(connection_info)
        try:
            await websocket.close()
        except Exception:
            pass