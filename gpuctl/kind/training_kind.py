from gpuctl.builder.training_builder import TrainingBuilder
from gpuctl.client.job_client import JobClient
from gpuctl.api.training import TrainingJob
from typing import Dict, Any


class TrainingKind:
    """Training job processing logic"""

    def __init__(self):
        self.builder = TrainingBuilder()
        self.client = JobClient()

    def create_training_job(self, training_job: TrainingJob,
                            namespace: str = "default") -> Dict[str, Any]:
        """Create training job"""
        k8s_job = self.builder.build_job(training_job)

        result = self.client.create_job(k8s_job, namespace)

        return {
            "job_id": result["name"],
            "name": training_job.job.name,
            "status": "created",
            "namespace": namespace,
            "resources": {
                "gpu": training_job.resources.gpu,
                "gpuType": training_job.resources.gpu_type,
                "pool": training_job.resources.pool
            }
        }

    def update_training_job(self, training_job: TrainingJob,
                            namespace: str = "default") -> Dict[str, Any]:
        """Update training job (delete and recreate)"""
        job_name = f"{training_job.job.name}"
        
        try:
            self.client.delete_job(job_name, namespace)
        except Exception:
            pass
        
        return self.create_training_job(training_job, namespace)

    def get_training_job_status(self, job_name: str,
                                namespace: str = "default") -> Dict[str, Any]:
        """Get training job status"""
        job_info = self.client.get_job(job_name, namespace)
        if not job_info:
            return {"status": "not_found"}

        pods = self.client.list_pods(namespace, labels={"job-name": job_name})

        status = "pending"
        if job_info["status"]["succeeded"] > 0:
            status = "succeeded"
        elif job_info["status"]["failed"] > 0:
            status = "failed"
        elif job_info["status"]["active"] > 0:
            status = "running"

        return {
            "name": job_name,
            "status": status,
            "pods": pods,
            "job_info": job_info
        }