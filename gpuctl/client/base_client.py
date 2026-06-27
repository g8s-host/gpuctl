from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
from typing import Optional


class KubernetesClient:
    """Kubernetes客户端基类"""

    def __init__(self, cluster: Optional[str] = None):
        """初始化客户端
        
        Args:
            cluster: 集群名称，如果为 None 则使用默认集群
        """
        self._load_config(cluster)
        self.core_v1 = client.CoreV1Api()
        self.batch_v1 = client.BatchV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.autoscaling_v1 = client.AutoscalingV1Api()

    def _load_config(self, cluster: Optional[str] = None):
        """加载Kubernetes配置
        
        Args:
            cluster: 集群名称，如果为 None 则使用默认集群
        """
        try:
            if os.getenv('KUBERNETES_SERVICE_HOST'):
                config.load_incluster_config()
            else:
                # 支持多云集群配置
                if cluster:
                    from gpuctl.multicloud.config import get_cluster
                    c = get_cluster(cluster)
                    if c:
                        config.load_kube_config(config_file=c.kubeconfig_path)
                    else:
                        raise RuntimeError(f"Cluster '{cluster}' not found")
                else:
                    # 检查是否配置了默认集群
                    from gpuctl.multicloud.config import load_config, get_current_kubeconfig
                    try:
                        kubeconfig_path = get_current_kubeconfig()
                        config.load_kube_config(config_file=kubeconfig_path)
                    except Exception:
                        # 回退到默认 kubeconfig
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

    def create_or_patch_config_map(self, name: str, namespace: str, data: dict) -> str:
        """创建或更新 ConfigMap：存在则 patch(合并 data),不存在则 create。

        用于 `gpuctl init`(写 kube-system/gpuctl-config 的 NFS 配置)等场景。

        Returns:
            "created"(新建) 或 "updated"(已存在 → patch)。
        """
        body = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            data=data,
        )
        try:
            self.core_v1.read_namespaced_config_map(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                self.core_v1.create_namespaced_config_map(namespace=namespace, body=body)
                return "created"
            raise
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