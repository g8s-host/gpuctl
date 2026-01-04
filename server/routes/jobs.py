from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
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
from server.auth import AuthValidator, security

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)

# 存储WebSocket连接
active_connections = []


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(request: JobCreateRequest, token: str = Depends(AuthValidator.validate_token)):
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
async def create_jobs_batch(request: BatchCreateRequest, token: str = Depends(AuthValidator.validate_token)):
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


@router.get("", response_model=JobListResponse)
async def get_jobs(
        kind: Optional[str] = Query(None, description="任务类型过滤"),
        pool: Optional[str] = Query(None, description="资源池过滤"),
        status: Optional[str] = Query(None, description="状态过滤"),
        page: int = Query(1, ge=1),
        pageSize: int = Query(20, ge=1, le=100),
        token: str = Depends(AuthValidator.validate_token)
):
    """获取任务列表"""
    try:
        client = JobClient()

        # 构建标签选择器
        labels = {}
        if kind:
            labels["g8s.host/job-type"] = kind
        if pool:
            labels["g8s.host/pool"] = pool

        jobs = client.list_jobs(labels=labels)

        # 状态过滤
        if status:
            filtered_jobs = []
            for job in jobs:
                # 直接使用原始状态进行过滤，不再转换为简化字符串
                if status:
                    # 保留原有过滤逻辑，以便兼容现有API
                    status_flag = "unknown"
                    if job["status"]["succeeded"] > 0:
                        status_flag = "succeeded"
                    elif job["status"]["failed"] > 0:
                        status_flag = "failed"
                    elif job["status"]["active"] > 0:
                        status_flag = "running"
                    else:
                        status_flag = "pending"
                    
                    if status_flag == status:
                        filtered_jobs.append(job)
                else:
                    filtered_jobs.append(job)
            jobs = filtered_jobs

        # 分页
        total = len(jobs)
        start_idx = (page - 1) * pageSize
        end_idx = start_idx + pageSize
        paginated_jobs = jobs[start_idx:end_idx]

        # 转换为响应格式
        items = []
        for job in paginated_jobs:
            # 获取任务状态，确保与k8s一致
            status_dict = job["status"]
            job_status = "pending"
            
            # 从标签中获取信息
            labels = job.get("labels", {})
            job_type = labels.get("g8s.host/job-type", "unknown")
            
            # 对于Job资源（Training任务）
            if job_type == "training":
                if status_dict["succeeded"] > 0:
                    job_status = "succeeded"
                elif status_dict["failed"] > 0:
                    job_status = "failed"
                elif status_dict["active"] > 0:
                    job_status = "running"
            # 对于Deployment资源（Inference服务）
            elif job_type == "inference":
                # Deployment的状态判断：
                # - Running: 至少有一个可用副本
                # - Pending: 没有可用副本（可能是Pending或Failed状态）
                if status_dict["active"] > 0:
                    job_status = "running"
            # 对于其他类型
            else:
                if status_dict["succeeded"] > 0:
                    job_status = "succeeded"
                elif status_dict["failed"] > 0:
                    job_status = "failed"
                elif status_dict["active"] > 0:
                    job_status = "running"

            # 创建JobItem对象
            job_item = JobItem(
                jobId=job["name"],
                name=job["name"].rsplit('-', 1)[0],  # 从名称中提取原始名称
                kind=job_type,
                pool=labels.get("g8s.host/pool", "default"),
                status=job_status,  # 使用简洁的状态字符串
                gpu=1,  # 需要从实际资源中获取
                gpuType="unknown",  # 需要从实际资源中获取
                startedAt=job.get("creation_timestamp")
            )

            items.append(job_item)

        return JobListResponse(total=total, items=items)

    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{jobId}", response_model=JobDetailResponse)
async def get_job_detail(jobId: str, token: str = Depends(AuthValidator.validate_token)):
    """获取任务详情"""
    try:
        client = JobClient()
        job_info = client.get_job(jobId)

        if not job_info:
            raise HTTPException(status_code=404, detail="Job not found")

        # 获取Pod信息
        pods = client.list_pods(labels={"job-name": jobId})

        # 构建响应
        labels = job_info.get("labels", {})

        # 获取资源信息（简化版，实际需要从Pod中解析）
        resources = {
            "gpu": 1,
            "gpuType": "unknown",
            "cpu": "unknown",
            "memory": "unknown"
        }

        # 获取指标（简化版，实际需要从监控系统获取）
        metrics = {
            "gpuUtilization": 0.0,
            "memoryUsage": "0Gi/0Gi",
            "networkLatency": "0ms",
            "throughput": "0 tokens/sec"
        }

        # 获取任务状态
        job_status = "pending"
        if job_info["status"]["succeeded"] > 0:
            job_status = "succeeded"
        elif job_info["status"]["failed"] > 0:
            job_status = "failed"
        elif job_info["status"]["active"] > 0:
            job_status = "running"

        return JobDetailResponse(
            jobId=jobId,
            name=job_info["name"],
            kind=labels.get("g8s.host/job-type", "unknown"),
            version="v0.1",
            yamlContent="",  # 实际需要从存储中获取原始YAML
            status=job_status,
            pool=labels.get("g8s.host/pool", "default"),
            resources=resources,
            metrics=metrics,
            createdAt=job_info.get("creation_timestamp"),
            startedAt=job_info.get("creation_timestamp"),
            k8sResources={
                "jobName": jobId,
                "pods": [pod["name"] for pod in pods]
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job detail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{jobId}", response_model=DeleteResponse)
async def delete_job(jobId: str, force: bool = Query(False, description="是否强制删除"), token: str = Depends(AuthValidator.validate_token)):
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


@router.post("/{jobId}/pause")
async def pause_job(jobId: str, token: str = Depends(AuthValidator.validate_token)):
    """暂停任务"""
    try:
        # 这里需要实现暂停逻辑
        # 实际实现会调用Kubernetes API暂停Job
        return {
            "jobId": jobId,
            "status": "paused",
            "message": "任务已暂停，资源保留"
        }
    except Exception as e:
        logger.error(f"Failed to pause job: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{jobId}/resume")
async def resume_job(jobId: str, token: str = Depends(AuthValidator.validate_token)):
    """恢复任务"""
    try:
        # 这里需要实现恢复逻辑
        return {
            "jobId": jobId,
            "status": "resumed",
            "message": "任务已恢复"
        }
    except Exception as e:
        logger.error(f"Failed to resume job: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{jobId}/logs", response_model=LogResponse)
async def get_job_logs(
        jobId: str,
        follow: bool = False,
        tail: int = Query(100, ge=1),
        pod: Optional[str] = None,
        token: str = Depends(AuthValidator.validate_token)
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


@router.get("/{jobId}/metrics", response_model=Dict[str, Any])
async def get_job_metrics(
        jobId: str,
        metric: Optional[str] = Query(None),
        startTime: Optional[datetime] = Query(None),
        endTime: Optional[datetime] = Query(None),
        token: str = Depends(AuthValidator.validate_token)
):
    """获取任务指标"""
    try:
        # 模拟指标数据
        metrics_data = {
            "gpuUtilization": [
                {"timestamp": (datetime.utcnow() - timedelta(minutes=10)).isoformat(), "value": 75.2},
                {"timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(), "value": 89.2},
                {"timestamp": datetime.utcnow().isoformat(), "value": 82.1}
            ],
            "memoryUsage": [
                {"timestamp": (datetime.utcnow() - timedelta(minutes=10)).isoformat(), "value": 65},
                {"timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(), "value": 68},
                {"timestamp": datetime.utcnow().isoformat(), "value": 70}
            ]
        }

        if metric:
            return {metric: metrics_data.get(metric, [])}

        return metrics_data

    except Exception as e:
        logger.error(f"Failed to get job metrics: {e}")
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