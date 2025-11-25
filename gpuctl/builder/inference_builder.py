from kubernetes import client
from .base_builder import BaseBuilder
from gpuctl.api.inference import InferenceJob


class InferenceBuilder(BaseBuilder):
    """推理任务构建器"""

    @classmethod
    def build_deployment(cls, inference_job: InferenceJob) -> client.V1Deployment:
        """构建K8s Deployment资源"""
        spec = inference_job.spec

        # 构建容器
        container = cls.build_container_spec(spec.environment, spec.resources)

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

        # 构建Deployment规格
        deployment_spec = client.V1DeploymentSpec(
            replicas=spec.service.replicas,
            template=template,
            selector=client.V1LabelSelector(
                match_labels={"app": f"inference-{spec.job.name}"}
            )
        )

        # 构建Deployment元数据
        metadata = client.V1ObjectMeta(
            name=f"inference-{spec.job.name}",
            labels={
                "gpuctl/job-type": "inference",
                "gpuctl/priority": spec.job.priority,
                "gpuctl/pool": spec.resources.pool or "default"
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
        spec = inference_job.spec

        service_spec = client.V1ServiceSpec(
            selector={"app": f"inference-{spec.job.name}"},
            ports=[client.V1ServicePort(
                port=spec.service.port,
                target_port=spec.service.port
            )],
            type="ClusterIP"  # 可以根据需要调整为NodePort或LoadBalancer
        )

        metadata = client.V1ObjectMeta(
            name=f"svc-{spec.job.name}",
            labels={
                "gpuctl/job-type": "inference",
                "gpuctl/pool": spec.resources.pool or "default"
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
        spec = inference_job.spec

        hpa_spec = client.V1HorizontalPodAutoscalerSpec(
            scale_target_ref=client.V1CrossVersionObjectReference(
                kind="Deployment",
                name=f"inference-{spec.job.name}",
                api_version="apps/v1"
            ),
            min_replicas=spec.autoscaling.min_replicas,
            max_replicas=spec.autoscaling.max_replicas,
            target_cpu_utilization_percentage=spec.autoscaling.target_gpu_utilization
        )

        metadata = client.V1ObjectMeta(
            name=f"hpa-{spec.job.name}",
            labels={
                "gpuctl/job-type": "inference",
                "gpuctl/pool": spec.resources.pool or "default"
            }
        )

        return client.V1HorizontalPodAutoscaler(
            api_version="autoscaling/v1",
            kind="HorizontalPodAutoscaler",
            metadata=metadata,
            spec=hpa_spec
        )