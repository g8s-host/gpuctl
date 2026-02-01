from kubernetes import client
from .base_builder import BaseBuilder
from gpuctl.api.compute import ComputeJob


class ComputeBuilder(BaseBuilder):
    """Compute job builder"""

    @classmethod
    def build_deployment(cls, compute_job: ComputeJob) -> client.V1Deployment:
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
        if compute_job.resources.pool and compute_job.resources.pool != "default":
            # 对于非默认池，使用 node_selector
            node_selector = {}
            node_selector["g8s.host/pool"] = compute_job.resources.pool
            if compute_job.resources.gpu_type:
                node_selector["g8s.host/gpuType"] = compute_job.resources.gpu_type
            pod_spec_extras['node_selector'] = node_selector
        else:
            # 对于默认池或未指定池，使用 node_affinity 实现反亲和性
            # 确保 Pod 不会调度到带有 g8s.host/pool 标签的节点上
            if compute_job.resources.gpu_type:
                # 如果指定了 GPU 类型，仍然使用 node_selector 来选择 GPU 类型
                node_selector = {}
                node_selector["g8s.host/gpuType"] = compute_job.resources.gpu_type
                pod_spec_extras['node_selector'] = node_selector
            # 添加反亲和性规则
            pod_spec_extras['affinity'] = client.V1Affinity(
                node_affinity=client.V1NodeAffinity(
                    required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
                        node_selector_terms=[client.V1NodeSelectorTerm(
                            match_expressions=[client.V1NodeSelectorRequirement(
                                key="g8s.host/pool",
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
        
        template = cls.build_pod_template_spec(
            container, 
            pod_spec_extras, 
            labels={
                "app": app_label,
                "g8s.host/job-type": "compute",
                "g8s.host/priority": compute_job.job.priority,
                "g8s.host/pool": compute_job.resources.pool or "default"
            },
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

        metadata = client.V1ObjectMeta(
            name=app_label,
            labels={
                "g8s.host/job-type": "compute",
                "g8s.host/priority": compute_job.job.priority,
                "g8s.host/pool": compute_job.resources.pool or "default"
            }
        )

        return client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=metadata,
            spec=deployment_spec
        )

    @classmethod
    def build_service(cls, compute_job: ComputeJob) -> client.V1Service:
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

        metadata = client.V1ObjectMeta(
            name=f"svc-{compute_job.job.name}",
            labels={
                "g8s.host/job-type": "compute",
                "g8s.host/pool": compute_job.resources.pool or "default"
            }
        )

        return client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=metadata,
            spec=service_spec
        )