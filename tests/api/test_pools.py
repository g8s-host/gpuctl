import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from gpuctl.client.pool_client import PoolClient
from server.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@patch.object(PoolClient, 'get_instance')
def test_get_pools(mock_get_instance, client):
    """测试获取资源池列表API"""
    mock_instance = MagicMock()
    mock_instance.list_pools.return_value = [
        {
            "name": "test-pool-1",
            "gpu_total": 8,
            "gpu_used": 4,
            "gpu_free": 4,
            "status": "active",
            "gpu_types": ["A100", "H100"]
        },
        {
            "name": "test-pool-2",
            "gpu_total": 4,
            "gpu_used": 0,
            "gpu_free": 4,
            "status": "active",
            "gpu_types": ["V100"]
        }
    ]
    mock_get_instance.return_value = mock_instance
    
    response = client.get("/api/v1/pools")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "test-pool-1"


@patch.object(PoolClient, 'get_instance')
def test_get_pool_detail(mock_get_instance, client):
    """测试获取资源池详情API"""
    mock_instance = MagicMock()
    mock_instance.get_pool.return_value = {
        "name": "test-pool",
        "gpu_total": 8,
        "gpu_used": 4,
        "gpu_free": 4,
        "status": "active",
        "gpu_types": ["A100", "H100"],
        "nodes": ["node-1", "node-2"]
    }
    mock_get_instance.return_value = mock_instance
    
    response = client.get("/api/v1/pools/test-pool")

    assert response.status_code == 200
    assert response.json()["name"] == "test-pool"
    assert response.json()["gpu_total"] == 8


@patch.object(PoolClient, 'get_instance')
def test_create_pool(mock_get_instance, client):
    """测试创建资源池API"""
    mock_instance = MagicMock()
    mock_instance.create_pool.return_value = {
        "success": True,
        "pool": "test-pool"
    }
    mock_instance._validate_nodes_exist = MagicMock()
    mock_get_instance.return_value = mock_instance
    
    response = client.post(
        "/api/v1/pools",
        json={
            "name": "test-pool",
            "gpu_types": ["A100", "H100"],
            "nodes": ["node-1", "node-2"]
        }
    )

    assert response.status_code == 201
    assert response.json() == {
        "name": "test-pool",
        "status": "created",
        "message": "资源池创建成功"
    }


@patch.object(PoolClient, 'get_instance')
def test_delete_pool(mock_get_instance, client):
    """测试删除资源池API"""
    mock_instance = MagicMock()
    mock_instance.delete_pool.return_value = True
    mock_get_instance.return_value = mock_instance
    
    response = client.delete("/api/v1/pools/test-pool")

    assert response.status_code == 200
    assert response.json() == {
        "name": "test-pool",
        "status": "deleted",
        "message": "资源池删除成功"
    }


def test_update_pool_returns_501(client):
    """回归测试：update_pool 尚未实现，应返回 501 而非假装成功的 200"""
    response = client.put(
        "/api/v1/pools/test-pool",
        json={
            "description": "Updated description",
            "nodes": ["node-1", "node-2", "node-3"]
        }
    )

    assert response.status_code == 501
