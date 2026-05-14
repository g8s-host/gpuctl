"""Unit tests for the JobSpec adapters in ``gpuctl.backend.spec``.

These are pure pure functions; tests stay tight and dependency-free.
"""

from __future__ import annotations

import pytest

from gpuctl.api.common import (
    EnvironmentConfig,
    JobMetadata,
    ResourceRequest,
    ServiceConfig,
    StorageConfig,
)
from gpuctl.api.training import TrainingJob
from gpuctl.api.inference import InferenceJob
from gpuctl.backend.spec import (
    inference_to_spec,
    parse_cpu,
    parse_memory,
    training_to_spec,
)
from gpuctl.constants import Kind, Labels, Priority


class TestParseMemory:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("32Gi", 34_359_738_368),
            ("512Mi", 536_870_912),
            ("1Ki", 1024),
            ("2G", 2_000_000_000),
            ("4096", 4096),
            (1024, 1024),
        ],
    )
    def test_valid(self, value, expected):
        assert parse_memory(value) == expected

    def test_invalid_unit(self):
        with pytest.raises(ValueError, match="unknown memory unit"):
            parse_memory("32Zi")

    def test_garbage(self):
        with pytest.raises(ValueError, match="unparseable"):
            parse_memory("not a number")


class TestParseCpu:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("8", 8000),
            ("8000m", 8000),
            (2, 2000),
            ("1.5", 1500),
            ("500m", 500),
        ],
    )
    def test_valid(self, value, expected):
        assert parse_cpu(value) == expected


def _training_job(**overrides) -> TrainingJob:
    base = dict(
        kind="training",
        version="v0.1",
        job=JobMetadata(name="t1", priority="high", description="hi"),
        environment=EnvironmentConfig(
            image="img:tag",
            command=["python", "train.py"],
            env=[{"NCCL_DEBUG": "INFO"}, {"name": "RANK", "value": "0"}],
        ),
        resources=ResourceRequest(
            pool="training-pool",
            gpu=2,
            gpu_type="a100-80g",
            cpu="8",
            memory="32Gi",
        ),
        storage=StorageConfig(workdirs=[{"path": "/data"}]),
    )
    base.update(overrides)
    return TrainingJob(**base)


class TestTrainingToSpec:
    def test_basic_fields(self):
        spec = training_to_spec(_training_job(), namespace="acme")
        assert spec.name == "t1"
        assert spec.namespace == "acme"
        assert spec.kind == Kind.TRAINING
        assert spec.image == "img:tag"
        assert spec.command == ("python", "train.py")
        assert spec.cpu_millicores == 8000
        assert spec.memory_bytes == 34_359_738_368
        assert spec.gpu_count == 2
        assert spec.gpu_type == "a100-80g"
        assert spec.pool == "training-pool"
        assert spec.long_running is False
        assert spec.restart_policy == "Never"

    def test_env_both_shapes_flattened(self):
        spec = training_to_spec(_training_job(), namespace="acme")
        assert ("NCCL_DEBUG", "INFO") in spec.env
        assert ("RANK", "0") in spec.env

    def test_labels_include_pool_priority_namespace(self):
        spec = training_to_spec(_training_job(), namespace="acme")
        labels = spec.labels_dict
        assert labels[Labels.JOB_TYPE] == "training"
        assert labels[Labels.PRIORITY] == "high"
        assert labels[Labels.POOL] == "training-pool"
        assert labels[Labels.NAMESPACE] == "acme"

    def test_description_becomes_annotation(self):
        spec = training_to_spec(_training_job(), namespace="acme")
        assert spec.annotations_dict[Labels.DESCRIPTION] == "hi"

    def test_workdirs_become_volume_mounts(self):
        spec = training_to_spec(_training_job(), namespace="acme")
        assert len(spec.workdirs) == 1
        assert spec.workdirs[0].host_path == "/data"
        assert spec.workdirs[0].container_path == "/data"
        assert spec.workdirs[0].read_only is False


class TestInferenceToSpec:
    def test_service_fields_propagate(self):
        job = InferenceJob(
            kind="inference",
            job=JobMetadata(name="inf1", priority="medium"),
            environment=EnvironmentConfig(image="vllm:latest"),
            resources=ResourceRequest(gpu=1, cpu="4", memory="8Gi"),
            service=ServiceConfig(replicas=1, port=8000, healthCheck="/health"),
        )
        spec = inference_to_spec(job, namespace="default")
        assert spec.kind == Kind.INFERENCE
        assert spec.long_running is True
        assert spec.restart_policy == "Always"
        assert spec.port == 8000
        assert spec.health_check == "/health"
        assert spec.replicas == 1
