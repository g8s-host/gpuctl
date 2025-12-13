import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from gpuctl.client.pool_client import PoolClient
from server.main import app

@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@patch('server.routes.labels.PoolClient')
def test_add_node_label(mock_pool_client, client):
    """测试为节点添加标签API"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance._label_node = MagicMock(return_value=True)
    mock_instance.get_node = MagicMock(return_value={"name": "node-1"})
    mock_pool_client.return_value = mock_instance
    
    # 发送API请求
    response = client.post(
        "/api/v1/nodes/node-1/labels",
        json={"key": "gpu-type", "value": "A100"},
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json() == {
        "nodeName": "node-1",
        "label": {"gpu-type": "A100"},
        "message": "标签添加成功"
    }


@patch('server.routes.labels.PoolClient')
def test_remove_node_label(mock_pool_client, client):
    """测试删除节点标签API"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance._remove_node_label = MagicMock(return_value=True)
    mock_instance.get_node = MagicMock(return_value={"name": "node-1"})
    mock_pool_client.return_value = mock_instance
    
    # 发送API请求
    response = client.delete(
        "/api/v1/nodes/node-1/labels/gpu-type",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json() == {
        "node": "node-1",
        "label": "gpu-type",
        "message": "标签删除成功"
    }


@patch('server.routes.labels.PoolClient')
def test_update_node_label(mock_pool_client, client):
    """测试更新节点标签API"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance._label_node = MagicMock(return_value=True)
    mock_instance.get_node = MagicMock(return_value={"name": "node-1"})
    mock_pool_client.return_value = mock_instance
    
    # 发送API请求
    response = client.put(
        "/api/v1/nodes/node-1/labels/gpu-type",
        json={"value": "H100"},
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json() == {
        "node": "node-1",
        "label": "gpu-type=H100",
        "message": "标签更新成功"
    }


@patch('server.routes.labels.PoolClient')
def test_get_node_labels(mock_pool_client, client):
    """测试获取节点标签API"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.get_node = MagicMock(return_value={
        "name": "node-1",
        "labels": {
            "gpuctl/pool": "test-pool",
            "gpu-type": "A100",
            "node-role.kubernetes.io/worker": "true"
        }
    })
    mock_pool_client.return_value = mock_instance
    
    # 发送API请求
    response = client.get(
        "/api/v1/nodes/node-1/labels",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json() == {
        "node": "node-1",
        "labels": {
            "gpuctl/pool": "test-pool",
            "gpu-type": "A100",
            "node-role.kubernetes.io/worker": "true"
        }
    }


@patch('server.routes.labels.PoolClient')
def test_list_all_node_labels(mock_pool_client, client):
    """测试获取所有节点标签API"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.list_nodes = MagicMock(return_value=[
        {
            "name": "node-1",
            "labels": {
                "gpuctl/pool": "test-pool",
                "gpu-type": "A100"
            }
        },
        {
            "name": "node-2",
            "labels": {
                "gpuctl/pool": "test-pool",
                "gpu-type": "H100"
            }
        }
    ])
    mock_pool_client.return_value = mock_instance
    
    # 发送API请求
    response = client.get(
        "/api/v1/labels",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
