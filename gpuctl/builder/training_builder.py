from kubernetes import client
from .base_builder import BaseBuilder
from gpuctl.api.training import TrainingJob
from gpuctl.constants import Labels, Kind, DEFAULT_POOL


class TrainingBuilder(BaseBuilder):
    """Training job builder"""

    @classmethod
    def build_job(cls, training_job: TrainingJob, namespace: str = "default") -> client.V1Job:
        """Build K8s Job resource"""
        workdirs = training_job.storage.workdirs if hasattr(training_job.storage, 'workdirs') else []
        
        container = cls.build_container_spec(training_job.environment, training_job.resources, workdirs)

        pod_spec_extras = {}
        if training_job.environment.image_pull_secret:
            pod_spec_extras['image_pull_secrets'] = [
                client.V1LocalObjectReference(name=training_job.environment.image_pull_secret)
            ]

        # 处理资源池选择
        if training_job.resources.pool and training_job.resources.pool != DEFAULT_POOL:
            # 对于非默认池，使用 node_selector
            node_selector = {}
            node_selector[Labels.POOL] = training_job.resources.pool
            if training_job.resources.gpu_type:
                node_selector[Labels.GPU_TYPE] = training_job.resources.gpu_type
            pod_spec_extras['node_selector'] = node_selector
        else:
            # 对于默认池或未指定池，使用 node_affinity 实现反亲和性
            # 确保 Pod 不会调度到带有 g8s.host/pool 标签的节点上
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

        # 构建 labels
        pod_labels = {
            Labels.JOB_TYPE: Kind.TRAINING,
            Labels.PRIORITY: training_job.job.priority,
            Labels.POOL: training_job.resources.pool or DEFAULT_POOL,
            Labels.NAMESPACE: namespace
        }

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
            priority_class_name=priority_class_name
        )

        job_spec = client.V1JobSpec(
            template=template,
            backoff_limit=3,
            ttl_seconds_after_finished=86400
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