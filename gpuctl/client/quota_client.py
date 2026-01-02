from .base_client import KubernetesClient
from kubernetes.client.rest import ApiException
from kubernetes.client import V1ResourceQuota, V1Namespace, V1ObjectMeta, V1LabelSelector
from typing import List, Dict, Any, Optional


class QuotaClient(KubernetesClient):
    """Resource quota management client"""

    _instance = None

    DEFAULT_NAMESPACE = "g8s-host"

    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_namespace_name(self, namespace_name: str) -> str:
        """Get namespace name"""
        return namespace_name

    def namespace_has_quota(self, namespace_name: str) -> bool:
        """Check if a namespace has quota configured"""
        try:
            if namespace_name == "default":
                return True
            namespaces = self.core_v1.list_namespace(
                label_selector="g8s.host/user-namespace=true"
            )
            if not namespaces.items:
                namespaces = self.core_v1.list_namespace(
                    label_selector="g8s.host/namespace=true"
                )
            for ns in namespaces.items:
                if ns.metadata.name == namespace_name:
                    return True
            return False
        except ApiException as e:
            self.handle_api_exception(e, f"check namespace {namespace_name}")
            return False

    def create_quota(self, quota_name: str, namespace_name: str, cpu: str = None,
                     memory: str = None, gpu: str = None) -> Dict[str, Any]:
        """Create resource quota for a namespace"""
        try:
            namespace = self._get_namespace_name(namespace_name)

            self._ensure_namespace_exists(namespace)

            hard_limits = {}
            if cpu:
                hard_limits["cpu"] = cpu
            if memory:
                hard_limits["memory"] = memory
            if gpu:
                hard_limits["nvidia.com/gpu"] = gpu

            resource_quota = V1ResourceQuota(
                api_version="v1",
                kind="ResourceQuota",
                metadata=V1ObjectMeta(
                    name=f"{quota_name}-{namespace_name}",
                    namespace=namespace,
                    labels={
                        "g8s.host/quota": quota_name,
                        "g8s.host/namespace": namespace_name
                    }
                ),
                spec={"hard": hard_limits}
            )

            self.core_v1.create_namespaced_resource_quota(
                namespace=namespace,
                body=resource_quota
            )

            return {
                "name": quota_name,
                "namespace": namespace,
                "cpu": cpu or "unlimited",
                "memory": memory or "unlimited",
                "gpu": gpu or "unlimited",
                "status": "created"
            }

        except ApiException as e:
            self.handle_api_exception(e, f"create quota {quota_name} for {namespace_name}")

    def apply_quota(self, quota_name: str, namespace_name: str, cpu: str = None,
                    memory: str = None, gpu: str = None) -> Dict[str, Any]:
        """Apply resource quota for a namespace (create or update)"""
        namespace = self._get_namespace_name(namespace_name)

        try:
            self.core_v1.read_namespaced_resource_quota(
                f"{quota_name}-{namespace_name}", namespace
            )
            return self.update_quota(quota_name, namespace_name, cpu, memory, gpu)
        except ApiException as e:
            if e.status == 404:
                return self.create_quota(quota_name, namespace_name, cpu, memory, gpu)
            raise

    def update_quota(self, quota_name: str, namespace_name: str, cpu: str = None,
                     memory: str = None, gpu: str = None) -> Dict[str, Any]:
        """Update existing resource quota"""
        try:
            namespace = self._get_namespace_name(namespace_name)

            hard_limits = {}
            if cpu:
                hard_limits["cpu"] = cpu
            if memory:
                hard_limits["memory"] = memory
            if gpu:
                hard_limits["nvidia.com/gpu"] = gpu

            self.core_v1.patch_namespaced_resource_quota(
                name=f"{quota_name}-{namespace_name}",
                namespace=namespace,
                body=[{"op": "replace", "path": "/spec/hard", "value": hard_limits}]
            )

            return {
                "name": quota_name,
                "namespace": namespace,
                "cpu": cpu or "unlimited",
                "memory": memory or "unlimited",
                "gpu": gpu or "unlimited",
                "status": "updated"
            }
        except ApiException as e:
            self.handle_api_exception(e, f"update quota {quota_name} for {namespace_name}")

    def create_quota_config(self, quota_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create resource quota for multiple namespaces"""
        results = []
        quota_name = quota_config.get("name", "default-quota")
        namespaces = quota_config.get("namespace", {})

        default_quota_config = quota_config.get("default")
        if default_quota_config:
            default_cpu = str(default_quota_config.get("cpu", 0))
            default_memory = str(default_quota_config.get("memory", "0Gi"))
            default_gpu = str(default_quota_config.get("gpu", 0))

            result = self._create_default_namespace_quota(
                quota_name=quota_name,
                cpu=default_cpu,
                memory=default_memory,
                gpu=default_gpu
            )
            results.append(result)

        for namespace_name, namespace_quota in namespaces.items():
            if namespace_name == "default":
                continue
            result = self.create_quota(
                quota_name=quota_name,
                namespace_name=namespace_name,
                cpu=namespace_quota.get("cpu"),
                memory=namespace_quota.get("memory"),
                gpu=namespace_quota.get("gpu")
            )
            results.append(result)

        return results

    def _ensure_namespace_exists(self, namespace_name: str) -> None:
        """Ensure namespace exists, create if not"""
        try:
            self.core_v1.read_namespace(namespace_name)
        except ApiException as e:
            if e.status == 404:
                if namespace_name == "default":
                    raise ValueError(f"Namespace 'default' is a reserved Kubernetes namespace. Please use a different namespace name.")
                namespace = V1Namespace(
                    api_version="v1",
                    kind="Namespace",
                    metadata=V1ObjectMeta(
                        name=namespace_name,
                        labels={
                            "g8s.host/namespace": "true"
                        }
                    )
                )
                self.core_v1.create_namespace(body=namespace)
            else:
                raise

    def _create_default_namespace_quota(self, quota_name: str, cpu: str = None,
                                         memory: str = None, gpu: str = None) -> Dict[str, Any]:
        """Create or update ResourceQuota in default namespace"""
        try:
            hard_limits = {}
            if cpu:
                hard_limits["cpu"] = cpu
            if memory:
                hard_limits["memory"] = memory
            if gpu:
                hard_limits["nvidia.com/gpu"] = gpu

            resource_quota = V1ResourceQuota(
                api_version="v1",
                kind="ResourceQuota",
                metadata=V1ObjectMeta(
                    name=f"{quota_name}-default",
                    namespace="default",
                    labels={
                        "g8s.host/quota": quota_name,
                        "g8s.host/namespace": "default"
                    }
                ),
                spec={"hard": hard_limits}
            )

            self.core_v1.create_namespaced_resource_quota(
                namespace="default",
                body=resource_quota
            )

            return {
                "name": quota_name,
                "namespace": "default",
                "cpu": cpu or "unlimited",
                "memory": memory or "unlimited",
                "gpu": gpu or "unlimited",
                "status": "created"
            }
        except ApiException as e:
            if e.status == 409:
                self.core_v1.patch_namespaced_resource_quota(
                    name=f"{quota_name}-default",
                    namespace="default",
                    body=[{"op": "replace", "path": "/spec/hard", "value": hard_limits}]
                )
                return {
                    "name": quota_name,
                    "namespace": "default",
                    "cpu": cpu or "unlimited",
                    "memory": memory or "unlimited",
                    "gpu": gpu or "unlimited",
                    "status": "updated"
                }
            self.handle_api_exception(e, f"create quota {quota_name} for default")

    def apply_default_quota(self, quota_name: str, cpu: str = None,
                            memory: str = None, gpu: str = None) -> Dict[str, Any]:
        """Apply resource quota for default namespace (create or update)"""
        return self._create_default_namespace_quota(quota_name, cpu, memory, gpu)

    def list_quotas(self, quota_name: str = None) -> List[Dict[str, Any]]:
        """List all resource quotas"""
        try:
            quotas = []
            
            # 扫描所有命名空间，查找带有g8s.host/quota标签的ResourceQuota
            all_namespaces = self.core_v1.list_namespace()
            
            for ns in all_namespaces.items:
                ns_name = ns.metadata.name
                quota_list = self.core_v1.list_namespaced_resource_quota(ns_name)

                for quota in quota_list.items:
                    if quota.metadata.labels.get("g8s.host/quota"):
                        if quota_name and quota.metadata.labels.get("g8s.host/quota") != quota_name:
                            continue

                        namespace_name = quota.metadata.labels.get("g8s.host/namespace", ns_name)
                        quota_info = self._build_quota_info(quota, namespace_name, ns_name)
                        quotas.append(quota_info)

            return quotas

        except ApiException as e:
            self.handle_api_exception(e, "list quotas")

    def get_quota(self, namespace_name: str) -> Optional[Dict[str, Any]]:
        """Get resource quota for a specific namespace"""
        try:
            namespace = self._get_namespace_name(namespace_name)

            quota_list = self.core_v1.list_namespaced_resource_quota(namespace)

            if not quota_list.items:
                return None

            quota = quota_list.items[0]
            return self._build_quota_info(quota, namespace_name, namespace)

        except ApiException as e:
            if e.status == 404:
                return None
            self.handle_api_exception(e, f"get quota for {namespace_name}")

    def describe_quota(self, namespace_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed quota information with usage"""
        try:
            namespace = self._get_namespace_name(namespace_name)

            quota_list = self.core_v1.list_namespaced_resource_quota(namespace)

            if not quota_list.items:
                return None

            quota = quota_list.items[0]
            quota_info = self._build_quota_info(quota, namespace_name, namespace)

            if quota.status and quota.status.used:
                quota_info["used"] = {
                    "cpu": quota.status.used.get("cpu", "0"),
                    "memory": quota.status.used.get("memory", "0"),
                    "nvidia.com/gpu": quota.status.used.get("nvidia.com/gpu", "0")
                }

            return quota_info

        except ApiException as e:
            if e.status == 404:
                return None
            self.handle_api_exception(e, f"describe quota for {namespace_name}")

    def _build_quota_info(self, quota, namespace_name: str, namespace: str) -> Dict[str, Any]:
        """Build quota information dictionary"""
        hard_limits = {}
        if quota.spec and quota.spec.hard:
            hard_limits = {
                "cpu": quota.spec.hard.get("cpu", "unlimited"),
                "memory": quota.spec.hard.get("memory", "unlimited"),
                "nvidia.com/gpu": quota.spec.hard.get("nvidia.com/gpu", "unlimited"),
                "pods": quota.spec.hard.get("pods", "unlimited")
            }

        used = {}
        if quota.status and quota.status.used:
            used = {
                "cpu": quota.status.used.get("cpu", "0"),
                "memory": quota.status.used.get("memory", "0"),
                "nvidia.com/gpu": quota.status.used.get("nvidia.com/gpu", "0")
            }

        return {
            "name": quota.metadata.labels.get("g8s.host/quota", "default"),
            "namespace": namespace,
            "hard": hard_limits,
            "used": used,
            "status": "Active"
        }

    def delete_quota(self, namespace_name: str) -> bool:
        """Delete resource quota for a namespace"""
        try:
            namespace = self._get_namespace_name(namespace_name)

            quota_list = self.core_v1.list_namespaced_resource_quota(namespace)

            for quota in quota_list.items:
                self.core_v1.delete_namespaced_resource_quota(
                    quota.metadata.name,
                    namespace
                )

            return True

        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"delete quota for {namespace_name}")

    def delete_quota_config(self, quota_name: str, include_default: bool = False) -> Dict[str, Any]:
        """Delete all quotas with the given name"""
        try:
            results = {"deleted": [], "failed": []}

            if include_default:
                try:
                    quota = self.core_v1.read_namespaced_resource_quota(
                        f"{quota_name}-default", "default"
                    )
                    if quota.metadata.labels.get("g8s.host/quota") == quota_name:
                        self.core_v1.delete_namespaced_resource_quota(
                            f"{quota_name}-default", "default"
                        )
                        results["deleted"].append({
                            "namespace": "default"
                        })
                except ApiException as e:
                    if e.status != 404:
                        results["failed"].append({
                            "namespace": "default",
                            "error": str(e)
                        })

            namespaces = self.core_v1.list_namespace(
                label_selector="g8s.host/user-namespace=true"
            )
            if not namespaces.items:
                namespaces = self.core_v1.list_namespace(
                    label_selector="g8s.host/namespace=true"
                )

            for ns in namespaces.items:
                ns_name = ns.metadata.name
                quota_list = self.core_v1.list_namespaced_resource_quota(ns_name)

                for quota in quota_list.items:
                    if quota.metadata.labels.get("g8s.host/quota") == quota_name:
                        try:
                            self.core_v1.delete_namespaced_resource_quota(
                                quota.metadata.name,
                                ns_name
                            )
                            self.core_v1.delete_namespace(ns_name)
                            results["deleted"].append({
                                "namespace": quota.metadata.labels.get("g8s.host/namespace"),
                                "original_namespace": ns_name
                            })
                        except Exception as e:
                            results["failed"].append({
                                "namespace": quota.metadata.labels.get("g8s.host/namespace"),
                                "error": str(e)
                            })

            return results

        except ApiException as e:
            self.handle_api_exception(e, f"delete quota config {quota_name}")
