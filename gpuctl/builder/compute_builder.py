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

        node_selector = {}
        if compute_job.resources.pool:
            node_selector["g8s.host/pool"] = compute_job.resources.pool
        if compute_job.resources.gpu_type:
            node_selector["g8s.host/gpu-type"] = compute_job.resources.gpu_type
        if node_selector:
            pod_spec_extras['node_selector'] = node_selector

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

        app_label = f"g8s-host-compute-{compute_job.job.name}"
        template = cls.build_pod_template_spec(
            container, 
            pod_spec_extras, 
            labels={"app": app_label},
            restart_policy="Always",
            workdirs=workdirs
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
        app_label = f"g8s-host-compute-{compute_job.job.name}"
        service_spec = client.V1ServiceSpec(
            selector={"app": app_label},
            ports=[client.V1ServicePort(
                port=compute_job.service.port,
                target_port=compute_job.service.port
            )],
            type="NodePort"
        )

        metadata = client.V1ObjectMeta(
            name=f"g8s-host-svc-{compute_job.job.name}",
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