from kubernetes import client
from typing import Dict, Any, List
from gpuctl.api.common import ResourceRequest, StorageConfig


class BaseBuilder:
    """基础构建器"""

    @staticmethod
    def build_volume_mounts(workdirs: List[Dict[str, str]]) -> List[client.V1VolumeMount]:
        """构建VolumeMounts"""
        volume_mounts = []
        for idx, workdir in enumerate(workdirs):
            volume_name = f"workdir-{idx}"
            mount_path = workdir.get("path", "")
            if mount_path:
                volume_mounts.append(client.V1VolumeMount(
                    name=volume_name,
                    mount_path=mount_path
                ))
        return volume_mounts

    @staticmethod
    def build_volumes(workdirs: List[Dict[str, str]]) -> List[client.V1Volume]:
        """构建Volumes"""
        volumes = []
        for idx, workdir in enumerate(workdirs):
            volume_name = f"workdir-{idx}"
            path = workdir.get("path", "")
            if path:
                volumes.append(client.V1Volume(
                    name=volume_name,
                    host_path=client.V1HostPathVolumeSource(
                        path=path,
                        type="DirectoryOrCreate"
                    )
                ))
        return volumes

    @staticmethod
    def build_container_spec(env_config, resources: ResourceRequest, workdirs: List[Dict[str, str]] = None) -> client.V1Container:
        """构建容器规格"""
        resource_requirements = client.V1ResourceRequirements(
            requests={
                "cpu": resources.cpu,
                "memory": resources.memory,
                "nvidia.com/gpu": str(resources.gpu)
            },
            limits={
                "cpu": resources.cpu,
                "memory": resources.memory,
                "nvidia.com/gpu": str(resources.gpu)
            }
        )

        env_vars = []
        for env_var in getattr(env_config, 'env', []):
            if isinstance(env_var, dict):
                for key, value in env_var.items():
                    env_vars.append(client.V1EnvVar(name=key, value=value))

        container = client.V1Container(
            name="main",
            image=env_config.image,
            command=getattr(env_config, 'command', None),
            args=getattr(env_config, 'args', None),
            env=env_vars,
            resources=resource_requirements,
            image_pull_policy="IfNotPresent"
        )

        # 添加VolumeMounts
        if workdirs:
            container.volume_mounts = BaseBuilder.build_volume_mounts(workdirs)

        return container

    @staticmethod
    def build_pod_template_spec(container: client.V1Container,
                                pod_spec_extras: Dict[str, Any] = None,
                                labels: Dict[str, str] = None,
                                restart_policy: str = "Never",
                                workdirs: List[Dict[str, str]] = None) -> client.V1PodTemplateSpec:
        """构建Pod模板规格"""
        spec = client.V1PodSpec(
            containers=[container],
            restart_policy=restart_policy
        )

        if pod_spec_extras:
            if 'image_pull_secrets' in pod_spec_extras:
                spec.image_pull_secrets = pod_spec_extras['image_pull_secrets']
            if 'node_selector' in pod_spec_extras:
                spec.node_selector = pod_spec_extras['node_selector']

        # 添加Volumes
        if workdirs:
            spec.volumes = BaseBuilder.build_volumes(workdirs)

        # 使用提供的labels，如果没有则使用默认值
        pod_labels = labels or {"app": "gpuctl-job"}
        metadata = client.V1ObjectMeta(labels=pod_labels)
        return client.V1PodTemplateSpec(metadata=metadata, spec=spec)