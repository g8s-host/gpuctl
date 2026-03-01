import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@patch('server.routes.nodes.PoolClient.get_instance')
def test_get_nodes(mock_get_instance, client):
    """测试获取节点列表API"""
    mock_instance = MagicMock()
    mock_instance.list_nodes.return_value = [
        {
            "name": "node-1",
            "gpu_total": 4,
            "gpu_used": 2,
            "gpu_free": 2,
            "gpu_types": ["A100"],
            "status": "ready",
            "labels": {"g8s.host/pool": "test-pool"}
        },
        {
            "name": "node-2",
            "gpu_total": 4,
            "gpu_used": 0,
            "gpu_free": 4,
            "gpu_types": ["H100"],
            "status": "ready",
            "labels": {"g8s.host/pool": "test-pool"}
        }
    ]
    mock_get_instance.return_value = mock_instance

    response = client.get(
        "/api/v1/nodes",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 2
    assert response.json()["items"][0]["nodeName"] == "node-1"


@patch('server.routes.nodes.PoolClient.get_instance')
def test_get_node_detail(mock_get_instance, client):
    """测试获取节点详情API"""
    mock_instance = MagicMock()
    mock_instance.get_node.return_value = {
        "name": "node-1",
        "gpu_total": 4,
        "gpu_used": 2,
        "gpu_free": 2,
        "gpu_types": ["A100"],
        "status": "ready",
        "labels": {"g8s.host/pool": "test-pool"},
        "addresses": ["192.168.1.100"]
    }
    mock_get_instance.return_value = mock_instance

    response = client.get(
        "/api/v1/nodes/node-1",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.json()["nodeName"] == "node-1"
    assert response.json()["resources"]["gpuTotal"] == 4


@patch('server.routes.nodes.PoolClient.get_instance')
def test_add_node_to_pool(mock_get_instance, client):
    """测试将节点添加到资源池API"""
    mock_instance = MagicMock()
    mock_instance.add_nodes_to_pool.return_value = {
        "success": True,
        "nodes": ["node-1"],
        "pool": "test-pool"
    }
    mock_get_instance.return_value = mock_instance

    response = client.post(
        "/api/v1/nodes/node-1/pools",
        json={"pool": "test-pool"},
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "node": "node-1",
        "pool": "test-pool",
        "message": "节点已成功添加到资源池"
    }


@patch('server.routes.nodes.PoolClient.get_instance')
def test_remove_node_from_pool(mock_get_instance, client):
    """测试从资源池移除节点API"""
    mock_instance = MagicMock()
    mock_instance.remove_nodes_from_pool.return_value = {
        "success": True,
        "nodes": ["node-1"],
        "pool": "test-pool"
    }
    mock_get_instance.return_value = mock_instance

    response = client.delete(
        "/api/v1/nodes/node-1/pools/test-pool",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "node": "node-1",
        "pool": "test-pool",
        "message": "节点已成功从资源池移除"
    }


@patch('server.routes.nodes.PoolClient.get_instance')
def test_get_node_labels(mock_get_instance, client):
    """测试获取节点标签API"""
    mock_instance = MagicMock()
    mock_instance.get_node.return_value = {
        "name": "node-1",
        "labels": {"g8s.host/pool": "test-pool", "gpu-type": "A100"}
    }
    mock_get_instance.return_value = mock_instance

    response = client.get(
        "/api/v1/nodes/node-1/labels",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "node": "node-1",
        "labels": {"g8s.host/pool": "test-pool", "gpu-type": "A100"}
    }
