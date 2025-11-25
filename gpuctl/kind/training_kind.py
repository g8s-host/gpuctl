from gpuctl.builder.training_builder import TrainingBuilder
from gpuctl.client.job_client import JobClient
from gpuctl.api.training import TrainingJob
from typing import Dict, Any


class TrainingKind:
    """训练任务处理逻辑"""

    def __init__(self):
        self.builder = TrainingBuilder()
        self.client = JobClient()

    def create_training_job(self, training_job: TrainingJob,
                            namespace: str = "default") -> Dict[str, Any]:
        """创建训练任务"""
        # 构建K8s Job资源
        k8s_job = self.builder.build_job(training_job)

        # 提交到Kubernetes
        result = self.client.create_job(k8s_job, namespace)

        return {
            "job_id": result["name"],
            "name": training_job.spec.job.name,
            "status": "created",
            "namespace": namespace,
            "resources": {
                "gpu": training_job.spec.resources.accelerator_count,
                "gpu_type": training_job.spec.resources.gpu_type,
                "pool": training_job.spec.resources.pool
            }
        }

    def get_training_job_status(self, job_name: str,
                                namespace: str = "default") -> Dict[str, Any]:
        """获取训练任务状态"""
        job_info = self.client.get_job(job_name, namespace)
        if not job_info:
            return {"status": "not_found"}

        # 获取Pod信息以获取详细状态
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