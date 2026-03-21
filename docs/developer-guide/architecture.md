# Architecture

This document describes gpuctl's layered architecture, core module responsibilities, data model and K8s resource mapping, and the label system.

---

## Overall Architecture

gpuctl uses a layered design with clear responsibilities at each layer:

```
┌────────────────────────────────────────────────────┐
│                    User Layer                        │
│  gpuctl CLI (argparse)  ·  REST API (FastAPI)       │
└────────────────────────┬───────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────┐
│               Parsing & Validation Layer             │
│  parser/base_parser.py                              │
│  · Reads YAML files                                 │
│  · Dispatches to Pydantic models by kind            │
│  · Field validation (required, range, format)       │
└────────────────────────┬───────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────┐
│                  Builder Layer                       │
│  builder/training_builder.py  → K8s Job            │
│  builder/inference_builder.py → K8s Deployment     │
│  builder/notebook_builder.py  → K8s StatefulSet    │
│  builder/compute_builder.py   → K8s Deployment     │
│  builder/base_builder.py      → Shared methods     │
└────────────────────────┬───────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────┐
│              K8s Client Layer                        │
│  client/job_client.py    Job CRUD                   │
│  client/pool_client.py   Pools (ConfigMap + Label)  │
│  client/quota_client.py  ResourceQuota + Namespace  │
│  client/log_client.py    Pod logs (streaming)       │
│  client/base_client.py   K8s connection & utils     │
└────────────────────────┬───────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────┐
│              Kubernetes API Server                   │
│         Job · Deployment · StatefulSet              │
│         Service · ConfigMap · ResourceQuota         │
└────────────────────────────────────────────────────┘
```

---

## Kind → K8s Resource Mapping

| Kind | K8s Primary Resource | API Group | Associated Service | Notes |
|------|---------------------|-----------|-------------------|-------|
| `training` | `Job` | `batch/v1` | None | One-shot training, terminates on completion |
| `inference` | `Deployment` | `apps/v1` | `svc-{name}` (NodePort) | Long-running inference service |
| `notebook` | `StatefulSet` | `apps/v1` | `svc-{name}` (NodePort) | Stateful development environment |
| `compute` | `Deployment` | `apps/v1` | `svc-{name}` (NodePort) | General-purpose CPU service |

---

## Naming Rules

All names derive from the YAML `job.name` field:

| Resource | Naming Rule | Example (`job.name: my-inference`) |
|----------|------------|-------------------------------------|
| Primary resource | `{name}` | `my-inference` |
| Service | `svc-{name}` | `svc-my-inference` |
| Pod (training) | `{name}-{random5}` | `my-training-zlflg` |
| Pod (inference) | `{name}-{rs-hash}-{pod-hash}` | `my-inference-854c6c5cd-kfh77` |
| Pod (notebook) | `{name}-{index}` | `my-notebook-0` |

---

## Label System

### Common Labels (all kinds)

| Label Key | Value | Purpose |
|-----------|-------|---------|
| `runwhere.ai/job-type` | `training` / `inference` / `notebook` / `compute` | Identify job type |
| `runwhere.ai/priority` | `high` / `medium` / `low` | Scheduling priority |
| `runwhere.ai/pool` | pool name or `default` | Bind to resource pool |
| `runwhere.ai/namespace` | namespace name | Record owning namespace |

### Reverse-Lookup Labels (Pod → job.name)

Used by `get jobs` to look up the original job name from a Pod:

| Kind | Label Key | How Set |
|------|-----------|---------|
| inference / notebook / compute | `app: {name}` | Set manually in Pod template by Builder |
| training | `job-name: {name}` | Set automatically by K8s Job controller |

Code implementation:

```python
def _get_job_name(labels: dict) -> str:
    return labels.get('app') or labels.get('job-name') or ''
```

### Node Labels (resource pool & GPU model)

| Label Key | Purpose |
|-----------|---------|
| `runwhere.ai/pool` | Mark which resource pool a node belongs to |
| `runwhere.ai/gpuType` | Mark GPU model (gpuctl internal use) |
| `runwhere.ai/gpu-type` | Mark GPU model (user-facing label) |

---

## Storage Mount Mechanism

Each `path` in `storage.workdirs` expands into a `Volume + VolumeMount` pair (hostPath type):

```
# gpuctl YAML (user-written)
storage:
  workdirs:
    - path: /models
    - path: /output

         ↓ Builder expands

# K8s Pod Spec (auto-generated by platform)
spec:
  volumes:
    - name: workdir-0
      hostPath: { path: /models, type: DirectoryOrCreate }
    - name: workdir-1
      hostPath: { path: /output, type: DirectoryOrCreate }
  containers:
    - volumeMounts:
        - { name: workdir-0, mountPath: /models }
        - { name: workdir-1, mountPath: /output }
```

**Key point**: The `path` field serves as both the host path and the container mount path — they are identical.

---

## `get jobs` Output Columns

`get jobs` queries Pods directly; each row represents one Pod instance:

| Column | Meaning | Data Source |
|--------|---------|-------------|
| JOB ID | Pod name (with hash) | `pod.metadata.name` |
| NAME | YAML `job.name` | `_get_job_name(pod.labels)` |
| NAMESPACE | Namespace | `pod.metadata.namespace` |
| KIND | Job type | label `runwhere.ai/job-type` |
| STATUS | Pod status | `pod.status.phase` + container status |
| READY | Ready/total containers | `container_statuses` |
| NODE | Scheduled node | `pod.spec.node_name` |
| IP | Pod IP | `pod.status.pod_ip` |
| AGE | Time since creation | `pod.metadata.creation_timestamp` |

---

## apply Semantics

`gpuctl apply -f xxx.yaml` is equivalent to:

```
delete (remove old resource + Service)
    +
create (recreate resource + Service)
```

That is, **delete then recreate** to implement configuration update semantics.

---

## Status Calculation Rules

The Status field shown by `describe job` is derived from K8s resource state:

| Resource Type | Status Logic |
|--------------|-------------|
| Job | `succeeded > 0` → Succeeded, `failed > 0` → Failed, `active > 0` → Running, else Pending |
| Deployment | `ready == desired && > 0` → Running, `ready > 0` → Partially Running, else Pending |
| StatefulSet | `readyReplicas >= replicas && > 0` → Running, `readyReplicas > 0` → Partially Running, else Pending |

---

## Constants File

[`gpuctl/constants.py`](https://github.com/runwhere-ai/gpuctl/blob/main/gpuctl/constants.py) centralizes all magic strings, including:

- `Kind` enum: TRAINING / INFERENCE / NOTEBOOK / COMPUTE
- `Labels` class: all label key constants
- `KIND_TO_RESOURCE` mapping: Kind → K8s resource type
- `CONTAINER_WAITING_REASONS`: container waiting states → user-friendly status strings
- `DEFAULT_NAMESPACE / DEFAULT_POOL`: default values

All modules should import constants from this file rather than hardcoding strings elsewhere.
