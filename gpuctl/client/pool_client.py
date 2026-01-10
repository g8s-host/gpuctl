from .base_client import KubernetesClient
from kubernetes.client.rest import ApiException
from typing import List, Dict, Any, Optional


class PoolClient(KubernetesClient):
    """Resource pool management client"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def list_pools(self) -> List[Dict[str, Any]]:
        """List all resource pools"""
        try:
            # Get all nodes
            nodes = self.core_v1.list_node()

            # Group by resource pool labels
            pool_nodes = {}
            for node in nodes.items:
                labels = node.metadata.labels or {}
                pool_name = labels.get("g8s.host/pool", "default")

                if pool_name not in pool_nodes:
                    pool_nodes[pool_name] = []
                pool_nodes[pool_name].append(node)

            # Build resource pool information
            pools = []
            for pool_name, nodes in pool_nodes.items():
                pool_info = self._build_pool_info(pool_name, nodes)
                pools.append(pool_info)

            return pools

        except ApiException as e:
            self.handle_api_exception(e, "list pools")

    def get_pool(self, pool_name: str) -> Optional[Dict[str, Any]]:
        """Get specific resource pool details"""
        try:
            # Get all nodes of this resource pool
            nodes = self.core_v1.list_node(
                label_selector=f"g8s.host/pool={pool_name}"
            )

            if not nodes.items:
                return None

            return self._build_pool_info(pool_name, nodes.items)

        except ApiException as e:
            self.handle_api_exception(e, f"get pool {pool_name}")

    def create_pool(self, pool_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create resource pool"""
        try:
            pool_name = pool_config["name"]
            node_names = pool_config.get("nodes", [])

            # Validate all nodes exist
            self._validate_nodes_exist(node_names)

            # Add resource pool labels to nodes
            for node_name in node_names:
                self._label_node(node_name, "g8s.host/pool", pool_name)

            return {
                "name": pool_name,
                "status": "created",
                "message": "Resource pool created successfully"
            }

        except ApiException as e:
            self.handle_api_exception(e, "create pool")

    def update_pool(self, pool_config: Dict[str, Any]) -> Dict[str, Any]:
        """Update resource pool"""
        try:
            pool_name = pool_config["name"]
            node_names = pool_config.get("nodes", [])

            existing_pool = self.get_pool(pool_name)
            if not existing_pool:
                raise ValueError(f"Pool {pool_name} does not exist")

            old_nodes = set(existing_pool.get("nodes", []))
            new_nodes = set(node_names)

            nodes_to_add = new_nodes - old_nodes
            nodes_to_remove = old_nodes - new_nodes

            if nodes_to_add:
                self._validate_nodes_exist(list(nodes_to_add))
                for node_name in nodes_to_add:
                    self._label_node(node_name, "g8s.host/pool", pool_name)

            if nodes_to_remove:
                for node_name in nodes_to_remove:
                    self._unlabel_node(node_name, "g8s.host/pool")

            return {
                "name": pool_name,
                "status": "updated",
                "message": "Resource pool updated successfully"
            }

        except ApiException as e:
            self.handle_api_exception(e, "update pool")

    def _validate_nodes_exist(self, node_names: List[str]) -> None:
        """Validate all nodes exist"""
        if not node_names:
            return

        # Get all existing nodes
        all_nodes = self.core_v1.list_node()
        existing_node_names = {node.metadata.name for node in all_nodes.items}

        # Check if any nodes don't exist
        invalid_nodes = [node for node in node_names if node not in existing_node_names]
        if invalid_nodes:
            raise ValueError(f"Nodes not found: {', '.join(invalid_nodes)}")

    def delete_pool(self, pool_name: str) -> bool:
        """Delete resource pool, including cascading deletion of associated jobs"""
        try:
            from gpuctl.client.job_client import JobClient
            from kubernetes.client import V1DeleteOptions
            
            # 1. Delete all associated jobs
            job_client = JobClient()
            # Get all jobs, then filter jobs belonging to this resource pool
            all_jobs = job_client.list_jobs()
            
            for job in all_jobs:
                # Check if job belongs to this resource pool
                job_pool = job.get('labels', {}).get('g8s.host/pool')
                if job_pool == pool_name:
                    # Build delete options
                    delete_options = V1DeleteOptions(propagation_policy="Foreground", grace_period_seconds=0)
                    
                    # Get job name
                    job_name = job['name']
                    
                    # Attempt to delete job resources
                    try:
                        # First try to delete Job resources
                        job_client.batch_v1.delete_namespaced_job(job_name, job.get('namespace', 'g8s-host'), body=delete_options)
                    except Exception:
                        pass
                    
                    try:
                        # Then try to delete Deployment resources
                        job_client.apps_v1.delete_namespaced_deployment(job_name, job.get('namespace', 'g8s-host'), body=delete_options)
                    except Exception:
                        pass
                    
                    try:
                        # Finally try to delete StatefulSet resources
                        job_client.apps_v1.delete_namespaced_stateful_set(job_name, job.get('namespace', 'g8s-host'), body=delete_options)
                    except Exception:
                        pass
                    
                    try:
                        # Attempt to delete related Service
                        # Use original job name to build service name
                        service_name = f"svc-{job_name}"
                        job_client.core_v1.delete_namespaced_service(service_name, job.get('namespace', 'default'), body=delete_options)
                    except Exception:
                        pass
            
            # 2. Remove resource pool labels
            # Get all nodes of resource pool
            nodes = self.core_v1.list_node(
                label_selector=f"g8s.host/pool={pool_name}"
            )

            # Remove resource pool labels
            for node in nodes.items:
                self._remove_node_label(node.metadata.name, "g8s.host/pool")

            return True

        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"delete pool {pool_name}")

    def add_nodes_to_pool(self, pool_name: str, node_names: List[str]) -> Dict[str, Any]:
        """Add nodes to resource pool"""
        try:
            # Validate all nodes exist
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
                "message": "Node addition completed"
            }

        except ApiException as e:
            self.handle_api_exception(e, f"add nodes to pool {pool_name}")

    def remove_nodes_from_pool(self, pool_name: str, node_names: List[str]) -> Dict[str, Any]:
        """Remove nodes from resource pool"""
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
                "message": "Node removal completed"
            }

        except ApiException as e:
            self.handle_api_exception(e, f"remove nodes from pool {pool_name}")

    def _build_pool_info(self, pool_name: str, nodes: List[Any]) -> Dict[str, Any]:
        """Build resource pool information"""
        gpu_total = 0
        gpu_used = 0
        gpu_types = set()
        node_names = [node.metadata.name for node in nodes]

        # Batch get used GPU count for all nodes
        node_used_gpus = self._get_all_nodes_used_gpu_count()

        # Get GPU info on nodes
        for node in nodes:
            # Get node GPU count (from node labels or resource capacity)
            gpu_count = self._get_node_gpu_count(node)
            gpu_total += gpu_count

            # Get GPU type
            gpu_type = self._get_node_gpu_type(node)
            if gpu_type:
                gpu_types.add(gpu_type)

            # Get used GPU count (from batch statistics result)
            gpu_used += node_used_gpus.get(node.metadata.name, 0)

        return {
            "name": pool_name,
            "description": f"{pool_name} resource pool",
            "nodes": node_names,
            "gpu_total": gpu_total,
            "gpu_used": gpu_used,
            "gpu_free": gpu_total - gpu_used,
            "gpu_types": list(gpu_types),
            "status": "active"
        }

    def _label_node(self, node_name: str, key: str, value: str) -> None:
        """Add label to node"""
        patch = {
            "metadata": {
                "labels": {
                    key: value
                }
            }
        }
        self.core_v1.patch_node(node_name, patch)

    def _unlabel_node(self, node_name: str, key: str) -> None:
        """Remove label from node"""
        self._remove_node_label(node_name, key)

    def _remove_node_label(self, node_name: str, key: str) -> None:
        """Remove node label"""
        patch = {
            "metadata": {
                "labels": {
                    key: None
                }
            }
        }
        self.core_v1.patch_node(node_name, patch)

    def _get_node_gpu_count(self, node) -> int:
        """Get node GPU count"""
        # Get GPU count from node capacity
        if node.status and node.status.capacity:
            gpu_resource = node.status.capacity.get("nvidia.com/gpu")
            if gpu_resource:
                return int(gpu_resource)
        return 0

    def _get_node_gpu_type(self, node) -> Optional[str]:
        """Get node GPU type"""
        labels = node.metadata.labels or {}
        return labels.get("nvidia.com/gpu-type")

    def _get_all_nodes_used_gpu_count(self) -> Dict[str, int]:
        """Batch get all nodes used GPU count"""
        try:
            # Get all Pods across all namespaces once
            pods = self.core_v1.list_pod_for_all_namespaces()

            # Initialize node GPU usage dictionary
            node_used_gpus = {}

            # Iterate all Pods, count GPU usage for each node
            for pod in pods.items:
                # Check if Pod is running
                if pod.status.phase not in ["Running", "Pending"]:
                    continue

                # Get Pod's node name
                node_name = pod.spec.node_name
                if not node_name:
                    continue

                # Count Pod requested GPU count
                pod_gpus = 0
                for container in pod.spec.containers:
                    if container.resources and container.resources.requests:
                        gpu_request = container.resources.requests.get("nvidia.com/gpu")
                        if gpu_request:
                            pod_gpus += int(gpu_request)

                # Update node GPU usage
                if node_name in node_used_gpus:
                    node_used_gpus[node_name] += pod_gpus
                else:
                    node_used_gpus[node_name] = pod_gpus

            return node_used_gpus

        except ApiException:
            return {}

    def _get_used_gpu_count(self, node_name: str) -> int:
        """Get node used GPU count (legacy method for compatibility)"""
        try:
            # Call new batch statistics method
            node_used_gpus = self._get_all_nodes_used_gpu_count()
            return node_used_gpus.get(node_name, 0)
        except Exception:
            return 0

    def list_nodes(self, filters: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """List all nodes with filtering support"""
        try:
            # Build label selector
            label_selector = None
            if filters:
                selector_parts = []
                if filters.get("pool"):
                    selector_parts.append(f"g8s.host/pool={filters['pool']}")
                if filters.get("gpu_type"):
                    selector_parts.append(f"nvidia.com/gpu-type={filters['gpu_type']}")
                if selector_parts:
                    label_selector = ",".join(selector_parts)

            # Get node list
            nodes = self.core_v1.list_node(label_selector=label_selector)

            # Batch get all nodes GPU usage
            node_used_gpus = self._get_all_nodes_used_gpu_count()

            # Build node information
            node_list = []
            for node in nodes.items:
                node_info = self._build_node_info(node, node_used_gpus)
                node_list.append(node_info)

            return node_list

        except ApiException as e:
            self.handle_api_exception(e, "list nodes")

    def get_node(self, node_name: str) -> Optional[Dict[str, Any]]:
        """Get specific node details"""
        try:
            node = self.core_v1.read_node(node_name)
            # Batch get all nodes GPU usage
            node_used_gpus = self._get_all_nodes_used_gpu_count()
            return self._build_node_info(node, node_used_gpus)
        except ApiException as e:
            if e.status == 404:
                return None
            self.handle_api_exception(e, f"get node {node_name}")

    def _build_node_info(self, node: Any, node_used_gpus: Dict[str, int] = None) -> Dict[str, Any]:
        """Build node information"""
        labels = node.metadata.labels or {}
        gpu_count = self._get_node_gpu_count(node)
        gpu_type = self._get_node_gpu_type(node)
        
        # If GPU usage not provided, call batch fetch method
        if node_used_gpus is None:
            node_used_gpus = self._get_all_nodes_used_gpu_count()
        
        # Get used GPU count from dictionary
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
                "cpu_used": 0,
                "memory_total": node.status.capacity.get("memory", "0"),
                "memory_used": 0,
                "gpu_total": gpu_count,
                "gpu_used": used_gpus,
                "gpu_free": gpu_count - used_gpus
            },
            "gpu_detail": [
                {
                    "gpuId": f"gpu-{i}",
                    "type": gpu_type,
                    "status": "used" if i < used_gpus else "free",
                    "utilization": 0,
                    "memoryUsage": "0Gi/0Gi"
                }
                for i in range(gpu_count)
            ],
            "running_jobs": [],
            "gpu_types": [gpu_type] if gpu_type else []
        }

    def _is_node_ready(self, node: Any) -> bool:
        """Check if node is ready"""
        for condition in node.status.conditions:
            if condition.type == "Ready":
                return condition.status == "True"
        return False