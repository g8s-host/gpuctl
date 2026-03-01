import pytest
from unittest.mock import patch, MagicMock, call
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
    
    assert result == 1


# ── create_pool_command ────────────────────────────────────────────────────────

@patch('gpuctl.cli.pool.PoolClient')
def test_create_pool(mock_pool_client):
    """测试用例: 创建资源池"""
    mock_instance = MagicMock()
    mock_instance.create_pool.return_value = {
        "name": "test-pool",
        "status": "created",
        "message": "Resource pool created successfully"
    }
    mock_pool_client.return_value = mock_instance

    args = Namespace(
        name="test-pool",
        description="带多个节点的资源池",
        nodes=["node1", "node2"],
        gpu_type="a100-80g",
        quota=None,
        json=False
    )
    result = create_pool_command(args)

    assert result == 0
    mock_instance.create_pool.assert_called_once()


@patch('gpuctl.cli.pool.PoolClient')
def test_create_pool_with_json(mock_pool_client):
    """测试用例: JSON格式输出创建资源池"""
    mock_instance = MagicMock()
    mock_instance.create_pool.return_value = {
        "name": "test-pool",
        "status": "created",
        "message": "Resource pool created successfully"
    }
    mock_pool_client.return_value = mock_instance

    args = Namespace(
        name="test-pool",
        description="测试资源池",
        nodes=["node1"],
        gpu_type="a10-24g",
        quota=None,
        json=True
    )
    result = create_pool_command(args)

    assert result == 0
    mock_instance.create_pool.assert_called_once()


@patch('gpuctl.cli.pool.PoolClient')
def test_create_pool_failure(mock_pool_client):
    """测试用例: 创建资源池失败（节点不存在等异常）"""
    mock_instance = MagicMock()
    mock_instance.create_pool.side_effect = Exception("Node 'nonexistent-node' not found")
    mock_pool_client.return_value = mock_instance

    args = Namespace(
        name="bad-pool",
        description="",
        nodes=["nonexistent-node"],
        gpu_type=None,
        quota=None,
        json=False
    )
    result = create_pool_command(args)

    assert result == 1


@patch('gpuctl.cli.pool.PoolClient')
def test_create_pool_failure_with_json(mock_pool_client):
    """测试用例: JSON格式输出创建资源池失败"""
    mock_instance = MagicMock()
    mock_instance.create_pool.side_effect = Exception("Pool already exists")
    mock_pool_client.return_value = mock_instance

    args = Namespace(
        name="existing-pool",
        description="",
        nodes=["node1"],
        gpu_type=None,
        quota=None,
        json=True
    )
    result = create_pool_command(args)

    assert result == 1


# ── delete_pool_command 补充 ───────────────────────────────────────────────────

@patch('gpuctl.cli.pool.PoolClient')
def test_delete_pool_with_force(mock_pool_client):
    """测试用例: 强制删除资源池"""
    mock_instance = MagicMock()
    mock_instance.delete_pool.return_value = True
    mock_pool_client.return_value = mock_instance

    args = Namespace(pool_name="test-pool", force=True, json=False)
    result = delete_pool_command(args)

    assert result == 0
    mock_instance.delete_pool.assert_called_once_with("test-pool")


@patch('gpuctl.cli.pool.PoolClient')
def test_delete_pool_with_json(mock_pool_client):
    """测试用例: JSON格式输出删除资源池"""
    mock_instance = MagicMock()
    mock_instance.delete_pool.return_value = True
    mock_pool_client.return_value = mock_instance

    args = Namespace(pool_name="test-pool", force=False, json=True)
    result = delete_pool_command(args)

    assert result == 0


@patch('gpuctl.cli.pool.PoolClient')
def test_delete_pool_exception(mock_pool_client):
    """测试用例: 删除资源池时发生异常"""
    mock_instance = MagicMock()
    mock_instance.delete_pool.side_effect = Exception("Connection refused")
    mock_pool_client.return_value = mock_instance

    args = Namespace(pool_name="test-pool", force=False, json=False)
    result = delete_pool_command(args)

    assert result == 1


# ── describe_pool_command 补充 ─────────────────────────────────────────────────

@patch('gpuctl.cli.pool.PoolClient')
def test_describe_pool_with_nodes_and_jobs(mock_pool_client):
    """测试用例: 查看包含节点和运行中作业的资源池详情"""
    mock_instance = MagicMock()
    mock_instance.get_pool.return_value = {
        "name": "test-pool",
        "description": "测试资源池",
        "status": "active",
        "gpu_total": 4,
        "gpu_used": 2,
        "gpu_free": 2,
        "gpu_types": ["A100"],
        "nodes": ["node-1", "node-2"],
        "jobs": [
            {"name": "train-job", "gpu": 2}
        ]
    }
    mock_pool_client.return_value = mock_instance

    args = Namespace(pool_name="test-pool", json=False)
    result = describe_pool_command(args)

    assert result == 0
    mock_instance.get_pool.assert_called_once_with("test-pool")


@patch('gpuctl.cli.pool.PoolClient')
def test_describe_pool_nonexistent_with_json(mock_pool_client):
    """测试用例: JSON格式输出查看不存在资源池详情"""
    mock_instance = MagicMock()
    mock_instance.get_pool.return_value = None
    mock_pool_client.return_value = mock_instance

    args = Namespace(pool_name="nonexistent-pool", json=True)
    result = describe_pool_command(args)

    assert result == 1
