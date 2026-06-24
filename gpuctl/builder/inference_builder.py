import math

from kubernetes import client
from .base_builder import BaseBuilder
from gpuctl.api.inference import InferenceJob
from gpuctl.api.common import parse_duration_seconds
from gpuctl.constants import Labels, Kind, DEFAULT_POOL, svc_name


class InferenceBuilder(BaseBuilder):
    """Inference job builder"""

    @classmethod
    def build_deployment(cls, inference_job: InferenceJob, namespace: str = "default") -> client.V1Deployment:
        """Build K8s Deployment resource"""
        workdirs = []
        if hasattr(inference_job, 'storage') and hasattr(inference_job.storage, 'workdirs'):
            workdirs = inference_job.storage.workdirs
        
        container = cls.build_container_spec(inference_job.environment, inference_job.resources, workdirs)

        pod_spec_extras = {}
        if inference_job.environment.image_pull_secret:
            pod_spec_extras['image_pull_secrets'] = [
                client.V1LocalObjectReference(name=inference_job.environment.image_pull_secret)
            ]

        # 处理资源池选择
        if inference_job.resources.pool and inference_job.resources.pool != DEFAULT_POOL:
            # 对于非默认池，使用 node_selector
            node_selector = {}
            node_selector[Labels.POOL] = inference_job.resources.pool
            if inference_job.resources.gpu_type:
                node_selector[Labels.GPU_TYPE] = inference_job.resources.gpu_type
            pod_spec_extras['node_selector'] = node_selector
        else:
            # 对于默认池或未指定池，使用 node_affinity 实现反亲和性
            # 确保 Pod 不会调度到带有 runwhere.ai/pool 标签的节点上
            if inference_job.resources.gpu_type:
                # 如果指定了 GPU 类型，仍然使用 node_selector 来选择 GPU 类型
                node_selector = {}
                node_selector[Labels.GPU_TYPE] = inference_job.resources.gpu_type
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

        if inference_job.service.health_check:
            health_path = inference_job.service.health_check
            svc_port = inference_job.service.port

            def _probe(failure_threshold):
                # 单次检查给 5s（K8s 默认 1s 太紧，重载下 /health 容易误判超时）；周期 10s。
                return client.V1Probe(
                    http_get=client.V1HTTPGetAction(path=health_path, port=svc_port),
                    timeout_seconds=5,
                    period_seconds=10,
                    failure_threshold=failure_threshold,
                )

            # startupProbe：启动期间（下载/加载模型、暖数据…）挂起 liveness/readiness，慢启动也不会被杀。
            # 宽限时长 = service.startupTimeout（默认 10m），失败阈值 = 宽限 / 周期。
            grace_seconds = parse_duration_seconds(inference_job.service.startup_timeout or "10m")
            container.startup_probe = _probe(max(1, math.ceil(grace_seconds / 10)))
            # 启动通过后才生效：连续 3 次（≈30s）失败才重启 / 摘流量。
            container.liveness_probe = _probe(3)
            container.readiness_probe = _probe(3)

        app_label = f"{inference_job.job.name}"
        
        # 获取优先级类名称
        from gpuctl.client.priority_client import PriorityConfig, PriorityLevel
        priority_config = PriorityConfig.PRIORITY_CLASSES.get(inference_job.job.priority)
        priority_class_name = priority_config["name"] if priority_config else None
        
        # 构建 labels
        pod_labels = {
            "app": app_label,
            Labels.JOB_TYPE: Kind.INFERENCE,
            Labels.PRIORITY: inference_job.job.priority,
            Labels.POOL: inference_job.resources.pool or DEFAULT_POOL,
            Labels.NAMESPACE: namespace
        }

        # 构建 annotations，包含 description
        pod_annotations = {}
        if inference_job.job.description:
            pod_annotations[Labels.DESCRIPTION] = inference_job.job.description

        template = cls.build_pod_template_spec(
            container,
            pod_spec_extras,
            labels=pod_labels,
            annotations=pod_annotations,
            restart_policy="Always",
            workdirs=workdirs,
            priority_class_name=priority_class_name,
            namespace=namespace,
        )

        deployment_spec = client.V1DeploymentSpec(
            replicas=inference_job.service.replicas,
            template=template,
            selector=client.V1LabelSelector(
                match_labels={"app": app_label}
            )
        )

        # 构建 metadata labels
        metadata_labels = {
            Labels.JOB_TYPE: Kind.INFERENCE,
            Labels.PRIORITY: inference_job.job.priority,
            Labels.POOL: inference_job.resources.pool or DEFAULT_POOL,
            Labels.NAMESPACE: namespace
        }

        # 构建 metadata annotations，包含 description
        metadata_annotations = {}
        if inference_job.job.description:
            metadata_annotations[Labels.DESCRIPTION] = inference_job.job.description

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
    def build_service(cls, inference_job: InferenceJob, namespace: str = "default") -> client.V1Service:
        """Build K8s Service resource"""
        app_label = f"{inference_job.job.name}"
        service_spec = client.V1ServiceSpec(
            selector={"app": app_label},
            ports=[client.V1ServicePort(
                port=inference_job.service.port,
                target_port=inference_job.service.port
            )],
            type="NodePort"
        )

        metadata_annotations = {}
        if inference_job.job.description:
            metadata_annotations[Labels.DESCRIPTION] = inference_job.job.description

        metadata = client.V1ObjectMeta(
            name=svc_name(inference_job.job.name),
            labels={
                Labels.JOB_TYPE: Kind.INFERENCE,
                Labels.POOL: inference_job.resources.pool or DEFAULT_POOL,
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

