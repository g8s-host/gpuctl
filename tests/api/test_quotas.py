import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from server.main import app


client = TestClient(app)


@patch('server.routes.quotas.BaseParser.parse_yaml')
@patch('server.routes.quotas.QuotaClient')
def test_create_quota(mock_quota_client_class, mock_parse_yaml):
    """测试创建资源配额API"""
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "quota"

    mock_quota_obj = MagicMock()
    mock_quota_obj.name = "test-quota"
    mock_quota_obj.description = "Test quota"
    mock_parsed_obj.quota = mock_quota_obj

    mock_ns_quota = MagicMock()
    mock_ns_quota.get_cpu_str = MagicMock(return_value="10")
    mock_ns_quota.memory = "20Gi"
    mock_ns_quota.get_gpu_str = MagicMock(return_value="4")
    mock_parsed_obj.namespace = {"team-a": mock_ns_quota}

    mock_parsed_obj.default = None
    mock_parse_yaml.return_value = mock_parsed_obj

    mock_client = MagicMock()
    mock_client.create_quota_config.return_value = [{
        'namespace': 'team-a',
        'cpu': '10',
        'memory': '20Gi',
        'gpu': '4'
    }]
    mock_quota_client_class.return_value = mock_client

    response = client.post(
        "/api/v1/quotas",
        json={
            "yamlContent": "kind: quota\nversion: v0.1\nquota:\n  name: test-quota\n  description: Test quota\nnamespace:\n  team-a:\n    cpu: 10\n    memory: 20Gi\n    gpu: 4"
        },
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 201
    assert response.json()["message"] == "配额创建成功"
    assert response.json()["name"] == "test-quota"
    assert len(response.json()["created"]) == 1


@patch('server.routes.quotas.QuotaClient')
def test_get_quotas(mock_quota_client_class):
    """测试获取资源配额列表API"""
    mock_client = MagicMock()
    mock_client.list_quotas.return_value = [
        {
            'name': 'test-quota',
            'namespace': 'team-a',
            'hard': {'cpu': '10', 'memory': '20Gi', 'nvidia.com/gpu': '4'},
            'status': 'active'
        }
    ]
    mock_quota_client_class.return_value = mock_client

    response = client.get(
        "/api/v1/quotas",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["name"] == "test-quota"


@patch('server.routes.quotas.QuotaClient')
def test_get_quota_detail(mock_quota_client_class):
    """测试获取资源配额详情API"""
    mock_client = MagicMock()
    mock_client.describe_quota.return_value = {
        'name': 'test-quota',
        'namespace': 'team-a',
        'hard': {'cpu': '10', 'memory': '20Gi', 'nvidia.com/gpu': '4'},
        'used': {'cpu': '5', 'memory': '10Gi', 'nvidia.com/gpu': '2'},
        'status': 'active'
    }
    mock_quota_client_class.return_value = mock_client

    response = client.get(
        "/api/v1/quotas/team-a",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "test-quota"
    assert response.json()["namespace"] == "team-a"
    assert response.json()["hard"]["cpu"] == "10"
    assert response.json()["used"]["cpu"] == "5"


@patch('server.routes.quotas.QuotaClient')
def test_delete_quota(mock_quota_client_class):
    """测试删除资源配额API"""
    mock_client = MagicMock()
    mock_client.delete_quota.return_value = True
    mock_quota_client_class.return_value = mock_client

    response = client.delete(
        "/api/v1/quotas/team-a",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.json()["jobId"] == "team-a"
    assert response.json()["status"] == "deleted"
    assert response.json()["message"] == "配额删除成功"


@patch('server.routes.quotas.QuotaClient')
def test_get_specific_quota(mock_quota_client_class):
    """测试获取特定命名空间的配额API"""
    mock_client = MagicMock()
    mock_client.get_quota.return_value = {
        'name': 'test-quota',
        'namespace': 'team-a',
        'hard': {'cpu': '10', 'memory': '20Gi', 'nvidia.com/gpu': '4'},
        'status': 'active'
    }
    mock_quota_client_class.return_value = mock_client

    response = client.get(
        "/api/v1/quotas?namespace=team-a",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "test-quota"
    assert response.json()["namespace"] == "team-a"
    assert response.json()["hard"]["cpu"] == "10"
