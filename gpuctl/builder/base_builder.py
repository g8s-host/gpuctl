from kubernetes import client
from typing import Dict, Any
from gpuctl.api.common import ResourceRequest


class BaseBuilder:
    """基础构建器"""

    @staticmethod
    def build_container_spec(env_config, resources: ResourceRequest) -> client.V1Container:
        """构建容器规格"""
        resource_requirements = client.V1ResourceRequirements(
            requests={
                "cpu": resources.cpu,
                "memory": resources.memory,
                "nvidia.com/gpu": str(resources.accelerator_count)
            },
            limits={
                "cpu": resources.cpu,
                "memory": resources.memory,
                "nvidia.com/gpu": str(resources.accelerator_count)
            }
        )

        env_vars = []
        for env_var in env_config.env:
            for key, value in env_var.items():
                env_vars.append(client.V1EnvVar(name=key, value=value))

        return client.V1Container(
            name="main",
            image=env_config.image,
            command=env_config.command,
            args=env_config.args,
            env=env_vars,
            resources=resource_requirements,
            image_pull_policy="IfNotPresent"
        )

    @staticmethod
    def build_pod_template_spec(container: client.V1Container,
                                pod_spec_extras: Dict[str, Any] = None) -> client.V1PodTemplateSpec:
        """构建Pod模板规格"""
        spec = client.V1PodSpec(containers=[container])

        if pod_spec_extras:
            if 'image_pull_secrets' in pod_spec_extras:
                spec.image_pull_secrets = pod_spec_extras['image_pull_secrets']
            if 'node_selector' in pod_spec_extras:
                spec.node_selector = pod_spec_extras['node_selector']

        metadata = client.V1ObjectMeta(labels={"app": "gpuctl-job"})
        return client.V1PodTemplateSpec(metadata=metadata, spec=spec)