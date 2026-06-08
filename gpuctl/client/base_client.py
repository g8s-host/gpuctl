from kubernetes import client, config
from kubernetes.client.rest import ApiException
from typing import Optional

from gpuctl.kube_config import load_k8s_config


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
            load_k8s_config(config)
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

    def read_config_map(self, name: str, namespace: str) -> Optional[object]:
        """Read a ConfigMap, returns None if not found"""
        try:
            return self.core_v1.read_namespaced_config_map(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                return None
            raise RuntimeError(f"Failed to read ConfigMap {namespace}/{name}: {e}")

    def create_or_patch_config_map(self, name: str, namespace: str, data: dict) -> str:
        """Create ConfigMap if absent, patch (replace data) if exists. Returns 'created' or 'updated'."""
        from kubernetes import client as k8s_client
        body = k8s_client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=k8s_client.V1ObjectMeta(name=name, namespace=namespace),
            data=data,
        )
        existing = self.read_config_map(name, namespace)
        if existing is None:
            self.core_v1.create_namespaced_config_map(namespace=namespace, body=body)
            return "created"
        else:
            self.core_v1.patch_namespaced_config_map(name=name, namespace=namespace, body=body)
            return "updated"

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
            except (json.JSONDecodeError, AttributeError, TypeError):
                detailed_msg = str(e.body)
            raise FileNotFoundError(f"Resource not found for {operation}: {detailed_msg}")
        else:
            # For other errors, include the detailed message from Kubernetes
            try:
                import json
                error_body = json.loads(e.body)
                detailed_msg = error_body.get("message", str(e))
            except (json.JSONDecodeError, AttributeError, TypeError):
                detailed_msg = str(e)
            raise RuntimeError(f"Kubernetes API error during {operation}: {detailed_msg}")
