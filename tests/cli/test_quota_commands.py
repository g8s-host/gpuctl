import pytest
from unittest.mock import patch, MagicMock
from argparse import Namespace
from gpuctl.cli.quota import create_quota_command, get_quotas_command, describe_quota_command, delete_quota_command
from gpuctl.parser.base_parser import ParserError


@patch('gpuctl.cli.quota.QuotaClient')
def test_get_quotas_command(mock_quota_client):
    """测试获取配额列表命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.list_quotas.return_value = [
        {
            "name": "test-quota-1",
            "namespace": "default",
            "hard": {
                "cpu": "10",
                "memory": "100Gi",
                "nvidia.com/gpu": "16"
            },
            "status": "Active"
        },
        {
            "name": "test-quota-2",
            "namespace": "test-namespace",
            "hard": {
                "cpu": "5",
                "memory": "50Gi",
                "nvidia.com/gpu": "8"
            },
            "status": "Active"
        }
    ]
    mock_quota_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(namespace=None)
    result = get_quotas_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.list_quotas.assert_called_once()


@patch('gpuctl.cli.quota.QuotaClient')
def test_get_quotas_with_namespace_command(mock_quota_client):
    """测试使用namespace参数获取配额列表命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.get_quota.return_value = {
        "name": "test-quota",
        "namespace": "test-namespace",
        "hard": {
            "cpu": "5",
            "memory": "50Gi",
            "nvidia.com/gpu": "8"
        },
        "status": "Active"
    }
    mock_quota_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(namespace="test-namespace")
    result = get_quotas_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.get_quota.assert_called_once_with("test-namespace")


@patch('gpuctl.cli.quota.QuotaClient')
def test_describe_quota_command(mock_quota_client):
    """测试获取配额详情命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.describe_quota.return_value = {
        "name": "test-quota",
        "namespace": "test-namespace",
        "hard": {
            "cpu": "5",
            "memory": "50Gi",
            "nvidia.com/gpu": "8"
        },
        "used": {
            "cpu": "2",
            "memory": "20Gi",
            "nvidia.com/gpu": "3"
        },
        "status": "Active"
    }
    mock_quota_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(namespace_name="test-namespace")
    result = describe_quota_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.describe_quota.assert_called_once_with("test-namespace")


@patch('gpuctl.cli.quota.QuotaClient')
def test_create_quota_command(mock_quota_client):
    """测试创建配额命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.create_quota_config.return_value = [
        {
            "namespace": "test-namespace",
            "cpu": "5",
            "memory": "50Gi",
            "gpu": "8"
        }
    ]
    mock_quota_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(file=["test-quota.yaml"], namespace="default")
    
    # 模拟解析YAML文件
    with patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file') as mock_parse_yaml_file:
        mock_parse_yaml_file.return_value.kind = "quota"
        mock_parse_yaml_file.return_value.metadata = MagicMock()
        mock_parse_yaml_file.return_value.metadata.name = "test-quota"
        mock_parse_yaml_file.return_value.metadata.description = "Test quota"
        mock_parse_yaml_file.return_value.default = MagicMock()
        mock_parse_yaml_file.return_value.default.get_cpu_str = MagicMock(return_value="10")
        mock_parse_yaml_file.return_value.default.memory = "100Gi"
        mock_parse_yaml_file.return_value.default.get_gpu_str = MagicMock(return_value="16")
        mock_parse_yaml_file.return_value.namespace = {
            "test-namespace": MagicMock(
                get_cpu_str=MagicMock(return_value="5"),
                memory="50Gi",
                get_gpu_str=MagicMock(return_value="8")
            )
        }
        
        result = create_quota_command(args)
        
        # 断言结果
        assert result == 0
        mock_instance.create_quota_config.assert_called_once()


@patch('gpuctl.cli.quota.QuotaClient')
def test_delete_quota_command(mock_quota_client):
    """测试删除配额命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.delete_quota.return_value = True
    mock_quota_client.return_value = mock_instance
    
    # 模拟input函数，避免交互式输入
    with patch('builtins.input', return_value='Y'):
        # 调用命令
        args = Namespace(namespace_name="test-namespace", file=None, force=False)
        result = delete_quota_command(args)
        
        # 断言结果
        assert result == 0
        mock_instance.delete_quota.assert_called_once_with("test-namespace")


@patch('gpuctl.cli.quota.QuotaClient')
def test_delete_quota_with_file_command(mock_quota_client):
    """测试通过文件删除配额命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.delete_quota_config.return_value = {
        "deleted": [{"namespace": "test-namespace"}],
        "failed": []
    }
    mock_quota_client.return_value = mock_instance
    
    # 模拟input函数，避免交互式输入
    with patch('builtins.input', return_value='Y'):
        # 调用命令
        args = Namespace(namespace_name=None, file="test-quota.yaml", force=False)
        
        # 模拟解析YAML文件
        with patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file') as mock_parse_yaml_file:
            mock_parse_yaml_file.return_value.kind = "quota"
            mock_parse_yaml_file.return_value.metadata = MagicMock()
            mock_parse_yaml_file.return_value.metadata.name = "test-quota"
            mock_parse_yaml_file.return_value.namespace = {"test-namespace": {}}
            mock_parse_yaml_file.return_value.default = None
            
            result = delete_quota_command(args)
            
            # 断言结果
            assert result == 0
            mock_parse_yaml_file.assert_called_once_with("test-quota.yaml")
            mock_instance.delete_quota_config.assert_called_once()


@patch('gpuctl.cli.quota.QuotaClient')
def test_delete_quota_with_force_command(mock_quota_client):
    """测试使用--force选项删除配额命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.delete_quota.return_value = True
    mock_quota_client.return_value = mock_instance
    
    # 调用命令 - 使用--force选项，不需要input
    args = Namespace(namespace_name="test-namespace", file=None, force=True)
    result = delete_quota_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.delete_quota.assert_called_once_with("test-namespace")
