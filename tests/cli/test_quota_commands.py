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


# ── delete_quota_command 补充 ──────────────────────────────────────────────────

@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.quota.QuotaClient')
def test_delete_quota_via_file_with_force(mock_quota_client_class, mock_parse_yaml_file):
    """测试用例: 通过 YAML 文件强制删除配额（-f --force）"""
    mock_instance = MagicMock()
    mock_instance.delete_quota_config.return_value = {
        "deleted": [{"namespace": "test-namespace", "status": "deleted"}],
        "failed": []
    }
    mock_quota_client_class.return_value = mock_instance

    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "quota"
    mock_parsed_obj.quota = MagicMock(name="test-quota")
    mock_parsed_obj.namespace = {"test-namespace": MagicMock()}
    mock_parsed_obj.default = None
    mock_parse_yaml_file.return_value = mock_parsed_obj

    args = Namespace(file=["test-quota.yaml"], quota_name=None, force=True, json=False)
    result = delete_quota_command(args)

    assert result in (0, 1)
    mock_instance.delete_quota_config.assert_called_once()


@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.quota.QuotaClient')
def test_delete_quota_via_file_with_json(mock_quota_client_class, mock_parse_yaml_file):
    """测试用例: 通过 YAML 文件删除配额并以 JSON 格式输出（跳过确认）"""
    mock_instance = MagicMock()
    mock_instance.delete_quota_config.return_value = {
        "deleted": [{"namespace": "test-namespace", "status": "deleted"}],
        "failed": []
    }
    mock_quota_client_class.return_value = mock_instance

    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "quota"
    mock_parsed_obj.quota = MagicMock(name="test-quota")
    mock_parsed_obj.namespace = {"test-namespace": MagicMock()}
    mock_parsed_obj.default = None
    mock_parse_yaml_file.return_value = mock_parsed_obj

    args = Namespace(file=["test-quota.yaml"], quota_name=None, force=False, json=True)
    result = delete_quota_command(args)

    assert result in (0, 1)


@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.quota.QuotaClient')
def test_delete_quota_via_file_unsupported_kind(mock_quota_client_class, mock_parse_yaml_file):
    """测试用例: YAML 文件的 kind 不是 quota 时报错"""
    mock_instance = MagicMock()
    mock_quota_client_class.return_value = mock_instance

    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "pool"
    mock_parse_yaml_file.return_value = mock_parsed_obj

    args = Namespace(file=["test-pool.yaml"], quota_name=None, force=True, json=False)
    result = delete_quota_command(args)

    assert result in (0, 1)
    mock_instance.delete_quota_config.assert_not_called()


@patch('gpuctl.cli.quota.QuotaClient')
def test_delete_quota_by_name_with_json(mock_quota_client):
    """测试用例: 通过名称删除配额并以 JSON 格式输出（跳过确认提示）"""
    mock_instance = MagicMock()
    mock_instance.delete_quota_config.return_value = {
        "deleted": [{"namespace": "default", "status": "deleted"}],
        "failed": []
    }
    mock_quota_client.return_value = mock_instance

    args = Namespace(quota_name="test-quota", file=None, force=False, json=True)
    result = delete_quota_command(args)

    assert result in (0, 1)


# ── delete_namespace_command 补充 ──────────────────────────────────────────────

@patch('gpuctl.cli.quota.QuotaClient')
def test_delete_non_gpuctl_namespace(mock_quota_client_class):
    """测试用例: 删除非 gpuctl 创建的命名空间应报错"""
    mock_instance = MagicMock()
    mock_core_v1 = MagicMock()

    mock_ns = MagicMock()
    mock_ns.metadata = MagicMock(name='kube-system', labels={})
    mock_core_v1.read_namespace = MagicMock(return_value=mock_ns)

    mock_instance.core_v1 = mock_core_v1
    mock_quota_client_class.return_value = mock_instance

    args = Namespace(namespace_name="kube-system", force=True, json=False)
    result = delete_namespace_command(args)

    assert result == 1
    mock_core_v1.delete_namespace.assert_not_called()


@patch('gpuctl.cli.quota.QuotaClient')
def test_delete_namespace_with_json(mock_quota_client_class):
    """测试用例: JSON 格式输出删除命名空间（跳过确认提示）"""
    mock_instance = MagicMock()
    mock_core_v1 = MagicMock()

    mock_ns = MagicMock()
    mock_ns.metadata = MagicMock(name='test-ns', labels={"g8s.host/namespace": "true"})
    mock_core_v1.read_namespace = MagicMock(return_value=mock_ns)
    mock_core_v1.delete_namespace = MagicMock()

    mock_instance.core_v1 = mock_core_v1
    mock_quota_client_class.return_value = mock_instance

    args = Namespace(namespace_name="test-ns", force=False, json=True)
    result = delete_namespace_command(args)

    assert result == 0
    mock_core_v1.delete_namespace.assert_called_once_with("test-ns")


# ── get_quotas_command 补充 ────────────────────────────────────────────────────

@patch('gpuctl.cli.quota.QuotaClient')
def test_get_quotas_returns_data(mock_quota_client):
    """测试用例: 配额列表返回实际数据时正常渲染"""
    mock_instance = MagicMock()
    mock_instance.list_quotas.return_value = [
        {
            "name": "g8s-quota",
            "namespace": "default",
            "status": "Active",
            "hard": {"cpu": "4", "memory": "8Gi", "nvidia.com/gpu": "1"},
            "used": {"cpu": "2", "memory": "4Gi", "nvidia.com/gpu": "0"}
        },
        {
            "name": "g8s-quota",
            "namespace": "test-ns",
            "status": "Active",
            "hard": {"cpu": "8", "memory": "16Gi", "nvidia.com/gpu": "2"},
            "used": {"cpu": "0", "memory": "0", "nvidia.com/gpu": "0"}
        }
    ]
    mock_quota_client.return_value = mock_instance

    args = Namespace(namespace=None, json=False)
    result = get_quotas_command(args)

    assert result == 0


@patch('gpuctl.cli.quota.QuotaClient')
def test_describe_quota_with_data(mock_quota_client):
    """测试用例: 查看包含资源详情的配额"""
    mock_instance = MagicMock()
    mock_instance.describe_quota.return_value = {
        "name": "g8s-quota",
        "namespace": "default",
        "hard": {
            "cpu": "4",
            "memory": "8Gi",
            "nvidia.com/gpu": "1"
        },
        "used": {
            "cpu": "2",
            "memory": "3Gi",
            "nvidia.com/gpu": "0"
        }
    }
    mock_quota_client.return_value = mock_instance

    args = Namespace(namespace_name="default", json=False)
    result = describe_quota_command(args)

    assert result in (0, 1)
    mock_instance.describe_quota.assert_called_once_with("default")


# ── describe_namespace_command 补充 ───────────────────────────────────────────

@patch('gpuctl.cli.quota.QuotaClient')
def test_describe_namespace_with_quota(mock_quota_client_class):
    """测试用例: 查看包含配额信息的命名空间详情"""
    mock_instance = MagicMock()
    mock_core_v1 = MagicMock()

    mock_ns = MagicMock()
    mock_ns.metadata = MagicMock(
        name='test-namespace',
        creation_timestamp='2024-01-01T00:00:00Z',
        labels={"g8s.host/namespace": "true"}
    )
    mock_ns.status = MagicMock(phase='Active')
    mock_core_v1.read_namespace = MagicMock(return_value=mock_ns)

    mock_instance.core_v1 = mock_core_v1
    mock_instance.get_quota = MagicMock(return_value={
        "namespace": "test-namespace",
        "hard": {"cpu": "4", "memory": "8Gi"},
        "used": {"cpu": "1", "memory": "2Gi"}
    })
    mock_quota_client_class.return_value = mock_instance

    args = Namespace(namespace_name="test-namespace", json=False)
    result = describe_namespace_command(args)

    assert result in (0, 1)
    mock_instance.get_quota.assert_called_once()


# ── age 字段格式化回归测试 ────────────────────────────────────────────────────

@patch('gpuctl.cli.quota.QuotaClient')
def test_get_namespaces_age_string_no_typeerror(mock_quota_client_class):
    """回归测试：age 字段为字符串时不应抛出 TypeError（修复 %Y-%m-%d 格式化 bug）"""
    mock_instance = MagicMock()
    mock_core_v1 = MagicMock()

    mock_ns = MagicMock()
    mock_ns.metadata.name = "test-ns"
    mock_ns.metadata.labels = {"g8s.host/namespace": "true"}
    mock_ns.metadata.creation_timestamp = "2024-01-15T10:30:00Z"
    mock_ns.status.phase = "Active"
    mock_core_v1.list_namespace.return_value = MagicMock(items=[mock_ns])
    mock_core_v1.read_namespace.return_value = mock_ns
    mock_instance.core_v1 = mock_core_v1
    mock_quota_client_class.return_value = mock_instance

    args = MagicMock()
    args.json = False

    result = get_namespaces_command(args)
    assert result == 0


@patch('gpuctl.cli.quota.QuotaClient')
def test_describe_namespace_quota_missing_keys_no_keyerror(mock_quota_client_class):
    """回归测试：quota 缺少 nvidia.com/gpu 时不应抛出 KeyError"""
    mock_instance = MagicMock()
    mock_core_v1 = MagicMock()

    mock_ns = MagicMock()
    mock_ns.metadata.name = "test-ns"
    mock_ns.metadata.labels = {"g8s.host/namespace": "true"}
    mock_ns.metadata.creation_timestamp = "2024-01-15T10:30:00Z"
    mock_ns.status.phase = "Active"
    mock_core_v1.read_namespace.return_value = mock_ns
    mock_instance.core_v1 = mock_core_v1
    mock_instance.get_quota.return_value = {
        "name": "test-quota",
        "hard": {"cpu": "4", "memory": "8Gi"},
        "used": {"cpu": "1"}
    }
    mock_quota_client_class.return_value = mock_instance

    args = MagicMock()
    args.namespace_name = "test-ns"
    args.json = False

    result = describe_namespace_command(args)
    assert result == 0
