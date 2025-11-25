from .base_client import KubernetesClient
from kubernetes.client.rest import ApiException
from typing import List, Dict, Any, Optional


class PoolClient(KubernetesClient):
    """资源池管理客户端"""

    def list_pools(self) -> List[Dict[str, Any]]:
        """列出所有资源池"""
        try:
            # 获取所有节点
            nodes = self.core_v1.list_node()

            # 按资源池标签分组
            pool_nodes = {}
            for node in nodes.items:
                labels = node.metadata.labels or {}
                pool_name = labels.get("gpuctl/pool", "default")

                if pool_name not in pool_nodes:
                    pool_nodes[pool_name] = []
                pool_nodes[pool_name].append(node)

            # 构建资源池信息
            pools = []
            for pool_name, nodes in pool_nodes.items():
                pool_info = self._build_pool_info(pool_name, nodes)
                pools.append(pool_info)

            return pools

        except ApiException as e:
            self.handle_api_exception(e, "list pools")

    def get_pool(self, pool_name: str) -> Optional[Dict[str, Any]]:
        """获取特定资源池详情"""
        try:
            # 获取该资源池的所有节点
            nodes = self.core_v1.list_node(
                label_selector=f"gpuctl/pool={pool_name}"
            )

            if not nodes.items:
                return None

            return self._build_pool_info(pool_name, nodes.items)

        except ApiException as e:
            self.handle_api_exception(e, f"get pool {pool_name}")

    def create_pool(self, pool_config: Dict[str, Any]) -> Dict[str, Any]:
        """创建资源池"""
        try:
            pool_name = pool_config["name"]

            # 为节点添加资源池标签
            for node_name in pool_config.get("nodes", []):
                self._label_node(node_name, "gpuctl/pool", pool_name)

            return {
                "name": pool_name,
                "status": "created",
                "message": "资源池创建成功"
            }

        except ApiException as e:
            self.handle_api_exception(e, "create pool")

    def delete_pool(self, pool_name: str) -> bool:
        """删除资源池"""
        try:
            # 获取资源池的所有节点
            nodes = self.core_v1.list_node(
                label_selector=f"gpuctl/pool={pool_name}"
            )

            # 移除资源池标签
            for node in nodes.items:
                self._remove_node_label(node.metadata.name, "gpuctl/pool")

            return True

        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"delete pool {pool_name}")

    def add_nodes_to_pool(self, pool_name: str, node_names: List[str]) -> Dict[str, Any]:
        """添加节点到资源池"""
        try:
            success = []
            failed = []

            for node_name in node_names:
                try:
                    self._label_node(node_name, "gpuctl/pool", pool_name)
                    success.append(node_name)
                except Exception as e:
                    failed.append({"node": node_name, "error": str(e)})

            return {
                "pool": pool_name,
                "success": success,
                "failed": failed,
                "message": "节点添加完成"
            }

        except ApiException as e:
            self.handle_api_exception(e, f"add nodes to pool {pool_name}")

    def remove_nodes_from_pool(self, pool_name: str, node_names: List[str]) -> Dict[str, Any]:
        """从资源池移除节点"""
        try:
            success = []
            failed = []

            for node_name in node_names:
                try:
                    self._remove_node_label(node_name, "gpuctl/pool")
                    success.append(node_name)
                except Exception as e:
                    failed.append({"node": node_name, "error": str(e)})

            return {
                "pool": pool_name,
                "success": success,
                "failed": failed,
                "message": "节点移除完成"
            }

        except ApiException as e:
            self.handle_api_exception(e, f"remove nodes from pool {pool_name}")

    def _build_pool_info(self, pool_name: str, nodes: List[Any]) -> Dict[str, Any]:
        """构建资源池信息"""
        gpu_total = 0
        gpu_used = 0
        gpu_types = set()

        # 获取节点上的GPU信息
        for node in nodes:
            # 获取节点的GPU数量（从节点标签或资源容量）
            gpu_count = self._get_node_gpu_count(node)
            gpu_total += gpu_count

            # 获取GPU类型
            gpu_type = self._get_node_gpu_type(node)
            if gpu_type:
                gpu_types.add(gpu_type)

            # 获取已使用的GPU数量（需要从运行的Pod中统计）
            gpu_used += self._get_used_gpu_count(node.metadata.name)

        return {
            "name": pool_name,
            "description": f"{pool_name}资源池",
            "nodes": [node.metadata.name for node in nodes],
            "gpu_total": gpu_total,
            "gpu_used": gpu_used,
            "gpu_free": gpu_total - gpu_used,
            "gpu_types": list(gpu_types),
            "status": "active"
        }

    def _label_node(self, node_name: str, key: str, value: str) -> None:
        """为节点添加标签"""
        patch = {
            "metadata": {
                "labels": {
                    key: value
                }
            }
        }
        self.core_v1.patch_node(node_name, patch)

    def _remove_node_label(self, node_name: str, key: str) -> None:
        """移除节点标签"""
        patch = {
            "metadata": {
                "labels": {
                    key: None
                }
            }
        }
        self.core_v1.patch_node(node_name, patch)

    def _get_node_gpu_count(self, node) -> int:
        """获取节点的GPU数量"""
        # 从节点容量中获取GPU数量
        if node.status and node.status.capacity:
            gpu_resource = node.status.capacity.get("nvidia.com/gpu")
            if gpu_resource:
                return int(gpu_resource)
        return 0

    def _get_node_gpu_type(self, node) -> Optional[str]:
        """获取节点的GPU类型"""
        labels = node.metadata.labels or {}
        return labels.get("nvidia.com/gpu-type")

    def _get_used_gpu_count(self, node_name: str) -> int:
        """获取节点上已使用的GPU数量"""
        try:
            # 获取节点上运行的所有Pod
            pods = self.core_v1.list_pod_for_all_namespaces(
                field_selector=f"spec.nodeName={node_name}"
            )

            used_gpus = 0
            for pod in pods.items:
                # 检查Pod是否正在运行
                if pod.status.phase not in ["Running", "Pending"]:
                    continue

                # 统计Pod请求的GPU数量
                for container in pod.spec.containers:
                    if container.resources and container.resources.requests:
                        gpu_request = container.resources.requests.get("nvidia.com/gpu")
                        if gpu_request:
                            used_gpus += int(gpu_request)

            return used_gpus

        except ApiException:
            return 0