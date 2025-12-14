from kubernetes import client
from .base_builder import BaseBuilder
from gpuctl.api.inference import InferenceJob


class InferenceBuilder(BaseBuilder):
    """推理任务构建器"""

    @classmethod
    def build_deployment(cls, inference_job: InferenceJob) -> client.V1Deployment:
        """构建K8s Deployment资源"""
        # 获取workdirs
        workdirs = []
        if hasattr(inference_job, 'storage') and hasattr(inference_job.storage, 'workdirs'):
            workdirs = inference_job.storage.workdirs
        
        # 构建容器
        container = cls.build_container_spec(inference_job.environment, inference_job.resources, workdirs)

        # 构建Pod模板
        pod_spec_extras = {}
        if inference_job.environment.image_pull_secret:
            pod_spec_extras['image_pull_secrets'] = [
                client.V1LocalObjectReference(name=inference_job.environment.image_pull_secret)
            ]

        node_selector = {}
        if inference_job.resources.pool:
            node_selector["g8s.host/pool"] = inference_job.resources.pool
        if inference_job.resources.gpu_type:
            node_selector["g8s.host/gpu-type"] = inference_job.resources.gpu_type
        if node_selector:
            pod_spec_extras['node_selector'] = node_selector

        # 添加健康检查
        if inference_job.service.health_check:
            health_path = inference_job.service.health_check
            container.liveness_probe = client.V1Probe(
                http_get=client.V1HTTPGetAction(
                    path=health_path,
                    port=inference_job.service.port
                ),
                initial_delay_seconds=30,
                period_seconds=10
            )
            container.readiness_probe = client.V1Probe(
                http_get=client.V1HTTPGetAction(
                    path=health_path,
                    port=inference_job.service.port
                ),
                initial_delay_seconds=5,
                period_seconds=10
            )

        # 为Deployment构建Pod模板，使用与selector匹配的labels和Always重启策略
        app_label = f"inference-{inference_job.job.name}"
        template = cls.build_pod_template_spec(
            container, 
            pod_spec_extras, 
            labels={"app": app_label}, 
            restart_policy="Always",  # Deployment要求使用Always重启策略
            workdirs=workdirs
        )

        # 构建Deployment规格
        deployment_spec = client.V1DeploymentSpec(
            replicas=inference_job.service.replicas,
            template=template,
            selector=client.V1LabelSelector(
                match_labels={"app": f"inference-{inference_job.job.name}"}
            )
        )

        # 构建Deployment元数据
        metadata = client.V1ObjectMeta(
            name=f"inference-{inference_job.job.name}",
            labels={
                "g8s.host/job-type": "inference",
                "g8s.host/priority": inference_job.job.priority,
                "g8s.host/pool": inference_job.resources.pool or "default"
            }
        )

        return client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=metadata,
            spec=deployment_spec
        )

    @classmethod
    def build_service(cls, inference_job: InferenceJob) -> client.V1Service:
        """构建K8s Service资源"""
        service_spec = client.V1ServiceSpec(
            selector={"app": f"inference-{inference_job.job.name}"},
            ports=[client.V1ServicePort(
                port=inference_job.service.port,
                target_port=inference_job.service.port
            )],
            type="ClusterIP"  # 可以根据需要调整为NodePort或LoadBalancer
        )

        metadata = client.V1ObjectMeta(
            name=f"svc-{inference_job.job.name}",
            labels={
                "g8s.host/job-type": "inference",
                "g8s.host/pool": inference_job.resources.pool or "default"
            }
        )

        return client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=metadata,
            spec=service_spec
        )

    @classmethod
    def build_hpa(cls, inference_job: InferenceJob) -> client.V1HorizontalPodAutoscaler:
        """构建水平Pod自动扩缩容资源"""
        hpa_spec = client.V1HorizontalPodAutoscalerSpec(
            scale_target_ref=client.V1CrossVersionObjectReference(
                kind="Deployment",
                name=f"inference-{inference_job.job.name}",
                api_version="apps/v1"
            ),
            min_replicas=inference_job.autoscaling.min_replicas,
            max_replicas=inference_job.autoscaling.max_replicas,
            target_cpu_utilization_percentage=inference_job.autoscaling.target_gpu_utilization
        )

        metadata = client.V1ObjectMeta(
            name=f"hpa-{inference_job.job.name}",
            labels={
                "g8s.host/job-type": "inference",
                "g8s.host/pool": inference_job.resources.pool or "default"
            }
        )

        return client.V1HorizontalPodAutoscaler(
            api_version="autoscaling/v1",
            kind="HorizontalPodAutoscaler",
            metadata=metadata,
            spec=hpa_spec
        )