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
        """获取Job信息"""
        try:
            job = self.batch_v1.read_namespaced_job(name, namespace)
            return self._job_to_dict(job)
        except ApiException as e:
            if e.status == 404:
                return None
            self.handle_api_exception(e, f"get job {name}")

    def list_jobs(self, namespace: str = DEFAULT_NAMESPACE,
                  labels: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """列出Jobs"""
        try:
            label_selector = None
            if labels:
                label_selector = ",".join([f"{k}={v}" for k, v in labels.items()])

            jobs = self.batch_v1.list_namespaced_job(
                namespace,
                label_selector=label_selector
            )
            return [self._job_to_dict(job) for job in jobs.items]
        except ApiException as e:
            self.handle_api_exception(e, "list jobs")

    def delete_job(self, name: str, namespace: str = DEFAULT_NAMESPACE) -> bool:
        """删除Job"""
        try:
            delete_options = client.V1DeleteOptions(propagation_policy="Background")
            self.batch_v1.delete_namespaced_job(name, namespace, body=delete_options)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            self.handle_api_exception(e, f"delete job {name}")

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