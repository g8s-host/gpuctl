from kubernetes import client
from .base_builder import BaseBuilder
from gpuctl.api.inference import InferenceJob
from gpuctl.constants import Labels, Kind, DEFAULT_POOL, svc_name


class InferenceBuilder(BaseBuilder):
    """Inference job builder"""

    @classmethod
    def build_deployment(cls, inference_job: InferenceJob, namespace: str = "default") -> client.V1Deployment:
        """Build K8s Deployment resource"""
        workdirs = []
        if hasattr(inference_job, 'storage') and hasattr(inference_job.storage, 'workdirs'):
            workdirs = inference_job.storage.workdirs
        
        container = cls.build_container_spec(inference_job.environment, inference_job.resources, workdirs)

        pod_spec_extras = {}
        if inference_job.environment.image_pull_secret:
            pod_spec_extras['image_pull_secrets'] = [
                client.V1LocalObjectReference(name=inference_job.environment.image_pull_secret)
            ]

        # 处理资源池选择
        if inference_job.resources.pool and inference_job.resources.pool != DEFAULT_POOL:
            # 对于非默认池，使用 node_selector
            node_selector = {}
            node_selector[Labels.POOL] = inference_job.resources.pool
            if inference_job.resources.gpu_type:
                node_selector[Labels.GPU_TYPE] = inference_job.resources.gpu_type
            pod_spec_extras['node_selector'] = node_selector
        else:
            # 对于默认池或未指定池，使用 node_affinity 实现反亲和性
            # 确保 Pod 不会调度到带有 runwhere.ai/pool 标签的节点上
            if inference_job.resources.gpu_type:
                # 如果指定了 GPU 类型，仍然使用 node_selector 来选择 GPU 类型
                node_selector = {}
                node_selector[Labels.GPU_TYPE] = inference_job.resources.gpu_type
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

        # 健康探针(startup + liveness + readiness)统一由 BaseBuilder 生成(支持 http 路径与 tcp)。
        container.startup_probe, container.liveness_probe, container.readiness_probe = \
            cls.build_health_probes(inference_job.service)

        app_label = f"{inference_job.job.name}"
        
        # 获取优先级类名称
        from gpuctl.client.priority_client import PriorityConfig, PriorityLevel
        priority_config = PriorityConfig.PRIORITY_CLASSES.get(inference_job.job.priority)
        priority_class_name = priority_config["name"] if priority_config else None
        
        # 构建 labels
        pod_labels = {
            "app": app_label,
            Labels.JOB_TYPE: Kind.INFERENCE,
            Labels.PRIORITY: inference_job.job.priority,
            Labels.POOL: inference_job.resources.pool or DEFAULT_POOL,
            Labels.NAMESPACE: namespace
        }

        # 构建 annotations，包含 description
        pod_annotations = {}
        if inference_job.job.description:
            pod_annotations[Labels.DESCRIPTION] = inference_job.job.description

        template = cls.build_pod_template_spec(
            container,
            pod_spec_extras,
            labels=pod_labels,
            annotations=pod_annotations,
            restart_policy="Always",
            workdirs=workdirs,
            priority_class_name=priority_class_name,
            namespace=namespace,
        )

        deployment_spec = client.V1DeploymentSpec(
            replicas=inference_job.service.replicas,
            template=template,
            selector=client.V1LabelSelector(
                match_labels={"app": app_label}
            )
        )

        # 构建 metadata labels
        metadata_labels = {
            Labels.JOB_TYPE: Kind.INFERENCE,
            Labels.PRIORITY: inference_job.job.priority,
            Labels.POOL: inference_job.resources.pool or DEFAULT_POOL,
            Labels.NAMESPACE: namespace
        }

        # 构建 metadata annotations，包含 description
        metadata_annotations = {}
        if inference_job.job.description:
            metadata_annotations[Labels.DESCRIPTION] = inference_job.job.description

        metadata = client.V1ObjectMeta(
            name=app_label,
            labels=metadata_labels,
            annotations=metadata_annotations
        )

        return client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=metadata,
            spec=deployment_spec
        )

    @classmethod
    def build_service(cls, inference_job: InferenceJob, namespace: str = "default",
                      head_only: bool = False) -> client.V1Service:
        """Build K8s Service resource (NodePort).

        head_only=True(多机 serving):selector 只命中 StatefulSet 的 pod-0(head),因为只有
        head 暴露 API;worker pod 同带 app 标签但不应接流量。pod-0 由 StatefulSet 控制器自动
        打上 statefulset.kubernetes.io/pod-name=<name>-0 标签。
        """
        app_label = f"{inference_job.job.name}"
        selector = ({"statefulset.kubernetes.io/pod-name": f"{app_label}-0"}
                    if head_only else {"app": app_label})
        service_spec = client.V1ServiceSpec(
            selector=selector,
            ports=[client.V1ServicePort(
                port=inference_job.service.port,
                target_port=inference_job.service.port
            )],
            type="NodePort"
        )

        metadata_annotations = {}
        if inference_job.job.description:
            metadata_annotations[Labels.DESCRIPTION] = inference_job.job.description

        metadata = client.V1ObjectMeta(
            name=svc_name(inference_job.job.name),
            labels={
                Labels.JOB_TYPE: Kind.INFERENCE,
                Labels.POOL: inference_job.resources.pool or DEFAULT_POOL,
                Labels.NAMESPACE: namespace
            },
            annotations=metadata_annotations
        )

        return client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=metadata,
            spec=service_spec
        )

    @classmethod
    def build_statefulset(cls, inference_job: InferenceJob, namespace: str = "default") -> client.V1StatefulSet:
        """Build a StatefulSet for multi-node (model-parallel) serving.

        一个逻辑副本 = `nodes` 个 Pod:pod-0 = head(对外 API + 集群头,如 ray --head),
        pod-1..N-1 = worker(加入 head 的集群)。head/worker 分工由用户命令按 RUNWHERE_NODE_RANK 决定。

        要点(见 InferenceKind 与本方法注释):
          - serviceName 指向 Headless Service(<name>-headless),提供 <name>-0.<...> 稳定 DNS;
          - podManagementPolicy=Parallel:否则 head 等 worker、worker 等 head,顺序启动会死锁;
          - 不设 http 健康探针:worker 不跑 API,liveness 会反复杀掉 worker;
          - 注入 RUNWHERE_* 引导变量(节点数 / 本节点序号 / head 地址 / 每节点卡数)。
        """
        nodes = inference_job.resources.nodes or 1
        workdirs = inference_job.storage.workdirs if hasattr(inference_job, 'storage') and hasattr(inference_job.storage, 'workdirs') else []

        container = cls.build_container_spec(inference_job.environment, inference_job.resources, workdirs)
        # 注意:多机刻意不设 startup/liveness/readiness http 探针 —— 仅 head 跑 API,
        # 给 worker 套 http liveness 会被反复重启。

        # 注入集群引导变量(RUNWHERE_* 契约):用户命令据此区分 head/worker 并互连。
        headless_name = f"{inference_job.job.name}-headless"
        head_addr = f"{inference_job.job.name}-0.{headless_name}.{namespace}.svc.cluster.local"
        boot_env = [
            client.V1EnvVar(name="RUNWHERE_NUM_NODES", value=str(nodes)),
            client.V1EnvVar(name="RUNWHERE_GPUS_PER_NODE", value=str(inference_job.resources.gpu or 0)),
            client.V1EnvVar(name="RUNWHERE_HEAD_ADDR", value=head_addr),
            client.V1EnvVar(
                name="RUNWHERE_NODE_RANK",
                value_from=client.V1EnvVarSource(
                    field_ref=client.V1ObjectFieldSelector(
                        # StatefulSet 控制器自动注入的序号标签(k8s 1.28+)
                        field_path="metadata.labels['apps.kubernetes.io/pod-index']"
                    )
                ),
            ),
        ]
        existing_env = list(container.env) if container.env else []
        existing_names = {e.name for e in existing_env}
        container.env = existing_env + [e for e in boot_env if e.name not in existing_names]

        pod_spec_extras = {}
        if inference_job.environment.image_pull_secret:
            pod_spec_extras['image_pull_secrets'] = [
                client.V1LocalObjectReference(name=inference_job.environment.image_pull_secret)
            ]

        # 资源池选择(与 build_deployment 同逻辑)
        if inference_job.resources.pool and inference_job.resources.pool != DEFAULT_POOL:
            node_selector = {Labels.POOL: inference_job.resources.pool}
            if inference_job.resources.gpu_type:
                node_selector[Labels.GPU_TYPE] = inference_job.resources.gpu_type
            pod_spec_extras['node_selector'] = node_selector
        else:
            if inference_job.resources.gpu_type:
                pod_spec_extras['node_selector'] = {Labels.GPU_TYPE: inference_job.resources.gpu_type}
            pod_spec_extras['affinity'] = client.V1Affinity(
                node_affinity=client.V1NodeAffinity(
                    required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
                        node_selector_terms=[client.V1NodeSelectorTerm(
                            match_expressions=[client.V1NodeSelectorRequirement(
                                key=Labels.POOL, operator="DoesNotExist"
                            )]
                        )]
                    )
                )
            )

        app_label = f"{inference_job.job.name}"

        from gpuctl.client.priority_client import PriorityConfig
        priority_config = PriorityConfig.PRIORITY_CLASSES.get(inference_job.job.priority)
        priority_class_name = priority_config["name"] if priority_config else None

        pod_labels = {
            Labels.APP: app_label,
            Labels.JOB_NAME: app_label,   # 供 Headless Service(build_headless_service 用 job-name)选中
            Labels.JOB_TYPE: Kind.INFERENCE,
            Labels.PRIORITY: inference_job.job.priority,
            Labels.POOL: inference_job.resources.pool or DEFAULT_POOL,
            Labels.NAMESPACE: namespace,
        }
        pod_annotations = {}
        if inference_job.job.description:
            pod_annotations[Labels.DESCRIPTION] = inference_job.job.description

        template = cls.build_pod_template_spec(
            container,
            pod_spec_extras,
            labels=pod_labels,
            annotations=pod_annotations,
            restart_policy="Always",
            workdirs=workdirs,
            priority_class_name=priority_class_name,
            namespace=namespace,
        )

        statefulset_spec = client.V1StatefulSetSpec(
            replicas=nodes,                       # N 个 Pod = N 个节点 = 这一个逻辑副本
            template=template,
            selector=client.V1LabelSelector(match_labels={Labels.APP: app_label}),
            service_name=headless_name,
            pod_management_policy="Parallel",     # head/worker 同时起,避免相互等待死锁
        )

        metadata_labels = {
            Labels.JOB_TYPE: Kind.INFERENCE,
            Labels.PRIORITY: inference_job.job.priority,
            Labels.POOL: inference_job.resources.pool or DEFAULT_POOL,
            Labels.NAMESPACE: namespace,
        }
        metadata_annotations = {}
        if inference_job.job.description:
            metadata_annotations[Labels.DESCRIPTION] = inference_job.job.description

        metadata = client.V1ObjectMeta(
            name=app_label,
            labels=metadata_labels,
            annotations=metadata_annotations,
        )

        return client.V1StatefulSet(
            api_version="apps/v1",
            kind="StatefulSet",
            metadata=metadata,
            spec=statefulset_spec,
        )

