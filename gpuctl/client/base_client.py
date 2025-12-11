from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
from typing import Optional


class KubernetesClient:
    """Kubernetes客户端基类"""

    def __init__(self):
        self._load_config()
        self.core_v1 = client.CoreV1Api()
        self.batch_v1 = client.BatchV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.autoscaling_v1 = client.AutoscalingV1Api()

    def _load_config(self):
        """加载Kubernetes配置"""
        try:
            if os.getenv('KUBERNETES_SERVICE_HOST'):
                config.load_incluster_config()
            else:
                config.load_kube_config()
        except Exception as e:
            raise RuntimeError(f"Failed to load Kubernetes config: {e}")

    def ensure_namespace_exists(self, namespace: str) -> None:
        """确保命名空间存在，如果不存在则创建"""
        try:
            # 检查命名空间是否存在
            self.core_v1.read_namespace(namespace)
        except ApiException as e:
            if e.status == 404:
                # 命名空间不存在，创建它
                try:
                    body = client.V1Namespace(
                        metadata=client.V1ObjectMeta(name=namespace)
                    )
                    self.core_v1.create_namespace(body)
                except ApiException as create_e:
                    raise RuntimeError(f"Failed to create namespace {namespace}: {create_e}")
            else:
                raise RuntimeError(f"Failed to check namespace {namespace}: {e}")

    def handle_api_exception(self, e: ApiException, operation: str) -> None:
        """处理API异常"""
        if e.status == 401:
            raise PermissionError(f"Authentication failed for {operation}")
        elif e.status == 403:
            raise PermissionError(f"Permission denied for {operation}")
        elif e.status == 404:
            # Parse the detailed error message from Kubernetes API response
            try:
                import json
                error_body = json.loads(e.body)
                detailed_msg = error_body.get("message", "Unknown resource")
                raise FileNotFoundError(f"Resource not found for {operation}: {detailed_msg}")
            except:
                # If parsing fails, use the original error message
                raise FileNotFoundError(f"Resource not found for {operation}: {e.body}")
        else:
            # For other errors, include the detailed message from Kubernetes
            try:
                import json
                error_body = json.loads(e.body)
                detailed_msg = error_body.get("message", str(e))
                raise RuntimeError(f"Kubernetes API error during {operation}: {detailed_msg}")
            except:
                raise RuntimeError(f"Kubernetes API error during {operation}: {e}")