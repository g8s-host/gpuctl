import pytest
import json as json_module
from unittest.mock import patch, MagicMock, PropertyMock, mock_open
from argparse import Namespace
from gpuctl.cli.job import create_job_command, get_jobs_command, delete_job_command, logs_job_command, apply_job_command, describe_job_command
from gpuctl.parser.base_parser import ParserError


def _setup_job_common_mocks():
    """设置作业相关的常用 mock 对象"""
    mock_priority_client = MagicMock()
    mock_priority_client.ensure_priority_classes = MagicMock()

    mock_k8s_client = MagicMock()
    mock_core_v1 = MagicMock()
    mock_namespace = MagicMock()
    type(mock_namespace).metadata = PropertyMock(
        name='metadata',
        return_value=MagicMock(name='test-namespace', creation_timestamp='2024-01-01T00:00:00Z')
    )
    type(mock_namespace).status = PropertyMock(
        name='status',
        return_value=MagicMock(phase='Active')
    )
    mock_core_v1.read_namespace = MagicMock(return_value=mock_namespace)
    
    mock_node_list = MagicMock()
    mock_node = MagicMock()
    mock_node.metadata = MagicMock(name='node-1', labels={})
    mock_node_list.items = [mock_node]
    mock_core_v1.list_node = MagicMock(return_value=mock_node_list)
    
    mock_k8s_client.core_v1 = mock_core_v1

    mock_quota_client = MagicMock()
    mock_quota_client.namespace_has_quota = MagicMock(return_value=True)
    mock_quota_client.core_v1 = mock_core_v1

    mock_pool_client = MagicMock()
    mock_pool_client.get_pool = MagicMock(return_value={'nodes': ['node-1']})

    return {
        'priority_client': mock_priority_client,
        'k8s_client': mock_k8s_client,
        'quota_client': mock_quota_client,
        'pool_client': mock_pool_client
    }


@patch('gpuctl.cli.job.TrainingKind')
@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.client.priority_client.PriorityClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.client.quota_client.QuotaClient')
@patch('gpuctl.client.pool_client.PoolClient')
def test_create_training_job(mock_pool_client_class, mock_quota_client_class, mock_k8s_client_class, mock_priority_client_class, mock_parse_yaml_file, mock_training_kind_class):
    """测试用例: 创建训练作业"""
    mocks = _setup_job_common_mocks()
    mock_priority_client_class.return_value = mocks['priority_client']
    mock_k8s_client_class.return_value = mocks['k8s_client']
    mock_quota_client_class.return_value = mocks['quota_client']
    mock_pool_client_class.return_value = mocks['pool_client']
    
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "training"
    mock_parsed_obj.job = MagicMock(name="test-job", namespace="default")
    mock_parse_yaml_file.return_value = mock_parsed_obj
    
    mock_handler = MagicMock()
    mock_handler.create_training_job.return_value = {
        "job_id": "test-training-job",
        "name": "test-training-job",
        "namespace": "default",
        "resources": {"gpu": 1, "cpu": 4}
    }
    mock_training_kind_class.return_value = mock_handler
    
    args = Namespace(file=["test.yaml"], namespace="default", json=False)
    result = create_job_command(args)
    
    assert result == 0
    mock_handler.create_training_job.assert_called_once()


@patch('gpuctl.cli.job.InferenceKind')
@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.client.priority_client.PriorityClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.client.quota_client.QuotaClient')
@patch('gpuctl.client.pool_client.PoolClient')
def test_create_inference_job(mock_pool_client_class, mock_quota_client_class, mock_k8s_client_class, mock_priority_client_class, mock_parse_yaml_file, mock_inference_kind_class):
    """测试用例: 创建推理作业"""
    mocks = _setup_job_common_mocks()
    mock_priority_client_class.return_value = mocks['priority_client']
    mock_k8s_client_class.return_value = mocks['k8s_client']
    mock_quota_client_class.return_value = mocks['quota_client']
    mock_pool_client_class.return_value = mocks['pool_client']
    
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "inference"
    mock_parsed_obj.job = MagicMock(name="test-inference-job", namespace="default")
    mock_parse_yaml_file.return_value = mock_parsed_obj
    
    mock_handler = MagicMock()
    mock_handler.create_inference_service.return_value = {
        "job_id": "test-inference-job",
        "name": "test-inference-job",
        "namespace": "default"
    }
    mock_inference_kind_class.return_value = mock_handler
    
    args = Namespace(file=["test.yaml"], namespace="default", json=False)
    result = create_job_command(args)
    
    assert result == 0
    mock_handler.create_inference_service.assert_called_once()


@patch('gpuctl.cli.job.NotebookKind')
@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.client.priority_client.PriorityClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.client.quota_client.QuotaClient')
@patch('gpuctl.client.pool_client.PoolClient')
def test_create_notebook_job(mock_pool_client_class, mock_quota_client_class, mock_k8s_client_class, mock_priority_client_class, mock_parse_yaml_file, mock_notebook_kind_class):
    """测试用例: 创建笔记本作业"""
    mocks = _setup_job_common_mocks()
    mock_priority_client_class.return_value = mocks['priority_client']
    mock_k8s_client_class.return_value = mocks['k8s_client']
    mock_quota_client_class.return_value = mocks['quota_client']
    mock_pool_client_class.return_value = mocks['pool_client']
    
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "notebook"
    mock_parsed_obj.job = MagicMock(name="test-notebook-job", namespace="default")
    mock_parse_yaml_file.return_value = mock_parsed_obj
    
    mock_handler = MagicMock()
    mock_handler.create_notebook.return_value = {
        "job_id": "test-notebook-job",
        "name": "test-notebook-job",
        "namespace": "default"
    }
    mock_notebook_kind_class.return_value = mock_handler
    
    args = Namespace(file=["test.yaml"], namespace="default", json=False)
    result = create_job_command(args)
    
    assert result == 0
    mock_handler.create_notebook.assert_called_once()


@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.client.priority_client.PriorityClient')
def test_create_job_unsupported_kind(mock_priority_client_class, mock_parse_yaml_file):
    """测试用例: 创建不支持的作业类型"""
    mocks = _setup_job_common_mocks()
    mock_priority_client_class.return_value = mocks['priority_client']
    
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "unsupported"
    mock_parse_yaml_file.return_value = mock_parsed_obj
    
    args = Namespace(file=["test.yaml"], namespace="default", json=False)
    result = create_job_command(args)
    
    assert result == 1


@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.client.priority_client.PriorityClient')
def test_create_job_parser_error(mock_priority_client_class, mock_parse_yaml_file):
    """测试用例: YAML解析错误"""
    mocks = _setup_job_common_mocks()
    mock_priority_client_class.return_value = mocks['priority_client']
    mock_parse_yaml_file.side_effect = ParserError("Invalid YAML")
    
    args = Namespace(file=["invalid.yaml"], namespace="default", json=False)
    result = create_job_command(args)
    
    assert result == 1


@patch('gpuctl.cli.job.TrainingKind')
@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.client.priority_client.PriorityClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.client.quota_client.QuotaClient')
@patch('gpuctl.client.pool_client.PoolClient')
def test_batch_create_jobs(mock_pool_client_class, mock_quota_client_class, mock_k8s_client_class, mock_priority_client_class, mock_parse_yaml_file, mock_training_kind_class):
    """测试用例: 批量创建作业"""
    mocks = _setup_job_common_mocks()
    mock_priority_client_class.return_value = mocks['priority_client']
    mock_k8s_client_class.return_value = mocks['k8s_client']
    mock_quota_client_class.return_value = mocks['quota_client']
    mock_pool_client_class.return_value = mocks['pool_client']
    
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "training"
    mock_parsed_obj.job = MagicMock(name="test-job", namespace="default")
    mock_parse_yaml_file.return_value = mock_parsed_obj
    
    mock_handler = MagicMock()
    mock_handler.create_training_job.return_value = {
        "job_id": "test-training-job",
        "name": "test-training-job",
        "namespace": "default",
        "resources": {"gpu": 1, "cpu": 4}
    }
    mock_training_kind_class.return_value = mock_handler
    
    args = Namespace(file=["test1.yaml", "test2.yaml"], namespace="default", json=False)
    result = create_job_command(args)
    
    assert result == 0


@patch('gpuctl.cli.job.JobClient')
def test_get_jobs(mock_job_client):
    """测试用例: 获取作业列表"""
    mock_instance = MagicMock()
    mock_instance.list_jobs.return_value = []
    mock_job_client.return_value = mock_instance
    
    args = Namespace(namespace=None, pool=None, kind=None, pods=False, json=False)
    result = get_jobs_command(args)
    
    assert result == 0


@patch('gpuctl.cli.job.JobClient')
def test_delete_job(mock_job_client):
    """测试用例: 删除作业"""
    mock_instance = MagicMock()
    mock_instance._get_all_gpuctl_namespaces.return_value = ["default"]
    mock_instance.list_jobs.return_value = [
        {"name": "test-nginx", "labels": {"g8s.host/job-type": "compute"}, "namespace": "default"}
    ]
    mock_instance.list_pods.return_value = []
    mock_instance.delete_deployment.return_value = True
    mock_instance.delete_service.return_value = True
    mock_job_client.return_value = mock_instance
    
    args = Namespace(file=None, resource=None, job_name="test-nginx", namespace="default", force=False, json=False)
    result = delete_job_command(args)
    
    assert result == 0
    mock_instance.delete_deployment.assert_called_once()


@patch('gpuctl.client.job_client.JobClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.cli.job.LogClient')
def test_get_job_logs(mock_log_client, mock_k8s_client, mock_job_client):
    """测试用例: 获取作业日志（logs_job_command pod 查找用内联 import，需 patch 源模块）"""
    mock_k8s_instance = MagicMock()
    mock_core_v1 = MagicMock()
    mock_core_v1.read_namespace = MagicMock()
    mock_k8s_instance.core_v1 = mock_core_v1
    mock_k8s_client.return_value = mock_k8s_instance
    
    mock_job_instance = MagicMock()
    mock_job_instance.list_pods.return_value = [
        {'name': 'test-nginx', 'status': {'phase': 'Running'}}
    ]
    mock_job_client.return_value = mock_job_instance
    
    mock_log_instance = MagicMock()
    mock_log_instance.get_job_logs.return_value = ["log line 1", "log line 2"]
    mock_log_client.return_value = mock_log_instance
    
    args = Namespace(job_name="test-nginx", namespace="default", follow=False, json=False)
    result = logs_job_command(args)
    
    assert result == 0


@patch('gpuctl.kind.training_kind.TrainingKind')
@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.job.JobClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.client.quota_client.QuotaClient')
@patch('gpuctl.client.pool_client.PoolClient')
def test_apply_job(mock_pool_client_class, mock_quota_client_class, mock_k8s_client_class, mock_job_client_class, mock_parse_yaml_file, mock_training_kind_class):
    """测试用例: 应用作业配置"""
    mocks = _setup_job_common_mocks()
    mock_k8s_client_class.return_value = mocks['k8s_client']
    mock_quota_client_class.return_value = mocks['quota_client']
    mock_pool_client_class.return_value = mocks['pool_client']
    
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "training"
    mock_parsed_obj.job = MagicMock(name="test-job", namespace="default")
    mock_parse_yaml_file.return_value = mock_parsed_obj
    
    mock_job_instance = MagicMock()
    mock_job_instance.get_job.return_value = None
    mock_job_client_class.return_value = mock_job_instance
    
    mock_handler = MagicMock()
    mock_handler.create_training_job.return_value = {
        "job_id": "test-training-job",
        "name": "test-training-job",
        "namespace": "default",
        "resources": {"gpu": 1, "cpu": 4}
    }
    mock_training_kind_class.return_value = mock_handler
    
    args = Namespace(file=["test.yaml"], namespace="default", json=False)
    result = apply_job_command(args)
    
    assert result == 0
    mock_handler.create_training_job.assert_called_once()


@patch('gpuctl.client.job_client.JobClient')
def test_describe_job(mock_job_client):
    """测试用例: 查看作业详情（describe_job_command 使用内联 import，需 patch 源模块）"""
    mock_instance = MagicMock()
    mock_instance._get_all_gpuctl_namespaces.return_value = []
    mock_instance.list_jobs.return_value = []
    mock_instance.get_job.return_value = {
        "name": "test-nginx",
        "namespace": "default",
        "labels": {"g8s.host/job-type": "compute"},
        "status": {}
    }
    mock_job_client.return_value = mock_instance
    
    args = Namespace(job_id="test-nginx", namespace="default", json=False)
    result = describe_job_command(args)
    
    assert result == 0


@patch('gpuctl.cli.job.JobClient')
def test_get_jobs_with_namespace(mock_job_client):
    """测试用例: 按命名空间过滤作业"""
    mock_instance = MagicMock()
    mock_instance.list_jobs.return_value = []
    mock_job_client.return_value = mock_instance
    
    args = Namespace(namespace="default", pool=None, kind=None, pods=False, json=False)
    result = get_jobs_command(args)
    
    assert result == 0


@patch('gpuctl.cli.job.JobClient')
def test_get_jobs_with_pool(mock_job_client):
    """测试用例: 按资源池过滤作业"""
    mock_instance = MagicMock()
    mock_instance.list_jobs.return_value = []
    mock_job_client.return_value = mock_instance
    
    args = Namespace(namespace=None, pool="test-pool", kind=None, pods=False, json=False)
    result = get_jobs_command(args)
    
    assert result == 0


@patch('gpuctl.cli.job.JobClient')
def test_get_jobs_with_kind(mock_job_client):
    """测试用例: 按作业类型过滤作业"""
    mock_instance = MagicMock()
    mock_instance.list_jobs.return_value = []
    mock_job_client.return_value = mock_instance
    
    args = Namespace(namespace=None, pool=None, kind="compute", pods=False, json=False)
    result = get_jobs_command(args)
    
    assert result == 0


@patch('gpuctl.cli.job.JobClient')
def test_get_jobs_with_json(mock_job_client):
    """测试用例: JSON格式输出作业"""
    mock_instance = MagicMock()
    mock_instance.list_jobs.return_value = []
    mock_job_client.return_value = mock_instance
    
    args = Namespace(namespace=None, pool=None, kind=None, pods=False, json=True)
    result = get_jobs_command(args)
    
    assert result == 0


@patch('gpuctl.cli.job.JobClient')
def test_delete_job_with_force(mock_job_client):
    """测试用例: 强制删除作业"""
    mock_instance = MagicMock()
    mock_instance._get_all_gpuctl_namespaces.return_value = ["default"]
    mock_instance.list_jobs.return_value = [
        {"name": "test-nginx", "labels": {"g8s.host/job-type": "training"}, "namespace": "default"}
    ]
    mock_instance.list_pods.return_value = []
    mock_instance.delete_job.return_value = True
    mock_job_client.return_value = mock_instance
    
    args = Namespace(file=None, resource=None, job_name="test-nginx", namespace="default", force=True, json=False)
    result = delete_job_command(args)
    
    assert result == 0
    mock_instance.delete_job.assert_called_once()


@patch('gpuctl.cli.job.JobClient')
def test_delete_job_with_json(mock_job_client):
    """测试用例: JSON格式输出删除操作"""
    mock_instance = MagicMock()
    mock_instance._get_all_gpuctl_namespaces.return_value = ["default"]
    mock_instance.list_jobs.return_value = [
        {"name": "test-nginx", "labels": {"g8s.host/job-type": "compute"}, "namespace": "default"}
    ]
    mock_instance.list_pods.return_value = []
    mock_instance.delete_deployment.return_value = True
    mock_instance.delete_service.return_value = True
    mock_job_client.return_value = mock_instance
    
    args = Namespace(file=None, resource=None, job_name="test-nginx", namespace="default", force=False, json=True)
    result = delete_job_command(args)
    
    assert result == 0


@patch('gpuctl.cli.job.JobClient')
def test_delete_nonexistent_job(mock_job_client):
    """测试用例: 删除不存在作业"""
    mock_instance = MagicMock()
    mock_instance._get_all_gpuctl_namespaces.return_value = ["default"]
    mock_instance.list_jobs.return_value = []
    mock_instance.list_pods.return_value = []
    mock_job_client.return_value = mock_instance
    
    args = Namespace(file=None, resource=None, job_name="nonexistent-job", namespace="default", force=False, json=False)
    result = delete_job_command(args)
    
    assert result == 1


@patch('gpuctl.client.job_client.JobClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.cli.job.LogClient')
def test_get_job_logs_with_follow(mock_log_client, mock_k8s_client, mock_job_client):
    """测试用例: 跟踪作业日志"""
    mock_k8s_instance = MagicMock()
    mock_core_v1 = MagicMock()
    mock_core_v1.read_namespace = MagicMock()
    mock_k8s_instance.core_v1 = mock_core_v1
    mock_k8s_client.return_value = mock_k8s_instance
    
    mock_job_instance = MagicMock()
    mock_job_instance.list_pods.return_value = [
        {'name': 'test-nginx', 'status': {'phase': 'Running'}}
    ]
    mock_job_client.return_value = mock_job_instance
    
    mock_log_instance = MagicMock()
    mock_log_instance.stream_job_logs.return_value = ["log line 1"]
    mock_log_client.return_value = mock_log_instance
    
    args = Namespace(job_name="test-nginx", namespace="default", follow=True, json=False)
    result = logs_job_command(args)
    
    assert result == 0


@patch('gpuctl.client.job_client.JobClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.cli.job.LogClient')
def test_get_job_logs_with_json(mock_log_client, mock_k8s_client, mock_job_client):
    """测试用例: JSON格式输出日志"""
    mock_k8s_instance = MagicMock()
    mock_core_v1 = MagicMock()
    mock_core_v1.read_namespace = MagicMock()
    mock_k8s_instance.core_v1 = mock_core_v1
    mock_k8s_client.return_value = mock_k8s_instance
    
    mock_job_instance = MagicMock()
    mock_job_instance.list_pods.return_value = [
        {'name': 'test-nginx', 'status': {'phase': 'Running'}}
    ]
    mock_job_client.return_value = mock_job_instance
    
    mock_log_instance = MagicMock()
    mock_log_instance.get_job_logs.return_value = ["log line 1"]
    mock_log_client.return_value = mock_log_instance
    
    args = Namespace(job_name="test-nginx", namespace="default", follow=False, json=True)
    result = logs_job_command(args)
    
    assert result == 0


@patch('gpuctl.cli.job.LogClient')
def test_get_nonexistent_job_logs(mock_log_client):
    """测试用例: 获取不存在作业日志（无 Pod 时返回错误）"""
    mock_instance = MagicMock()
    mock_instance.get_job_logs.side_effect = Exception("No pods found")
    mock_log_client.return_value = mock_instance
    
    args = Namespace(job_name="nonexistent-job", namespace="default", follow=False, json=False)
    result = logs_job_command(args)
    
    assert result == 1


@patch('gpuctl.client.job_client.JobClient')
def test_describe_job_with_json(mock_job_client):
    """测试用例: JSON格式输出作业详情"""
    mock_instance = MagicMock()
    mock_instance._get_all_gpuctl_namespaces.return_value = []
    mock_instance.list_jobs.return_value = []
    mock_instance.get_job.return_value = {
        "name": "test-nginx",
        "namespace": "default",
        "labels": {"g8s.host/job-type": "compute"},
        "status": {}
    }
    mock_job_client.return_value = mock_instance
    
    args = Namespace(job_id="test-nginx", namespace="default", json=True)
    result = describe_job_command(args)
    
    assert result == 0


@patch('gpuctl.client.job_client.JobClient')
def test_describe_nonexistent_job(mock_job_client):
    """测试用例: 查看不存在作业详情（get_job 抛出异常时返回错误）"""
    mock_instance = MagicMock()
    mock_instance._get_all_gpuctl_namespaces.return_value = []
    mock_instance.list_jobs.return_value = []
    mock_instance.get_job.side_effect = Exception("Job not found")
    mock_job_client.return_value = mock_instance
    
    args = Namespace(job_id="nonexistent-job", namespace="default", json=False)
    result = describe_job_command(args)
    
    assert result == 1


# ── create_job_command 补充 ────────────────────────────────────────────────────

@patch('gpuctl.kind.compute_kind.ComputeKind')
@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.client.priority_client.PriorityClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.client.quota_client.QuotaClient')
@patch('gpuctl.client.pool_client.PoolClient')
def test_create_compute_job(mock_pool_client_class, mock_quota_client_class, mock_k8s_client_class,
                            mock_priority_client_class, mock_parse_yaml_file, mock_compute_kind_class):
    """测试用例: 创建 compute 类型作业"""
    mocks = _setup_job_common_mocks()
    mock_priority_client_class.return_value = mocks['priority_client']
    mock_k8s_client_class.return_value = mocks['k8s_client']
    mock_quota_client_class.return_value = mocks['quota_client']
    mock_pool_client_class.return_value = mocks['pool_client']

    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "compute"
    mock_parsed_obj.job = MagicMock(name="test-nginx", namespace="default")
    mock_parse_yaml_file.return_value = mock_parsed_obj

    mock_handler = MagicMock()
    mock_handler.create_compute_service.return_value = {
        "job_id": "test-nginx",
        "name": "test-nginx",
        "namespace": "default",
        "resources": {"cpu": 1, "memory": "2Gi", "pool": "default"}
    }
    mock_compute_kind_class.return_value = mock_handler

    args = Namespace(file=["test.yaml"], namespace="default", json=False)
    result = create_job_command(args)

    assert result == 0
    mock_handler.create_compute_service.assert_called_once()


@patch('gpuctl.cli.job.TrainingKind')
@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.client.priority_client.PriorityClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.client.quota_client.QuotaClient')
@patch('gpuctl.client.pool_client.PoolClient')
def test_create_training_job_with_json(mock_pool_client_class, mock_quota_client_class, mock_k8s_client_class,
                                       mock_priority_client_class, mock_parse_yaml_file, mock_training_kind_class):
    """测试用例: 以 JSON 格式输出创建训练作业结果"""
    mocks = _setup_job_common_mocks()
    mock_priority_client_class.return_value = mocks['priority_client']
    mock_k8s_client_class.return_value = mocks['k8s_client']
    mock_quota_client_class.return_value = mocks['quota_client']
    mock_pool_client_class.return_value = mocks['pool_client']

    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "training"
    mock_parsed_obj.job = MagicMock(name="test-job", namespace="default")
    mock_parse_yaml_file.return_value = mock_parsed_obj

    mock_handler = MagicMock()
    mock_handler.create_training_job.return_value = {
        "job_id": "test-training-job",
        "name": "test-training-job",
        "namespace": "default",
        "resources": {"gpu": 1, "cpu": 4}
    }
    mock_training_kind_class.return_value = mock_handler

    args = Namespace(file=["test.yaml"], namespace="default", json=True)
    result = create_job_command(args)

    assert result == 0


@patch('gpuctl.cli.job.TrainingKind')
@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.client.priority_client.PriorityClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.client.quota_client.QuotaClient')
@patch('gpuctl.client.pool_client.PoolClient')
def test_create_job_custom_namespace(mock_pool_client_class, mock_quota_client_class, mock_k8s_client_class,
                                     mock_priority_client_class, mock_parse_yaml_file, mock_training_kind_class):
    """测试用例: 使用 -n 指定命名空间创建作业"""
    mocks = _setup_job_common_mocks()
    mock_priority_client_class.return_value = mocks['priority_client']
    mock_k8s_client_class.return_value = mocks['k8s_client']
    mock_quota_client_class.return_value = mocks['quota_client']
    mock_pool_client_class.return_value = mocks['pool_client']

    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "training"
    mock_parsed_obj.job = MagicMock(name="test-job", namespace=None)
    mock_parse_yaml_file.return_value = mock_parsed_obj

    mock_handler = MagicMock()
    mock_handler.create_training_job.return_value = {
        "job_id": "test-training-job",
        "name": "test-training-job",
        "namespace": "custom-ns",
        "resources": {"gpu": 1, "cpu": 4}
    }
    mock_training_kind_class.return_value = mock_handler

    args = Namespace(file=["test.yaml"], namespace="custom-ns", json=False)
    result = create_job_command(args)

    assert result == 0


# ── apply_job_command 补充 ─────────────────────────────────────────────────────

@patch('gpuctl.kind.inference_kind.InferenceKind')
@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.job.JobClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.client.quota_client.QuotaClient')
@patch('gpuctl.client.pool_client.PoolClient')
def test_apply_inference_job(mock_pool_client_class, mock_quota_client_class, mock_k8s_client_class,
                             mock_job_client_class, mock_parse_yaml_file, mock_inference_kind_class):
    """测试用例: 应用推理作业配置（新建）"""
    mocks = _setup_job_common_mocks()
    mock_k8s_client_class.return_value = mocks['k8s_client']
    mock_quota_client_class.return_value = mocks['quota_client']
    mock_pool_client_class.return_value = mocks['pool_client']

    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "inference"
    mock_parsed_obj.job = MagicMock(name="test-inference", namespace="default")
    mock_parse_yaml_file.return_value = mock_parsed_obj

    mock_job_instance = MagicMock()
    mock_job_instance.get_job.return_value = None
    mock_job_client_class.return_value = mock_job_instance

    mock_handler = MagicMock()
    mock_handler.create_inference_service.return_value = {
        "job_id": "test-inference-job",
        "name": "test-inference-job",
        "namespace": "default"
    }
    mock_inference_kind_class.return_value = mock_handler

    args = Namespace(file=["test.yaml"], namespace="default", json=False)
    result = apply_job_command(args)

    assert result == 0
    mock_handler.create_inference_service.assert_called_once()


@patch('gpuctl.kind.notebook_kind.NotebookKind')
@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.job.JobClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.client.quota_client.QuotaClient')
@patch('gpuctl.client.pool_client.PoolClient')
def test_apply_notebook_job(mock_pool_client_class, mock_quota_client_class, mock_k8s_client_class,
                            mock_job_client_class, mock_parse_yaml_file, mock_notebook_kind_class):
    """测试用例: 应用 Notebook 作业配置（新建）"""
    mocks = _setup_job_common_mocks()
    mock_k8s_client_class.return_value = mocks['k8s_client']
    mock_quota_client_class.return_value = mocks['quota_client']
    mock_pool_client_class.return_value = mocks['pool_client']

    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "notebook"
    mock_parsed_obj.job = MagicMock(name="test-notebook", namespace="default")
    mock_parse_yaml_file.return_value = mock_parsed_obj

    mock_job_instance = MagicMock()
    mock_job_instance.get_job.return_value = None
    mock_job_client_class.return_value = mock_job_instance

    mock_handler = MagicMock()
    mock_handler.create_notebook.return_value = {
        "job_id": "test-notebook-job",
        "name": "test-notebook-job",
        "namespace": "default"
    }
    mock_notebook_kind_class.return_value = mock_handler

    args = Namespace(file=["test.yaml"], namespace="default", json=False)
    result = apply_job_command(args)

    assert result == 0
    mock_handler.create_notebook.assert_called_once()


@patch('gpuctl.kind.training_kind.TrainingKind')
@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.job.JobClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.client.quota_client.QuotaClient')
@patch('gpuctl.client.pool_client.PoolClient')
def test_apply_job_with_json(mock_pool_client_class, mock_quota_client_class, mock_k8s_client_class,
                             mock_job_client_class, mock_parse_yaml_file, mock_training_kind_class):
    """测试用例: JSON 格式输出应用作业配置"""
    mocks = _setup_job_common_mocks()
    mock_k8s_client_class.return_value = mocks['k8s_client']
    mock_quota_client_class.return_value = mocks['quota_client']
    mock_pool_client_class.return_value = mocks['pool_client']

    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "training"
    mock_parsed_obj.job = MagicMock(name="test-job", namespace="default")
    mock_parse_yaml_file.return_value = mock_parsed_obj

    mock_job_instance = MagicMock()
    mock_job_instance.get_job.return_value = None
    mock_job_client_class.return_value = mock_job_instance

    mock_handler = MagicMock()
    mock_handler.create_training_job.return_value = {
        "job_id": "test-training-job",
        "name": "test-training-job",
        "namespace": "default"
    }
    mock_training_kind_class.return_value = mock_handler

    args = Namespace(file=["test.yaml"], namespace="default", json=True)
    result = apply_job_command(args)

    assert result == 0


@patch('gpuctl.kind.training_kind.TrainingKind')
@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.job.JobClient')
@patch('gpuctl.client.base_client.KubernetesClient')
@patch('gpuctl.client.quota_client.QuotaClient')
@patch('gpuctl.client.pool_client.PoolClient')
def test_apply_existing_job(mock_pool_client_class, mock_quota_client_class, mock_k8s_client_class,
                            mock_job_client_class, mock_parse_yaml_file, mock_training_kind_class):
    """测试用例: 应用配置时作业已存在（执行更新）"""
    mocks = _setup_job_common_mocks()
    mock_k8s_client_class.return_value = mocks['k8s_client']
    mock_quota_client_class.return_value = mocks['quota_client']
    mock_pool_client_class.return_value = mocks['pool_client']

    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "training"
    mock_parsed_obj.job = MagicMock(name="test-job", namespace="default")
    mock_parse_yaml_file.return_value = mock_parsed_obj

    mock_job_instance = MagicMock()
    mock_job_instance.get_job.return_value = {"name": "existing-job", "namespace": "default"}
    mock_job_client_class.return_value = mock_job_instance

    mock_handler = MagicMock()
    mock_handler.update_training_job.return_value = {
        "job_id": "test-training-job",
        "name": "test-training-job",
        "namespace": "default",
        "action": "updated"
    }
    mock_training_kind_class.return_value = mock_handler

    args = Namespace(file=["test.yaml"], namespace="default", json=False)
    result = apply_job_command(args)

    assert result == 0
    mock_handler.update_training_job.assert_called_once()


# ── delete_job_command 补充 ────────────────────────────────────────────────────

@patch('gpuctl.cli.job.JobClient')
@patch('gpuctl.parser.base_parser.BaseParser.parse_yaml_file')
def test_delete_job_via_yaml(mock_parse_yaml_file, mock_job_client):
    """测试用例: 通过 YAML 文件删除作业（-f 参数）"""
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.kind = "training"
    mock_job_attr = MagicMock()
    mock_job_attr.name = "test-training"
    mock_job_attr.namespace = "default"
    mock_parsed_obj.job = mock_job_attr
    mock_parse_yaml_file.return_value = mock_parsed_obj

    mock_instance = MagicMock()
    mock_instance._get_all_gpuctl_namespaces.return_value = ["default"]
    mock_instance.list_jobs.return_value = [
        {"name": "test-training", "labels": {"g8s.host/job-type": "training"}, "namespace": "default"}
    ]
    mock_instance.list_pods.return_value = []
    mock_instance.delete_job.return_value = True
    mock_job_client.return_value = mock_instance

    args = Namespace(file=["test.yaml"], resource=None, job_name=None, namespace="default", force=False, json=False)
    result = delete_job_command(args)

    assert result == 0
    mock_instance.delete_job.assert_called_once()


# ── get_jobs_command 补充 ──────────────────────────────────────────────────────

@patch('gpuctl.cli.job.JobClient')
def test_get_jobs_with_pods_flag(mock_job_client):
    """测试用例: 使用 --pods 标志列出 Pod 级别作业"""
    mock_instance = MagicMock()
    mock_instance.list_jobs.return_value = [
        {
            "name": "test-nginx-pod-abc",
            "namespace": "default",
            "kind": "compute",
            "labels": {"g8s.host/job-type": "compute"},
            "status": {"phase": "Running"},
            "node": "node-1",
            "ip": "10.42.0.10",
            "creation_timestamp": None
        }
    ]
    mock_job_client.return_value = mock_instance

    args = Namespace(namespace=None, pool=None, kind=None, pods=True, json=False)
    result = get_jobs_command(args)

    assert result == 0


@patch('gpuctl.cli.job.JobClient')
def test_get_jobs_returns_data(mock_job_client):
    """测试用例: 作业列表返回实际数据时正常渲染"""
    mock_instance = MagicMock()
    mock_instance.list_jobs.return_value = [
        {
            "name": "test-training-job",
            "namespace": "default",
            "kind": "training",
            "labels": {"g8s.host/job-type": "training"},
            "status": {"phase": "Running"},
            "node": "node-1",
            "ip": "10.42.0.5",
            "creation_timestamp": None
        },
        {
            "name": "test-inference-job",
            "namespace": "new-test",
            "kind": "inference",
            "labels": {"g8s.host/job-type": "inference"},
            "status": {"phase": "Failed"},
            "node": "node-2",
            "ip": "N/A",
            "creation_timestamp": None
        }
    ]
    mock_job_client.return_value = mock_instance

    args = Namespace(namespace=None, pool=None, kind=None, pods=False, json=False)
    result = get_jobs_command(args)

    assert result == 0


@patch('gpuctl.cli.job.JobClient')
def test_get_jobs_returns_data_with_json(mock_job_client):
    """测试用例: 作业列表以 JSON 格式返回实际数据"""
    jobs_data = [
        {
            "name": "test-training-job",
            "namespace": "default",
            "kind": "training",
            "labels": {"g8s.host/job-type": "training"},
            "status": {"phase": "Running"},
            "node": "node-1",
            "ip": "10.42.0.5",
            "creation_timestamp": None
        }
    ]
    mock_instance = MagicMock()
    mock_instance.list_jobs.return_value = jobs_data
    mock_job_client.return_value = mock_instance

    args = Namespace(namespace=None, pool=None, kind=None, pods=False, json=True)
    result = get_jobs_command(args)

    assert result == 0


# ── describe_job_command 补充 ──────────────────────────────────────────────────

@patch('gpuctl.client.job_client.JobClient')
def test_describe_job_with_namespace(mock_job_client):
    """测试用例: 在指定命名空间下查看作业详情"""
    mock_instance = MagicMock()
    mock_instance._get_all_gpuctl_namespaces.return_value = []
    mock_instance.list_jobs.return_value = []
    mock_instance.get_job.return_value = {
        "name": "test-nginx",
        "namespace": "custom-ns",
        "labels": {"g8s.host/job-type": "compute"},
        "status": {}
    }
    mock_job_client.return_value = mock_instance

    args = Namespace(job_id="test-nginx", namespace="custom-ns", json=False)
    result = describe_job_command(args)

    assert result == 0
