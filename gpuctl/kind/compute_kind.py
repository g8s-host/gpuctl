from gpuctl.builder.compute_builder import ComputeBuilder
from gpuctl.client.job_client import JobClient
from gpuctl.api.compute import ComputeJob
from typing import Dict, Any


class ComputeKind:
    """计算任务处理逻辑"""

    def __init__(self):
        self.builder = ComputeBuilder()
        self.client = JobClient()

    def create_compute_service(self, compute_job: ComputeJob, namespace: str = "default") -> Dict[str, Any]:
        """创建计算任务"""
        # 构建K8s Deployment资源
        deployment = self.builder.build_deployment(compute_job)
        
        # 构建K8s Service资源
        service = self.builder.build_service(compute_job)

        # 提交Deployment到Kubernetes
        deployment_result = self.client.create_deployment(deployment, namespace)
        
        # 提交Service到Kubernetes
        service_result = self.client.create_service(service, namespace)

        return {
            "job_id": deployment_result["name"],
            "name": compute_job.job.name,
            "status": "created",
            "namespace": namespace,
            "resources": {
                "cpu": compute_job.resources.cpu,
                "memory": compute_job.resources.memory,
                "pool": compute_job.resources.pool
            },
            "service": {
                "name": service_result["name"],
                "port": compute_job.service.port
            }
        }

    def get_compute_job_status(self, job_name: str, namespace: str = "default") -> Dict[str, Any]:
        """获取计算任务状态"""
        deployment_name = f"g8s-host-compute-{job_name}"
        deployment_info = self.client.get_deployment(deployment_name, namespace)
        
        if not deployment_info:
            return {"status": "not_found"}

        # 获取Pod信息以获取详细状态
        pods = self.client.list_pods(namespace, labels={"app": deployment_name})

        status = "pending"
        ready_replicas = deployment_info.get("status", {}).get("ready_replicas", 0)
        desired_replicas = deployment_info.get("spec", {}).get("replicas", 0)
        
        if ready_replicas == desired_replicas and desired_replicas > 0:
            status = "running"
        elif deployment_info.get("status", {}).get("available_replicas", 0) > 0:
            status = "partially_available"

        return {
            "name": job_name,
            "status": status,
            "deployment_name": deployment_name,
            "pods": pods,
            "deployment_info": deployment_info
        }