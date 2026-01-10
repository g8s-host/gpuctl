import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from server.main import app


client = TestClient(app)


@patch('server.routes.quotas.BaseParser.parse_yaml')
@patch('server.routes.quotas.QuotaClient')
def test_create_quota(mock_quota_client, mock_parse_yaml):
    """测试创建资源配额API"""
    # 设置模拟返回值
    mock_parse_yaml.return_value.kind = "quota"
    mock_parse_yaml.return_value.metadata = type('MockMetadata', (), {
        'name': 'test-quota',
        'description': 'Test quota'
    })()
    mock_parse_yaml.return_value.namespace = {
        'team-a': type('MockQuota', (), {
            'get_cpu_str': lambda self: '10',
            'memory': '20Gi',
            'get_gpu_str': lambda self: '4'
        })()
    }
    mock_parse_yaml.return_value.default = None
    
    mock_client = MagicMock()
    mock_client.create_quota_config.return_value = [{
        'namespace': 'team-a',
        'cpu': '10',
        'memory': '20Gi',
        'gpu': '4'
    }]
    mock_quota_client.return_value = mock_client
    
    # 发送API请求
    response = client.post(
        "/api/v1/quotas",
        json={
            "yamlContent": "kind: quota\nversion: v0.1\nmetadata:\n  name: test-quota\n  description: Test quota\nnamespace:\n  team-a:\n    cpu: 10\n    memory: 20Gi\n    gpu: 4"
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 201
    assert response.json()["message"] == "配额创建成功"
    assert response.json()["name"] == "test-quota"
    assert len(response.json()["created"]) == 1


@patch('server.routes.quotas.QuotaClient')
def test_get_quotas(mock_quota_client):
    """测试获取资源配额列表API"""
    # 设置模拟返回值
    mock_client = MagicMock()
    mock_client.list_quotas.return_value = [
        {
            'name': 'test-quota',
            'namespace': 'team-a',
            'hard': {'cpu': '10', 'memory': '20Gi', 'nvidia.com/gpu': '4'},
            'status': 'active'
        }
    ]
    mock_quota_client.return_value = mock_client
    
    # 发送API请求
    response = client.get(
        "/api/v1/quotas",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["name"] == "test-quota"


@patch('server.routes.quotas.QuotaClient')
def test_get_quota_detail(mock_quota_client):
    """测试获取资源配额详情API"""
    # 设置模拟返回值
    mock_client = MagicMock()
    mock_client.describe_quota.return_value = {
        'name': 'test-quota',
        'namespace': 'team-a',
        'hard': {'cpu': '10', 'memory': '20Gi', 'nvidia.com/gpu': '4'},
        'used': {'cpu': '5', 'memory': '10Gi', 'nvidia.com/gpu': '2'},
        'status': 'active'
    }
    mock_quota_client.return_value = mock_client
    
    # 发送API请求
    response = client.get(
        "/api/v1/quotas/team-a",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json()["name"] == "test-quota"
    assert response.json()["namespace"] == "team-a"
    assert response.json()["hard"]["cpu"] == "10"
    assert response.json()["used"]["cpu"] == "5"


@patch('server.routes.quotas.QuotaClient')
def test_delete_quota(mock_quota_client):
    """测试删除资源配额API"""
    # 设置模拟返回值
    mock_client = MagicMock()
    mock_client.delete_quota.return_value = True
    mock_quota_client.return_value = mock_client
    
    # 发送API请求
    response = client.delete(
        "/api/v1/quotas/team-a",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json()["jobId"] == "team-a"
    assert response.json()["status"] == "deleted"
    assert response.json()["message"] == "配额删除成功"


@patch('server.routes.quotas.QuotaClient')
def test_get_specific_quota(mock_quota_client):
    """测试获取特定命名空间的配额API"""
    # 设置模拟返回值
    mock_client = MagicMock()
    mock_client.get_quota.return_value = {
        'name': 'test-quota',
        'namespace': 'team-a',
        'hard': {'cpu': '10', 'memory': '20Gi', 'nvidia.com/gpu': '4'},
        'status': 'active'
    }
    mock_quota_client.return_value = mock_client
    
    # 发送API请求
    response = client.get(
        "/api/v1/quotas?namespace=team-a",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json()["name"] == "test-quota"
    assert response.json()["namespace"] == "team-a"
    assert response.json()["hard"]["cpu"] == "10"
