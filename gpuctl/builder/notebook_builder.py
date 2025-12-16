from kubernetes import client
from .base_builder import BaseBuilder
from gpuctl.api.notebook import NotebookJob


class NotebookBuilder(BaseBuilder):
    """Notebook任务构建器"""

    @classmethod
    def build_statefulset(cls, notebook_job: NotebookJob) -> client.V1StatefulSet:
        """构建K8s StatefulSet资源"""
        # 获取workdirs
        workdirs = notebook_job.storage.workdirs if hasattr(notebook_job.storage, 'workdirs') else []
        
        # 构建容器
        container = cls.build_container_spec(notebook_job.environment, notebook_job.resources, workdirs)

        # 添加Notebook特定配置，使用默认端口8888
        container.ports = [client.V1ContainerPort(container_port=8888)]

        # 构建Pod模板
        pod_spec_extras = {}
        if notebook_job.environment.image_pull_secret:
            pod_spec_extras['image_pull_secrets'] = [
                client.V1LocalObjectReference(name=notebook_job.environment.image_pull_secret)
            ]

        node_selector = {}
        if notebook_job.resources.pool:
            node_selector["g8s.host/pool"] = notebook_job.resources.pool
        if notebook_job.resources.gpu_type:
            node_selector["g8s.host/gpu-type"] = notebook_job.resources.gpu_type
        if node_selector:
            pod_spec_extras['node_selector'] = node_selector

        # 为StatefulSet构建Pod模板，使用与selector匹配的labels和Always重启策略
        app_label = f"g8s-host-notebook-{notebook_job.job.name}"
        template = cls.build_pod_template_spec(
            container, 
            pod_spec_extras, 
            labels={"app": app_label}, 
            restart_policy="Always",  # StatefulSet要求使用Always重启策略
            workdirs=workdirs
        )

        # 构建StatefulSet规格
        service_name = f"g8s-host-svc-{notebook_job.job.name}"
        statefulset_spec = client.V1StatefulSetSpec(
            replicas=1,  # Notebook通常是单实例
            template=template,
            selector=client.V1LabelSelector(
                match_labels={"app": app_label}
            ),
            service_name=service_name
        )

        # 构建StatefulSet元数据
        metadata = client.V1ObjectMeta(
            name=app_label,
            labels={
                "g8s.host/job-type": "notebook",
                "g8s.host/priority": notebook_job.job.priority,
                "g8s.host/pool": notebook_job.resources.pool or "default"
            }
        )

        return client.V1StatefulSet(
            api_version="apps/v1",
            kind="StatefulSet",
            metadata=metadata,
            spec=statefulset_spec
        )

    @classmethod
    def build_service(cls, notebook_job: NotebookJob) -> client.V1Service:
        """构建K8s Service资源"""
        app_label = f"g8s-host-notebook-{notebook_job.job.name}"
        service_spec = client.V1ServiceSpec(
            selector={"app": app_label},
            ports=[client.V1ServicePort(
                port=notebook_job.service.port,
                target_port=notebook_job.service.port
            )],
            type="NodePort"  # 方便外部访问
        )

        metadata = client.V1ObjectMeta(
            name=f"g8s-host-svc-{notebook_job.job.name}",
            labels={
                "g8s.host/job-type": "notebook",
                "g8s.host/pool": notebook_job.resources.pool or "default"
            }
        )

        return client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=metadata,
            spec=service_spec
        )