import math
import os
from typing import Dict, Any, List, Optional, Tuple

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from gpuctl.api.common import ResourceRequest, StorageConfig, parse_duration_seconds
from gpuctl.constants import Labels

_NFS_CONFIGMAP_NAME = "gpuctl-config"
_NFS_CONFIGMAP_NS = "kube-system"


def get_kubeconfig_for_cluster(cluster: Optional[str] = None) -> str:
    """获取指定集群或默认集群的 kubeconfig 路径
    
    Args:
        cluster: 集群名称，如果为 None 则使用默认集群
        
    Returns:
        str: kubeconfig 文件路径
        
    Raises:
        ValueError: 集群不存在
        FileNotFoundError: 没有配置且没有默认 kubeconfig
    """
    if cluster:
        # 使用指定集群
        from gpuctl.multicloud.config import get_cluster
        c = get_cluster(cluster)
        if not c:
            raise ValueError(f"Cluster '{cluster}' not found. Run 'gpuctl cluster list' to see available clusters.")
        return c.kubeconfig_path
    
    # 使用默认集群
    from gpuctl.multicloud.config import load_config
    registry = load_config()
    if registry.default_cluster:
        return get_kubeconfig_for_cluster(registry.default_cluster)
    
    # 回退到环境变量或默认路径
    kubeconfig = os.environ.get('KUBECONFIG')
    if kubeconfig:
        return kubeconfig
    
    default_path = os.path.expanduser("~/.kube/config")
    if os.path.exists(default_path):
        return default_path
    
    raise FileNotFoundError(
        "No cluster configured and no default kubeconfig found. "
        "Please run 'gpuctl cluster add' or set KUBECONFIG environment variable."
    )


def load_kubernetes_config(cluster: Optional[str] = None) -> None:
    """加载 Kubernetes 配置
    
    Args:
        cluster: 集群名称，如果为 None 则使用默认集群
    """
    kubeconfig_path = get_kubeconfig_for_cluster(cluster)
    config.load_kube_config(config_file=kubeconfig_path)


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
            import os
            if os.getenv("KUBERNETES_SERVICE_HOST"):
                k8s_config.load_incluster_config()
            else:
                k8s_config.load_kube_config()
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
    def build_headless_service(job_name: str, namespace: str, port: int = 29500,
                              publish_not_ready: bool = False) -> client.V1Service:
        """Build a HeadlessService for worker discovery (distributed training & multi-node serving).

        publish_not_ready=True 发布未就绪 Pod 的 DNS —— 多机 serving 必需:head 的 readiness 依赖
        worker 入群、worker 又要先解析到 head 才能入群,不发布未就绪地址会死锁。训练默认 False。
        """
        return client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(
                name=f"{job_name}-headless",
                namespace=namespace,
            ),
            spec=client.V1ServiceSpec(
                cluster_ip="None",
                publish_not_ready_addresses=publish_not_ready,
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
    def build_health_probes(service):
        """三件套健康探针(startup / liveness / readiness),供任何带 healthCheck 的服务复用。

        service.health_check 取值:
          - '/path'          → httpGet 探针(GET 该路径,看 2xx/3xx)
          - 'tcp' 或 'tcp:N'  → tcpSocket 探针(只看端口能否连上;给 redis 这类非 HTTP 服务)
        startupProbe 宽限 = service.startupTimeout(默认 10m);这段时间内挂起 liveness/readiness,
        慢启动不被杀。period / 单次 timeout / 失败阈值走合理默认,不向用户暴露 K8s 细节。
        无 health_check 时返回 (None, None, None)。
        """
        if not service or not getattr(service, "health_check", None):
            return None, None, None
        hc = service.health_check
        port = service.port
        if hc == "tcp" or hc.startswith("tcp:"):
            if ":" in hc:
                try:
                    port = int(hc.split(":", 1)[1])
                except ValueError:
                    pass
            action = {"tcp_socket": client.V1TCPSocketAction(port=port)}
        else:
            action = {"http_get": client.V1HTTPGetAction(path=hc, port=port)}

        def _probe(failure_threshold):
            # 单次检查给 5s(K8s 默认 1s 太紧);周期 10s。
            return client.V1Probe(
                timeout_seconds=5, period_seconds=10,
                failure_threshold=failure_threshold, **action,
            )

        grace = parse_duration_seconds(getattr(service, "startup_timeout", None) or "10m")
        # startup 失败阈值 = 宽限 / 周期;liveness/readiness 连续 3 次(≈30s)失败才动作。
        return _probe(max(1, math.ceil(grace / 10))), _probe(3), _probe(3)

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
    def build_telemetry_sidecar(pod_labels: Dict[str, str] = None) -> Optional[client.V1Container]:
        """遥测 sidecar(feature-flag 控制,默认关闭)。

        作为 native sidecar(initContainer + restartPolicy=Always)注入,主容器退出时
        随之终止,不破坏 Job 完成语义。仅靠 NVIDIA_VISIBLE_DEVICES 读【设备级】GPU 利用率,
        不申请 nvidia.com/gpu、不需要 privileged(见 docs/sidecar-agent-design.md §3 实测)。

        两种 agent 形态(GPUCTL_TELEMETRY_MODE):
          binary(默认):rw-telemetry-agent Go 二进制(探针框架,见 telemetry-agent/),
                         小镜像、可扩展(jupyter/metrics 等探针后续加)。用镜像 ENTRYPOINT。
          shell:纯 bash + /dev/tcp 兜底版(无需自建镜像,跑在 cuda base 上),仅 GPU 设备级。

        开关与配置(全部经 gpuctl 进程的环境变量):
          GPUCTL_TELEMETRY_ENDPOINT   设置即开启,如 http://runwhere-ai.runwhere-apps:8000/api/v1/telemetry
          GPUCTL_TELEMETRY_MODE       binary(默认)/ shell
          GPUCTL_TELEMETRY_INTERVAL   采样间隔秒,默认 5
          GPUCTL_TELEMETRY_NVIDIA_VISIBLE  默认 "all"(runw 设备级);生产可换本任务 GPU UUID
          GPUCTL_TELEMETRY_IMAGE      默认随 mode:binary→rw-telemetry-agent:dev,shell→nvidia/cuda 基础镜像
          GPUCTL_TELEMETRY_RUNTIME_CLASS  默认 "nvidia"(注入卡所需)
        """
        endpoint = os.getenv("GPUCTL_TELEMETRY_ENDPOINT")
        if not endpoint:
            return None  # 默认关闭

        from urllib.parse import urlsplit
        u = urlsplit(endpoint)
        host = u.hostname or ""
        if not host:
            return None
        port = str(u.port or (443 if u.scheme == "https" else 80))
        path = u.path or "/"

        mode = os.getenv("GPUCTL_TELEMETRY_MODE", "binary").strip().lower()
        interval = os.getenv("GPUCTL_TELEMETRY_INTERVAL", "5")
        visible = os.getenv("GPUCTL_TELEMETRY_NVIDIA_VISIBLE", "all")
        default_image = ("nvidia/cuda:12.2.2-base-ubuntu22.04" if mode == "shell"
                         else "rw-telemetry-agent:dev")
        image = os.getenv("GPUCTL_TELEMETRY_IMAGE", default_image)
        job_type = (pod_labels or {}).get(Labels.JOB_TYPE, "unknown")

        def _field(p: str) -> client.V1EnvVarSource:
            return client.V1EnvVarSource(
                field_ref=client.V1ObjectFieldSelector(field_path=p))

        # 两种模式共用:Go agent 读 RW_TELEMETRY_ENDPOINT;shell 读 RW_T_HOST/PORT/PATH。
        env = [
            client.V1EnvVar(name="NVIDIA_VISIBLE_DEVICES", value=visible),
            client.V1EnvVar(name="NVIDIA_DRIVER_CAPABILITIES", value="utility"),
            client.V1EnvVar(name="RW_TELEMETRY_ENDPOINT", value=endpoint),
            client.V1EnvVar(name="RW_T_HOST", value=host),
            client.V1EnvVar(name="RW_T_PORT", value=port),
            client.V1EnvVar(name="RW_T_PATH", value=path),
            client.V1EnvVar(name="RW_T_INTERVAL", value=str(interval)),
            client.V1EnvVar(name="RW_JOB_TYPE", value=job_type),
            client.V1EnvVar(name="RW_POD_NAME", value_from=_field("metadata.name")),
            client.V1EnvVar(name="RW_POD_NAMESPACE", value_from=_field("metadata.namespace")),
        ]

        # 纯 bash + /dev/tcp 上报,零依赖(cuda base 无 curl);nvidia-smi 由 runtime 注入
        shell_script = r'''set -u
H="$RW_T_HOST"; P="$RW_T_PORT"; UPATH="$RW_T_PATH"; IV="${RW_T_INTERVAL:-5}"
echo "[rw-telemetry] $RW_POD_NAMESPACE/$RW_POD_NAME type=$RW_JOB_TYPE -> $H:$P$UPATH every ${IV}s"
post() {
  exec 3<>"/dev/tcp/$H/$P" 2>/dev/null || { echo "[rw-telemetry] connect $H:$P fail"; return 1; }
  printf 'POST %s HTTP/1.1\r\nHost: %s\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%s' \
    "$UPATH" "$H" "${#1}" "$1" >&3
  head -c 64 <&3 >/dev/null 2>&1
  exec 3>&- 3<&- 2>/dev/null
}
while true; do
  L=$(nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null | head -1)
  I=$(echo "$L" | awk -F, '{gsub(/ /,"");print $1}')
  U=$(echo "$L" | awk -F, '{gsub(/ /,"");print $2}')
  MU=$(echo "$L" | awk -F, '{gsub(/ /,"");print $3}')
  MT=$(echo "$L" | awk -F, '{gsub(/ /,"");print $4}')
  B="{\"namespace\":\"$RW_POD_NAMESPACE\",\"pod\":\"$RW_POD_NAME\",\"job_type\":\"$RW_JOB_TYPE\",\"gpu_index\":${I:-0},\"gpu_util\":${U:-0},\"mem_used\":${MU:-0},\"mem_total\":${MT:-0}}"
  post "$B" || true
  sleep "$IV"
done
'''

        # 注意:不在构造器里传 restart_policy —— 老版本 k8s client 不识别该参数会报错。
        # native sidecar 的 restart_policy 由注入处按 client 能力设置(见 build_pod_template_spec)。
        kwargs = dict(
            name="rw-telemetry",
            image=image,
            image_pull_policy="IfNotPresent",
            env=env,
            resources=client.V1ResourceRequirements(
                requests={"cpu": "10m", "memory": "32Mi"},
                limits={"cpu": "200m", "memory": "128Mi"},
            ),
        )
        if mode == "shell":
            # 用 cuda base + bash 脚本;binary 模式则交给镜像 ENTRYPOINT。
            kwargs["command"] = ["bash", "-lc"]
            kwargs["args"] = [shell_script]
        return client.V1Container(**kwargs)

    @staticmethod
    def _container_requests_gpu(container: client.V1Container) -> bool:
        """容器是否申请了 nvidia.com/gpu(>0)。"""
        res = getattr(container, "resources", None)
        if not res:
            return False
        for bucket in (getattr(res, "limits", None), getattr(res, "requests", None)):
            if not bucket:
                continue
            v = bucket.get("nvidia.com/gpu")
            if v in (None, ""):
                continue
            try:
                if int(str(v)) > 0:
                    return True
            except (ValueError, TypeError):
                return True
        return False

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
            if 'subdomain' in pod_spec_extras:
                spec.subdomain = pod_spec_extras['subdomain']

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

        # GPU 指标采集 sidecar:仅 GPU 任务(gpu>0)注入,读该卡利用率/显存上报 console。
        # 上报端点由 console 启动时自动推导并写入 GPUCTL_TELEMETRY_ENDPOINT
        # (见 runwhere-ai src/console/telemetry_autoconfig.py);纯 CLI 无 console 时
        # 该 env 不设 → build_telemetry_sidecar 返回 None,不注入。
        sidecar = (BaseBuilder.build_telemetry_sidecar(pod_labels)
                   if BaseBuilder._container_requests_gpu(container) else None)
        if sidecar is not None:
            import inspect
            supports_native = "restart_policy" in inspect.signature(
                client.V1Container.__init__).parameters
            if supports_native:
                # native sidecar:initContainer + restartPolicy=Always。主容器退出即随之
                # 终止,不破坏 Job 完成语义(k8s 1.28+ / client v28+)。
                sidecar.restart_policy = "Always"
                spec.init_containers = (list(spec.init_containers) if spec.init_containers else []) + [sidecar]
            else:
                # 老 client 无 native sidecar:退回普通 sidecar。对 Deployment/StatefulSet 安全;
                # 对 Job 会阻止其完成(死循环常驻)—— 该路径仅作兜底,生产应升级 client。
                spec.containers = list(spec.containers) + [sidecar]
            rc = os.getenv("GPUCTL_TELEMETRY_RUNTIME_CLASS", "nvidia")
            if rc:
                spec.runtime_class_name = rc

        # GPU 工作负载必须用 nvidia 运行时类才能真正注入设备/驱动库;否则容器内
        # 无 /dev/nvidia*、无 nvidia-smi,CUDA 不可用(本集群 nvidia 是 RuntimeClass
        # 而非默认 runtime)。仅在申请了 GPU 且未设过 runtime_class 时设置;
        # env GPUCTL_GPU_RUNTIME_CLASS 可覆盖,设为空字符串可禁用(默认 runtime 已是 nvidia 的集群)。
        if spec.runtime_class_name is None and BaseBuilder._container_requests_gpu(container):
            gpu_rc = os.getenv("GPUCTL_GPU_RUNTIME_CLASS", "nvidia")
            if gpu_rc:
                spec.runtime_class_name = gpu_rc

        metadata = client.V1ObjectMeta(labels=pod_labels, annotations=annotations)
        return client.V1PodTemplateSpec(metadata=metadata, spec=spec)