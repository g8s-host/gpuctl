from .. import DEFAULT_NAMESPACE
from .base_client import KubernetesClient
from .quota_client import QuotaClient
from kubernetes import client
from kubernetes.client.rest import ApiException
from typing import List, Dict, Any, Optional


class JobClient(KubernetesClient):
    """任务管理客户端"""

    def _validate_namespace_quota(self, namespace: str) -> bool:
        """验证namespace是否已配置quota"""
        if namespace == "default":
            return True
        
        quota_client = QuotaClient.get_instance()
        if quota_client.namespace_has_quota(namespace):
            return True
        return False

    def create_job(self, job: client.V1Job, namespace: str = DEFAULT_NAMESPACE) -> Dict[str, Any]:
        """创建Job"""
        if not self._validate_namespace_quota(namespace):
            raise ValueError(
                f"Namespace '{namespace}' has no quota configured. "
                f"Please create a quota configuration first using 'gpuctl create -f <quota.yaml>'"
            )
        
        try:
            self.ensure_namespace_exists(namespace)
            response = self.batch_v1.create_namespaced_job(namespace, job)
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "uid": response.metadata.uid
            }
        except ApiException as e:
            self.handle_api_exception(e, "create job")

    def update_job(self, name: str, namespace: str, job: client.V1Job) -> Dict[str, Any]:
        """更新Job"""
        try:
            job.metadata.resource_version = None
            response = self.batch_v1.replace_namespaced_job(name, namespace, job)
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "uid": response.metadata.uid
            }
        except ApiException as e:
            self.handle_api_exception(e, f"update job {name}")

    def get_job(self, name: str, namespace: str = DEFAULT_NAMESPACE) -> Optional[Dict[str, Any]]:
        """获取作业资源信息，包括Job、Deployment和StatefulSet"""
        try:
            # 先尝试获取Job资源
            job = self.batch_v1.read_namespaced_job(name, namespace)
            return self._job_to_dict(job)
        except ApiException as e:
            if e.status != 404:
                self.handle_api_exception(e, f"get job {name}")

        try:
            # 再尝试获取Deployment资源
            deployment = self.apps_v1.read_namespaced_deployment(name, namespace)
            return self._deployment_to_dict(deployment)
        except ApiException as e:
            if e.status != 404:
                self.handle_api_exception(e, f"get deployment {name}")

        try:
            # 最后尝试获取StatefulSet资源
            statefulset = self.apps_v1.read_namespaced_stateful_set(name, namespace)
            return self._statefulset_to_dict(statefulset)
        except ApiException as e:
            if e.status != 404:
                self.handle_api_exception(e, f"get statefulset {name}")

        # 所有类型都未找到
        return None

    def list_jobs(self, namespace: str = None,
                  labels: Dict[str, str] = None, include_pods: bool = False) -> List[Dict[str, Any]]:
        """列出所有作业资源，包括Job、Deployment和StatefulSet"""
        try:
            all_jobs = []

            # 如果没有指定labels，添加默认过滤器，只返回gpuctl创建的资源
            # 所有gpuctl创建的资源都会带有g8s.host/job-type标签
            if not labels and not include_pods:
                # 当include_pods=True时，不要使用gpuctl_filter，因为Pod资源可能没有g8s.host/job-type标签
                use_gpuctl_filter = True
            else:
                use_gpuctl_filter = False

            if namespace:
                return self._list_jobs_in_namespace(namespace, labels, include_pods, use_gpuctl_filter)
            else:
                all_namespaces = self._get_all_gpuctl_namespaces()
                for ns in all_namespaces:
                    ns_jobs = self._list_jobs_in_namespace(ns, labels, include_pods, use_gpuctl_filter)
                    all_jobs.extend(ns_jobs)
                return all_jobs
        except ApiException as e:
            self.handle_api_exception(e, "list jobs")

    def _get_all_gpuctl_namespaces(self) -> List[str]:
        """获取所有gpuctl管理的namespace，包括default和带有g8s.host标签的namespace"""
        namespaces = set()
        
        # 始终包含default命名空间
        namespaces.add("default")
        
        try:
            # 获取带有g8s.host/namespace标签的命名空间
            labeled_ns = self.core_v1.list_namespace(
                label_selector="g8s.host/namespace=true"
            )
            for ns in labeled_ns.items:
                namespaces.add(ns.metadata.name)
            
            # 扫描所有命名空间查找带有g8s.host标签的资源
            all_ns = self.core_v1.list_namespace()
            for ns in all_ns.items:
                ns_name = ns.metadata.name
                
                # 检查该命名空间下的job
                try:
                    jobs = self.batch_v1.list_namespaced_job(ns_name, label_selector="g8s.host/")
                    if jobs.items:
                        namespaces.add(ns_name)
                        continue
                except ApiException:
                    pass
                
                # 检查该命名空间下的deployment
                try:
                    deployments = self.apps_v1.list_namespaced_deployment(ns_name, label_selector="g8s.host/")
                    if deployments.items:
                        namespaces.add(ns_name)
                        continue
                except ApiException:
                    pass
                
                # 检查该命名空间下的statefulset
                try:
                    statefulsets = self.apps_v1.list_namespaced_stateful_set(ns_name, label_selector="g8s.host/")
                    if statefulsets.items:
                        namespaces.add(ns_name)
                except ApiException:
                    pass
        
        except ApiException as e:
            self.handle_api_exception(e, "list namespaces")
        
        return list(namespaces)

    def _list_jobs_in_namespace(self, namespace: str, labels: Dict[str, str] = None, include_pods: bool = False, use_gpuctl_filter: bool = False) -> List[Dict[str, Any]]:
        """在指定namespace中列出作业资源"""
        # 构建标签选择器
        selector_parts = []
        
        # 如果需要过滤gpuctl创建的资源，添加g8s.host/job-type标签存在性检查
        if use_gpuctl_filter:
            selector_parts.append("g8s.host/job-type")
        
        # 添加用户提供的标签选择器
        if labels:
            for k, v in labels.items():
                selector_parts.append(f"{k}={v}")
        
        # 组合所有标签选择器，使用逗号分隔（AND关系）
        label_selector = ",".join(selector_parts) if selector_parts else None
        
        jobs = []

        if include_pods:
            try:
                pods = self.core_v1.list_namespaced_pod(namespace, label_selector=label_selector)
                for pod in pods.items:
                    try:
                        pod_dict = self._pod_to_dict(pod)
                        jobs.append(pod_dict)
                    except Exception as e:
                        print(f"Warning: Failed to process pod {pod.metadata.name}: {e}")
            except ApiException as e:
                if e.status != 404:
                    raise
        else:
            try:
                job_list = self.batch_v1.list_namespaced_job(namespace, label_selector=label_selector)
                jobs.extend([self._job_to_dict(job) for job in job_list.items])
            except ApiException as e:
                if e.status != 404:
                    raise

            try:
                deployment_list = self.apps_v1.list_namespaced_deployment(namespace, label_selector=label_selector)
                jobs.extend([self._deployment_to_dict(deployment) for deployment in deployment_list.items])
            except ApiException as e:
                if e.status != 404:
                    raise

            try:
                statefulset_list = self.apps_v1.list_namespaced_stateful_set(namespace, label_selector=label_selector)
                jobs.extend([self._statefulset_to_dict(statefulset) for statefulset in statefulset_list.items])
            except ApiException as e:
                if e.status != 404:
                    raise

        return jobs







    def _wait_for_resource_deletion(self, check_func, name: str, resource_type: str, timeout: int = 600, interval: float = 0.3) -> bool:
        """等待资源删除完成
        
        Args:
            check_func: 检查资源是否存在的函数
            name: 资源名称
            resource_type: 资源类型
            timeout: 超时时间（秒）
            interval: 检查间隔（秒）
            
        Returns:
            bool: 资源是否在超时前被删除
        """
        import time
        import sys
        
        start_time = time.time()
        dot_count = 0
        
        while time.time() - start_time < timeout:
            if not check_func(name):
                return True
            
            dot_count = (dot_count % 3) + 1
            dots = "." * dot_count
            print(f"\r{dots:<3}", end="", flush=True)
            time.sleep(interval)
        
        print(f"\r⚠️  超时：{resource_type} {name} 在 {timeout} 秒内未被删除")
        return False
    
    def _is_job_exists(self, name: str, namespace: str = DEFAULT_NAMESPACE) -> bool:
        """检查Job资源是否存在"""
        try:
            self.batch_v1.read_namespaced_job(name, namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"check job existence {name}")
            return False
    
    def _is_deployment_exists(self, name: str, namespace: str = DEFAULT_NAMESPACE) -> bool:
        """检查Deployment资源是否存在"""
        try:
            self.apps_v1.read_namespaced_deployment(name, namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"check deployment existence {name}")
            return False
    
    def _is_statefulset_exists(self, name: str, namespace: str = DEFAULT_NAMESPACE) -> bool:
        """检查StatefulSet资源是否存在"""
        try:
            self.apps_v1.read_namespaced_stateful_set(name, namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"check statefulset existence {name}")
            return False
    
    def _is_service_exists(self, name: str, namespace: str = DEFAULT_NAMESPACE) -> bool:
        """检查Service资源是否存在"""
        try:
            self.core_v1.read_namespaced_service(name, namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"check service existence {name}")
            return False
    
    def delete_job(self, name: str, namespace: str = DEFAULT_NAMESPACE, force: bool = False) -> bool:
        """删除作业资源，包括Job、Deployment、StatefulSet和相关Service"""
        try:
            # 配置删除选项
            if force:
                delete_options = client.V1DeleteOptions(
                    propagation_policy="Foreground",
                    grace_period_seconds=0
                )
            else:
                delete_options = client.V1DeleteOptions(propagation_policy="Foreground")  # 改为Foreground策略，等待资源删除完成
            
            deleted = False
            
            # 1. 尝试删除Job资源
            try:
                self.batch_v1.delete_namespaced_job(name, namespace, body=delete_options)
                # 等待Job删除完成
                self._wait_for_resource_deletion(lambda n: self._is_job_exists(n, namespace), name, "Job")
                deleted = True
            except ApiException as e:
                if e.status != 404:
                    self.handle_api_exception(e, f"delete job {name}")
            
            # 2. 尝试删除Deployment资源
            try:
                self.apps_v1.delete_namespaced_deployment(name, namespace, body=delete_options)
                # 等待Deployment删除完成
                self._wait_for_resource_deletion(lambda n: self._is_deployment_exists(n, namespace), name, "Deployment")
                deleted = True
            except ApiException as e:
                if e.status != 404:
                    self.handle_api_exception(e, f"delete deployment {name}")
            
            # 3. 尝试删除StatefulSet资源
            try:
                self.apps_v1.delete_namespaced_stateful_set(name, namespace, body=delete_options)
                # 等待StatefulSet删除完成
                self._wait_for_resource_deletion(lambda n: self._is_statefulset_exists(n, namespace), name, "StatefulSet")
                deleted = True
            except ApiException as e:
                if e.status != 404:
                    self.handle_api_exception(e, f"delete statefulset {name}")
            
            # 4. 尝试删除相关Service（无论前面是否成功删除，都尝试删除Service）
            try:
                self.core_v1.delete_namespaced_service(name, namespace, body=delete_options)
                # 等待Service删除完成
                self._wait_for_resource_deletion(lambda n: self._is_service_exists(n, namespace), name, "Service")
            except ApiException as e:
                if e.status != 404:
                    self.handle_api_exception(e, f"delete service {name}")
            
            return deleted
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"delete job {name}")
    
    def delete_deployment(self, name: str, namespace: str = DEFAULT_NAMESPACE, force: bool = False) -> bool:
        """删除Deployment"""
        try:
            # 配置删除选项
            if force:
                # 强制删除：立即终止Pod并删除Deployment，不等待优雅终止
                delete_options = client.V1DeleteOptions(
                    propagation_policy="Foreground",
                    grace_period_seconds=0
                )
            else:
                # 正常删除：等待Pod优雅终止
                delete_options = client.V1DeleteOptions(propagation_policy="Foreground")  # 改为Foreground策略，等待资源删除完成
            
            self.apps_v1.delete_namespaced_deployment(name, namespace, body=delete_options)
            # 等待Deployment删除完成
            return self._wait_for_resource_deletion(lambda n: self._is_deployment_exists(n, namespace), name, "Deployment")
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"delete deployment {name}")
    
    def delete_statefulset(self, name: str, namespace: str = DEFAULT_NAMESPACE, force: bool = False) -> bool:
        """删除StatefulSet"""
        try:
            # 配置删除选项
            if force:
                # 强制删除：立即终止Pod并删除StatefulSet，不等待优雅终止
                delete_options = client.V1DeleteOptions(
                    propagation_policy="Foreground",
                    grace_period_seconds=0
                )
            else:
                # 正常删除：等待Pod优雅终止
                delete_options = client.V1DeleteOptions(propagation_policy="Foreground")  # 改为Foreground策略，等待资源删除完成
            
            self.apps_v1.delete_namespaced_stateful_set(name, namespace, body=delete_options)
            # 等待StatefulSet删除完成
            return self._wait_for_resource_deletion(lambda n: self._is_statefulset_exists(n, namespace), name, "StatefulSet")
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"delete statefulset {name}")
    
    def delete_service(self, name: str, namespace: str = DEFAULT_NAMESPACE) -> bool:
        """删除Service"""
        try:
            delete_options = client.V1DeleteOptions(propagation_policy="Foreground")  # 改为Foreground策略，等待资源删除完成
            self.core_v1.delete_namespaced_service(name, namespace, body=delete_options)
            # 等待Service删除完成
            return self._wait_for_resource_deletion(lambda n: self._is_service_exists(n, namespace), name, "Service")
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"delete service {name}")

    def delete_pod(self, name: str, namespace: str = DEFAULT_NAMESPACE, force: bool = False) -> bool:
        """删除Pod"""
        try:
            # 配置删除选项
            if force:
                delete_options = client.V1DeleteOptions(
                    propagation_policy="Foreground",
                    grace_period_seconds=0
                )
            else:
                delete_options = client.V1DeleteOptions(propagation_policy="Foreground")
            
            self.core_v1.delete_namespaced_pod(name, namespace, body=delete_options)
            # 等待Pod删除完成
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"delete pod {name}")

    def _is_pod_exists(self, name: str, namespace: str = DEFAULT_NAMESPACE) -> bool:
        """检查Pod资源是否存在"""
        try:
            self.core_v1.read_namespaced_pod(name, namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"check pod existence {name}")
            return False

    def _pod_to_dict(self, pod: client.V1Pod) -> Dict[str, Any]:
        """将Pod对象转换为字典格式"""
        try:
            job_type = "compute"
            labels = pod.metadata.labels or {}
            pod_name = pod.metadata.name
            
            # 优先使用标签来判断作业类型
            if "g8s.host/job-type" in labels:
                job_type = labels["g8s.host/job-type"]
            elif "job-name" in labels:
                job_type = "training"
            # 保持对旧格式Pod名称的支持，保持向后兼容
            elif "g8s-host-inference-" in pod_name:
                job_type = "inference"
            elif "g8s-host-compute-" in pod_name:
                job_type = "compute"
            elif "g8s-host-notebook-" in pod_name:
                job_type = "notebook"
            else:
                # 对于新格式的没有前缀的Pod，默认使用'inference'类型
                job_type = "inference"
            
            active = 0
            succeeded = 0
            failed = 0
            pod_phase = "Unknown"
            pod_conditions = []
            container_statuses = []
            
            if pod.status:
                pod_phase = pod.status.phase or "Unknown"
                
                if pod.status.phase == "Running":
                    active = 1
                elif pod.status.phase == "Succeeded":
                    succeeded = 1
                elif pod.status.phase == "Failed":
                    failed = 1
                
                pod_conditions = pod.status.conditions or []
                container_statuses = pod.status.container_statuses or []
            
            pod_dict = {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "labels": labels.copy(),
                "creation_timestamp": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
                "start_time": pod.status.start_time.isoformat() if pod.status and pod.status.start_time else (pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None),
                "completion_time": None,
                "status": {
                    "active": active,
                    "succeeded": succeeded,
                    "failed": failed,
                    "phase": pod_phase,
                    "conditions": pod_conditions,
                    "container_statuses": container_statuses
                }
            }
            
            if "g8s.host/job-type" not in pod_dict["labels"]:
                pod_dict["labels"]["g8s.host/job-type"] = job_type
            
            return pod_dict
        except Exception as e:
            return {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "labels": pod.metadata.labels or {},
                "creation_timestamp": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
                "start_time": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
                "completion_time": None,
                "status": {
                    "active": 0,
                    "succeeded": 0,
                    "failed": 0
                }
            }

    def _job_to_dict(self, job: client.V1Job) -> Dict[str, Any]:
        """将Job对象转换为字典"""
        return {
            "name": job.metadata.name,
            "namespace": job.metadata.namespace,
            "labels": job.metadata.labels or {},
            "creation_timestamp": job.metadata.creation_timestamp.isoformat() if job.metadata.creation_timestamp else None,
            "start_time": job.status.start_time.isoformat() if job.status and job.status.start_time else None,
            "completion_time": job.status.completion_time.isoformat() if job.status and job.status.completion_time else None,
            "status": {
                "active": job.status.active or 0,
                "succeeded": job.status.succeeded or 0,
                "failed": job.status.failed or 0
            }
        }

    def _deployment_to_dict(self, deployment: client.V1Deployment) -> Dict[str, Any]:
        """将Deployment对象转换为字典"""
        return {
            "name": deployment.metadata.name,
            "namespace": deployment.metadata.namespace,
            "labels": deployment.metadata.labels or {},
            "creation_timestamp": deployment.metadata.creation_timestamp.isoformat() if deployment.metadata.creation_timestamp else None,
            "start_time": deployment.metadata.creation_timestamp.isoformat() if deployment.metadata.creation_timestamp else None,
            "completion_time": None,
            "status": {
                "active": deployment.status.ready_replicas or 0,
                "succeeded": 0,
                "failed": deployment.status.unavailable_replicas or 0
            }
        }



    def _statefulset_to_dict(self, statefulset: client.V1StatefulSet) -> Dict[str, Any]:
        """将StatefulSet对象转换为字典"""
        replicas = statefulset.status.replicas or 0
        ready_replicas = statefulset.status.ready_replicas or 0
        return {
            "name": statefulset.metadata.name,
            "namespace": statefulset.metadata.namespace,
            "labels": statefulset.metadata.labels or {},
            "creation_timestamp": statefulset.metadata.creation_timestamp.isoformat() if statefulset.metadata.creation_timestamp else None,
            "start_time": statefulset.metadata.creation_timestamp.isoformat() if statefulset.metadata.creation_timestamp else None,
            "completion_time": None,
            "status": {
                "active": ready_replicas,
                "succeeded": 0,
                "failed": replicas - ready_replicas
            }
        }

    def create_deployment(self, deployment: client.V1Deployment, namespace: str = DEFAULT_NAMESPACE) -> Dict[str, Any]:
        """创建Deployment"""
        if not self._validate_namespace_quota(namespace):
            raise ValueError(
                f"Namespace '{namespace}' has no quota configured. "
                f"Please create a quota configuration first using 'gpuctl create -f <quota.yaml>'"
            )
        
        try:
            self.ensure_namespace_exists(namespace)
            response = self.apps_v1.create_namespaced_deployment(namespace, deployment)
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "uid": response.metadata.uid
            }
        except ApiException as e:
            self.handle_api_exception(e, "create deployment")

    def update_deployment(self, name: str, namespace: str, deployment: client.V1Deployment) -> Dict[str, Any]:
        """更新Deployment"""
        try:
            deployment.metadata.resource_version = None
            response = self.apps_v1.replace_namespaced_deployment(name, namespace, deployment)
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "uid": response.metadata.uid
            }
        except ApiException as e:
            self.handle_api_exception(e, f"update deployment {name}")

    def create_service(self, service: client.V1Service, namespace: str = DEFAULT_NAMESPACE) -> Dict[str, Any]:
        """创建Service"""
        if not self._validate_namespace_quota(namespace):
            raise ValueError(
                f"Namespace '{namespace}' has no quota configured. "
                f"Please create a quota configuration first using 'gpuctl create -f <quota.yaml>'"
            )
        
        try:
            self.ensure_namespace_exists(namespace)
            response = self.core_v1.create_namespaced_service(namespace, service)
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "uid": response.metadata.uid
            }
        except ApiException as e:
            self.handle_api_exception(e, "create service")

    def update_service(self, name: str, namespace: str, service: client.V1Service) -> Dict[str, Any]:
        """更新Service"""
        try:
            service.metadata.resource_version = None
            response = self.core_v1.replace_namespaced_service(name, namespace, service)
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "uid": response.metadata.uid
            }
        except ApiException as e:
            self.handle_api_exception(e, f"update service {name}")

    def create_hpa(self, hpa: client.V1HorizontalPodAutoscaler, namespace: str = DEFAULT_NAMESPACE) -> Dict[str, Any]:
        """创建HorizontalPodAutoscaler"""
        if not self._validate_namespace_quota(namespace):
            raise ValueError(
                f"Namespace '{namespace}' has no quota configured. "
                f"Please create a quota configuration first using 'gpuctl create -f <quota.yaml>'"
            )
        
        try:
            self.ensure_namespace_exists(namespace)
            response = self.autoscaling_v1.create_namespaced_horizontal_pod_autoscaler(namespace, hpa)
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "uid": response.metadata.uid
            }
        except ApiException as e:
            self.handle_api_exception(e, "create hpa")

    def create_statefulset(self, statefulset: client.V1StatefulSet, namespace: str = DEFAULT_NAMESPACE) -> Dict[str, Any]:
        """创建StatefulSet"""
        if not self._validate_namespace_quota(namespace):
            raise ValueError(
                f"Namespace '{namespace}' has no quota configured. "
                f"Please create a quota configuration first using 'gpuctl create -f <quota.yaml>'"
            )
        
        try:
            self.ensure_namespace_exists(namespace)
            response = self.apps_v1.create_namespaced_stateful_set(namespace, statefulset)
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "uid": response.metadata.uid
            }
        except ApiException as e:
            self.handle_api_exception(e, "create statefulset")

    def update_statefulset(self, name: str, namespace: str, statefulset: client.V1StatefulSet) -> Dict[str, Any]:
        """更新StatefulSet"""
        try:
            statefulset.metadata.resource_version = None
            response = self.apps_v1.replace_namespaced_stateful_set(name, namespace, statefulset)
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "uid": response.metadata.uid
            }
        except ApiException as e:
            self.handle_api_exception(e, f"update statefulset {name}")

    def list_pods(self, namespace: str = DEFAULT_NAMESPACE, labels: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """列出Pods"""
        try:
            label_selector = None
            if labels:
                label_selector = ",".join([f"{k}={v}" for k, v in labels.items()])

            pods = self.core_v1.list_namespaced_pod(
                namespace,
                label_selector=label_selector
            )
            return [self._pod_to_dict(pod) for pod in pods.items]
        except ApiException as e:
            self.handle_api_exception(e, "list pods")



