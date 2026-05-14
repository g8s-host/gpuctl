"""Kubernetes backend.

Translates ``JobSpec`` into Kubernetes API objects directly, without going
through the existing per-kind builders. The legacy builder/client code paths
remain in place for the existing CLI flow; this backend is the forward-looking
implementation that both backends share an interface with.

In v0.10 the legacy CLI path (``gpuctl create -f`` against k8s) is still the
dominant path — see ``training_kind.py`` for how routing is selected.
"""

from __future__ import annotations

from typing import Iterator

from gpuctl.backend.base import (
    Backend,
    JobHandle,
    JobSpec,
    JobState,
    JobStatus,
)
from gpuctl.backend.errors import (
    BackendNotConfiguredError,
    JobAlreadyExistsError,
    JobNotFoundError,
    UnsupportedFeatureError,
)
from gpuctl.constants import DEFAULT_POOL, Kind, Labels


class KubernetesBackend:
    name = "kubernetes"

    def __init__(self) -> None:
        try:
            from gpuctl.client.base_client import KubernetesClient
        except ImportError as exc:  # pragma: no cover
            raise BackendNotConfiguredError(
                "kubernetes client library is not installed"
            ) from exc
        try:
            self._k8s = KubernetesClient()
        except RuntimeError as exc:
            raise BackendNotConfiguredError(str(exc)) from exc

    # ----- create -----

    def create_job(self, spec: JobSpec) -> JobHandle:
        if spec.kind == Kind.TRAINING:
            return self._create_training(spec)
        raise UnsupportedFeatureError(
            f"KubernetesBackend.create_job for kind={spec.kind!r} is not yet "
            f"implemented via the backend interface; use the legacy path."
        )

    def _create_training(self, spec: JobSpec) -> JobHandle:
        from kubernetes import client
        from kubernetes.client.rest import ApiException

        container = _build_container(spec)
        pod_spec = _build_pod_spec(spec, [container])
        labels = spec.labels_dict
        annotations = spec.annotations_dict

        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels=labels, annotations=annotations),
            spec=pod_spec,
        )
        job_spec = client.V1JobSpec(
            template=template,
            backoff_limit=3,
            ttl_seconds_after_finished=86400,
        )
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=spec.name, labels=labels, annotations=annotations
            ),
            spec=job_spec,
        )
        try:
            self._k8s.ensure_namespace_exists(spec.namespace)
            response = self._k8s.batch_v1.create_namespaced_job(spec.namespace, job)
        except ApiException as exc:
            if exc.status == 409:
                raise JobAlreadyExistsError(spec.name, spec.namespace) from exc
            raise
        return JobHandle(
            name=response.metadata.name,
            namespace=response.metadata.namespace,
            kind=spec.kind,
            backend=self.name,
            backend_ref=response.metadata.uid or response.metadata.name,
        )

    # ----- delete / get / list / logs -----

    def delete_job(self, name: str, namespace: str) -> None:
        from gpuctl.client.job_client import JobClient

        client = JobClient()
        try:
            client.delete_job(name, namespace)
        except FileNotFoundError:
            return  # idempotent

    def get_job(self, name: str, namespace: str) -> JobStatus:
        from gpuctl.client.job_client import JobClient

        info = JobClient().get_job(name, namespace)
        if not info:
            raise JobNotFoundError(name, namespace)
        return _job_info_to_status(name, namespace, info, backend=self.name)

    def list_jobs(
        self, namespace: str, labels: dict[str, str] | None = None
    ) -> list[JobStatus]:
        from gpuctl.client.job_client import JobClient

        rows = JobClient().list_jobs(namespace, labels=labels or {}, include_pods=False)
        return [
            _job_info_to_status(r["name"], namespace, r, backend=self.name)
            for r in rows
        ]

    def stream_logs(
        self, name: str, namespace: str, tail: int = 100, follow: bool = False
    ) -> Iterator[str]:
        from gpuctl.client.log_client import LogClient

        for line in LogClient().stream_job_logs(  # type: ignore[attr-defined]
            name, namespace, tail_lines=tail, follow=follow
        ):
            yield line

    def health_check(self) -> None:
        try:
            self._k8s.core_v1.list_namespace(limit=1, _request_timeout=5)
        except Exception as exc:
            raise BackendNotConfiguredError(
                f"kubernetes API not reachable: {exc}"
            ) from exc


# ---------- helpers ----------


def _build_container(spec: JobSpec):
    from kubernetes import client

    requests: dict[str, str] = {
        "cpu": f"{spec.cpu_millicores}m",
        "memory": str(spec.memory_bytes),
    }
    limits = dict(requests)
    if spec.gpu_count > 0:
        requests["nvidia.com/gpu"] = str(spec.gpu_count)
        limits["nvidia.com/gpu"] = str(spec.gpu_count)
    env_vars = [client.V1EnvVar(name=k, value=v) for k, v in spec.env]
    volume_mounts = [
        client.V1VolumeMount(
            name=f"workdir-{idx}",
            mount_path=mount.container_path,
            read_only=mount.read_only,
        )
        for idx, mount in enumerate(spec.workdirs)
    ]
    return client.V1Container(
        name="main",
        image=spec.image,
        command=list(spec.command) or None,
        args=list(spec.args) or None,
        env=env_vars or None,
        resources=client.V1ResourceRequirements(requests=requests, limits=limits),
        image_pull_policy="IfNotPresent",
        volume_mounts=volume_mounts or None,
    )


def _build_pod_spec(spec: JobSpec, containers: list):
    from kubernetes import client

    volumes = [
        client.V1Volume(
            name=f"workdir-{idx}",
            host_path=client.V1HostPathVolumeSource(
                path=mount.host_path, type="DirectoryOrCreate"
            ),
        )
        for idx, mount in enumerate(spec.workdirs)
    ]
    pod_spec = client.V1PodSpec(
        containers=containers,
        restart_policy=spec.restart_policy,
        volumes=volumes or None,
    )
    if spec.image_pull_secret:
        pod_spec.image_pull_secrets = [
            client.V1LocalObjectReference(name=spec.image_pull_secret)
        ]
    pool = spec.pool
    if pool and pool != DEFAULT_POOL:
        ns_selector: dict[str, str] = {Labels.POOL: pool}
        if spec.gpu_type:
            ns_selector[Labels.GPU_TYPE] = spec.gpu_type
        pod_spec.node_selector = ns_selector
    else:
        if spec.gpu_type:
            pod_spec.node_selector = {Labels.GPU_TYPE: spec.gpu_type}
        # Default-pool affinity: avoid nodes labelled with any pool.
        pod_spec.affinity = client.V1Affinity(
            node_affinity=client.V1NodeAffinity(
                required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
                    node_selector_terms=[
                        client.V1NodeSelectorTerm(
                            match_expressions=[
                                client.V1NodeSelectorRequirement(
                                    key=Labels.POOL, operator="DoesNotExist"
                                )
                            ]
                        )
                    ]
                )
            )
        )
    return pod_spec


def _job_info_to_status(
    name: str, namespace: str, info: dict, *, backend: str
) -> JobStatus:
    status_dict = info.get("status") or {}
    state = _coarse_state_from_k8s(status_dict)
    return JobStatus(
        name=name,
        namespace=info.get("namespace") or namespace,
        kind=Kind(info.get("labels", {}).get(Labels.JOB_TYPE, Kind.TRAINING)),
        state=state,
        backend=backend,
        node=None,
        container_id=None,
        started_at=info.get("start_time"),
        finished_at=info.get("completion_time"),
        exit_code=None,
        message=None,
        raw=info,
    )


def _coarse_state_from_k8s(status: dict) -> JobState:
    # Job
    if {"active", "succeeded", "failed"} & status.keys():
        if (status.get("succeeded") or 0) > 0:
            return JobState.SUCCEEDED
        if (status.get("failed") or 0) > 0:
            return JobState.FAILED
        if (status.get("active") or 0) > 0:
            return JobState.RUNNING
        return JobState.PENDING
    # Deployment / StatefulSet
    if "ready_replicas" in status:
        ready = status.get("ready_replicas") or 0
        desired = status.get("replicas") or 0
        if ready >= desired and desired > 0:
            return JobState.RUNNING
        return JobState.PENDING
    # Pod
    phase = status.get("phase")
    if phase == "Running":
        return JobState.RUNNING
    if phase == "Succeeded":
        return JobState.SUCCEEDED
    if phase == "Failed":
        return JobState.FAILED
    if phase == "Pending":
        return JobState.PENDING
    return JobState.UNKNOWN
