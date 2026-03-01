from gpuctl.builder.compute_builder import ComputeBuilder
from gpuctl.client.job_client import JobClient
from gpuctl.api.compute import ComputeJob
from kubernetes.client.rest import ApiException
from typing import Dict, Any


class ComputeKind:
    """Compute job processing logic"""

    def __init__(self):
        self.builder = ComputeBuilder()
        self.client = JobClient()

    def create_compute_service(self, compute_job: ComputeJob, namespace: str = "default") -> Dict[str, Any]:
        """Create compute job"""
        deployment = self.builder.build_deployment(compute_job, namespace)
        
        service = self.builder.build_service(compute_job, namespace)

        deployment_result = self.client.create_deployment(deployment, namespace)
        
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
        """Get compute job status"""
        deployment_name = f"{job_name}"
        try:
            raw = self.client.apps_v1.read_namespaced_deployment(deployment_name, namespace)
        except ApiException as e:
            if e.status == 404:
                return {"status": "not_found"}
            raise
        deployment_status = raw.status or {}
        ready_replicas = deployment_status.ready_replicas or 0
        desired_replicas = raw.spec.replicas or 0
        available_replicas = deployment_status.available_replicas or 0

        if ready_replicas == desired_replicas and desired_replicas > 0:
            status = "running"
        elif available_replicas > 0:
            status = "partially_available"
        else:
            status = "pending"

        pods = self.client.list_pods(namespace, labels={"app": deployment_name})
        return {
            "name": job_name,
            "status": status,
            "deployment_name": deployment_name,
            "pods": pods,
            "ready_replicas": ready_replicas,
            "desired_replicas": desired_replicas
        }
        
    def update_compute_service(self, compute_job: ComputeJob, namespace: str = "default") -> Dict[str, Any]:
        """Update compute job"""
        deployment = self.builder.build_deployment(compute_job, namespace)
        service = self.builder.build_service(compute_job, namespace)
        
        deployment_name = deployment.metadata.name
        service_name = service.metadata.name
        
        # Check if deployment exists
        if self.client._is_deployment_exists(deployment_name, namespace):
            # Update existing deployment
            deployment_result = self.client.update_deployment(deployment_name, namespace, deployment)
        else:
            # Create new deployment if it doesn't exist
            deployment_result = self.client.create_deployment(deployment, namespace)
        
        # Check if service exists
        if self.client._is_service_exists(service_name, namespace):
            # Update existing service
            service_result = self.client.update_service(service_name, namespace, service)
        else:
            # Create new service if it doesn't exist
            service_result = self.client.create_service(service, namespace)
        
        return {
            "job_id": deployment_result["name"],
            "name": compute_job.job.name,
            "status": "updated",
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