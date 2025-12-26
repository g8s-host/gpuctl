from .base_client import KubernetesClient
from kubernetes.client.rest import ApiException
from typing import List, Dict, Any, Optional


class PoolClient(KubernetesClient):
    """资源池管理客户端"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def list_pools(self) -> List[Dict[str, Any]]:
        """列出所有资源池"""
        try:
            # 获取所有节点
            nodes = self.core_v1.list_node()

            # 按资源池标签分组
            pool_nodes = {}
            for node in nodes.items:
                labels = node.metadata.labels or {}
                pool_name = labels.get("g8s.host/pool", "default")

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
                label_selector=f"g8s.host/pool={pool_name}"
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
            node_names = pool_config.get("nodes", [])

            # 验证所有节点是否存在
            self._validate_nodes_exist(node_names)

            # 为节点添加资源池标签
            for node_name in node_names:
                self._label_node(node_name, "g8s.host/pool", pool_name)

            return {
                "name": pool_name,
                "status": "created",
                "message": "资源池创建成功"
            }

        except ApiException as e:
            self.handle_api_exception(e, "create pool")

    def _validate_nodes_exist(self, node_names: List[str]) -> None:
        """验证所有节点是否存在"""
        if not node_names:
            return

        # 获取所有现有节点
        all_nodes = self.core_v1.list_node()
        existing_node_names = {node.metadata.name for node in all_nodes.items}

        # 检查是否有节点不存在
        invalid_nodes = [node for node in node_names if node not in existing_node_names]
        if invalid_nodes:
            raise ValueError(f"节点不存在: {', '.join(invalid_nodes)}")

    def delete_pool(self, pool_name: str) -> bool:
        """删除资源池，包括级联删除关联的作业"""
        try:
            from gpuctl.client.job_client import JobClient
            from kubernetes.client import V1DeleteOptions
            
            # 1. 删除所有关联的作业
            job_client = JobClient()
            # 获取所有作业，然后筛选出属于该资源池的作业
            all_jobs = job_client.list_jobs()
            
            for job in all_jobs:
                # 检查作业是否属于该资源池
                job_pool = job.get('labels', {}).get('g8s.host/pool')
                if job_pool == pool_name:
                    # 构建删除选项
                    delete_options = V1DeleteOptions(propagation_policy="Foreground", grace_period_seconds=0)
                    
                    # 获取作业名称
                    job_name = job['name']
                    
                    # 尝试删除作业资源
                    try:
                        # 先尝试删除Job资源
                        job_client.batch_v1.delete_namespaced_job(job_name, job.get('namespace', 'g8s-host'), body=delete_options)
                    except Exception:
                        pass
                    
                    try:
                        # 再尝试删除Deployment资源
                        job_client.apps_v1.delete_namespaced_deployment(job_name, job.get('namespace', 'g8s-host'), body=delete_options)
                    except Exception:
                        pass
                    
                    try:
                        # 最后尝试删除StatefulSet资源
                        job_client.apps_v1.delete_namespaced_stateful_set(job_name, job.get('namespace', 'g8s-host'), body=delete_options)
                    except Exception:
                        pass
                    
                    try:
                        # 尝试删除相关Service
                        service_name = f"g8s-host-svc-{job_name}"
                        if job_name.startswith("g8s-host-"):
                            # 如果是完整名称，提取基础名称
                            service_name = f"g8s-host-svc-{job_name[10:]}"
                        job_client.core_v1.delete_namespaced_service(service_name, job.get('namespace', 'g8s-host'), body=delete_options)
                    except Exception:
                        pass
            
            # 2. 移除资源池标签
            # 获取资源池的所有节点
            nodes = self.core_v1.list_node(
                label_selector=f"g8s.host/pool={pool_name}"
            )

            # 移除资源池标签
            for node in nodes.items:
                self._remove_node_label(node.metadata.name, "g8s.host/pool")

            return True

        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"delete pool {pool_name}")

    def add_nodes_to_pool(self, pool_name: str, node_names: List[str]) -> Dict[str, Any]:
        """添加节点到资源池"""
        try:
            # 验证所有节点是否存在
            self._validate_nodes_exist(node_names)
            
            success = []
            failed = []

            for node_name in node_names:
                try:
                    self._label_node(node_name, "g8s.host/pool", pool_name)
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
                    self._remove_node_label(node_name, "g8s.host/pool")
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
        node_names = [node.metadata.name for node in nodes]

        # 批量获取所有节点的已使用GPU数量
        node_used_gpus = self._get_all_nodes_used_gpu_count()

        # 获取节点上的GPU信息
        for node in nodes:
            # 获取节点的GPU数量（从节点标签或资源容量）
            gpu_count = self._get_node_gpu_count(node)
            gpu_total += gpu_count

            # 获取GPU类型
            gpu_type = self._get_node_gpu_type(node)
            if gpu_type:
                gpu_types.add(gpu_type)

            # 获取已使用的GPU数量（从批量统计结果中获取）
            gpu_used += node_used_gpus.get(node.metadata.name, 0)

        return {
            "name": pool_name,
            "description": f"{pool_name}资源池",
            "nodes": node_names,
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

    def _get_all_nodes_used_gpu_count(self) -> Dict[str, int]:
        """批量获取所有节点上已使用的GPU数量"""
        try:
            # 一次获取所有命名空间的所有Pod
            pods = self.core_v1.list_pod_for_all_namespaces()

            # 初始化节点GPU使用情况字典
            node_used_gpus = {}

            # 遍历所有Pod，统计每个节点的GPU使用情况
            for pod in pods.items:
                # 检查Pod是否正在运行
                if pod.status.phase not in ["Running", "Pending"]:
                    continue

                # 获取Pod所在的节点名称
                node_name = pod.spec.node_name
                if not node_name:
                    continue

                # 统计Pod请求的GPU数量
                pod_gpus = 0
                for container in pod.spec.containers:
                    if container.resources and container.resources.requests:
                        gpu_request = container.resources.requests.get("nvidia.com/gpu")
                        if gpu_request:
                            pod_gpus += int(gpu_request)

                # 更新节点的GPU使用情况
                if node_name in node_used_gpus:
                    node_used_gpus[node_name] += pod_gpus
                else:
                    node_used_gpus[node_name] = pod_gpus

            return node_used_gpus

        except ApiException:
            return {}

    def _get_used_gpu_count(self, node_name: str) -> int:
        """获取节点上已使用的GPU数量（兼容旧方法）"""
        try:
            # 调用新的批量统计方法
            node_used_gpus = self._get_all_nodes_used_gpu_count()
            return node_used_gpus.get(node_name, 0)
        except Exception:
            return 0

    def list_nodes(self, filters: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """列出所有节点，支持过滤"""
        try:
            # 构建标签选择器
            label_selector = None
            if filters:
                selector_parts = []
                if filters.get("pool"):
                    selector_parts.append(f"g8s.host/pool={filters['pool']}")
                if filters.get("gpu_type"):
                    selector_parts.append(f"nvidia.com/gpu-type={filters['gpu_type']}")
                if selector_parts:
                    label_selector = ",".join(selector_parts)

            # 获取节点列表
            nodes = self.core_v1.list_node(label_selector=label_selector)

            # 批量获取所有节点的GPU使用情况
            node_used_gpus = self._get_all_nodes_used_gpu_count()

            # 构建节点信息
            node_list = []
            for node in nodes.items:
                node_info = self._build_node_info(node, node_used_gpus)
                node_list.append(node_info)

            return node_list

        except ApiException as e:
            self.handle_api_exception(e, "list nodes")

    def get_node(self, node_name: str) -> Optional[Dict[str, Any]]:
        """获取特定节点详情"""
        try:
            node = self.core_v1.read_node(node_name)
            # 批量获取所有节点的GPU使用情况
            node_used_gpus = self._get_all_nodes_used_gpu_count()
            return self._build_node_info(node, node_used_gpus)
        except ApiException as e:
            if e.status == 404:
                return None
            self.handle_api_exception(e, f"get node {node_name}")

    def _build_node_info(self, node: Any, node_used_gpus: Dict[str, int] = None) -> Dict[str, Any]:
        """构建节点信息"""
        labels = node.metadata.labels or {}
        gpu_count = self._get_node_gpu_count(node)
        gpu_type = self._get_node_gpu_type(node)
        
        # 如果没有提供GPU使用情况，调用批量获取方法
        if node_used_gpus is None:
            node_used_gpus = self._get_all_nodes_used_gpu_count()
        
        # 从字典中获取已使用的GPU数量
        used_gpus = node_used_gpus.get(node.metadata.name, 0)

        return {
            "name": node.metadata.name,
            "status": "active" if self._is_node_ready(node) else "not_ready",
            "k8s_status": node.status.conditions[-1].type if node.status.conditions else "unknown",
            "labels": labels,
            "created_at": node.metadata.creation_timestamp.isoformat() if node.metadata.creation_timestamp else None,
            "last_updated_at": node.status.conditions[-1].last_transition_time.isoformat() if node.status.conditions else None,
            "resources": {
                "cpu_total": int(node.status.capacity.get("cpu", "0")),
                "cpu_used": 0,  # 需要从运行的Pod中统计
                "memory_total": node.status.capacity.get("memory", "0"),
                "memory_used": 0,  # 需要从运行的Pod中统计
                "gpu_total": gpu_count,
                "gpu_used": used_gpus,
                "gpu_free": gpu_count - used_gpus
            },
            "gpu_detail": [
                {
                    "gpuId": f"gpu-{i}",
                    "type": gpu_type,
                    "status": "used" if i < used_gpus else "free",
                    "utilization": 0,  # 需要从监控系统获取
                    "memoryUsage": "0Gi/0Gi"  # 需要从监控系统获取
                }
                for i in range(gpu_count)
            ],
            "running_jobs": [],  # 需要从运行的Pod中统计
            "gpu_types": [gpu_type] if gpu_type else []
        }

    def _is_node_ready(self, node: Any) -> bool:
        """检查节点是否就绪"""
        for condition in node.status.conditions:
            if condition.type == "Ready":
                return condition.status == "True"
        return False