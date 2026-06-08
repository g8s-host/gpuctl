from kubernetes import client
from kubernetes.client.rest import ApiException
from typing import Dict, Any, List, Optional, Tuple
from gpuctl.api.common import ResourceRequest, StorageConfig
from gpuctl.kube_config import load_k8s_config

_NFS_CONFIGMAP_NAME = "gpuctl-config"
_NFS_CONFIGMAP_NS = "kube-system"


class BaseBuilder:
    """Base builder"""

    @staticmethod
    def read_nfs_config() -> Optional[Tuple[str, str]]:
        """Read NFS config from gpuctl-config ConfigMap.

        Returns:
            (nfs_server, nfs_path) tuple, or None if ConfigMap absent/incomplete.
        """
        try:
            from kubernetes import client as k8s_client, config as k8s_config
            load_k8s_config(k8s_config)
            core_v1 = k8s_client.CoreV1Api()
            cm = core_v1.read_namespaced_config_map(
                name=_NFS_CONFIGMAP_NAME, namespace=_NFS_CONFIGMAP_NS
            )
            nfs_server = cm.data.get("nfs.server") if cm.data else None
            nfs_path = cm.data.get("nfs.path") if cm.data else None
            if nfs_server and nfs_path:
                return nfs_server, nfs_path
            return None
        except ApiException as e:
            if e.status == 404:
                return None
            raise
        except Exception:
            return None

    @staticmethod
    def build_nfs_volumes(namespace: str) -> Tuple[List[client.V1Volume], List[client.V1VolumeMount]]:
        """Build NFS home + datasets volumes/mounts for the given namespace.

        Returns empty lists if NFS is not configured (graceful degradation).
        """
        nfs_config = BaseBuilder.read_nfs_config()
        if not nfs_config:
            return [], []

        nfs_server, nfs_path = nfs_config
        home_path = f"{nfs_path}/home/{namespace}"
        datasets_path = f"{nfs_path}/datasets"

        volumes = [
            client.V1Volume(
                name="home",
                nfs=client.V1NFSVolumeSource(
                    server=nfs_server,
                    path=home_path,
                    read_only=False,
                ),
            ),
            client.V1Volume(
                name="datasets",
                nfs=client.V1NFSVolumeSource(
                    server=nfs_server,
                    path=datasets_path,
                    read_only=True,
                ),
            ),
        ]
        mounts = [
            client.V1VolumeMount(name="home", mount_path="/home/jovyan"),
            client.V1VolumeMount(name="datasets", mount_path="/datasets", read_only=True),
        ]
        return volumes, mounts

    @staticmethod
    def build_headless_service(job_name: str, namespace: str, port: int = 29500) -> client.V1Service:
        """Build a HeadlessService for distributed training worker discovery."""
        return client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(
                name=f"{job_name}-headless",
                namespace=namespace,
            ),
            spec=client.V1ServiceSpec(
                cluster_ip="None",
                selector={"job-name": job_name},
                ports=[client.V1ServicePort(port=port, name="ddp")],
            ),
        )

    @staticmethod
    def build_conda_entrypoint(
        user_command: List[str],
        conda_env: Optional[str],
    ) -> Tuple[List[str], List[str], List[Dict[str, str]]]:
        """Wrap user command in a conda activation script if conda_env is set.

        Args:
            user_command: The original command list from EnvironmentConfig.
            conda_env:    Conda environment name; None means no wrapping.

        Returns:
            (command, args, extra_env_vars) tuple for the container spec.
            - command: entrypoint to use (bash wrapper inline or user command)
            - args:    arguments passed to the entrypoint
            - extra_env_vars: additional env vars to inject (e.g. GPUCTL_CONDA_ENV)
        """
        if not conda_env:
            return user_command, [], []

        # Inline conda activation wrapper
        wrapper_script = (
            "source /opt/conda/etc/profile.d/conda.sh && "
            "conda activate \"${GPUCTL_CONDA_ENV}\" && "
            'exec "$@"'
        )
        command = ["bash", "-c", wrapper_script, "--"]
        args = list(user_command)
        extra_env = [{"GPUCTL_CONDA_ENV": conda_env}]
        return command, args, extra_env

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
                                annotations: Dict[str, str] = None,
                                restart_policy: str = "Never",
                                workdirs: List[Dict[str, str]] = None,
                                priority_class_name: str = None,
                                namespace: str = None) -> client.V1PodTemplateSpec:
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

        all_volumes = []
        if workdirs:
            # workdir mounts 已在 build_container_spec 中设置到 container.volume_mounts
            all_volumes.extend(BaseBuilder.build_volumes(workdirs))

        # 自动追加 NFS volumes 和 mounts（向后兼容：NFS 未初始化时返回空列表）
        if namespace:
            nfs_volumes, nfs_mounts = BaseBuilder.build_nfs_volumes(namespace)
            all_volumes.extend(nfs_volumes)
            if nfs_mounts:
                existing = list(container.volume_mounts) if container.volume_mounts else []
                container.volume_mounts = existing + nfs_mounts

        if all_volumes:
            spec.volumes = all_volumes

        # 添加优先级类
        if priority_class_name:
            spec.priority_class_name = priority_class_name

        pod_labels = labels or {"app": "gpuctl-job"}
        metadata = client.V1ObjectMeta(labels=pod_labels, annotations=annotations)
        return client.V1PodTemplateSpec(metadata=metadata, spec=spec)
