"""
Centralised constants for the gpuctl project.

Every magic string that appears in more than one module should live here.
Import from this module instead of sprinkling literals across the codebase.
"""

from enum import Enum


# ── Kind (job type) ──────────────────────────────────────────────────────────

class Kind(str, Enum):
    TRAINING = "training"
    INFERENCE = "inference"
    NOTEBOOK = "notebook"
    COMPUTE = "compute"


JOB_KINDS: tuple[str, ...] = tuple(k.value for k in Kind)

NON_JOB_KINDS: tuple[str, ...] = ("quota", "pool", "resource")

ALL_KINDS: tuple[str, ...] = JOB_KINDS + NON_JOB_KINDS

KINDS_WITH_SERVICE: tuple[str, ...] = (
    Kind.INFERENCE, Kind.NOTEBOOK, Kind.COMPUTE,
)


# ── K8s resource type ────────────────────────────────────────────────────────

class K8sResourceType(str, Enum):
    JOB = "Job"
    DEPLOYMENT = "Deployment"
    STATEFULSET = "StatefulSet"
    POD = "Pod"
    SERVICE = "Service"


KIND_TO_RESOURCE: dict[str, str] = {
    Kind.TRAINING:  K8sResourceType.JOB,
    Kind.INFERENCE: K8sResourceType.DEPLOYMENT,
    Kind.NOTEBOOK:  K8sResourceType.STATEFULSET,
    Kind.COMPUTE:   K8sResourceType.DEPLOYMENT,
}


def infer_resource_type(status_dict: dict, job_type: str) -> str:
    """Infer K8s resource type from status fields, falling back to kind mapping."""
    if "phase" in status_dict:
        return K8sResourceType.POD
    if "ready_replicas" in status_dict:
        return (K8sResourceType.STATEFULSET
                if job_type == Kind.NOTEBOOK
                else K8sResourceType.DEPLOYMENT)
    if {"active", "succeeded", "failed"} <= status_dict.keys():
        return K8sResourceType.JOB
    return KIND_TO_RESOURCE.get(job_type, K8sResourceType.POD)


# ── Priority ─────────────────────────────────────────────────────────────────

class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


DEFAULT_PRIORITY = Priority.MEDIUM


# ── Label keys ───────────────────────────────────────────────────────────────

class Labels:
    JOB_TYPE   = "runwhere.ai/job-type"
    PRIORITY   = "runwhere.ai/priority"
    POOL       = "runwhere.ai/pool"
    NAMESPACE  = "runwhere.ai/namespace"
    GPU_TYPE       = "runwhere.ai/gpuType"
    GPU_TYPE_KEBAB = "runwhere.ai/gpu-type"
    PORT       = "runwhere.ai/port"
    DESCRIPTION = "runwhere.ai/description"
    QUOTA      = "runwhere.ai/quota"
    NS_MARKER  = "runwhere.ai/namespace"

    APP        = "app"
    JOB_NAME   = "job-name"


NS_LABEL_SELECTOR = f"{Labels.NS_MARKER}=true"


# ── Service naming ───────────────────────────────────────────────────────────

SVC_PREFIX = "svc-"


def svc_name(job_name: str) -> str:
    """Canonical service name for a given job name."""
    return f"{SVC_PREFIX}{job_name}"


# ── Pod phase → display status ───────────────────────────────────────────────

PHASE_TO_STATUS: dict[str, str] = {
    "Pending":     "Pending",
    "Running":     "Running",
    "Succeeded":   "Succeeded",
    "Failed":      "Failed",
    "Unknown":     "Unknown",
    "Completed":   "Completed",
    "Terminating": "Terminating",
    "Deleting":    "Deleting",
}

# Container waiting reasons that map directly to a display status.
CONTAINER_WAITING_REASONS: dict[str, str] = {
    "ImagePullBackOff":           "ImagePullBackOff",
    "ErrImagePull":               "ErrImagePull",
    "CrashLoopBackOff":           "CrashLoopBackOff",
    "CreateContainerConfigError": "CreateContainerConfigError",
    "CreateContainerError":       "CreateContainerError",
    "ContainerCreating":          "ContainerCreating",
    "InvalidImageName":           "InvalidImageName",
    "ImageInspectError":          "ImageInspectError",
    "RegistryUnavailable":        "RegistryUnavailable",
    "RunInitContainerError":      "RunInitContainerError",
    "Resizing":                   "Resizing",
    "Restarting":                 "Restarting",
    "Waiting":                    "Waiting",
    "Terminating":                "Terminating",
    "Unknown":                    "Unknown",
}


def get_detailed_status(waiting_reason: str, waiting_message: str) -> str:
    """Resolve a container waiting reason to a user-facing status string."""
    if waiting_reason in CONTAINER_WAITING_REASONS:
        return CONTAINER_WAITING_REASONS[waiting_reason]
    if "BackOff" in waiting_reason:
        return "BackOff"
    msg_lower = waiting_message.lower()
    if "NotFound" in waiting_reason or "not found" in msg_lower:
        return "NotFound"
    if "Permission" in waiting_reason or "denied" in msg_lower:
        return "PermissionDenied"
    if "Storage" in waiting_reason or "storage" in msg_lower:
        return "StorageError"
    return waiting_reason if waiting_reason else "Waiting"


# ── Default values ───────────────────────────────────────────────────────────

DEFAULT_NAMESPACE = "default"
DEFAULT_POOL = "default"
