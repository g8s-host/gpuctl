from gpuctl.builder.inference_builder import InferenceBuilder
from gpuctl.client.job_client import JobClient
from gpuctl.api.inference import InferenceJob
from typing import Dict, Any


class InferenceKind:
    """推理任务处理逻辑"""

    def __init__(self):
        self.builder = InferenceBuilder()
        self.client = JobClient()

    def create_inference_service(self, inference_job: InferenceJob,
                                 namespace: str = "default") -> Dict[str, Any]:
        """创建推理服务"""
        # 构建K8s Deployment和Service资源
        deployment = self.builder.build_deployment(inference_job)
        service = self.builder.build_service(inference_job)

        # 提交到Kubernetes
        deployment_result = self.client.create_deployment(deployment, namespace)
        service_result = self.client.create_service(service, namespace)

        # 如果启用了自动扩缩容，创建HPA
        hpa_result = None
        if inference_job.autoscaling.enabled:
            hpa = self.builder.build_hpa(inference_job)
            hpa_result = self.client.create_hpa(hpa, namespace)

        return {
            "job_id": deployment_result["name"],
            "name": inference_job.job.name,
            "status": "created",
            "namespace": namespace,
            "resources": {
                "gpu": inference_job.resources.gpu,
                "gpu_type": inference_job.resources.gpu_type,
                "pool": inference_job.resources.pool,
                "service_port": inference_job.service.port
            },
            "k8s_resources": {
                "deployment": deployment_result["name"],
                "service": service_result["name"],
                "hpa": hpa_result["name"] if hpa_result else None
            }
        }