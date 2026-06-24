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
        assert "runwhere.ai/description" in deployment.metadata.annotations
        assert deployment.metadata.annotations["runwhere.ai/description"] == "测试Inference任务描述"

        # 验证 Pod template 中也包含 description
        assert deployment.spec.template.metadata.annotations is not None
        assert "runwhere.ai/description" in deployment.spec.template.metadata.annotations
        assert deployment.spec.template.metadata.annotations["runwhere.ai/description"] == "测试Inference任务描述"

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
            assert "runwhere.ai/description" not in deployment.metadata.annotations

        # 验证 Pod template 中也不包含 description
        if deployment.spec.template.metadata.annotations:
            assert "runwhere.ai/description" not in deployment.spec.template.metadata.annotations

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
        assert "runwhere.ai/description" in service.metadata.annotations
        assert service.metadata.annotations["runwhere.ai/description"] == "测试Inference任务描述"

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
            assert "runwhere.ai/description" not in service.metadata.annotations


class TestInferenceStartupProbe:
    """startupProbe（慢启动宽限）+ 慷慨的存活/就绪探针默认值。"""

    def _job(self, **service_kw):
        return InferenceJob(
            kind="inference",
            version="v0.1",
            job=JobMetadata(name="t", namespace="default", priority="medium"),
            environment=EnvironmentConfig(image="vllm/vllm-openai:latest"),
            resources=ResourceRequest(pool="default", cpu=2, memory="4Gi"),
            service=ServiceConfig(port=8000, replicas=1, **service_kw),
        )

    def _container(self, job):
        return InferenceBuilder.build_deployment(job).spec.template.spec.containers[0]

    def test_default_grace_is_10min_startup_probe(self):
        c = self._container(self._job(health_check="/health"))
        assert c.startup_probe is not None
        # 默认 10m ÷ 10s 周期 = 60 次
        assert c.startup_probe.failure_threshold == 60
        assert c.startup_probe.period_seconds == 10
        assert c.startup_probe.timeout_seconds == 5
        assert c.startup_probe.http_get.path == "/health"
        assert c.startup_probe.http_get.port == 8000

    def test_custom_startup_timeout(self):
        c = self._container(self._job(health_check="/health", startup_timeout="5m"))
        assert c.startup_probe.failure_threshold == 30   # 300 ÷ 10

    def test_liveness_readiness_have_generous_defaults(self):
        c = self._container(self._job(health_check="/health"))
        for probe in (c.liveness_probe, c.readiness_probe):
            assert probe is not None
            assert probe.timeout_seconds == 5      # 不是 K8s 默认的 1s
            assert probe.period_seconds == 10
            assert probe.failure_threshold == 3

    def test_no_health_check_means_no_probes(self):
        c = self._container(self._job())           # 没有 health_check
        assert c.startup_probe is None
        assert c.liveness_probe is None
        assert c.readiness_probe is None


class TestParseDuration:
    def test_parse_duration_seconds(self):
        from gpuctl.api.common import parse_duration_seconds
        assert parse_duration_seconds("600") == 600
        assert parse_duration_seconds("600s") == 600
        assert parse_duration_seconds("10m") == 600
        assert parse_duration_seconds("1h") == 3600
        with pytest.raises(ValueError):
            parse_duration_seconds("ten-minutes")
