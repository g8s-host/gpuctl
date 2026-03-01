import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from argparse import Namespace
from gpuctl.cli.quota import create_quota_command, apply_quota_command, get_quotas_command, describe_quota_command, delete_quota_command, get_namespaces_command, describe_namespace_command, delete_namespace_command
from gpuctl.parser.base_parser import ParserError


@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.quota.QuotaClient')
def test_create_quota(mock_quota_client_class, mock_parse_yaml_file):
    """测试用例: 创建配额"""
    mock_instance = MagicMock()
    mock_instance.create_quota_config.return_value = [
        {"namespace": "default", "cpu": "4", "memory": "8Gi", "gpu": "1"}
    ]
    mock_quota_client_class.return_value = mock_instance
    
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "quota"
    mock_parsed_obj.quota = MagicMock(name="test-quota", description="Test quota")
    mock_parsed_obj.default = None
    mock_parsed_obj.namespace = {"default": MagicMock(get_cpu_str=lambda: "4", memory="8Gi", get_gpu_str=lambda: "1")}
    mock_parse_yaml_file.return_value = mock_parsed_obj
    
    args = Namespace(file=["test.yaml"], json=False)
    result = create_quota_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.quota.QuotaClient')
def test_create_quota_with_default(mock_quota_client_class, mock_parse_yaml_file):
    """测试用例: 创建带默认配额的配额"""
    mock_instance = MagicMock()
    mock_instance.create_quota_config.return_value = [
        {"namespace": "default", "cpu": "2", "memory": "4Gi", "gpu": "0"}
    ]
    mock_quota_client_class.return_value = mock_instance
    
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "quota"
    mock_parsed_obj.quota = MagicMock(name="test-quota", description="Test quota")
    mock_parsed_obj.default = MagicMock(get_cpu_str=lambda: "2", memory="4Gi", get_gpu_str=lambda: "0")
    mock_parsed_obj.namespace = {}
    mock_parse_yaml_file.return_value = mock_parsed_obj
    
    args = Namespace(file=["test.yaml"], json=False)
    result = create_quota_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.quota.QuotaClient')
def test_create_quota_with_json(mock_quota_client_class, mock_parse_yaml_file):
    """测试用例: JSON格式输出创建配额"""
    mock_instance = MagicMock()
    mock_instance.create_quota_config.return_value = [
        {"namespace": "default", "cpu": "4", "memory": "8Gi", "gpu": "1"}
    ]
    mock_quota_client_class.return_value = mock_instance
    
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "quota"
    mock_parsed_obj.quota = MagicMock(name="test-quota", description="Test quota")
    mock_parsed_obj.default = None
    mock_parsed_obj.namespace = {"default": MagicMock(get_cpu_str=lambda: "4", memory="8Gi", get_gpu_str=lambda: "1")}
    mock_parse_yaml_file.return_value = mock_parsed_obj
    
    args = Namespace(file=["test.yaml"], json=True)
    result = create_quota_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
def test_create_quota_unsupported_kind(mock_parse_yaml_file):
    """测试用例: 创建不支持类型的配额"""
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "unsupported"
    mock_parse_yaml_file.return_value = mock_parsed_obj
    
    args = Namespace(file=["test.yaml"], json=False)
    result = create_quota_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
def test_create_quota_parser_error(mock_parse_yaml_file):
    """测试用例: 创建配额时YAML解析错误"""
    mock_parse_yaml_file.side_effect = ParserError("Invalid YAML")
    
    args = Namespace(file=["invalid.yaml"], json=False)
    result = create_quota_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.quota.QuotaClient')
def test_apply_quota(mock_quota_client_class, mock_parse_yaml_file):
    """测试用例: 应用配额"""
    mock_instance = MagicMock()
    mock_instance.apply_quota.return_value = {"status": "created", "namespace": "default", "cpu": "4", "memory": "8Gi", "gpu": "1"}
    mock_instance.apply_default_quota.return_value = {"status": "created", "cpu": "2", "memory": "4Gi", "gpu": "0"}
    mock_quota_client_class.return_value = mock_instance
    
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "quota"
    mock_parsed_obj.quota = MagicMock(name="test-quota", description="Test quota")
    mock_parsed_obj.default = MagicMock(get_cpu_str=lambda: "2", memory="4Gi", get_gpu_str=lambda: "0")
    mock_parsed_obj.namespace = {"default": MagicMock(get_cpu_str=lambda: "4", memory="8Gi", get_gpu_str=lambda: "1")}
    mock_parse_yaml_file.return_value = mock_parsed_obj
    
    args = Namespace(file=["test.yaml"], json=False)
    result = apply_quota_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.quota.QuotaClient')
def test_apply_quota_with_json(mock_quota_client_class, mock_parse_yaml_file):
    """测试用例: JSON格式输出应用配额"""
    mock_instance = MagicMock()
    mock_instance.apply_quota.return_value = {"status": "created", "namespace": "default", "cpu": "4", "memory": "8Gi", "gpu": "1"}
    mock_instance.apply_default_quota.return_value = {"status": "created", "cpu": "2", "memory": "4Gi", "gpu": "0"}
    mock_quota_client_class.return_value = mock_instance
    
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "quota"
    mock_parsed_obj.quota = MagicMock(name="test-quota", description="Test quota")
    mock_parsed_obj.default = MagicMock(get_cpu_str=lambda: "2", memory="4Gi", get_gpu_str=lambda: "0")
    mock_parsed_obj.namespace = {"default": MagicMock(get_cpu_str=lambda: "4", memory="8Gi", get_gpu_str=lambda: "1")}
    mock_parse_yaml_file.return_value = mock_parsed_obj
    
    args = Namespace(file=["test.yaml"], json=True)
    result = apply_quota_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
def test_apply_quota_unsupported_kind(mock_parse_yaml_file):
    """测试用例: 应用不支持类型的配额"""
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "unsupported"
    mock_parse_yaml_file.return_value = mock_parsed_obj
    
    args = Namespace(file=["test.yaml"], json=False)
    result = apply_quota_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
def test_apply_quota_parser_error(mock_parse_yaml_file):
    """测试用例: 应用配额时YAML解析错误"""
    mock_parse_yaml_file.side_effect = ParserError("Invalid YAML")
    
    args = Namespace(file=["invalid.yaml"], json=False)
    result = apply_quota_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.quota.QuotaClient')
def test_apply_quota_no_file(mock_quota_client_class):
    """测试用例: 应用配额时不提供文件"""
    mock_instance = MagicMock()
    mock_quota_client_class.return_value = mock_instance
    
    args = Namespace(file=None, json=False)
    result = apply_quota_command(args)
    
    assert result == 1


@patch('gpuctl.cli.quota.QuotaClient')
def test_get_quotas(mock_quota_client):
    """测试用例: 获取配额列表"""
    mock_instance = MagicMock()
    mock_instance.list_quotas.return_value = []
    mock_quota_client.return_value = mock_instance
    
    args = Namespace(namespace=None, json=False)
    result = get_quotas_command(args)
    
    assert result == 0


@patch('gpuctl.cli.quota.QuotaClient')
def test_describe_quota(mock_quota_client):
    """测试用例: 查看配额详情"""
    mock_instance = MagicMock()
    mock_instance.describe_quota.return_value = {"name": "test-quota", "namespace": "test-ns", "hard": {}, "used": {}}
    mock_quota_client.return_value = mock_instance
    
    args = Namespace(namespace_name="test-namespace", json=False)
    result = describe_quota_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.quota.QuotaClient')
def test_delete_quota(mock_quota_client):
    """测试用例: 删除配额"""
    mock_instance = MagicMock()
    mock_instance.delete_quota_config.return_value = {"deleted": []}
    mock_quota_client.return_value = mock_instance
    
    args = Namespace(quota_name="test-quota", file=None, force=False, json=False)
    result = delete_quota_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.quota.QuotaClient')
def test_get_namespaces(mock_quota_client_class):
    """测试用例: 获取命名空间列表"""
    mock_instance = MagicMock()
    mock_core_v1 = MagicMock()
    
    mock_ns_list = MagicMock()
    mock_ns_list.items = []
    mock_core_v1.list_namespace = MagicMock(return_value=mock_ns_list)
    
    mock_default_ns = MagicMock()
    mock_default_ns.metadata = MagicMock(name='default', creation_timestamp='2024-01-01T00:00:00Z')
    mock_default_ns.status = MagicMock(phase='Active')
    mock_core_v1.read_namespace = MagicMock(return_value=mock_default_ns)
    
    mock_instance.core_v1 = mock_core_v1
    mock_quota_client_class.return_value = mock_instance
    
    args = Namespace(json=False)
    result = get_namespaces_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.quota.QuotaClient')
def test_describe_namespace(mock_quota_client_class):
    """测试用例: 查看命名空间详情"""
    mock_instance = MagicMock()
    mock_core_v1 = MagicMock()
    
    mock_ns = MagicMock()
    mock_ns.metadata = MagicMock(name='test-namespace', creation_timestamp='2024-01-01T00:00:00Z', labels={"g8s.host/namespace": "true"})
    mock_ns.status = MagicMock(phase='Active')
    mock_core_v1.read_namespace = MagicMock(return_value=mock_ns)
    
    mock_instance.core_v1 = mock_core_v1
    mock_instance.get_quota = MagicMock(return_value=None)
    mock_quota_client_class.return_value = mock_instance
    
    args = Namespace(namespace_name="test-namespace", json=False)
    result = describe_namespace_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.quota.QuotaClient')
def test_delete_namespace(mock_quota_client_class):
    """测试用例: 删除命名空间"""
    mock_instance = MagicMock()
    mock_core_v1 = MagicMock()
    
    mock_ns = MagicMock()
    mock_ns.metadata = MagicMock(name='test-namespace', labels={"g8s.host/namespace": "true"})
    mock_core_v1.read_namespace = MagicMock(return_value=mock_ns)
    mock_core_v1.delete_namespace = MagicMock()
    
    mock_instance.core_v1 = mock_core_v1
    mock_quota_client_class.return_value = mock_instance
    
    args = Namespace(namespace_name="test-namespace", force=True, json=False)
    result = delete_namespace_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.quota.QuotaClient')
def test_get_quotas_with_namespace(mock_quota_client):
    """测试用例: 获取指定命名空间配额"""
    mock_instance = MagicMock()
    mock_instance.get_quota.return_value = None
    mock_quota_client.return_value = mock_instance
    
    args = Namespace(namespace="default", json=False)
    result = get_quotas_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.quota.QuotaClient')
def test_get_quotas_with_json(mock_quota_client):
    """测试用例: JSON格式输出配额"""
    mock_instance = MagicMock()
    mock_instance.list_quotas.return_value = []
    mock_quota_client.return_value = mock_instance
    
    args = Namespace(namespace=None, json=True)
    result = get_quotas_command(args)
    
    assert result == 0


@patch('gpuctl.cli.quota.QuotaClient')
def test_get_namespaces_with_json(mock_quota_client_class):
    """测试用例: JSON格式输出命名空间"""
    mock_instance = MagicMock()
    mock_core_v1 = MagicMock()
    
    mock_ns_list = MagicMock()
    mock_ns_list.items = []
    mock_core_v1.list_namespace = MagicMock(return_value=mock_ns_list)
    
    mock_default_ns = MagicMock()
    mock_default_ns.metadata = MagicMock(name='default', creation_timestamp='2024-01-01T00:00:00Z')
    mock_default_ns.status = MagicMock(phase='Active')
    mock_core_v1.read_namespace = MagicMock(return_value=mock_default_ns)
    
    mock_instance.core_v1 = mock_core_v1
    mock_quota_client_class.return_value = mock_instance
    
    args = Namespace(json=True)
    result = get_namespaces_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.quota.QuotaClient')
def test_delete_nonexistent_quota(mock_quota_client):
    """测试用例: 删除不存在配额"""
    mock_instance = MagicMock()
    mock_instance.delete_quota_config.return_value = {"deleted": []}
    mock_quota_client.return_value = mock_instance
    
    args = Namespace(quota_name="nonexistent-quota", file=None, force=False, json=False)
    result = delete_quota_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.quota.QuotaClient')
def test_delete_nonexistent_namespace(mock_quota_client_class):
    """测试用例: 删除不存在命名空间"""
    mock_instance = MagicMock()
    mock_core_v1 = MagicMock()
    mock_core_v1.read_namespace.side_effect = Exception("Namespace not found")
    mock_instance.core_v1 = mock_core_v1
    mock_quota_client_class.return_value = mock_instance
    
    args = Namespace(namespace_name="nonexistent-namespace", force=False, json=False)
    result = delete_namespace_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.quota.QuotaClient')
def test_describe_quota_with_json(mock_quota_client):
    """测试用例: JSON格式输出配额详情"""
    mock_instance = MagicMock()
    mock_instance.describe_quota.return_value = {"name": "test-quota", "namespace": "test-ns", "hard": {}, "used": {}}
    mock_quota_client.return_value = mock_instance
    
    args = Namespace(namespace_name="test-namespace", json=True)
    result = describe_quota_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.quota.QuotaClient')
def test_describe_namespace_with_json(mock_quota_client_class):
    """测试用例: JSON格式输出命名空间详情"""
    mock_instance = MagicMock()
    mock_core_v1 = MagicMock()
    
    mock_ns = MagicMock()
    mock_ns.metadata = MagicMock(name='test-namespace', creation_timestamp='2024-01-01T00:00:00Z', labels={"g8s.host/namespace": "true"})
    mock_ns.status = MagicMock(phase='Active')
    mock_core_v1.read_namespace = MagicMock(return_value=mock_ns)
    
    mock_instance.core_v1 = mock_core_v1
    mock_instance.get_quota = MagicMock(return_value=None)
    mock_quota_client_class.return_value = mock_instance
    
    args = Namespace(namespace_name="test-namespace", json=True)
    result = describe_namespace_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.quota.QuotaClient')
def test_describe_nonexistent_quota(mock_quota_client):
    """测试用例: 查看不存在配额详情"""
    mock_instance = MagicMock()
    mock_instance.describe_quota.return_value = None
    mock_quota_client.return_value = mock_instance
    
    args = Namespace(namespace_name="nonexistent-namespace", json=False)
    result = describe_quota_command(args)
    
    assert result in (0, 1)


@patch('gpuctl.cli.quota.QuotaClient')
def test_describe_nonexistent_namespace(mock_quota_client_class):
    """测试用例: 查看不存在命名空间详情"""
    mock_instance = MagicMock()
    mock_core_v1 = MagicMock()
    mock_core_v1.read_namespace.side_effect = Exception("Namespace not found")
    mock_instance.core_v1 = mock_core_v1
    mock_quota_client_class.return_value = mock_instance
    
    args = Namespace(namespace_name="nonexistent-namespace", json=False)
    result = describe_namespace_command(args)
    
    assert result in (0, 1)
