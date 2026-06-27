from gpuctl.builder.inference_builder import InferenceBuilder
from gpuctl.builder.base_builder import BaseBuilder
from gpuctl.client.job_client import JobClient
from gpuctl.api.inference import InferenceJob
from gpuctl.constants import svc_name
from typing import Dict, Any


class InferenceKind:
    """Inference job processing logic"""

    def __init__(self):
        self.builder = InferenceBuilder()
        self.client = JobClient()

    def create_inference_service(self, inference_job: InferenceJob,
                                 namespace: str = "default") -> Dict[str, Any]:
        """Create inference service.

        resources.nodes<=1:单 Pod Deployment + NodePort Service(现状,含张量并行 gpu:N)。
        resources.nodes>1 :多机 serving —— StatefulSet(replicas=nodes) + Headless Service(稳定 DNS)
                 + 只指向 head(pod-0)的 NodePort Service。见 _create_multinode。
        """
        nodes = inference_job.resources.nodes or 1
        if nodes > 1:
            # 护栏:多机(模型并行)暂不支持多副本(数据并行)同时开 —— 那是「N 组×M 台」,
            # 单个 StatefulSet 表达不了,需多个 StatefulSet/LWS(罕见,v1 不做)。
            replicas = inference_job.service.replicas or 1
            if replicas > 1:
                raise ValueError(
                    f"多机 serving(resources.nodes={nodes})暂不支持多副本"
                    f"(service.replicas={replicas})。请把 service.replicas 设为 1;"
                    f"要数据并行多副本请用 resources.nodes=1。"
                )
            return self._create_multinode(inference_job, namespace)

        deployment = self.builder.build_deployment(inference_job, namespace)
        service = self.builder.build_service(inference_job, namespace)

        deployment_result = self.client.create_deployment(deployment, namespace)
        service_result = self.client.create_service(service, namespace)

        return {
            "job_id": deployment_result["name"],
            "name": inference_job.job.name,
            "status": "created",
            "namespace": namespace,
            "resources": {
                "gpu": inference_job.resources.gpu,
                "gpuType": inference_job.resources.gpu_type,
                "pool": inference_job.resources.pool,
                "service_port": inference_job.service.port
            },
            "k8s_resources": {
                "deployment": deployment_result["name"],
                "service": service_result["name"]
            }
        }

    def _create_multinode(self, inference_job: InferenceJob,
                          namespace: str) -> Dict[str, Any]:
        """多机(模型并行)serving:StatefulSet + Headless + head-only NodePort Service。"""
        name = inference_job.job.name
        statefulset = self.builder.build_statefulset(inference_job, namespace)
        headless = BaseBuilder.build_headless_service(
            name, namespace, port=inference_job.service.port, publish_not_ready=True
        )
        service = self.builder.build_service(inference_job, namespace, head_only=True)

        sts_result = self.client.create_statefulset(statefulset, namespace)
        # headless 幂等:已存在则跳过(create_service 把 409 包成 RuntimeError,不便靠异常判定)
        if not self.client._is_service_exists(f"{name}-headless", namespace):
            self.client.create_service(headless, namespace)
        service_result = self.client.create_service(service, namespace)

        return {
            "job_id": sts_result["name"],
            "name": name,
            "status": "created",
            "namespace": namespace,
            "resources": {
                "gpu": inference_job.resources.gpu,
                "gpuType": inference_job.resources.gpu_type,
                "pool": inference_job.resources.pool,
                "service_port": inference_job.service.port,
                "nodes": inference_job.resources.nodes,
            },
            "k8s_resources": {
                "statefulset": sts_result["name"],
                "headless": f"{name}-headless",
                "service": service_result["name"],
            }
        }

    def update_inference_service(self, inference_job: InferenceJob,
                                 namespace: str = "default") -> Dict[str, Any]:
        """Update inference service (delete and recreate).

        两种形态(Deployment / StatefulSet)与两个 Service(NodePort / headless)都尝试删除,
        以支持单机↔多机互转,避免残留。
        """
        name = inference_job.job.name

        for fn in (self.client.delete_deployment, self.client.delete_statefulset):
            try:
                fn(name, namespace)
            except Exception:
                pass
        for svc in (svc_name(name), f"{name}-headless"):
            try:
                self.client.delete_service(svc, namespace)
            except Exception:
                pass

        return self.create_inference_service(inference_job, namespace)
