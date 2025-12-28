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

    def _get_user_namespace(self, user_name: str) -> str:
        """Get namespace for a user"""
        return user_name

    def create_quota(self, quota_name: str, user_name: str, cpu: str = None,
                     memory: str = None, gpu: str = None) -> Dict[str, Any]:
        """Create resource quota for a user"""
        try:
            namespace_name = self._get_user_namespace(user_name)

            self._ensure_namespace_exists(namespace_name)

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
                    name=f"{quota_name}-{user_name}",
                    namespace=namespace_name,
                    labels={
                        "g8s.host/quota": quota_name,
                        "g8s.host/user": user_name
                    }
                ),
                spec={"hard": hard_limits}
            )

            self.core_v1.create_namespaced_resource_quota(
                namespace=namespace_name,
                body=resource_quota
            )

            return {
                "name": quota_name,
                "user": user_name,
                "namespace": namespace_name,
                "cpu": cpu or "unlimited",
                "memory": memory or "unlimited",
                "gpu": gpu or "unlimited",
                "status": "created"
            }

        except ApiException as e:
            self.handle_api_exception(e, f"create quota {quota_name} for {user_name}")

    def apply_quota(self, quota_name: str, user_name: str, cpu: str = None,
                    memory: str = None, gpu: str = None) -> Dict[str, Any]:
        """Apply resource quota for a user (create or update)"""
        namespace_name = self._get_user_namespace(user_name)

        try:
            self.core_v1.read_namespaced_resource_quota(
                f"{quota_name}-{user_name}", namespace_name
            )
            return self.update_quota(quota_name, user_name, cpu, memory, gpu)
        except ApiException as e:
            if e.status == 404:
                return self.create_quota(quota_name, user_name, cpu, memory, gpu)
            raise

    def update_quota(self, quota_name: str, user_name: str, cpu: str = None,
                     memory: str = None, gpu: str = None) -> Dict[str, Any]:
        """Update existing resource quota"""
        try:
            namespace_name = self._get_user_namespace(user_name)

            hard_limits = {}
            if cpu:
                hard_limits["cpu"] = cpu
            if memory:
                hard_limits["memory"] = memory
            if gpu:
                hard_limits["nvidia.com/gpu"] = gpu

            self.core_v1.patch_namespaced_resource_quota(
                name=f"{quota_name}-{user_name}",
                namespace=namespace_name,
                body=[{"op": "replace", "path": "/spec/hard", "value": hard_limits}]
            )

            return {
                "name": quota_name,
                "user": user_name,
                "namespace": namespace_name,
                "cpu": cpu or "unlimited",
                "memory": memory or "unlimited",
                "gpu": gpu or "unlimited",
                "status": "updated"
            }
        except ApiException as e:
            self.handle_api_exception(e, f"update quota {quota_name} for {user_name}")

    def create_quota_config(self, quota_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create resource quota for multiple users"""
        results = []
        quota_name = quota_config.get("name", "default-quota")
        users = quota_config.get("users", {})

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

        for user_name, user_quota in users.items():
            if user_name == "default":
                continue
            result = self.create_quota(
                quota_name=quota_name,
                user_name=user_name,
                cpu=user_quota.get("cpu"),
                memory=user_quota.get("memory"),
                gpu=user_quota.get("gpu")
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
                    raise ValueError(f"Namespace 'default' is a reserved Kubernetes namespace. Please use a different user name.")
                namespace = V1Namespace(
                    api_version="v1",
                    kind="Namespace",
                    metadata=V1ObjectMeta(
                        name=namespace_name,
                        labels={
                            "g8s.host/user-namespace": "true"
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
                        "g8s.host/user": "default"
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
                "user": "default",
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
                    "user": "default",
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
            namespaces = self.core_v1.list_namespace(
                label_selector="g8s.host/user-namespace=true"
            )

            for ns in namespaces.items:
                ns_name = ns.metadata.name
                quota_list = self.core_v1.list_namespaced_resource_quota(ns_name)

                for quota in quota_list.items:
                    if quota_name and quota.metadata.labels.get("g8s.host/quota") != quota_name:
                        continue

                    user_name = quota.metadata.labels.get("g8s.host/user", "")
                    quota_info = self._build_quota_info(quota, user_name, ns_name)
                    quotas.append(quota_info)

            return quotas

        except ApiException as e:
            self.handle_api_exception(e, "list quotas")

    def get_quota(self, user_name: str) -> Optional[Dict[str, Any]]:
        """Get resource quota for a specific user"""
        try:
            namespace_name = self._get_user_namespace(user_name)

            quota_list = self.core_v1.list_namespaced_resource_quota(namespace_name)

            if not quota_list.items:
                return None

            quota = quota_list.items[0]
            return self._build_quota_info(quota, user_name, namespace_name)

        except ApiException as e:
            if e.status == 404:
                return None
            self.handle_api_exception(e, f"get quota for {user_name}")

    def describe_quota(self, user_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed quota information with usage"""
        try:
            namespace_name = self._get_user_namespace(user_name)

            quota_list = self.core_v1.list_namespaced_resource_quota(namespace_name)

            if not quota_list.items:
                return None

            quota = quota_list.items[0]
            quota_info = self._build_quota_info(quota, user_name, namespace_name)

            if quota.status and quota.status.used:
                quota_info["usage"] = {
                    "cpu": quota_info["hard"].get("cpu", "unlimited"),
                    "memory": quota_info["hard"].get("memory", "unlimited"),
                    "gpu": quota_info["hard"].get("nvidia.com/gpu", "unlimited")
                }

            return quota_info

        except ApiException as e:
            if e.status == 404:
                return None
            self.handle_api_exception(e, f"describe quota for {user_name}")

    def _build_quota_info(self, quota, user_name: str, namespace_name: str) -> Dict[str, Any]:
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
            "user": user_name,
            "namespace": namespace_name,
            "hard": hard_limits,
            "used": used,
            "status": "Active"
        }

    def delete_quota(self, user_name: str) -> bool:
        """Delete resource quota for a user"""
        try:
            namespace_name = self._get_user_namespace(user_name)

            quota_list = self.core_v1.list_namespaced_resource_quota(namespace_name)

            for quota in quota_list.items:
                self.core_v1.delete_namespaced_resource_quota(
                    quota.metadata.name,
                    namespace_name
                )

            return True

        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"delete quota for {user_name}")

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
                            "user": "default",
                            "namespace": "default"
                        })
                except ApiException as e:
                    if e.status != 404:
                        results["failed"].append({
                            "user": "default",
                            "error": str(e)
                        })

            namespaces = self.core_v1.list_namespace(
                label_selector="g8s.host/user-namespace=true"
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
                                "user": quota.metadata.labels.get("g8s.host/user"),
                                "namespace": ns_name
                            })
                        except Exception as e:
                            results["failed"].append({
                                "user": quota.metadata.labels.get("g8s.host/user"),
                                "error": str(e)
                            })

            return results

        except ApiException as e:
            self.handle_api_exception(e, f"delete quota config {quota_name}")
