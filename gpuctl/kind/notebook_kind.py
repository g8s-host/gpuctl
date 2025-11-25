from gpuctl.builder.notebook_builder import NotebookBuilder
from gpuctl.client.job_client import JobClient
from gpuctl.api.notebook import NotebookJob
from typing import Dict, Any


class NotebookKind:
    """Notebook任务处理逻辑"""

    def __init__(self):
        self.builder = NotebookBuilder()
        self.client = JobClient()

    def create_notebook(self, notebook_job: NotebookJob,
                        namespace: str = "default") -> Dict[str, Any]:
        """创建Notebook服务"""
        # 构建K8s StatefulSet和Service资源
        statefulset = self.builder.build_statefulset(notebook_job)
        service = self.builder.build_service(notebook_job)

        # 提交到Kubernetes
        statefulset_result = self.client.create_statefulset(statefulset, namespace)
        service_result = self.client.create_service(service, namespace)

        return {
            "job_id": statefulset_result["name"],
            "name": notebook_job.spec.job.name,
            "status": "created",
            "namespace": namespace,
            "resources": {
                "gpu": notebook_job.spec.resources.accelerator_count,
                "gpu_type": notebook_job.spec.resources.gpu_type,
                "pool": notebook_job.spec.resources.pool,
                "service_port": 8888  # Jupyter默认端口
            },
            "access_url": self._build_access_url(service_result, notebook_job)
        }

    def _build_access_url(self, service_result: Dict[str, Any],
                          notebook_job: NotebookJob) -> str:
        """构建Notebook访问URL"""
        # 这里简化实现，实际需要根据Service类型和配置生成访问URL
        service_name = service_result["name"]
        namespace = service_result["namespace"]

        # 如果是NodePort或LoadBalancer类型，需要获取实际IP和端口
        # 这里返回一个格式化的访问信息
        return f"http://{service_name}.{namespace}.svc.cluster.local:8888"