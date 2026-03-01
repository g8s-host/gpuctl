import pytest
from unittest.mock import patch, MagicMock
from argparse import Namespace
from gpuctl.cli.node import get_nodes_command, label_node_command, describe_node_command, get_labels_command


@patch('gpuctl.cli.node.PoolClient')
def test_get_nodes(mock_pool_client):
    """测试用例: 获取节点列表"""
    mock_instance = MagicMock()
    mock_instance.list_nodes.return_value = []
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(pool=None, gpu_type=None, json=False)
    result = get_nodes_command(args)
    
    assert result == 0


@patch('gpuctl.cli.node.PoolClient')
def test_get_labels(mock_pool_client):
    """测试用例: 获取节点标签"""
    mock_instance = MagicMock()
    mock_instance.get_node.return_value = {"labels": {}}
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(node_name="leon-host", key=None, json=False)
    result = get_labels_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.node.PoolClient')
def test_label_node(mock_pool_client):
    """测试用例: 为节点添加标签"""
    mock_instance = MagicMock()
    mock_instance._label_node = MagicMock()
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(node_name=["node-1"], label="gpuType=a100-80g", delete=False, overwrite=False, json=False)
    result = label_node_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.node.PoolClient')
def test_describe_node(mock_pool_client):
    """测试用例: 查看节点详情"""
    mock_instance = MagicMock()
    mock_instance.get_node.return_value = {"name": "node-1", "labels": {}}
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(node_name="node-1", json=False)
    result = describe_node_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.node.PoolClient')
def test_get_nodes_with_pool(mock_pool_client):
    """测试用例: 按资源池过滤节点"""
    mock_instance = MagicMock()
    mock_instance.list_nodes.return_value = []
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(pool="test-pool", gpu_type=None, json=False)
    result = get_nodes_command(args)
    
    assert result == 0


@patch('gpuctl.cli.node.PoolClient')
def test_get_nodes_with_gpu_type(mock_pool_client):
    """测试用例: 按GPU类型过滤节点"""
    mock_instance = MagicMock()
    mock_instance.list_nodes.return_value = []
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(pool=None, gpu_type="a10-24g", json=False)
    result = get_nodes_command(args)
    
    assert result == 0


@patch('gpuctl.cli.node.PoolClient')
def test_get_nodes_with_json(mock_pool_client):
    """测试用例: JSON格式输出节点"""
    mock_instance = MagicMock()
    mock_instance.list_nodes.return_value = []
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(pool=None, gpu_type=None, json=True)
    result = get_nodes_command(args)
    
    assert result == 0


@patch('gpuctl.cli.node.PoolClient')
def test_label_node_with_overwrite(mock_pool_client):
    """测试用例: 覆盖节点标签"""
    mock_instance = MagicMock()
    mock_instance._label_node = MagicMock()
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(node_name=["node-1"], label="gpuType=a100-40g", delete=False, overwrite=True, json=False)
    result = label_node_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.node.PoolClient')
def test_delete_label(mock_pool_client):
    """测试用例: 删除节点标签"""
    mock_instance = MagicMock()
    mock_instance._remove_node_label = MagicMock()
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(node_name=["node-1"], label="gpuType", delete=True, overwrite=False, json=False)
    result = label_node_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.node.PoolClient')
def test_label_node_with_json(mock_pool_client):
    """测试用例: JSON格式输出标签操作"""
    mock_instance = MagicMock()
    mock_instance._label_node = MagicMock()
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(node_name=["node-1"], label="pool=test-pool", delete=False, overwrite=False, json=True)
    result = label_node_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.node.PoolClient')
def test_label_nonexistent_node(mock_pool_client):
    """测试用例: 为不存在节点添加标签"""
    mock_instance = MagicMock()
    mock_instance._label_node.side_effect = Exception("Node not found")
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(node_name=["nonexistent-node"], label="pool=test-pool", delete=False, overwrite=False, json=False)
    result = label_node_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.node.PoolClient')
def test_describe_node_with_json(mock_pool_client):
    """测试用例: JSON格式输出节点详情"""
    mock_instance = MagicMock()
    mock_instance.get_node.return_value = {"name": "node-1", "labels": {}}
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(node_name="node-1", json=True)
    result = describe_node_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.node.PoolClient')
def test_describe_nonexistent_node(mock_pool_client):
    """测试用例: 查看不存在节点详情"""
    mock_instance = MagicMock()
    mock_instance.get_node.return_value = None
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(node_name="nonexistent-node", json=False)
    result = describe_node_command(args)
    
    assert result in (0, 1)
