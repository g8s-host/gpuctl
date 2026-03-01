import pytest
from unittest.mock import patch, MagicMock
from kubernetes import client
from gpuctl.builder.training_builder import TrainingBuilder
from gpuctl.api.training import TrainingJob
from gpuctl.api.common import JobMetadata, EnvironmentConfig, ResourceRequest, StorageConfig


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
        assert "g8s.host/description" in job.metadata.annotations
        assert job.metadata.annotations["g8s.host/description"] == "测试Training任务描述"

        # 验证 Pod template 中也包含 description
        assert job.spec.template.metadata.annotations is not None
        assert "g8s.host/description" in job.spec.template.metadata.annotations
        assert job.spec.template.metadata.annotations["g8s.host/description"] == "测试Training任务描述"

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
            assert "g8s.host/description" not in job.metadata.annotations

        # 验证 Pod template 中也不包含 description
        if job.spec.template.metadata.annotations:
            assert "g8s.host/description" not in job.spec.template.metadata.annotations
