from kubernetes import client
from typing import Dict, Any, List
from gpuctl.api.common import ResourceRequest, StorageConfig


class BaseBuilder:
    """Base builder"""

    @staticmethod
    def build_volume_mounts(workdirs: List[Dict[str, str]]) -> List[client.V1VolumeMount]:
        """Build VolumeMounts"""
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
        """Build Volumes"""
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
        """Build container spec"""
        requests = {
            "cpu": resources.cpu,
            "memory": resources.memory
        }
        limits = {
            "cpu": resources.cpu,
            "memory": resources.memory
        }
        
        if resources.gpu > 0:
            requests["nvidia.com/gpu"] = str(resources.gpu)
            limits["nvidia.com/gpu"] = str(resources.gpu)
        
        resource_requirements = client.V1ResourceRequirements(
            requests=requests,
            limits=limits
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

        if workdirs:
            container.volume_mounts = BaseBuilder.build_volume_mounts(workdirs)

        return container

    @staticmethod
    def build_pod_template_spec(container: client.V1Container,
                                pod_spec_extras: Dict[str, Any] = None,
                                labels: Dict[str, str] = None,
                                restart_policy: str = "Never",
                                workdirs: List[Dict[str, str]] = None,
                                priority_class_name: str = None) -> client.V1PodTemplateSpec:
        """Build Pod template spec"""
        spec = client.V1PodSpec(
            containers=[container],
            restart_policy=restart_policy
        )

        if pod_spec_extras:
            if 'image_pull_secrets' in pod_spec_extras:
                spec.image_pull_secrets = pod_spec_extras['image_pull_secrets']
            if 'node_selector' in pod_spec_extras:
                spec.node_selector = pod_spec_extras['node_selector']
            if 'affinity' in pod_spec_extras:
                spec.affinity = pod_spec_extras['affinity']

        if workdirs:
            spec.volumes = BaseBuilder.build_volumes(workdirs)

        # 添加优先级类
        if priority_class_name:
            spec.priority_class_name = priority_class_name

        pod_labels = labels or {"app": "gpuctl-job"}
        metadata = client.V1ObjectMeta(labels=pod_labels)
        return client.V1PodTemplateSpec(metadata=metadata, spec=spec)