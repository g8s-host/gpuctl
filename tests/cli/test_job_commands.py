import pytest
from unittest.mock import patch, MagicMock
from argparse import Namespace
from gpuctl.cli.job import create_job_command, get_jobs_command, delete_job_command, logs_job_command, pause_job_command, resume_job_command
from gpuctl.parser.base_parser import ParserError


@patch('gpuctl.cli.job.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.job.TrainingKind')
def test_create_training_job(mock_training_kind, mock_parse_yaml_file):
    """测试创建训练作业命令"""
    # 设置模拟返回值
    mock_parse_yaml_file.return_value.kind = "training"
    mock_parse_yaml_file.return_value.job.name = "test-job"
    
    mock_handler = MagicMock()
    mock_handler.create_training_job.return_value = {
        "job_id": "test-training-job",
        "name": "test-training-job",
        "namespace": "default",
        "resources": {"gpu": 1, "cpu": 4}
    }
    mock_training_kind.return_value = mock_handler
    
    # 调用命令 - 现在file是列表
    args = Namespace(file=["test.yaml"], namespace="default")
    result = create_job_command(args)
    
    # 断言结果
    assert result == 0
    mock_parse_yaml_file.assert_called_once_with("test.yaml")
    mock_training_kind.assert_called_once()
    mock_handler.create_training_job.assert_called_once()


@patch('gpuctl.cli.job.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.job.InferenceKind')
def test_create_inference_job(mock_inference_kind, mock_parse_yaml_file):
    """测试创建推理作业命令"""
    # 设置模拟返回值
    mock_parse_yaml_file.return_value.kind = "inference"
    mock_parse_yaml_file.return_value.job.name = "test-inference-job"
    
    mock_handler = MagicMock()
    mock_handler.create_inference_service.return_value = {
        "job_id": "test-inference-job",
        "name": "test-inference-job",
        "namespace": "default"
    }
    mock_inference_kind.return_value = mock_handler
    
    # 调用命令 - 现在file是列表
    args = Namespace(file=["test.yaml"], namespace="default")
    result = create_job_command(args)
    
    # 断言结果
    assert result == 0


@patch('gpuctl.cli.job.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.job.NotebookKind')
def test_create_notebook_job(mock_notebook_kind, mock_parse_yaml_file):
    """测试创建笔记本作业命令"""
    # 设置模拟返回值
    mock_parse_yaml_file.return_value.kind = "notebook"
    mock_parse_yaml_file.return_value.job.name = "test-notebook-job"
    
    mock_handler = MagicMock()
    mock_handler.create_notebook.return_value = {
        "job_id": "test-notebook-job",
        "name": "test-notebook-job",
        "namespace": "default"
    }
    mock_notebook_kind.return_value = mock_handler
    
    # 调用命令 - 现在file是列表
    args = Namespace(file=["test.yaml"], namespace="default")
    result = create_job_command(args)
    
    # 断言结果
    assert result == 0


@patch('gpuctl.cli.job.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.job.InferenceKind')
def test_create_inference_job(mock_inference_kind, mock_parse_yaml_file):
    """测试创建推理作业命令"""
    # 设置模拟返回值
    mock_parse_yaml_file.return_value.kind = "inference"
    mock_parse_yaml_file.return_value.job.name = "test-inference-job"
    
    mock_handler = MagicMock()
    mock_handler.create_inference_service.return_value = {
        "job_id": "test-inference-job",
        "name": "test-inference-job",
        "namespace": "default"
    }
    mock_inference_kind.return_value = mock_handler
    
    # 调用命令
    args = Namespace(file="test.yaml", namespace="default")
    result = create_job_command(args)
    
    # 断言结果
    assert result == 0


@patch('gpuctl.cli.job.BaseParser.parse_yaml_file')
@patch('gpuctl.cli.job.NotebookKind')
def test_create_notebook_job(mock_notebook_kind, mock_parse_yaml_file):
    """测试创建笔记本作业命令"""
    # 设置模拟返回值
    mock_parse_yaml_file.return_value.kind = "notebook"
    mock_parse_yaml_file.return_value.job.name = "test-notebook-job"
    
    mock_handler = MagicMock()
    mock_handler.create_notebook.return_value = {
        "job_id": "test-notebook-job",
        "name": "test-notebook-job",
        "namespace": "default"
    }
    mock_notebook_kind.return_value = mock_handler
    
    # 调用命令
    args = Namespace(file="test.yaml", namespace="default")
    result = create_job_command(args)
    
    # 断言结果
    assert result == 0


@patch('gpuctl.cli.job.BaseParser.parse_yaml_file')
def test_create_job_unsupported_kind(mock_parse_yaml_file):
    """测试创建不支持的作业类型"""
    # 设置模拟返回值
    mock_parse_yaml_file.return_value.kind = "unsupported"
    
    # 调用命令
    args = Namespace(file="test.yaml", namespace="default")
    result = create_job_command(args)
    
    # 断言结果
    assert result == 1


@patch('gpuctl.cli.job.BaseParser.parse_yaml_file')
def test_create_job_parser_error(mock_parse_yaml_file):
    """测试YAML解析错误"""
    # 设置模拟返回值
    mock_parse_yaml_file.side_effect = ParserError("Invalid YAML")
    
    # 调用命令
    args = Namespace(file="invalid.yaml", namespace="default")
    result = create_job_command(args)
    
    # 断言结果
    assert result == 1


@patch('gpuctl.cli.job.JobClient')
def test_get_jobs_command(mock_job_client):
    """测试获取作业列表命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.list_jobs.return_value = [
        {
            "name": "test-job-1",
            "namespace": "default",
            "labels": {"gpuctl/job-type": "training"},
            "creation_timestamp": "2023-01-01T12:00:00Z",
            "status": {"succeeded": 0, "failed": 0, "active": 1}
        },
        {
            "name": "test-job-2",
            "namespace": "default",
            "labels": {"gpuctl/job-type": "inference"},
            "creation_timestamp": "2023-01-02T12:00:00Z",
            "status": {"succeeded": 0, "failed": 0, "active": 1}
        }
    ]
    mock_job_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(namespace="default", pool=None, type=None)
    result = get_jobs_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.list_jobs.assert_called_once_with("default", labels={})


@patch('gpuctl.cli.job.JobClient')
def test_get_jobs_command_with_filters(mock_job_client):
    """测试带过滤条件的作业列表命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.list_jobs.return_value = []
    mock_job_client.return_value = mock_instance
    
    # 调用命令 - 带过滤条件
    args = Namespace(namespace="default", pool="test-pool", type="training")
    result = get_jobs_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.list_jobs.assert_called_once_with(
        "default", 
        labels={"gpuctl/pool": "test-pool", "gpuctl/job-type": "training"}
    )


@patch('gpuctl.cli.job.JobClient')
def test_get_jobs_command_empty(mock_job_client):
    """测试获取空作业列表命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.list_jobs.return_value = []
    mock_job_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(namespace="default", pool=None, type=None)
    result = get_jobs_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.list_jobs.assert_called_once_with("default", labels={})


@patch('gpuctl.cli.job.JobClient')
def test_delete_job_by_name(mock_job_client):
    """测试通过名称删除作业命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.delete_job.return_value = True
    mock_job_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(file=None, resource_name="test-job", namespace="default")
    result = delete_job_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.delete_job.assert_called_once_with("test-job", "default")


@patch('gpuctl.cli.job.BaseParser.parse_yaml_file')
def test_delete_job_by_file(mock_parse_yaml_file):
    """测试通过YAML文件删除作业命令"""
    # 设置模拟返回值
    mock_parse_yaml_file.return_value.kind = "training"
    mock_parse_yaml_file.return_value.job.name = "test-job"
    
    # 调用命令
    # 模拟整个KubernetesClient的初始化过程，避免实际加载Kubernetes配置
    with patch('gpuctl.client.base_client.KubernetesClient._load_config') as mock_load_config, \
         patch('gpuctl.cli.job.JobClient') as mock_job_client:
        
        # 模拟_load_config方法，避免实际加载Kubernetes配置
        mock_load_config.return_value = None
        
        # 模拟JobClient
        mock_job_instance = MagicMock()
        mock_job_instance.delete_job.return_value = True
        mock_job_client.return_value = mock_job_instance
        
        args = Namespace(file="test.yaml", resource_name=None, namespace="default")
        result = delete_job_command(args)
        
        # 断言结果
        assert result == 0
        mock_parse_yaml_file.assert_called_once_with("test.yaml")
        mock_job_instance.delete_job.assert_called_once_with("test-job", "default")


@patch('gpuctl.cli.job.LogClient')
def test_logs_job_command(mock_log_client):
    """测试获取作业日志命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.get_job_logs.return_value = [
        "2023-01-01T12:00:00Z INFO: Job started",
        "2023-01-01T12:01:00Z INFO: Job completed"
    ]
    mock_log_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(job_name="test-job", namespace="default")
    result = logs_job_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.get_job_logs.assert_called_once()


@patch('gpuctl.cli.job.JobClient')
def test_pause_job_command(mock_job_client):
    """测试暂停作业命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.pause_job.return_value = True
    mock_job_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(job_name="test-job", namespace="default")
    result = pause_job_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.pause_job.assert_called_once_with("test-job", "default")


@patch('gpuctl.cli.job.JobClient')
def test_resume_job_command(mock_job_client):
    """测试恢复作业命令"""
    # 设置模拟返回值
    mock_instance = MagicMock()
    mock_instance.resume_job.return_value = True
    mock_job_client.return_value = mock_instance
    
    # 调用命令
    args = Namespace(job_name="test-job", namespace="default")
    result = resume_job_command(args)
    
    # 断言结果
    assert result == 0
    mock_instance.resume_job.assert_called_once_with("test-job", "default")
