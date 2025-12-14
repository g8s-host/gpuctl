import pytest
from unittest.mock import patch, MagicMock
from argparse import Namespace
from gpuctl.cli.node import get_nodes_command, label_node_command, add_node_to_pool_command, remove_node_from_pool_command


@patch('gpuctl.cli.node.PoolClient')
def test_get_nodes_command(mock_pool_client):
    """测试获取节点列表命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.list_nodes.return_value = [
        {
            "name": "node-1",
            "status": "active",
            "gpu_total": 8,
            "gpu_used": 4,
            "gpu_free": 4,
            "gpu_types": ["A100"],
            "labels": {"g8s.host/pool": "training-pool"}
        },
        {
            "name": "node-2",
            "status": "active",
            "gpu_total": 4,
            "gpu_used": 0,
            "gpu_free": 4,
            "gpu_types": ["V100"],
            "labels": {"g8s.host/pool": "inference-pool"}
        }
    ]
    mock_pool_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(pool=None, gpu_type=None)
    result = get_nodes_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.list_nodes.assert_called_once()


@patch('gpuctl.cli.node.PoolClient')
def test_label_node_add(mock_pool_client):
    """测试为节点添加标签命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_pool_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(node_name=["node-1"], label="nvidia.com/gpu-type=a100", delete=False)
    result = label_node_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance._label_node.assert_called_once_with("node-1", "nvidia.com/gpu-type", "a100")


@patch('gpuctl.cli.node.PoolClient')
def test_label_node_delete(mock_pool_client):
    """测试删除节点标签命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_pool_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(node_name=["node-1"], label="nvidia.com/gpu-type", delete=True)
    result = label_node_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance._remove_node_label.assert_called_once_with("node-1", "nvidia.com/gpu-type")


@patch('gpuctl.cli.node.PoolClient')
def test_label_node_missing_label(mock_pool_client):
    """测试缺少标签参数的情况"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_pool_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(node_name=["node-1"], label=None, delete=False)
    result = label_node_command(args)
    
    # 断言结果
    assert result == 1


@patch('gpuctl.cli.node.PoolClient')
def test_add_node_to_pool(mock_pool_client):
    """测试将节点添加到资源池命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.add_nodes_to_pool.return_value = {
        "success": ["node-1", "node-2"],
        "failed": []
    }
    mock_pool_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(node_name=["node-1", "node-2"], pool="training-pool")
    result = add_node_to_pool_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.add_nodes_to_pool.assert_called_once_with("training-pool", ["node-1", "node-2"])


@patch('gpuctl.cli.node.PoolClient')
def test_add_node_to_pool_partial_success(mock_pool_client):
    """测试部分节点添加到资源池成功的情况"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.add_nodes_to_pool.return_value = {
        "success": ["node-1"],
        "failed": [{"node": "node-2", "error": "Node not found"}]
    }
    mock_pool_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(node_name=["node-1", "node-2"], pool="training-pool")
    result = add_node_to_pool_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.add_nodes_to_pool.assert_called_once_with("training-pool", ["node-1", "node-2"])


@patch('gpuctl.cli.node.PoolClient')
def test_remove_node_from_pool(mock_pool_client):
    """测试从资源池移除节点命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.remove_nodes_from_pool.return_value = {
        "success": ["node-1"],
        "failed": []
    }
    mock_pool_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(node_name=["node-1"], pool="training-pool")
    result = remove_node_from_pool_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.remove_nodes_from_pool.assert_called_once_with("training-pool", ["node-1"])


@patch('gpuctl.cli.node.PoolClient')
def test_remove_node_from_pool_partial_success(mock_pool_client):
    """测试部分节点从资源池移除成功的情况"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.remove_nodes_from_pool.return_value = {
        "success": ["node-1"],
        "failed": [{"node": "node-2", "error": "Node not found"}]
    }
    mock_pool_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(node_name=["node-1", "node-2"], pool="training-pool")
    result = remove_node_from_pool_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.remove_nodes_from_pool.assert_called_once_with("training-pool", ["node-1", "node-2"])
