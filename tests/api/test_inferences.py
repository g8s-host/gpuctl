"""POST /api/v1/inferences —— JSON 原生推理部署入口(Agent-First PRD §4.5)。

只测这一层"翻译 + 转发":JSON body -> InferenceJob -> InferenceKind.create_inference_service()。
底层部署逻辑(Deployment/Service/StatefulSet 构建)已经在 test_jobs.py 的
kind:inference YAML 路径覆盖,这里不重复。
"""
from unittest.mock import patch

import pytest

from server.routes.inferences import GpuSpec, InferenceCreateRequest


# ── InferenceCreateRequest.to_inference_job() 纯逻辑 ────────────────────────────

def test_minimal_request_gets_friendly_defaults():
    req = InferenceCreateRequest(name="qwen-7b-ft", image="vllm/vllm:latest")
    job = req.to_inference_job()

    assert job.job.name == "qwen-7b-ft"
    assert job.environment.image == "vllm/vllm:latest"
    assert job.environment.command == []  # 不覆盖,让镜像自带 entrypoint 跑
    assert job.resources.gpu == 1
    assert job.resources.cpu == "4"
    assert job.resources.memory == "16Gi"
    assert job.service.port == 8000
    assert job.service.replicas == 1


def test_gpu_accepts_bare_int():
    req = InferenceCreateRequest(name="n", image="i", gpu=4)
    assert isinstance(req.gpu, GpuSpec)
    assert req.gpu.count == 4
    assert req.to_inference_job().resources.gpu == 4


def test_gpu_accepts_structured_object():
    req = InferenceCreateRequest(name="n", image="i", gpu={"count": 2, "type": "A100"})
    assert req.gpu.count == 2
    assert req.gpu.type == "A100"
    assert req.to_inference_job().resources.gpu == 2


def test_env_dict_converted_to_internal_list_shape():
    req = InferenceCreateRequest(name="n", image="i", env={"A": "1", "B": "2"})
    job = req.to_inference_job()
    assert job.environment.env == [{"A": "1", "B": "2"}]


def test_env_empty_stays_empty_list():
    req = InferenceCreateRequest(name="n", image="i")
    assert req.to_inference_job().environment.env == []


# ── HTTP layer ───────────────────────────────────────────────────────────────

@patch("server.routes.inferences._node_port", return_value=30123)
@patch("server.routes.inferences.InferenceKind")
def test_create_inference_returns_201_with_endpoint(mock_kind_cls, mock_node_port, client):
    mock_kind_cls.return_value.create_inference_service.return_value = {"job_id": "qwen-7b-ft"}

    r = client.post("/api/v1/inferences", json={
        "name": "qwen-7b-ft",
        "image": "vllm/vllm:latest",
        "gpu": {"count": 1},
        "env": {"VLLM_SERVED_MODELS": "qwen-ft"},
    })

    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "qwen-7b-ft"
    assert body["namespace"] == "default"
    assert body["status"] == "Starting"
    assert body["gpu"] == 1
    assert body["node_port"] == 30123
    assert body["internal_endpoint"] == "http://svc-qwen-7b-ft.default.svc.cluster.local:8000"

    mock_kind_cls.return_value.create_inference_service.assert_called_once()
    assert mock_kind_cls.return_value.create_inference_service.call_args.kwargs["namespace"] == "default"


@patch("server.routes.inferences._node_port", return_value=None)
@patch("server.routes.inferences.InferenceKind")
def test_create_inference_passes_custom_namespace(mock_kind_cls, mock_node_port, client):
    mock_kind_cls.return_value.create_inference_service.return_value = {"job_id": "x"}

    r = client.post("/api/v1/inferences", json={
        "name": "svc-a", "image": "img", "namespace": "team-a",
    })

    assert r.status_code == 201
    assert r.json()["namespace"] == "team-a"
    call = mock_kind_cls.return_value.create_inference_service.call_args
    assert call.kwargs["namespace"] == "team-a"


@patch("server.routes.inferences._node_port", return_value=None)
@patch("server.routes.inferences.InferenceKind")
def test_create_inference_value_error_is_400(mock_kind_cls, mock_node_port, client):
    mock_kind_cls.return_value.create_inference_service.side_effect = ValueError(
        "多机 serving 暂不支持多副本"
    )

    r = client.post("/api/v1/inferences", json={"name": "n", "image": "i"})

    assert r.status_code == 400
    assert "多机" in r.json()["error"]["message"]


@patch("server.routes.inferences._node_port", return_value=None)
@patch("server.routes.inferences.InferenceKind")
def test_create_inference_unexpected_error_is_500(mock_kind_cls, mock_node_port, client):
    mock_kind_cls.return_value.create_inference_service.side_effect = RuntimeError("boom")

    r = client.post("/api/v1/inferences", json={"name": "n", "image": "i"})

    assert r.status_code == 500


@pytest.mark.parametrize("body", [{}, {"name": "n"}, {"image": "i"}])
def test_create_inference_missing_required_fields_is_422(client, body):
    r = client.post("/api/v1/inferences", json=body)
    assert r.status_code == 422
