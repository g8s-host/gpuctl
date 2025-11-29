import pytest
from unittest.mock import patch, MagicMock
from argparse import Namespace
from gpuctl.cli.pool import get_pools_command, create_pool_command


@patch('gpuctl.cli.pool.PoolClient')
def test_get_pools_command(mock_pool_client):
    """测试获取资源池列表命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.list_pools.return_value = [
        {
            "name": "test-pool-1",
            "status": "active",
            "gpu_total": 8,
            "gpu_used": 4,
            "gpu_free": 4,
            "gpu_types": ["A100", "H100"],
            "nodes": ["node-1", "node-2"]
        },
        {
            "name": "test-pool-2",
            "status": "active",
            "gpu_total": 4,
            "gpu_used": 0,
            "gpu_free": 4,
            "gpu_types": ["V100"],
            "nodes": ["node-3"]
        }
    ]
    mock_pool_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace()
    result = get_pools_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.list_pools.assert_called_once()


@patch('gpuctl.cli.pool.PoolClient')
def test_get_pools_command_empty(mock_pool_client):
    """测试获取空资源池列表命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.list_pools.return_value = []
    mock_pool_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace()
    result = get_pools_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.list_pools.assert_called_once()


@patch('gpuctl.cli.pool.PoolClient')
def test_create_pool_command(mock_pool_client):
    """测试创建资源池命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.create_pool.return_value = {
        "name": "test-pool",
        "status": "created",
        "message": "Pool created successfully"
    }
    mock_pool_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(
        name="test-pool",
        description="Test pool",
        nodes=["node-1", "node-2"],
        gpu_type=["A100"],
        quota={"maxJobs": 100, "maxGpuPerJob": 8}
    )
    result = create_pool_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.create_pool.assert_called_once()
    assert mock_instance.create_pool.call_args[0][0]["name"] == "test-pool"
    assert mock_instance.create_pool.call_args[0][0]["description"] == "Test pool"
    assert mock_instance.create_pool.call_args[0][0]["nodes"] == ["node-1", "node-2"]
    assert mock_instance.create_pool.call_args[0][0]["gpu_type"] == ["A100"]
