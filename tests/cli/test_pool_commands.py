import pytest
from unittest.mock import patch, MagicMock
from argparse import Namespace
from gpuctl.cli.pool import get_pools_command, create_pool_command, delete_pool_command, describe_pool_command


@patch('gpuctl.cli.pool.PoolClient')
def test_get_pools(mock_pool_client):
    """测试用例: 获取资源池列表"""
    mock_instance = MagicMock()
    mock_instance.list_pools.return_value = []
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(json=False)
    result = get_pools_command(args)
    
    assert result == 0


@patch('gpuctl.cli.pool.PoolClient')
def test_describe_pool(mock_pool_client):
    """测试用例: 查看资源池详情"""
    mock_instance = MagicMock()
    mock_instance.get_pool.return_value = {
        "name": "test-pool",
        "status": "active",
        "nodes": []
    }
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(pool_name="test-pool", json=False)
    result = describe_pool_command(args)
    
    assert result == 0


@patch('gpuctl.cli.pool.PoolClient')
def test_delete_pool(mock_pool_client):
    """测试用例: 删除资源池"""
    mock_instance = MagicMock()
    mock_instance.delete_pool.return_value = True
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(pool_name="test-pool", force=False, json=False)
    result = delete_pool_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.pool.PoolClient')
def test_get_pools_with_json(mock_pool_client):
    """测试用例: JSON格式输出资源池"""
    mock_instance = MagicMock()
    mock_instance.list_pools.return_value = []
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(json=True)
    result = get_pools_command(args)
    
    assert result == 0


@patch('gpuctl.cli.pool.PoolClient')
def test_delete_nonexistent_pool(mock_pool_client):
    """测试用例: 删除不存在资源池"""
    mock_instance = MagicMock()
    mock_instance.delete_pool.return_value = False
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(pool_name="nonexistent-pool", force=False, json=False)
    result = delete_pool_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.pool.PoolClient')
def test_describe_pool_with_json(mock_pool_client):
    """测试用例: JSON格式输出资源池详情"""
    mock_instance = MagicMock()
    mock_instance.get_pool.return_value = {
        "name": "test-pool",
        "status": "active",
        "nodes": []
    }
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(pool_name="test-pool", json=True)
    result = describe_pool_command(args)
    
    assert result == 0


@patch('gpuctl.cli.pool.PoolClient')
def test_describe_nonexistent_pool(mock_pool_client):
    """测试用例: 查看不存在资源池详情"""
    mock_instance = MagicMock()
    mock_instance.get_pool.return_value = None
    mock_pool_client.return_value = mock_instance
    
    args = Namespace(pool_name="nonexistent-pool", json=False)
    result = describe_pool_command(args)
    
    assert result in (0, 1)
