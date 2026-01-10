from .. import DEFAULT_NAMESPACE
from .base_client import KubernetesClient
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from typing import List, Optional
import time


class LogClient(KubernetesClient):
    """日志管理客户端"""
    
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
    
    def _get_job_pods(self, job_name: str, namespace: str = DEFAULT_NAMESPACE):
        """获取Job关联的所有Pod"""
        def _try_get_in_namespace(ns: str):
            """在指定命名空间中尝试获取Job关联的Pod"""
            # 首先尝试直接将job_name作为Pod名称返回
            try:
                pod = self.core_v1.read_namespaced_pod(job_name, ns)
                return [pod]
            except ApiException as e:
                if e.status != 404:
                    self.handle_api_exception(e, f"check pod {job_name}")
            
            # 简化标签选择器，只使用基础名称和标准标签
            base_name = job_name
            if "-" in job_name:
                # 如果是Pod名称，去掉后缀获取基础名称
                parts = job_name.split("-")
                if len(parts) >= 3:
                    # 格式：base-name-deployment-hash-pod-suffix
                    base_name = "-".join(parts[:-2])
            
            selectors = [
                f"job-name={job_name}",
                f"app={job_name}",
                f"job-name={base_name}",
                f"app={base_name}",
                f"app.kubernetes.io/name={base_name}",
                f"app.kubernetes.io/instance={base_name}"
            ]
            
            for selector in selectors:
                try:
                    pods = self.core_v1.list_namespaced_pod(
                        namespace=ns,
                        label_selector=selector
                    )
                    if pods.items:
                        return pods.items
                except ApiException as e:
                    if e.status != 404:
                        print(f"Warning: Failed to get pods with selector {selector}: {e}")
            
            # 当前命名空间中未找到pods
            return []
        
        # 1. 优先在指定命名空间中查找
        pods = _try_get_in_namespace(namespace)
        if pods:
            return pods
        
        # 2. 如果在指定命名空间中未找到，搜索所有gpuctl管理的命名空间
        all_namespaces = self._get_all_gpuctl_namespaces()
        for ns in all_namespaces:
            if ns == namespace:
                continue  # 跳过已经检查过的命名空间
            
            pods = _try_get_in_namespace(ns)
            if pods:
                return pods
        
        # 所有命名空间中都未找到pods
        return []

    def get_job_logs(self, job_name: str, namespace: str = DEFAULT_NAMESPACE,
                     tail: int = 100, pod_name: Optional[str] = None) -> List[str]:
        """获取任务日志"""
        def _try_get_logs_in_namespace(ns: str, pod: Optional[str] = None):
            """在指定命名空间中尝试获取日志"""
            try:
                # 如果未指定Pod，先尝试直接将job_name作为Pod名称获取
                if not pod:
                    try:
                        # 尝试直接将job_name作为Pod名称获取日志
                        log_content = self.core_v1.read_namespaced_pod_log(
                            name=job_name,
                            namespace=ns,
                            tail_lines=tail,
                            timestamps=True
                        )
                        # 按行分割日志
                        logs = log_content.strip().split('\n') if log_content else []
                        return logs
                    except ApiException as e:
                        if e.status != 404:
                            self.handle_api_exception(e, f"get logs for pod {job_name}")
                        # 如果直接获取失败，尝试找到Job关联的Pod
                        pods = self._get_job_pods(job_name, ns)
                        if not pods:
                            return None
                        pod = pods[0].metadata.name

                # 获取Pod日志
                log_content = self.core_v1.read_namespaced_pod_log(
                    name=pod,
                    namespace=ns,
                    tail_lines=tail,
                    timestamps=True
                )

                # 按行分割日志
                logs = log_content.strip().split('\n') if log_content else []
                return logs
            except ApiException as e:
                # 只忽略404错误，其他错误向上抛出
                if e.status != 404:
                    raise
                return None
        
        try:
            # 1. 优先在指定命名空间中查找
            logs = _try_get_logs_in_namespace(namespace, pod_name)
            if logs is not None:
                return logs
            
            # 2. 如果在指定命名空间中未找到，搜索所有gpuctl管理的命名空间
            all_namespaces = self._get_all_gpuctl_namespaces()
            for ns in all_namespaces:
                if ns == namespace:
                    continue  # 跳过已经检查过的命名空间
                
                logs = _try_get_logs_in_namespace(ns, pod_name)
                if logs is not None:
                    return logs
            
            # 所有命名空间中都未找到日志
            return ["No pods found for this job"]

        except ApiException as e:
            self.handle_api_exception(e, f"get logs for job {job_name}")

    def stream_job_logs(self, job_name: str, namespace: str = DEFAULT_NAMESPACE,
                        pod_name: Optional[str] = None):
        """流式获取任务日志（生成器）"""
        def _try_stream_in_namespace(ns: str, pod: Optional[str] = None):
            """在指定命名空间中尝试流式获取日志"""
            try:
                target_pod = pod
                # 如果未指定Pod，先尝试直接将job_name作为Pod名称
                if not target_pod:
                    try:
                        # 尝试直接将job_name作为Pod名称获取
                        # 先检查Pod是否存在
                        self.core_v1.read_namespaced_pod(job_name, ns)
                        target_pod = job_name
                    except ApiException as e:
                        if e.status != 404:
                            yield f"Error checking pod {job_name}: {e}"
                            return
                        # 如果直接获取失败，尝试找到Job关联的Pod
                        pods = self._get_job_pods(job_name, ns)
                        if not pods:
                            return
                        target_pod = pods[0].metadata.name

                # 使用Kubernetes API获取流式日志
                try:
                    # 使用stream方法获取日志
                    logs = self.core_v1.read_namespaced_pod_log(
                        name=target_pod,
                        namespace=ns,
                        follow=True,
                        timestamps=True,
                        _preload_content=False
                    )
                    
                    for line in logs:
                        if line:
                            yield line.decode('utf-8').strip()
                    logs.close()
                    return
                except ApiException as e:
                    if e.status == 404:
                        return
                    yield f"Error streaming logs: {e}"
                    return
            except Exception as e:
                yield f"Error streaming logs: {e}"
                return
        
        # 1. 优先在指定命名空间中查找
        found = False
        for log in _try_stream_in_namespace(namespace, pod_name):
            yield log
            found = True
        
        if found:
            return
        
        # 2. 如果在指定命名空间中未找到，搜索所有gpuctl管理的命名空间
        all_namespaces = self._get_all_gpuctl_namespaces()
        for ns in all_namespaces:
            if ns == namespace:
                continue  # 跳过已经检查过的命名空间
            
            found = False
            for log in _try_stream_in_namespace(ns, pod_name):
                yield log
                found = True
            
            if found:
                return
        
        # 所有命名空间中都未找到日志
        yield "No pods found for this job"

    def get_pod_logs(self, pod_name: str, namespace: str = DEFAULT_NAMESPACE,
                     container: Optional[str] = None, tail: int = 100) -> List[str]:
        """获取特定Pod的日志"""
        def _try_get_logs_in_namespace(ns: str):
            """在指定命名空间中尝试获取Pod日志"""
            try:
                log_content = self.core_v1.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=ns,
                    container=container,
                    tail_lines=tail,
                    timestamps=True
                )

                logs = log_content.strip().split('\n') if log_content else []
                return logs
            except ApiException as e:
                # 只忽略404错误，其他错误向上抛出
                if e.status != 404:
                    raise
                return None
        
        try:
            # 1. 优先在指定命名空间中查找
            logs = _try_get_logs_in_namespace(namespace)
            if logs is not None:
                return logs
            
            # 2. 如果在指定命名空间中未找到，搜索所有gpuctl管理的命名空间
            all_namespaces = self._get_all_gpuctl_namespaces()
            for ns in all_namespaces:
                if ns == namespace:
                    continue  # 跳过已经检查过的命名空间
                
                logs = _try_get_logs_in_namespace(ns)
                if logs is not None:
                    return logs
            
            # 所有命名空间中都未找到日志
            return ["Pod not found in any gpuctl-managed namespace"]

        except ApiException as e:
            self.handle_api_exception(e, f"get logs for pod {pod_name}")

