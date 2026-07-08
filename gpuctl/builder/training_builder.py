from kubernetes import client
from .base_builder import BaseBuilder
from gpuctl.api.training import TrainingJob
from gpuctl.constants import Labels, Kind, DEFAULT_POOL


class TrainingBuilder(BaseBuilder):
    """Training job builder"""

    @classmethod
    def _resolve_nfs_namespace(cls, training_job: TrainingJob, default_namespace: str) -> str:
        """Resolve the namespace used for NFS home path.

        If environment.notebook is set, look up the Notebook's namespace via K8s.
        Falls back to the job's own namespace if notebook not found or not set.
        """
        notebook_name = training_job.environment.notebook if training_job.environment else None
        if not notebook_name:
            return default_namespace
        try:
            from kubernetes import client as k8s_client, config as k8s_config
            import os
            if os.getenv("KUBERNETES_SERVICE_HOST"):
                k8s_config.load_incluster_config()
            else:
                k8s_config.load_kube_config()
            apps_v1 = k8s_client.AppsV1Api()
            # Use list across all namespaces with field selector instead of iterating
            result = apps_v1.list_stateful_set_for_all_namespaces(
                field_selector=f"metadata.name={notebook_name}"
            )
            if result.items:
                return result.items[0].metadata.namespace
        except Exception:
            pass
        return default_namespace

    @classmethod
    def build_job(cls, training_job: TrainingJob, namespace: str = "default") -> client.V1Job:
        """Build K8s Job resource"""
        workdirs = training_job.storage.workdirs if hasattr(training_job.storage, 'workdirs') else []

        # Resolve NFS namespace (may differ from job namespace if notebook is referenced)
        nfs_namespace = cls._resolve_nfs_namespace(training_job, namespace)

        # Apply conda entrypoint wrapper if conda env is specified
        env_config = training_job.environment
        original_command = list(env_config.command) if env_config.command else []
        conda_command, conda_args, conda_env_vars = cls.build_conda_entrypoint(
            original_command, env_config.conda
        )

        # Merge conda extra env vars into environment env list
        merged_env = list(env_config.env)
        merged_env.extend(conda_env_vars)

        # Build a patched env config with updated command/args/env
        patched_env = env_config.model_copy(update={
            "command": conda_command,
            "args": conda_args,
            "env": merged_env,
        })
        container = cls.build_container_spec(patched_env, training_job.resources, workdirs)

        # env 钉卡：仅显式 gpuIds 走这条路。去掉 nvidia.com/gpu 请求，改
        # NVIDIA_VISIBLE_DEVICES 直接圈 UUID/索引；默认 GPU 请求仍交给 device-plugin。
        gpu_ids = getattr(training_job.resources, "gpu_ids", None)
        if gpu_ids:
            for bucket in (container.resources.requests, container.resources.limits):
                if bucket:
                    bucket.pop("nvidia.com/gpu", None)
            container.env = list(container.env or []) + [
                client.V1EnvVar(name="NVIDIA_VISIBLE_DEVICES", value=",".join(str(g) for g in gpu_ids)),
                client.V1EnvVar(name="NVIDIA_DRIVER_CAPABILITIES", value="compute,utility"),
            ]

        pod_spec_extras = {}
        if training_job.environment.image_pull_secret:
            pod_spec_extras['image_pull_secrets'] = [
                client.V1LocalObjectReference(name=training_job.environment.image_pull_secret)
            ]

        # 处理资源池选择（env 钉卡时改为按节点钉，绕开 pool 亲和性）
        if gpu_ids:
            if getattr(training_job.resources, "node", None):
                pod_spec_extras['node_selector'] = {"kubernetes.io/hostname": training_job.resources.node}
        elif training_job.resources.pool and training_job.resources.pool != DEFAULT_POOL:
            # 对于非默认池，使用 node_selector
            node_selector = {}
            node_selector[Labels.POOL] = training_job.resources.pool
            if training_job.resources.gpu_type:
                node_selector[Labels.GPU_TYPE] = training_job.resources.gpu_type
            pod_spec_extras['node_selector'] = node_selector
        else:
            # 对于默认池或未指定池，使用 node_affinity 实现反亲和性
            # 确保 Pod 不会调度到带有 runwhere.ai/pool 标签的节点上
            if training_job.resources.gpu_type:
                # 如果指定了 GPU 类型，仍然使用 node_selector 来选择 GPU 类型
                node_selector = {}
                node_selector[Labels.GPU_TYPE] = training_job.resources.gpu_type
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

        # 获取优先级类名称
        from gpuctl.client.priority_client import PriorityConfig, PriorityLevel
        priority_config = PriorityConfig.PRIORITY_CLASSES.get(training_job.job.priority)
        priority_class_name = priority_config["name"] if priority_config else None

        # 分布式配置:节点数统一来自 resources.nodes(旧 distributed.workers 作兼容回退)
        from gpuctl.api.training import resolve_training_nodes
        nodes = resolve_training_nodes(training_job)
        is_distributed = nodes > 1

        # 构建 labels（distributed 模式需要 job-name 供 HeadlessService selector 使用）
        pod_labels = {
            Labels.JOB_TYPE: Kind.TRAINING,
            Labels.PRIORITY: training_job.job.priority,
            Labels.POOL: training_job.resources.pool or DEFAULT_POOL,
            Labels.NAMESPACE: namespace,
        }
        if is_distributed:
            pod_labels["job-name"] = training_job.job.name
            pod_spec_extras['subdomain'] = training_job.job.name + "-headless"

        # 构建 annotations，包含 description
        pod_annotations = {}
        if training_job.job.description:
            pod_annotations[Labels.DESCRIPTION] = training_job.job.description

        template = cls.build_pod_template_spec(
            container,
            pod_spec_extras,
            labels=pod_labels,
            annotations=pod_annotations,
            workdirs=workdirs,
            priority_class_name=priority_class_name,
            namespace=nfs_namespace,
        )

        # env 钉卡：强制 nvidia runtime（容器不再请求 nvidia.com/gpu，自动判定不会设它，故显式设）
        if gpu_ids:
            template.spec.runtime_class_name = "nvidia"

        if is_distributed:
            workers = nodes
            master_port = training_job.distributed.master_port
            job_name = training_job.job.name
            # Inject DDP environment variables into the container
            ddp_env = [
                client.V1EnvVar(
                    name="MASTER_ADDR",
                    value=f"{job_name}-0.{job_name}-headless.{namespace}.svc.cluster.local",
                ),
                client.V1EnvVar(name="MASTER_PORT", value=str(master_port)),
                client.V1EnvVar(name="WORLD_SIZE", value=str(workers)),
                client.V1EnvVar(
                    name="RANK",
                    value_from=client.V1EnvVarSource(
                        field_ref=client.V1ObjectFieldSelector(
                            field_path="metadata.annotations['batch.kubernetes.io/job-completion-index']"
                        )
                    ),
                ),
                client.V1EnvVar(name="LOCAL_RANK", value="0"),
                client.V1EnvVar(
                    name="GPUCTL_NPROC_PER_NODE",
                    value=str(training_job.resources.gpu or 1),
                ),
            ]
            existing_env = list(container.env) if container.env else []
            existing_names = {e.name for e in existing_env}
            container.env = existing_env + [e for e in ddp_env if e.name not in existing_names]

            job_spec = client.V1JobSpec(
                completion_mode="Indexed",
                completions=workers,
                parallelism=workers,
                template=template,
                backoff_limit=3,
                ttl_seconds_after_finished=86400,
            )
        else:
            job_spec = client.V1JobSpec(
                template=template,
                backoff_limit=3,
                ttl_seconds_after_finished=86400,
            )

        # 构建 metadata labels
        metadata_labels = {
            Labels.JOB_TYPE: Kind.TRAINING,
            Labels.PRIORITY: training_job.job.priority,
            Labels.POOL: training_job.resources.pool or DEFAULT_POOL,
            Labels.NAMESPACE: namespace
        }

        # 构建 metadata annotations，包含 description
        metadata_annotations = {}
        if training_job.job.description:
            metadata_annotations[Labels.DESCRIPTION] = training_job.job.description

        # 提交就睡（queue=true）：以 suspend 创建 + 打队列标签；v1 由 console 展示后人工放行。
        # priority/pool 标签已在 metadata_labels 里（runwhere.ai/priority、runwhere.ai/pool），
        # 此处只补队列专属的几个；submitted-at 走注解（label 值不允许冒号）。
        if getattr(training_job.job, "queue", False):
            from datetime import datetime, timezone
            job_spec.suspend = True
            metadata_labels.update({
                "runwhere.ai/queued": "true",
                "runwhere.ai/queue-state": "pending",
                "runwhere.ai/gpu-request": str(training_job.resources.gpu or 0),
                "runwhere.ai/owner": namespace,
            })
            metadata_annotations["runwhere.ai/submitted-at"] = (
                datetime.now(timezone.utc).isoformat()
            )

        metadata = client.V1ObjectMeta(
            name=f"{training_job.job.name}",
            labels=metadata_labels,
            annotations=metadata_annotations
        )

        return client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=metadata,
            spec=job_spec
        )
