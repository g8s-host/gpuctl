"""Multi-node (model-parallel) inference: StatefulSet + Headless + head-only Service.

nodes>1 turns one logical serving replica into a StatefulSet of N pods (pod-0 = head
serving the API, pod-1..N-1 = workers), with a Headless Service for stable DNS and a
NodePort Service that targets only the head. The platform injects RUNWHERE_* bootstrap
env vars; the user's command does the head/worker split (e.g. ray + vllm).
"""
import pytest
from unittest.mock import patch

from gpuctl.builder.inference_builder import InferenceBuilder
from gpuctl.builder.base_builder import BaseBuilder
from gpuctl.api.inference import InferenceJob
from gpuctl.api.common import JobMetadata, EnvironmentConfig, ResourceRequest, ServiceConfig


def _make_inf(nodes=1, gpu=2, replicas=1):
    return InferenceJob(
        kind="inference",
        version="v0.1",
        job=JobMetadata(name="qwen-235b", namespace="alice", priority="medium"),
        environment=EnvironmentConfig(
            image="vllm/vllm-openai:latest",
            command=["bash", "-c", "serve"],
        ),
        resources=ResourceRequest(cpu=8, memory="64Gi", gpu=gpu, nodes=nodes),
        service=ServiceConfig(replicas=replicas, port=8000),
    )


class TestMultiNodeStatefulSet:

    @patch.object(BaseBuilder, "read_nfs_config", return_value=None)
    def test_builds_statefulset_topology(self, _nfs):
        sts = InferenceBuilder.build_statefulset(_make_inf(nodes=2), "alice")
        assert sts.kind == "StatefulSet"
        assert sts.spec.replicas == 2                                  # N pods = N nodes
        assert sts.spec.service_name == "qwen-235b-headless"           # 指向 headless,稳定 DNS
        assert sts.spec.pod_management_policy == "Parallel"            # 防 head/worker 互等死锁
        assert sts.spec.template.spec.restart_policy == "Always"

    @patch.object(BaseBuilder, "read_nfs_config", return_value=None)
    def test_injects_runwhere_env(self, _nfs):
        sts = InferenceBuilder.build_statefulset(_make_inf(nodes=2, gpu=4), "alice")
        c = sts.spec.template.spec.containers[0]
        env = {e.name: e for e in c.env}
        assert {"RUNWHERE_NUM_NODES", "RUNWHERE_NODE_RANK",
                "RUNWHERE_HEAD_ADDR", "RUNWHERE_GPUS_PER_NODE"} <= set(env)
        assert env["RUNWHERE_NUM_NODES"].value == "2"
        assert env["RUNWHERE_GPUS_PER_NODE"].value == "4"
        assert env["RUNWHERE_HEAD_ADDR"].value == \
            "qwen-235b-0.qwen-235b-headless.alice.svc.cluster.local"
        # NODE_RANK 取自 StatefulSet 自动注入的序号标签
        assert env["RUNWHERE_NODE_RANK"].value_from.field_ref.field_path == \
            "metadata.labels['apps.kubernetes.io/pod-index']"

    @patch.object(BaseBuilder, "read_nfs_config", return_value=None)
    def test_no_http_health_probes(self, _nfs):
        """worker pod 不跑 API,套 http liveness 会被反复重启 → 多机不设探针。"""
        sts = InferenceBuilder.build_statefulset(_make_inf(nodes=2), "alice")
        c = sts.spec.template.spec.containers[0]
        assert c.liveness_probe is None
        assert c.readiness_probe is None
        assert c.startup_probe is None

    @patch.object(BaseBuilder, "read_nfs_config", return_value=None)
    def test_pod_labels_for_headless_and_app(self, _nfs):
        sts = InferenceBuilder.build_statefulset(_make_inf(nodes=2), "alice")
        labels = sts.spec.template.metadata.labels
        assert labels.get("app") == "qwen-235b"
        assert labels.get("job-name") == "qwen-235b"      # headless(job-name selector)选中
        assert labels.get("runwhere.ai/job-type") == "inference"


class TestHeadOnlyService:

    def test_head_only_selects_pod_zero(self):
        svc = InferenceBuilder.build_service(_make_inf(nodes=2), "alice", head_only=True)
        assert svc.spec.selector == {"statefulset.kubernetes.io/pod-name": "qwen-235b-0"}
        assert svc.spec.type == "NodePort"

    def test_default_selects_app(self):
        svc = InferenceBuilder.build_service(_make_inf(), "alice")
        assert svc.spec.selector == {"app": "qwen-235b"}


class TestHeadlessPublishNotReady:

    def test_publish_not_ready_true(self):
        h = BaseBuilder.build_headless_service("qwen-235b", "alice", port=8000, publish_not_ready=True)
        assert h.spec.publish_not_ready_addresses is True
        assert h.spec.cluster_ip == "None"
        assert h.metadata.name == "qwen-235b-headless"

    def test_default_does_not_publish_not_ready(self):
        h = BaseBuilder.build_headless_service("j", "alice")          # 训练默认行为不变
        assert not h.spec.publish_not_ready_addresses


class TestKindRouting:

    @patch.object(BaseBuilder, "read_nfs_config", return_value=None)
    @patch("gpuctl.kind.inference_kind.JobClient")
    def test_multinode_creates_sts_headless_headsvc(self, MockJC, _nfs):
        inst = MockJC.return_value
        inst._is_service_exists.return_value = False
        inst.create_statefulset.return_value = {"name": "qwen-235b", "namespace": "alice"}
        inst.create_service.return_value = {"name": "svc-qwen-235b", "namespace": "alice"}
        from gpuctl.kind.inference_kind import InferenceKind

        res = InferenceKind().create_inference_service(_make_inf(nodes=2), "alice")

        assert inst.create_statefulset.called
        assert inst.create_service.call_count == 2          # headless + head-only NodePort
        assert not inst.create_deployment.called
        assert res["k8s_resources"]["statefulset"] == "qwen-235b"
        assert res["k8s_resources"]["headless"] == "qwen-235b-headless"

    @patch.object(BaseBuilder, "read_nfs_config", return_value=None)
    @patch("gpuctl.kind.inference_kind.JobClient")
    def test_singlenode_creates_deployment(self, MockJC, _nfs):
        inst = MockJC.return_value
        inst.create_deployment.return_value = {"name": "qwen-235b", "namespace": "alice"}
        inst.create_service.return_value = {"name": "svc-qwen-235b", "namespace": "alice"}
        from gpuctl.kind.inference_kind import InferenceKind

        res = InferenceKind().create_inference_service(_make_inf(nodes=1), "alice")

        assert inst.create_deployment.called
        assert not inst.create_statefulset.called
        assert "deployment" in res["k8s_resources"]

    @patch.object(BaseBuilder, "read_nfs_config", return_value=None)
    @patch("gpuctl.kind.inference_kind.JobClient")
    def test_multinode_plus_replicas_rejected(self, MockJC, _nfs):
        """多机(nodes>1)+ 多副本(replicas>1)= 罕见的 N 组×M 台,v1 明确报错挡掉。"""
        from gpuctl.kind.inference_kind import InferenceKind
        with pytest.raises(ValueError):
            InferenceKind().create_inference_service(_make_inf(nodes=2, replicas=3), "alice")
