import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)


@patch('gpuctl.client.pool_client.PoolClient')
def test_get_pools(mock_pool_client):
    """测试获取资源池列表API"""
    # 设置模拟返回值
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
    mock_pool_client.return_value = mock_instance
    
    # 发送API请求
    response = client.get(
        "/api/v1/pools",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "test-pool-1"


@patch('gpuctl.client.pool_client.PoolClient')
def test_get_pool_detail(mock_pool_client):
    """测试获取资源池详情API"""
    # 设置模拟返回值
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
    mock_pool_client.return_value = mock_instance
    
    # 发送API请求
    response = client.get(
        "/api/v1/pools/test-pool",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json()["name"] == "test-pool"
    assert response.json()["gpu_total"] == 8


@patch('gpuctl.client.pool_client.PoolClient')
def test_create_pool(mock_pool_client):
    """测试创建资源池API"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.create_pool.return_value = {
        "success": True,
        "pool": "test-pool"
    }
    mock_pool_client.return_value = mock_instance
    
    # 发送API请求
    response = client.post(
        "/api/v1/pools",
        json={
            "name": "test-pool",
            "gpu_types": ["A100", "H100"],
            "nodes": ["node-1", "node-2"]
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 201
    assert response.json() == {
        "name": "test-pool",
        "message": "资源池创建成功"
    }


@patch('gpuctl.client.pool_client.PoolClient')
def test_delete_pool(mock_pool_client):
    """测试删除资源池API"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.delete_pool.return_value = True
    mock_pool_client.return_value = mock_instance
    
    # 发送API请求
    response = client.delete(
        "/api/v1/pools/test-pool",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json() == {
        "name": "test-pool",
        "message": "资源池删除成功"
    }
