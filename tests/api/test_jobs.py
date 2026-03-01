import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from server.main import app
from server.models import JobCreateRequest


client = TestClient(app)


@patch('server.routes.jobs.BaseParser.parse_yaml')
@patch('server.routes.jobs.TrainingKind')
def test_create_job(mock_training_kind, mock_parse_yaml):
    """测试创建作业API"""
    # 设置模拟返回值
    mock_parse_yaml.return_value.kind = "training"
    mock_handler = MagicMock()
    mock_handler.create_training_job.return_value = {
        "job_id": "test-job",
        "name": "test-job",
        "status": "created"
    }
    mock_training_kind.return_value = mock_handler
    
    # 发送API请求
    response = client.post(
        "/api/v1/jobs",
        json={
            "yamlContent": "kind: training\nversion: v0.1\njob:\n  name: test-job"
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 201
    assert response.json() == {
        "jobId": "test-job",
        "name": "test-job",
        "kind": "training",
        "status": "pending",
        "createdAt": response.json()["createdAt"],
        "message": "任务已提交至资源池"
    }


@patch('server.routes.jobs.BaseParser.parse_yaml')
@patch('server.routes.jobs.InferenceKind')
def test_create_inference_job(mock_inference_kind, mock_parse_yaml):
    """测试创建推理作业API"""
    # 设置模拟返回值
    mock_parse_yaml.return_value.kind = "inference"
    mock_handler = MagicMock()
    mock_handler.create_inference_service.return_value = {
        "job_id": "test-inference-job",
        "name": "test-inference-job",
        "status": "created"
    }
    mock_inference_kind.return_value = mock_handler
    
    # 发送API请求
    response = client.post(
        "/api/v1/jobs",
        json={
            "yamlContent": "kind: inference\nversion: v0.1\njob:\n  name: test-inference-job"
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 201
    assert response.json()["jobId"] == "test-inference-job"
    assert response.json()["kind"] == "inference"


@patch('server.routes.jobs.JobClient')
def test_get_jobs(mock_job_client):
    """测试获取作业列表API"""
    # 模拟 Pod 级别数据（与 CLI gpuctl get jobs 一致）
    mock_pod = MagicMock()
    mock_pod.state = MagicMock()
    mock_pod.state.waiting = None
    mock_pod.state.terminated = None
    mock_pod.ready = True

    mock_instance = MagicMock()
    mock_instance.list_jobs.return_value = [
        {
            "name": "test-job-1-abc123-xyz",
            "namespace": "default",
            "labels": {"g8s.host/job-type": "training", "g8s.host/pool": "test-pool"},
            "status": {
                "active": 1,
                "succeeded": 0,
                "failed": 0,
                "phase": "Running",
                "pod_ip": "10.42.0.1",
                "container_statuses": [mock_pod]
            },
            "spec": {"node_name": "node-1"},
            "creation_timestamp": "2023-01-01T12:00:00Z"
        }
    ]
    mock_job_client.return_value = mock_instance

    response = client.get(
        "/api/v1/jobs",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1
    item = response.json()["items"][0]
    assert item["jobId"] == "test-job-1-abc123-xyz"
    assert item["namespace"] == "default"
    assert item["kind"] == "training"
    assert item["status"] == "Running"
    assert item["ready"] == "1/1"
    assert item["node"] == "node-1"
    assert item["ip"] == "10.42.0.1"
    assert "age" in item


@patch('server.routes.jobs.JobClient')
def test_get_job_detail(mock_job_client):
    """测试获取作业详情API"""
    mock_instance = MagicMock()
    mock_instance.get_job.return_value = {
        "name": "test-job",
        "namespace": "default",
        "labels": {"g8s.host/job-type": "training", "g8s.host/pool": "test-pool"},
        "status": {"active": 1, "succeeded": 0, "failed": 0},
        "creation_timestamp": "2023-01-01T12:00:00Z",
        "start_time": "2023-01-01T12:01:00Z",
        "completion_time": None,
    }
    mock_instance.get_pod.return_value = None
    mock_job_client.return_value = mock_instance

    response = client.get(
        "/api/v1/jobs/test-job",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "test-job"
    assert data["name"] == "test-job"
    assert data["namespace"] == "default"
    assert data["kind"] == "training"
    assert data["status"] == "Running"
    assert data["pool"] == "test-pool"
    assert "age" in data


@patch('server.routes.jobs.JobClient')
def test_delete_job(mock_job_client):
    """测试删除作业API"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.delete_job.return_value = True
    mock_job_client.return_value = mock_instance
    
    # 发送API请求
    response = client.delete(
        "/api/v1/jobs/test-job",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json() == {
        "jobId": "test-job",
        "status": "terminating",
        "message": "任务删除指令已下发"
    }


@patch('server.routes.jobs.JobClient')
def test_delete_job_force(mock_job_client):
    """测试强制删除作业API"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.delete_job.return_value = True
    mock_job_client.return_value = mock_instance
    
    # 发送API请求 - 带force参数
    response = client.delete(
        "/api/v1/jobs/test-job?force=true",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json() == {
        "jobId": "test-job",
        "status": "terminating",
        "message": "任务删除指令已下发"
    }
    # 验证force参数被正确传递
    mock_instance.delete_job.assert_called_once_with("test-job", force=True)





@patch('server.routes.jobs.LogClient')
def test_get_job_logs(mock_log_client):
    """测试获取作业日志API"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.get_job_logs.return_value = [
        "2023-01-01T12:00:00Z INFO: Job started",
        "2023-01-01T12:01:00Z INFO: Job completed"
    ]
    mock_log_client.return_value = mock_instance
    
    # 发送API请求
    response = client.get(
        "/api/v1/jobs/test-job/logs",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json() == {
        "logs": [
            "2023-01-01T12:00:00Z INFO: Job started",
            "2023-01-01T12:01:00Z INFO: Job completed"
        ],
        "lastTimestamp": response.json()["lastTimestamp"]
    }


@patch('server.routes.jobs.LogClient')
def test_get_job_logs_follow_returns_400_not_500(mock_log_client):
    """回归测试：follow=True 时应返回 400，而非被 except Exception 吞掉后返回 500"""
    mock_instance = MagicMock()
    mock_log_client.return_value = mock_instance

    response = client.get(
        "/api/v1/jobs/test-job/logs?follow=true",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 400
    assert "WebSocket" in response.json().get("error", "")


@patch('server.routes.jobs.BaseParser.parse_yaml')
@patch('server.routes.jobs.TrainingKind')
def test_batch_create_jobs(mock_training_kind, mock_parse_yaml):
    """测试批量创建作业API"""
    # 设置模拟返回值
    mock_parse_yaml.return_value.kind = "training"
    mock_parse_yaml.return_value.job.name = "test-job-{}"
    mock_handler = MagicMock()
    mock_handler.create_training_job.return_value = {
        "job_id": "test-job-{}",
        "name": "test-job-{}",
        "status": "created"
    }
    mock_training_kind.return_value = mock_handler
    
    # 发送API请求
    response = client.post(
        "/api/v1/jobs/batch",
        json={
            "yamlContents": [
                "kind: training\nversion: v0.1\njob:\n  name: test-job-1",
                "kind: training\nversion: v0.1\njob:\n  name: test-job-2"
            ]
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 201
    response_json = response.json()
    assert len(response_json["success"]) == 2
    assert len(response_json["failed"]) == 0
    assert response_json["success"][0]["jobId"] == "test-job-{}"
    assert response_json["success"][1]["jobId"] == "test-job-{}"


@patch('server.routes.jobs.BaseParser.parse_yaml')
@patch('server.routes.jobs.NotebookKind')
def test_create_notebook_job(mock_notebook_kind, mock_parse_yaml):
    """测试创建笔记本作业API"""
    # 设置模拟返回值
    mock_parse_yaml.return_value.kind = "notebook"
    mock_handler = MagicMock()
    mock_handler.create_notebook.return_value = {
        "job_id": "test-notebook-job",
        "name": "test-notebook-job",
        "status": "created"
    }
    mock_notebook_kind.return_value = mock_handler
    
    # 发送API请求
    response = client.post(
        "/api/v1/jobs",
        json={
            "yamlContent": "kind: notebook\nversion: v0.1\njob:\n  name: test-notebook-job"
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 201
    assert response.json()["jobId"] == "test-notebook-job"
    assert response.json()["kind"] == "notebook"


@patch('server.routes.jobs.BaseParser.parse_yaml')
@patch('server.routes.jobs.ComputeKind')
def test_create_compute_job(mock_compute_kind, mock_parse_yaml):
    """测试创建计算作业API"""
    # 设置模拟返回值
    mock_parse_yaml.return_value.kind = "compute"
    mock_handler = MagicMock()
    mock_handler.create_compute_service.return_value = {
        "job_id": "test-compute-job",
        "name": "test-compute-job",
        "status": "created"
    }
    mock_compute_kind.return_value = mock_handler
    
    # 发送API请求
    response = client.post(
        "/api/v1/jobs",
        json={
            "yamlContent": "kind: compute\nversion: v0.1\njob:\n  name: test-compute-job"
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 201
    assert response.json()["jobId"] == "test-compute-job"
    assert response.json()["kind"] == "compute"


@patch('server.routes.jobs.BaseParser.parse_yaml')
@patch('server.routes.jobs.TrainingKind')
@patch('server.routes.jobs.InferenceKind')
@patch('server.routes.jobs.NotebookKind')
@patch('server.routes.jobs.ComputeKind')
def test_batch_create_jobs_with_multiple_kinds(mock_compute_kind, mock_notebook_kind, mock_inference_kind, mock_training_kind, mock_parse_yaml):
    """测试批量创建多种类型的作业API"""
    # 设置模拟返回值
    # 第一次调用返回training类型，第二次返回compute类型
    mock_parse_yaml.side_effect = [
        type('MockTraining', (), {'kind': 'training', 'job': type('MockJob', (), {'name': 'test-training-job'})})(),
        type('MockCompute', (), {'kind': 'compute', 'job': type('MockJob', (), {'name': 'test-compute-job'})})()
    ]
    
    # 设置各类型handler的返回值
    mock_training_handler = MagicMock()
    mock_training_handler.create_training_job.return_value = {
        "job_id": "test-training-job",
        "name": "test-training-job",
        "status": "created"
    }
    mock_training_kind.return_value = mock_training_handler
    
    mock_compute_handler = MagicMock()
    mock_compute_handler.create_compute_service.return_value = {
        "job_id": "test-compute-job",
        "name": "test-compute-job",
        "status": "created"
    }
    mock_compute_kind.return_value = mock_compute_handler
    
    # 发送API请求
    response = client.post(
        "/api/v1/jobs/batch",
        json={
            "yamlContents": [
                "kind: training\nversion: v0.1\njob:\n  name: test-training-job",
                "kind: compute\nversion: v0.1\njob:\n  name: test-compute-job"
            ]
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 201
    response_json = response.json()
    assert len(response_json["success"]) == 2
    assert len(response_json["failed"]) == 0
    assert response_json["success"][0]["jobId"] == "test-training-job"
    assert response_json["success"][1]["jobId"] == "test-compute-job"
