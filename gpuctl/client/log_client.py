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
            # 如果未指定Pod，先尝试直接将job_name作为Pod名称获取
            if not pod_name:
                try:
                    # 尝试直接将job_name作为Pod名称获取日志
                    log_content = self.core_v1.read_namespaced_pod_log(
                        name=job_name,
                        namespace=namespace,
                        tail_lines=tail,
                        timestamps=True
                    )
                    # 按行分割日志
                    logs = log_content.strip().split('\n') if log_content else []
                    return logs
                except ApiException as e:
                    if e.status != 404:
                        self.handle_api_exception(e, f"get logs for pod {job_name}")
                    # 如果直接获取失败，尝试找到Job关联的Pod
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
            # 如果未指定Pod，先尝试直接将job_name作为Pod名称
            if not pod_name:
                try:
                    # 尝试直接将job_name作为Pod名称获取
                    # 使用Kubernetes API的stream方法获取日志
                    # 先检查Pod是否存在
                    self.core_v1.read_namespaced_pod(job_name, namespace)
                    pod_name = job_name
                except ApiException as e:
                    if e.status != 404:
                        yield f"Error checking pod {job_name}: {e}"
                        return
                    # 如果直接获取失败，尝试找到Job关联的Pod
                    pods = self._get_job_pods(job_name, namespace)
                    if not pods:
                        yield "No pods found for this job"
                        return
                    pod_name = pods[0].metadata.name

            # 使用subprocess调用kubectl命令，确保权限正确
            import subprocess
            cmd = ["kubectl", "logs", pod_name, "-n", namespace, "-f", "--timestamps"]
            
            # 启动kubectl命令并持续读取输出
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # 持续读取日志流，直到用户中断或命令结束
            for line in iter(process.stdout.readline, ''):
                if line:
                    yield line.strip()
            
            # 等待命令结束并获取返回码
            process.wait()
            if process.returncode != 0:
                yield f"Error streaming logs: kubectl command returned non-zero exit code: {process.returncode}"

        except Exception as e:
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
            # 首先尝试直接将job_name作为Pod名称返回
            try:
                pod = self.core_v1.read_namespaced_pod(job_name, namespace)
                return [pod]
            except ApiException as e:
                if e.status != 404:
                    self.handle_api_exception(e, f"check pod {job_name}")
            
            # 简化标签选择器，只使用基础名称和标准标签
            # 去掉g8s-host-前缀兼容逻辑
            base_name = job_name
            if "-" in job_name:
                # 如果是Pod名称，去掉后缀获取基础名称
                parts = job_name.split("-")
                if len(parts) >= 3:
                    # 格式：base-name-deployment-hash-pod-suffix
                    base_name = "-".join(parts[:-2])
            
            selectors = [
                f"job-name={job_name}",
                f"app={job_name}",
                f"job-name={base_name}",
                f"app={base_name}",
                f"app.kubernetes.io/name={base_name}",
                f"app.kubernetes.io/instance={base_name}"
            ]
            
            for selector in selectors:
                try:
                    pods = self.core_v1.list_namespaced_pod(
                        namespace=namespace,
                        label_selector=selector
                    )
                    if pods.items:
                        return pods.items
                except ApiException as e:
                    if e.status != 404:
                        print(f"Warning: Failed to get pods with selector {selector}: {e}")
            
            # 如果所有选择器都找不到pods，返回空列表
            return []

        except ApiException as e:
            self.handle_api_exception(e, f"get pods for job {job_name}")