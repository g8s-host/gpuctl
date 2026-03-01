import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from server.main import app
from datetime import datetime


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@patch('server.routes.labels.PoolClient.get_instance')
def test_get_node_label_key(mock_get_instance, client):
    """测试获取特定节点标签API"""
    mock_instance = MagicMock()
    mock_node = MagicMock()
    mock_node.metadata.labels = {
        "gpu-type": "A100",
        "g8s.host/pool": "test-pool"
    }
    mock_node.metadata.creation_timestamp = datetime.now()
    mock_instance.core_v1.read_node.return_value = mock_node
    mock_get_instance.return_value = mock_instance

    response = client.get(
        "/api/v1/nodes/node-1/labels/gpu-type",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.json()["label"]["key"] == "gpu-type"
    assert response.json()["label"]["value"] == "A100"


@patch('server.routes.labels.PoolClient.get_instance')
def test_batch_add_node_labels(mock_get_instance, client):
    """测试批量添加节点标签API"""
    mock_instance = MagicMock()
    mock_node1 = MagicMock()
    mock_node1.metadata.labels = {"existing": "label"}
    mock_node2 = MagicMock()
    mock_node2.metadata.labels = {}
    mock_instance.core_v1.read_node = MagicMock(side_effect=[mock_node1, mock_node2])
    mock_instance._label_node = MagicMock(return_value=True)
    mock_get_instance.return_value = mock_instance

    response = client.post(
        "/api/v1/nodes/labels/batch?nodeNames=node-1,node-2&key=gpu-type&value=A100&overwrite=true",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert "success" in response.json()
    assert "failed" in response.json()


@patch('server.routes.labels.PoolClient.get_instance')
def test_get_node_labels_all(mock_get_instance, client):
    """测试获取所有节点标签API"""
    mock_instance = MagicMock()
    mock_instance.list_nodes.return_value = [
        {
            "name": "node-1",
            "labels": {"gpu-type": "A100", "pool": "test-pool"}
        },
        {
            "name": "node-2",
            "labels": {"gpu-type": "H100", "pool": "test-pool"}
        }
    ]
    mock_get_instance.return_value = mock_instance

    response = client.get(
        "/api/v1/nodes/labels/all",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert "items" in response.json()
