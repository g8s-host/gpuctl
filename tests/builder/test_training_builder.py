import pytest
from unittest.mock import patch, MagicMock
from kubernetes import client
from gpuctl.builder.training_builder import TrainingBuilder
from gpuctl.api.training import TrainingJob, DistributedConfig
from gpuctl.api.common import JobMetadata, EnvironmentConfig, ResourceRequest, StorageConfig
from gpuctl.builder.base_builder import BaseBuilder


class TestTrainingBuilder:
    """测试 TrainingBuilder 的 description 存储到 annotation 功能"""

    def test_build_job_with_description(self):
        """测试 Job 包含 description 在 annotation 中"""
        # 创建测试数据
        training_job = TrainingJob(
            kind="training",
            version="v0.1",
            job=JobMetadata(
                name="test-training",
                namespace="default",
                priority="high",
                description="测试Training任务描述"
            ),
            environment=EnvironmentConfig(
                image="pytorch/pytorch:latest",
                command=["python", "train.py"]
            ),
            resources=ResourceRequest(
                pool="default",
                gpu=1,
                cpu=4,
                memory="16Gi"
            ),
            storage=StorageConfig(
                workdirs=[{"path": "/workspace"}]
            )
        )

        # 构建 Job
        job = TrainingBuilder.build_job(training_job)

        # 验证 annotation 中包含 description
        assert job.metadata.annotations is not None
        assert "runwhere.ai/description" in job.metadata.annotations
        assert job.metadata.annotations["runwhere.ai/description"] == "测试Training任务描述"

        # 验证 Pod template 中也包含 description
        assert job.spec.template.metadata.annotations is not None
        assert "runwhere.ai/description" in job.spec.template.metadata.annotations
        assert job.spec.template.metadata.annotations["runwhere.ai/description"] == "测试Training任务描述"

    def test_build_job_without_description(self):
        """测试 Job 没有 description 时不添加 annotation"""
        # 创建测试数据（没有 description）
        training_job = TrainingJob(
            kind="training",
            version="v0.1",
            job=JobMetadata(
                name="test-training",
                namespace="default",
                priority="high"
                # 没有 description
            ),
            environment=EnvironmentConfig(
                image="pytorch/pytorch:latest",
                command=["python", "train.py"]
            ),
            resources=ResourceRequest(
                pool="default",
                gpu=1,
                cpu=4,
                memory="16Gi"
            ),
            storage=StorageConfig(
                workdirs=[{"path": "/workspace"}]
            )
        )

        # 构建 Job
        job = TrainingBuilder.build_job(training_job)

        # 验证 annotation 中不包含 description
        if job.metadata.annotations:
            assert "runwhere.ai/description" not in job.metadata.annotations

        # 验证 Pod template 中也不包含 description
        if job.spec.template.metadata.annotations:
            assert "runwhere.ai/description" not in job.spec.template.metadata.annotations


def _make_training_job(mode="standalone", workers=1, conda=None, notebook=None, command=None):
    return TrainingJob(
        kind="training",
        version="v0.1",
        job=JobMetadata(name="test-job", namespace="alice", priority="medium"),
        environment=EnvironmentConfig(
            image="pytorch/pytorch:latest",
            command=command or ["python", "train.py"],
            conda=conda,
            notebook=notebook,
        ),
        resources=ResourceRequest(cpu=4, memory="16Gi", gpu=2),
        distributed=DistributedConfig(mode=mode, workers=workers),
    )


class TestDistributedMode:

    @patch.object(BaseBuilder, "read_nfs_config", return_value=None)
    @patch.object(TrainingBuilder, "_resolve_nfs_namespace", return_value="alice")
    def test_standalone_produces_normal_job(self, _rns, _nfs):
        job = TrainingBuilder.build_job(_make_training_job(mode="standalone"), "alice")
        assert job.spec.completion_mode is None or job.spec.completion_mode != "Indexed"
        assert job.spec.parallelism is None or job.spec.parallelism == 1 or job.spec.parallelism != 4

    @patch.object(BaseBuilder, "read_nfs_config", return_value=None)
    @patch.object(TrainingBuilder, "_resolve_nfs_namespace", return_value="alice")
    def test_distributed_produces_indexed_job(self, _rns, _nfs):
        job = TrainingBuilder.build_job(
            _make_training_job(mode="multi-node", workers=4), "alice"
        )
        assert job.spec.completion_mode == "Indexed"
        assert job.spec.completions == 4
        assert job.spec.parallelism == 4

    @patch.object(BaseBuilder, "read_nfs_config", return_value=None)
    @patch.object(TrainingBuilder, "_resolve_nfs_namespace", return_value="alice")
    def test_distributed_injects_ddp_env_vars(self, _rns, _nfs):
        job = TrainingBuilder.build_job(
            _make_training_job(mode="multi-node", workers=4), "alice"
        )
        container = job.spec.template.spec.containers[0]
        env_names = {e.name for e in container.env}
        assert "MASTER_ADDR" in env_names
        assert "MASTER_PORT" in env_names
        assert "WORLD_SIZE" in env_names
        assert "RANK" in env_names
        assert "LOCAL_RANK" in env_names
        assert "GPUCTL_NPROC_PER_NODE" in env_names

        world_size_env = next(e for e in container.env if e.name == "WORLD_SIZE")
        assert world_size_env.value == "4"

        nproc_env = next(e for e in container.env if e.name == "GPUCTL_NPROC_PER_NODE")
        assert nproc_env.value == "2"  # resources.gpu

    @patch.object(BaseBuilder, "read_nfs_config", return_value=None)
    @patch.object(TrainingBuilder, "_resolve_nfs_namespace", return_value="alice")
    def test_distributed_workers_1_behaves_like_standalone(self, _rns, _nfs):
        """workers=1 should not create Indexed Job"""
        job = TrainingBuilder.build_job(
            _make_training_job(mode="multi-node", workers=1), "alice"
        )
        assert job.spec.completion_mode != "Indexed" if job.spec.completion_mode else True

    @patch.object(BaseBuilder, "read_nfs_config", return_value=None)
    @patch.object(TrainingBuilder, "_resolve_nfs_namespace", return_value="alice")
    def test_distributed_pod_labels_include_job_name(self, _rns, _nfs):
        job = TrainingBuilder.build_job(
            _make_training_job(mode="multi-node", workers=4), "alice"
        )
        pod_labels = job.spec.template.metadata.labels
        assert pod_labels.get("job-name") == "test-job"


class TestCondaEntrypoint:

    def test_no_conda_returns_original_command(self):
        cmd, args, envs = BaseBuilder.build_conda_entrypoint(["python", "train.py"], None)
        assert cmd == ["python", "train.py"]
        assert args == []
        assert envs == []

    def test_conda_wraps_command(self):
        cmd, args, envs = BaseBuilder.build_conda_entrypoint(["python", "train.py"], "myenv")
        assert "bash" in cmd
        assert "conda activate" in " ".join(cmd)
        assert args == ["python", "train.py"]
        assert any("GPUCTL_CONDA_ENV" in str(e) for e in envs)

    @patch.object(BaseBuilder, "read_nfs_config", return_value=None)
    @patch.object(TrainingBuilder, "_resolve_nfs_namespace", return_value="alice")
    def test_conda_env_var_injected_into_container(self, _rns, _nfs):
        job = TrainingBuilder.build_job(
            _make_training_job(conda="myenv"), "alice"
        )
        container = job.spec.template.spec.containers[0]
        env_names_values = {e.name: e.value for e in (container.env or []) if e.value}
        assert env_names_values.get("GPUCTL_CONDA_ENV") == "myenv"

    @patch.object(BaseBuilder, "read_nfs_config", return_value=None)
    @patch.object(TrainingBuilder, "_resolve_nfs_namespace", return_value="alice")
    def test_command_string_auto_normalized(self, _rns, _nfs):
        """String command should be auto-converted to ['bash', '-c', str]"""
        tj = _make_training_job(command="python train.py")
        assert tj.environment.command == ["bash", "-c", "python train.py"]
