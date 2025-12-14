from .. import DEFAULT_NAMESPACE
from .base_client import KubernetesClient
from kubernetes import client
from kubernetes.client.rest import ApiException
from typing import List, Dict, Any, Optional


class JobClient(KubernetesClient):
    """任务管理客户端"""

    def create_job(self, job: client.V1Job, namespace: str = DEFAULT_NAMESPACE) -> Dict[str, Any]:
        """创建Job"""
        try:
            # 确保命名空间存在
            self.ensure_namespace_exists(namespace)
            response = self.batch_v1.create_namespaced_job(namespace, job)
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "uid": response.metadata.uid
            }
        except ApiException as e:
            self.handle_api_exception(e, "create job")

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

    def list_jobs(self, namespace: str = DEFAULT_NAMESPACE,
                  labels: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """列出所有作业资源，包括Job、Deployment和StatefulSet"""
        try:
            label_selector = None
            if labels:
                label_selector = ",".join([f"{k}={v}" for k, v in labels.items()])

            all_jobs = []

            # 获取Job资源（Training任务）
            jobs = self.batch_v1.list_namespaced_job(
                namespace,
                label_selector=label_selector
            )
            all_jobs.extend([self._job_to_dict(job) for job in jobs.items])

            # 获取Deployment资源（Inference服务）
            deployments = self.apps_v1.list_namespaced_deployment(
                namespace,
                label_selector=label_selector
            )
            for deployment in deployments.items:
                all_jobs.append(self._deployment_to_dict(deployment))

            # 获取StatefulSet资源（Notebook服务）
            statefulsets = self.apps_v1.list_namespaced_stateful_set(
                namespace,
                label_selector=label_selector
            )
            for statefulset in statefulsets.items:
                all_jobs.append(self._statefulset_to_dict(statefulset))

            return all_jobs
        except ApiException as e:
            self.handle_api_exception(e, "list jobs")

    def delete_job(self, name: str, namespace: str = DEFAULT_NAMESPACE, force: bool = False) -> bool:
        """删除Job"""
        try:
            # 配置删除选项
            if force:
                # 强制删除：立即终止Pod并删除Job，不等待优雅终止
                delete_options = client.V1DeleteOptions(
                    propagation_policy="Foreground",
                    grace_period_seconds=0
                )
            else:
                # 正常删除：等待Pod优雅终止
                delete_options = client.V1DeleteOptions(propagation_policy="Background")
            
            self.batch_v1.delete_namespaced_job(name, namespace, body=delete_options)
            return True
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
                delete_options = client.V1DeleteOptions(propagation_policy="Background")
            
            self.apps_v1.delete_namespaced_deployment(name, namespace, body=delete_options)
            return True
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
                delete_options = client.V1DeleteOptions(propagation_policy="Background")
            
            self.apps_v1.delete_namespaced_stateful_set(name, namespace, body=delete_options)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"delete statefulset {name}")

    def delete_service(self, name: str, namespace: str = DEFAULT_NAMESPACE) -> bool:
        """删除Service"""
        try:
            delete_options = client.V1DeleteOptions(propagation_policy="Background")
            self.core_v1.delete_namespaced_service(name, namespace, body=delete_options)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"delete service {name}")

    def _job_to_dict(self, job: client.V1Job) -> Dict[str, Any]:
        """将Job对象转换为字典"""
        return {
            "name": job.metadata.name,
            "namespace": job.metadata.namespace,
            "labels": job.metadata.labels or {},
            "creation_timestamp": job.metadata.creation_timestamp.isoformat() if job.metadata.creation_timestamp else None,
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
            "status": {
                "active": ready_replicas,
                "succeeded": 0,
                "failed": replicas - ready_replicas
            }
        }

    def create_deployment(self, deployment: client.V1Deployment, namespace: str = DEFAULT_NAMESPACE) -> Dict[str, Any]:
        """创建Deployment"""
        try:
            # 确保命名空间存在
            self.ensure_namespace_exists(namespace)
            response = self.apps_v1.create_namespaced_deployment(namespace, deployment)
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "uid": response.metadata.uid
            }
        except ApiException as e:
            self.handle_api_exception(e, "create deployment")

    def create_service(self, service: client.V1Service, namespace: str = DEFAULT_NAMESPACE) -> Dict[str, Any]:
        """创建Service"""
        try:
            # 确保命名空间存在
            self.ensure_namespace_exists(namespace)
            response = self.core_v1.create_namespaced_service(namespace, service)
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "uid": response.metadata.uid
            }
        except ApiException as e:
            self.handle_api_exception(e, "create service")

    def create_hpa(self, hpa: client.V1HorizontalPodAutoscaler, namespace: str = DEFAULT_NAMESPACE) -> Dict[str, Any]:
        """创建HorizontalPodAutoscaler"""
        try:
            # 确保命名空间存在
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
        try:
            # 确保命名空间存在
            self.ensure_namespace_exists(namespace)
            response = self.apps_v1.create_namespaced_stateful_set(namespace, statefulset)
            return {
                "name": response.metadata.name,
                "namespace": response.metadata.namespace,
                "uid": response.metadata.uid
            }
        except ApiException as e:
            self.handle_api_exception(e, "create statefulset")

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

    def _pod_to_dict(self, pod: client.V1Pod) -> Dict[str, Any]:
        """将Pod对象转换为字典"""
        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "labels": pod.metadata.labels or {},
            "phase": pod.status.phase,
            "node_name": pod.spec.node_name if pod.spec else None,
            "creation_timestamp": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
        }

    def pause_job(self, name: str, namespace: str = DEFAULT_NAMESPACE) -> bool:
        """暂停Job"""
        try:
            # 获取当前Job
            job = self.batch_v1.read_namespaced_job(name, namespace)
            # 保存原始并行度和完成数
            job.metadata.annotations = job.metadata.annotations or {}
            job.metadata.annotations["gpuctl/original-parallelism"] = str(job.spec.parallelism or 1)
            job.metadata.annotations["gpuctl/original-completions"] = str(job.spec.completions or 1)
            # 设置并行度为0，暂停Job
            job.spec.parallelism = 0
            job.spec.completions = 0
            # 更新Job
            self.batch_v1.patch_namespaced_job(name, namespace, job)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"pause job {name}")

    def resume_job(self, name: str, namespace: str = DEFAULT_NAMESPACE) -> bool:
        """恢复Job"""
        try:
            # 获取当前Job
            job = self.batch_v1.read_namespaced_job(name, namespace)
            # 获取原始并行度和完成数
            original_parallelism = job.metadata.annotations.get("gpuctl/original-parallelism", "1")
            original_completions = job.metadata.annotations.get("gpuctl/original-completions", "1")
            # 恢复并行度和完成数
            job.spec.parallelism = int(original_parallelism)
            job.spec.completions = int(original_completions)
            # 移除注解
            if "gpuctl/original-parallelism" in job.metadata.annotations:
                del job.metadata.annotations["gpuctl/original-parallelism"]
            if "gpuctl/original-completions" in job.metadata.annotations:
                del job.metadata.annotations["gpuctl/original-completions"]
            # 更新Job
            self.batch_v1.patch_namespaced_job(name, namespace, job)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"resume job {name}")