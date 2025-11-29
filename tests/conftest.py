import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel

# 导入模拟数据
from mock.nodes import mock_nodes, mock_node_details
from mock.jobs import mock_jobs, mock_pods, mock_job_logs
from mock.pools import mock_pools, mock_pool_details

# 导入需要的模块
from fastapi.testclient import TestClient
from server.main import app
from gpuctl.api.inference import InferenceJob
from gpuctl.api.training import TrainingJob
from gpuctl.api.notebook import NotebookJob


@pytest.fixture
def test_client():
    """FastAPI测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_job_client():
    """模拟JobClient，使用真实的模拟数据"""
    with patch('gpuctl.client.job_client.JobClient') as mock:
        mock_instance = MagicMock()
        
        # 模拟list_jobs方法，返回模拟作业数据
        mock_instance.list_jobs.return_value = mock_jobs
        
        # 模拟get_job方法，返回模拟作业详情
        def mock_get_job(job_id):
            for job in mock_jobs:
                if job['name'] == job_id:
                    return job
            return None
        mock_instance.get_job.side_effect = mock_get_job
        
        # 模拟list_pods方法，返回模拟Pod数据
        mock_instance.list_pods.return_value = mock_pods
        
        # 模拟delete_job方法，返回True表示成功
        mock_instance.delete_job.return_value = True
        
        # 模拟pause_job和resume_job方法
        mock_instance.pause_job.return_value = True
        mock_instance.resume_job.return_value = True
        
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_log_client():
    """模拟LogClient，使用真实的模拟数据"""
    with patch('gpuctl.client.log_client.LogClient') as mock:
        mock_instance = MagicMock()
        
        # 模拟get_job_logs方法，返回模拟日志数据
        def mock_get_job_logs(job_id, tail=100, pod_name=None):
            return mock_job_logs.get(job_id, [])
        mock_instance.get_job_logs.side_effect = mock_get_job_logs
        
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_pool_client():
    """模拟PoolClient，使用真实的模拟数据"""
    with patch('gpuctl.client.pool_client.PoolClient') as mock:
        mock_instance = MagicMock()
        
        # 模拟list_pools方法，返回模拟资源池数据
        mock_instance.list_pools.return_value = mock_pools
        
        # 模拟list_nodes方法，返回模拟节点数据
        mock_instance.list_nodes.return_value = mock_nodes
        
        # 模拟get_node方法，返回模拟节点详情
        def mock_get_node(node_name):
            for node in mock_nodes:
                if node['name'] == node_name:
                    return node
            return None
        mock_instance.get_node.side_effect = mock_get_node
        
        # 模拟add_nodes_to_pool方法
        def mock_add_nodes_to_pool(node_names, pool_name):
            return {
                "success": node_names,
                "failed": []
            }
        mock_instance.add_nodes_to_pool.side_effect = mock_add_nodes_to_pool
        
        # 模拟remove_nodes_from_pool方法
        def mock_remove_nodes_from_pool(node_names, pool_name):
            return {
                "success": node_names,
                "failed": []
            }
        mock_instance.remove_nodes_from_pool.side_effect = mock_remove_nodes_from_pool
        
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_auth_validator():
    """模拟AuthValidator"""
    with patch('server.auth.AuthValidator.validate_token') as mock:
        mock.return_value = "test-token"
        yield mock


@pytest.fixture
def training_job():
    """创建训练作业测试数据"""
    return TrainingJob(
        kind="training",
        version="v0.1",
        job=BaseModel(
            name="test-training-job",
            description="Test training job"
        ),
        environment=BaseModel(
            image="registry.example.com/training:v1.0",
            command=["python", "train.py"],
            env=[]
        ),
        resources=BaseModel(
            pool="training-pool",
            gpu=1,
            cpu=4,
            memory="16Gi"
        )
    )


@pytest.fixture
def inference_job():
    """创建推理作业测试数据"""
    return InferenceJob(
        kind="inference",
        version="v0.1",
        job=BaseModel(
            name="test-inference-job",
            description="Test inference job"
        ),
        environment=BaseModel(
            image="registry.example.com/inference:v1.0",
            command=["python", "serve.py"],
            env=[]
        ),
        resources=BaseModel(
            pool="inference-pool",
            gpu=1,
            cpu=4,
            memory="16Gi"
        ),
        service=BaseModel(
            replicas=1,
            port=8000
        )
    )


@pytest.fixture
def notebook_job():
    """创建笔记本作业测试数据"""
    return NotebookJob(
        kind="notebook",
        version="v0.1",
        job=BaseModel(
            name="test-notebook-job",
            description="Test notebook job"
        ),
        environment=BaseModel(
            image="registry.example.com/notebook:v1.0",
            command=["jupyter", "notebook"],
            env=[]
        ),
        resources=BaseModel(
            pool="notebook-pool",
            gpu=1,
            cpu=4,
            memory="16Gi"
        )
    )


@pytest.fixture
def test_yaml_content():
    """测试YAML内容"""
    return """
kind: training
version: v0.1
job:
  name: test-job
  description: Test job
environment:
  image: registry.example.com/test:v1.0
  command: ["python", "test.py"]
resources:
  pool: test-pool
  gpu: 1
  cpu: 4
  memory: 16Gi
"""


@pytest.fixture
def mock_namespace():
    """模拟命名空间"""
    return "default"
