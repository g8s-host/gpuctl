import pytest
from unittest.mock import patch, MagicMock
from kubernetes import client
from gpuctl.builder.inference_builder import InferenceBuilder
from gpuctl.api.inference import InferenceJob
from gpuctl.api.common import JobMetadata, EnvironmentConfig, ResourceRequest, ServiceConfig


class TestInferenceBuilder:
    """测试 InferenceBuilder 的 description 存储到 annotation 功能"""

    def test_build_deployment_with_description(self):
        """测试 Deployment 包含 description 在 annotation 中"""
        # 创建测试数据
        inference_job = InferenceJob(
            kind="inference",
            version="v0.1",
            job=JobMetadata(
                name="test-inference",
                namespace="default",
                priority="medium",
                description="测试Inference任务描述"
            ),
            environment=EnvironmentConfig(
                image="tensorflow/serving:latest"
            ),
            resources=ResourceRequest(
                pool="default",
                cpu=2,
                memory="4Gi"
            ),
            service=ServiceConfig(
                port=8501,
                replicas=1
            )
        )

        # 构建 Deployment
        deployment = InferenceBuilder.build_deployment(inference_job)

        # 验证 annotation 中包含 description
        assert deployment.metadata.annotations is not None
        assert "g8s.host/description" in deployment.metadata.annotations
        assert deployment.metadata.annotations["g8s.host/description"] == "测试Inference任务描述"

        # 验证 Pod template 中也包含 description
        assert deployment.spec.template.metadata.annotations is not None
        assert "g8s.host/description" in deployment.spec.template.metadata.annotations
        assert deployment.spec.template.metadata.annotations["g8s.host/description"] == "测试Inference任务描述"

    def test_build_deployment_without_description(self):
        """测试 Deployment 没有 description 时不添加 annotation"""
        # 创建测试数据（没有 description）
        inference_job = InferenceJob(
            kind="inference",
            version="v0.1",
            job=JobMetadata(
                name="test-inference",
                namespace="default",
                priority="medium"
                # 没有 description
            ),
            environment=EnvironmentConfig(
                image="tensorflow/serving:latest"
            ),
            resources=ResourceRequest(
                pool="default",
                cpu=2,
                memory="4Gi"
            ),
            service=ServiceConfig(
                port=8501,
                replicas=1
            )
        )

        # 构建 Deployment
        deployment = InferenceBuilder.build_deployment(inference_job)

        # 验证 annotation 中不包含 description
        if deployment.metadata.annotations:
            assert "g8s.host/description" not in deployment.metadata.annotations

        # 验证 Pod template 中也不包含 description
        if deployment.spec.template.metadata.annotations:
            assert "g8s.host/description" not in deployment.spec.template.metadata.annotations

    def test_build_service_with_description(self):
        """测试 Service 包含 description 在 annotation 中"""
        inference_job = InferenceJob(
            kind="inference",
            version="v0.1",
            job=JobMetadata(
                name="test-inference",
                namespace="default",
                priority="medium",
                description="测试Inference任务描述"
            ),
            environment=EnvironmentConfig(
                image="tensorflow/serving:latest"
            ),
            resources=ResourceRequest(
                pool="default",
                cpu=2,
                memory="4Gi"
            ),
            service=ServiceConfig(
                port=8501,
                replicas=1
            )
        )

        # 构建 Service
        service = InferenceBuilder.build_service(inference_job)

        # 验证 annotation 中包含 description
        assert service.metadata.annotations is not None
        assert "g8s.host/description" in service.metadata.annotations
        assert service.metadata.annotations["g8s.host/description"] == "测试Inference任务描述"

    def test_build_service_without_description(self):
        """测试 Service 没有 description 时不添加 annotation"""
        inference_job = InferenceJob(
            kind="inference",
            version="v0.1",
            job=JobMetadata(
                name="test-inference",
                namespace="default",
                priority="medium"
                # 没有 description
            ),
            environment=EnvironmentConfig(
                image="tensorflow/serving:latest"
            ),
            resources=ResourceRequest(
                pool="default",
                cpu=2,
                memory="4Gi"
            ),
            service=ServiceConfig(
                port=8501,
                replicas=1
            )
        )

        # 构建 Service
        service = InferenceBuilder.build_service(inference_job)

        # 验证 annotation 中不包含 description
        if service.metadata.annotations:
            assert "g8s.host/description" not in service.metadata.annotations
