from gpuctl.builder.notebook_builder import NotebookBuilder
from gpuctl.client.job_client import JobClient
from gpuctl.api.notebook import NotebookJob
from typing import Dict, Any


class NotebookKind:
    """Notebook job processing logic"""

    def __init__(self):
        self.builder = NotebookBuilder()
        self.client = JobClient()

    def create_notebook(self, notebook_job: NotebookJob,
                        namespace: str = "default") -> Dict[str, Any]:
        """Create Notebook service"""
        statefulset = self.builder.build_statefulset(notebook_job)
        service = self.builder.build_service(notebook_job)

        statefulset_result = self.client.create_statefulset(statefulset, namespace)
        service_result = self.client.create_service(service, namespace)

        return {
            "job_id": statefulset_result["name"],
            "name": notebook_job.job.name,
            "status": "created",
            "namespace": namespace,
            "resources": {
                "gpu": notebook_job.resources.gpu,
                "gpu_type": notebook_job.resources.gpu_type,
                "pool": notebook_job.resources.pool,
                "service_port": 8888
            },
            "access_url": self._build_access_url(service_result, notebook_job)
        }

    def update_notebook(self, notebook_job: NotebookJob,
                        namespace: str = "default") -> Dict[str, Any]:
        """Update Notebook service (delete and recreate)"""
        statefulset_name = f"{notebook_job.job.name}"
        service_name = f"svc-{notebook_job.job.name}"
        
        try:
            self.client.delete_statefulset(statefulset_name, namespace)
        except Exception:
            pass
        
        try:
            self.client.delete_service(service_name, namespace)
        except Exception:
            pass
        
        return self.create_notebook(notebook_job, namespace)

    def _build_access_url(self, service_result: Dict[str, Any],
                          notebook_job: NotebookJob) -> str:
        """Build Notebook access URL"""
        service_name = service_result["name"]
        namespace = service_result["namespace"]

        return f"http://{service_name}.{namespace}.svc.cluster.local:8888"