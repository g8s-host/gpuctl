from kubernetes import client
from .base_builder import BaseBuilder
from gpuctl.api.compute import ComputeJob
from gpuctl.constants import Labels, Kind, DEFAULT_POOL, svc_name


class ComputeBuilder(BaseBuilder):
    """Compute job builder"""

    @classmethod
    def build_deployment(cls, compute_job: ComputeJob, namespace: str = "default") -> client.V1Deployment:
        """Build K8s Deployment resource"""
        workdirs = []
        if compute_job.storage and hasattr(compute_job.storage, 'workdirs'):
            workdirs = compute_job.storage.workdirs
        
        container = cls.build_container_spec(compute_job.environment, compute_job.resources, workdirs)

        pod_spec_extras = {}
        if compute_job.environment.image_pull_secret:
            pod_spec_extras['image_pull_secrets'] = [
                client.V1LocalObjectReference(name=compute_job.environment.image_pull_secret)
            ]

        # 处理资源池选择
        if compute_job.resources.pool and compute_job.resources.pool != DEFAULT_POOL:
            # 对于非默认池，使用 node_selector
            node_selector = {}
            node_selector[Labels.POOL] = compute_job.resources.pool
            if compute_job.resources.gpu_type:
                node_selector[Labels.GPU_TYPE] = compute_job.resources.gpu_type
            pod_spec_extras['node_selector'] = node_selector
        else:
            # 对于默认池或未指定池，使用 node_affinity 实现反亲和性
            # 确保 Pod 不会调度到带有 g8s.host/pool 标签的节点上
            if compute_job.resources.gpu_type:
                # 如果指定了 GPU 类型，仍然使用 node_selector 来选择 GPU 类型
                node_selector = {}
                node_selector[Labels.GPU_TYPE] = compute_job.resources.gpu_type
                pod_spec_extras['node_selector'] = node_selector
            # 添加反亲和性规则
            pod_spec_extras['affinity'] = client.V1Affinity(
                node_affinity=client.V1NodeAffinity(
                    required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
                        node_selector_terms=[client.V1NodeSelectorTerm(
                            match_expressions=[client.V1NodeSelectorRequirement(
                                key=Labels.POOL,
                                operator="DoesNotExist"
                            )]
                        )]
                    )
                )
            )

        if compute_job.service and compute_job.service.health_check:
            health_path = compute_job.service.health_check
            container.liveness_probe = client.V1Probe(
                http_get=client.V1HTTPGetAction(
                    path=health_path,
                    port=compute_job.service.port
                ),
                initial_delay_seconds=30,
                period_seconds=10
            )
            container.readiness_probe = client.V1Probe(
                http_get=client.V1HTTPGetAction(
                    path=health_path,
                    port=compute_job.service.port
                ),
                initial_delay_seconds=5,
                period_seconds=10
            )

        app_label = f"{compute_job.job.name}"
        
        # 获取优先级类名称
        from gpuctl.client.priority_client import PriorityConfig, PriorityLevel
        priority_config = PriorityConfig.PRIORITY_CLASSES.get(compute_job.job.priority)
        priority_class_name = priority_config["name"] if priority_config else None
        
        # 构建 labels
        pod_labels = {
            "app": app_label,
            Labels.JOB_TYPE: Kind.COMPUTE,
            Labels.PRIORITY: compute_job.job.priority,
            Labels.POOL: compute_job.resources.pool or DEFAULT_POOL,
            Labels.NAMESPACE: namespace
        }
        # 添加 port 到 label（如果存在）
        if compute_job.service and compute_job.service.port:
            pod_labels[Labels.PORT] = str(compute_job.service.port)

        # 构建 annotations，包含 description（因为 description 可能包含空格，不能放在 label 中）
        pod_annotations = {}
        if compute_job.job.description:
            pod_annotations[Labels.DESCRIPTION] = compute_job.job.description

        template = cls.build_pod_template_spec(
            container,
            pod_spec_extras,
            labels=pod_labels,
            annotations=pod_annotations,
            restart_policy="Always",
            workdirs=workdirs,
            priority_class_name=priority_class_name
        )

        deployment_spec = client.V1DeploymentSpec(
            replicas=compute_job.service.replicas if compute_job.service else 1,
            template=template,
            selector=client.V1LabelSelector(
                match_labels={"app": app_label}
            )
        )

        # 构建 metadata labels
        metadata_labels = {
            Labels.JOB_TYPE: Kind.COMPUTE,
            Labels.PRIORITY: compute_job.job.priority,
            Labels.POOL: compute_job.resources.pool or DEFAULT_POOL,
            Labels.NAMESPACE: namespace
        }
        # 添加 port 到 label（如果存在）
        if compute_job.service and compute_job.service.port:
            metadata_labels[Labels.PORT] = str(compute_job.service.port)

        # 构建 metadata annotations，包含 description
        metadata_annotations = {}
        if compute_job.job.description:
            metadata_annotations[Labels.DESCRIPTION] = compute_job.job.description

        metadata = client.V1ObjectMeta(
            name=app_label,
            labels=metadata_labels,
            annotations=metadata_annotations
        )

        return client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=metadata,
            spec=deployment_spec
        )

    @classmethod
    def build_service(cls, compute_job: ComputeJob, namespace: str = "default") -> client.V1Service:
        """Build K8s Service resource"""
        app_label = f"{compute_job.job.name}"
        service_spec = client.V1ServiceSpec(
            selector={"app": app_label},
            ports=[client.V1ServicePort(
                port=compute_job.service.port,
                target_port=compute_job.service.port
            )],
            type="NodePort"
        )

        metadata_annotations = {}
        if compute_job.job.description:
            metadata_annotations[Labels.DESCRIPTION] = compute_job.job.description

        metadata = client.V1ObjectMeta(
            name=svc_name(compute_job.job.name),
            labels={
                Labels.JOB_TYPE: Kind.COMPUTE,
                Labels.POOL: compute_job.resources.pool or DEFAULT_POOL,
                Labels.NAMESPACE: namespace
            },
            annotations=metadata_annotations
        )

        return client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=metadata,
            spec=service_spec
        )