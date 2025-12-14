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
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.list_jobs.return_value = [
        {
            "name": "test-job-1",
            "namespace": "default",
            "labels": {"g8s.host/job-type": "training", "g8s.host/pool": "test-pool"},
            "status": {"active": 1, "succeeded": 0, "failed": 0},
            "creation_timestamp": "2023-01-01T12:00:00Z"
        }
    ]
    mock_job_client.return_value = mock_instance
    
    # 发送API请求
    response = client.get(
        "/api/v1/jobs",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["jobId"] == "test-job-1"


@patch('server.routes.jobs.JobClient')
def test_get_job_detail(mock_job_client):
    """测试获取作业详情API"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.get_job.return_value = {
        "name": "test-job",
        "namespace": "default",
        "labels": {"g8s.host/job-type": "training", "g8s.host/pool": "test-pool"},
        "status": {"active": 1, "succeeded": 0, "failed": 0},
        "creation_timestamp": "2023-01-01T12:00:00Z"
    }
    mock_instance.list_pods.return_value = [
        {"name": "test-job-pod-1"}
    ]
    mock_job_client.return_value = mock_instance
    
    # 发送API请求
    response = client.get(
        "/api/v1/jobs/test-job",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json()["jobId"] == "test-job"
    assert response.json()["name"] == "test-job"


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


@patch('server.routes.jobs.JobClient')
def test_pause_job(mock_job_client):
    """测试暂停作业API"""
    # 发送API请求
    response = client.post(
        "/api/v1/jobs/test-job/pause",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json() == {
        "jobId": "test-job",
        "status": "paused",
        "message": "任务已暂停，资源保留"
    }


@patch('server.routes.jobs.JobClient')
def test_resume_job(mock_job_client):
    """测试恢复作业API"""
    # 发送API请求
    response = client.post(
        "/api/v1/jobs/test-job/resume",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json() == {
        "jobId": "test-job",
        "status": "resumed",
        "message": "任务已恢复"
    }


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


@patch('server.routes.jobs.JobClient')
def test_get_job_metrics(mock_job_client):
    """测试获取作业指标API"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_job_client.return_value = mock_instance
    
    # 发送API请求
    response = client.get(
        "/api/v1/jobs/test-job/metrics",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    response_json = response.json()
    assert "gpuUtilization" in response_json
    assert "memoryUsage" in response_json
    
    # 验证指标数据结构
    for metric_type in ["gpuUtilization", "memoryUsage"]:
        assert isinstance(response_json[metric_type], list)
        for metric_item in response_json[metric_type]:
            assert "timestamp" in metric_item
            assert "value" in metric_item


@patch('server.routes.jobs.BaseParser.parse_yaml')
@patch('server.routes.jobs.TrainingKind')
def test_batch_create_jobs(mock_training_kind, mock_parse_yaml):
    """测试批量创建作业API"""
    # 设置模拟返回值
    mock_parse_yaml.return_value.kind = "training"
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
