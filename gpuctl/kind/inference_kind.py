from gpuctl.builder.inference_builder import InferenceBuilder
from gpuctl.client.job_client import JobClient
from gpuctl.api.inference import InferenceJob
from typing import Dict, Any


class InferenceKind:
    """Inference job processing logic"""

    def __init__(self):
        self.builder = InferenceBuilder()
        self.client = JobClient()

    def create_inference_service(self, inference_job: InferenceJob,
                                 namespace: str = "default") -> Dict[str, Any]:
        """Create inference service"""
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

    def update_inference_service(self, inference_job: InferenceJob,
                                 namespace: str = "default") -> Dict[str, Any]:
        """Update inference service (delete and recreate)"""
        deployment_name = f"{inference_job.job.name}"
        service_name = f"svc-{inference_job.job.name}"
        
        try:
            self.client.delete_deployment(deployment_name, namespace)
        except Exception:
            pass
        
        try:
            self.client.delete_service(service_name, namespace)
        except Exception:
            pass
        
        return self.create_inference_service(inference_job, namespace)