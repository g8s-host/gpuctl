from .. import DEFAULT_NAMESPACE
from .base_client import KubernetesClient
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from typing import List, Optional
import time


class LogClient(KubernetesClient):
    """日志管理客户端"""

    def get_job_logs(self, job_name: str, namespace: str = DEFAULT_NAMESPACE,
                     tail: int = 100, pod_name: Optional[str] = None) -> List[str]:
        """获取任务日志"""
        try:
            # 如果未指定Pod，找到Job关联的Pod
            if not pod_name:
                pods = self._get_job_pods(job_name, namespace)
                if not pods:
                    return ["No pods found for this job"]
                pod_name = pods[0].metadata.name

            # 获取Pod日志
            log_content = self.core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=tail,
                timestamps=True
            )

            # 按行分割日志
            logs = log_content.strip().split('\n') if log_content else []
            return logs

        except ApiException as e:
            self.handle_api_exception(e, f"get logs for job {job_name}")

    def stream_job_logs(self, job_name: str, namespace: str = DEFAULT_NAMESPACE,
                        pod_name: Optional[str] = None):
        """流式获取任务日志（生成器）"""
        try:
            # 如果未指定Pod，找到Job关联的Pod
            if not pod_name:
                pods = self._get_job_pods(job_name, namespace)
                if not pods:
                    yield "No pods found for this job"
                    return
                pod_name = pods[0].metadata.name

            # 使用流式API获取实时日志
            watcher = stream(
                self.core_v1.read_namespaced_pod_log,
                name=pod_name,
                namespace=namespace,
                follow=True,
                timestamps=True,
                _preload_content=False
            )

            # 实时输出日志
            for line in watcher:
                if line:
                    yield line.strip()

            watcher.close()

        except ApiException as e:
            yield f"Error streaming logs: {e}"

    def get_pod_logs(self, pod_name: str, namespace: str = DEFAULT_NAMESPACE,
                     container: Optional[str] = None, tail: int = 100) -> List[str]:
        """获取特定Pod的日志"""
        try:
            log_content = self.core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container,
                tail_lines=tail,
                timestamps=True
            )

            logs = log_content.strip().split('\n') if log_content else []
            return logs

        except ApiException as e:
            self.handle_api_exception(e, f"get logs for pod {pod_name}")

    def _get_job_pods(self, job_name: str, namespace: str = DEFAULT_NAMESPACE):
        """获取Job关联的所有Pod"""
        try:
            # 通过标签选择器找到Job关联的Pod
            pods = self.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"job-name={job_name}"
            )
            return pods.items

        except ApiException as e:
            self.handle_api_exception(e, f"get pods for job {job_name}")