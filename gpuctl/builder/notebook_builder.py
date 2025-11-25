from kubernetes import client
from .base_builder import BaseBuilder
from gpuctl.api.notebook import NotebookJob


class NotebookBuilder(BaseBuilder):
    """Notebook任务构建器"""

    @classmethod
    def build_statefulset(cls, notebook_job: NotebookJob) -> client.V1StatefulSet:
        """构建K8s StatefulSet资源"""
        spec = notebook_job.spec

        # 构建容器
        container = cls.build_container_spec(spec.environment, spec.resources)

        # 添加Notebook特定配置
        container.ports = [client.V1ContainerPort(container_port=8888)]

        # 构建Pod模板
        pod_spec_extras = {}
        if spec.environment.image_pull_secret:
            pod_spec_extras['image_pull_secrets'] = [
                client.V1LocalObjectReference(name=spec.environment.image_pull_secret)
            ]

        if spec.resources.pool:
            pod_spec_extras['node_selector'] = {
                "gpuctl/pool": spec.resources.pool
            }

        template = cls.build_pod_template_spec(container, pod_spec_extras)

        # 构建StatefulSet规格
        statefulset_spec = client.V1StatefulSetSpec(
            replicas=1,  # Notebook通常是单实例
            template=template,
            selector=client.V1LabelSelector(
                match_labels={"app": f"notebook-{spec.job.name}"}
            ),
            service_name=f"svc-{spec.job.name}"
        )

        # 构建StatefulSet元数据
        metadata = client.V1ObjectMeta(
            name=f"notebook-{spec.job.name}",
            labels={
                "gpuctl/job-type": "notebook",
                "gpuctl/priority": spec.job.priority,
                "gpuctl/pool": spec.resources.pool or "default"
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
        spec = notebook_job.spec

        service_spec = client.V1ServiceSpec(
            selector={"app": f"notebook-{spec.job.name}"},
            ports=[client.V1ServicePort(
                port=8888,
                target_port=8888
            )],
            type="NodePort"  # 方便外部访问
        )

        metadata = client.V1ObjectMeta(
            name=f"svc-{spec.job.name}",
            labels={
                "gpuctl/job-type": "notebook",
                "gpuctl/pool": spec.resources.pool or "default"
            }
        )

        return client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=metadata,
            spec=service_spec
        )