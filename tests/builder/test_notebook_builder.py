import pytest
from unittest.mock import patch, MagicMock
from kubernetes import client
from gpuctl.builder.notebook_builder import NotebookBuilder
from gpuctl.api.notebook import NotebookJob
from gpuctl.api.common import JobMetadata, EnvironmentConfig, ResourceRequest, StorageConfig


class TestNotebookBuilder:
    """测试 NotebookBuilder 的 description 存储到 annotation 功能"""

    def test_build_statefulset_with_description(self):
        """测试 StatefulSet 包含 description 在 annotation 中"""
        # 创建测试数据
        notebook_job = NotebookJob(
            kind="notebook",
            version="v0.1",
            job=JobMetadata(
                name="test-notebook",
                namespace="default",
                priority="medium",
                description="测试Notebook任务描述"
            ),
            environment=EnvironmentConfig(
                image="jupyter/minimal-notebook:latest",
                command=["jupyter-lab"]
            ),
            resources=ResourceRequest(
                pool="default",
                cpu=1,
                memory="2Gi"
            ),
            storage=StorageConfig(
                workdirs=[{"path": "/home/jovyan/work"}]
            ),
            service={"port": 8888}
        )

        # 构建 StatefulSet
        statefulset = NotebookBuilder.build_statefulset(notebook_job)

        # 验证 annotation 中包含 description
        assert statefulset.metadata.annotations is not None
        assert "g8s.host/description" in statefulset.metadata.annotations
        assert statefulset.metadata.annotations["g8s.host/description"] == "测试Notebook任务描述"

        # 验证 Pod template 中也包含 description
        assert statefulset.spec.template.metadata.annotations is not None
        assert "g8s.host/description" in statefulset.spec.template.metadata.annotations
        assert statefulset.spec.template.metadata.annotations["g8s.host/description"] == "测试Notebook任务描述"

    def test_build_statefulset_without_description(self):
        """测试 StatefulSet 没有 description 时不添加 annotation"""
        # 创建测试数据（没有 description）
        notebook_job = NotebookJob(
            kind="notebook",
            version="v0.1",
            job=JobMetadata(
                name="test-notebook",
                namespace="default",
                priority="medium"
                # 没有 description
            ),
            environment=EnvironmentConfig(
                image="jupyter/minimal-notebook:latest",
                command=["jupyter-lab"]
            ),
            resources=ResourceRequest(
                pool="default",
                cpu=1,
                memory="2Gi"
            ),
            storage=StorageConfig(
                workdirs=[{"path": "/home/jovyan/work"}]
            ),
            service={"port": 8888}
        )

        # 构建 StatefulSet
        statefulset = NotebookBuilder.build_statefulset(notebook_job)

        # 验证 annotation 中不包含 description
        if statefulset.metadata.annotations:
            assert "g8s.host/description" not in statefulset.metadata.annotations

        # 验证 Pod template 中也不包含 description
        if statefulset.spec.template.metadata.annotations:
            assert "g8s.host/description" not in statefulset.spec.template.metadata.annotations

    def test_build_service_with_description(self):
        """测试 Service 包含 description 在 annotation 中"""
        notebook_job = NotebookJob(
            kind="notebook",
            version="v0.1",
            job=JobMetadata(
                name="test-notebook",
                namespace="default",
                priority="medium",
                description="测试Notebook任务描述"
            ),
            environment=EnvironmentConfig(
                image="jupyter/minimal-notebook:latest"
            ),
            resources=ResourceRequest(
                pool="default",
                cpu=1,
                memory="2Gi"
            ),
            storage=StorageConfig(),
            service={"port": 8888}
        )

        # 构建 Service
        service = NotebookBuilder.build_service(notebook_job)

        # 验证 annotation 中包含 description
        assert service.metadata.annotations is not None
        assert "g8s.host/description" in service.metadata.annotations
        assert service.metadata.annotations["g8s.host/description"] == "测试Notebook任务描述"

    def test_build_service_without_description(self):
        """测试 Service 没有 description 时不添加 annotation"""
        notebook_job = NotebookJob(
            kind="notebook",
            version="v0.1",
            job=JobMetadata(
                name="test-notebook",
                namespace="default",
                priority="medium"
                # 没有 description
            ),
            environment=EnvironmentConfig(
                image="jupyter/minimal-notebook:latest"
            ),
            resources=ResourceRequest(
                pool="default",
                cpu=1,
                memory="2Gi"
            ),
            storage=StorageConfig(),
            service={"port": 8888}
        )

        # 构建 Service
        service = NotebookBuilder.build_service(notebook_job)

        # 验证 annotation 中不包含 description
        if service.metadata.annotations:
            assert "g8s.host/description" not in service.metadata.annotations
