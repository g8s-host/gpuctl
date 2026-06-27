# User Guide

Welcome to gpuctl! This guide will help you master gpuctl's core features from scratch and efficiently manage GPU compute resources.

## Contents

<div class="grid cards" markdown>

-   :material-clock-fast:{ .lg .middle } **Quickstart**

    ---

    Complete installation and submit your first job in under 5 minutes.

    [:octicons-arrow-right-24: Quickstart](quickstart.md)

-   :material-brain:{ .lg .middle } **Training Jobs**

    ---

    LlamaFactory and DeepSpeed distributed training, with complete examples for single-node multi-GPU and multi-node multi-GPU scenarios.

    [:octicons-arrow-right-24: Training Jobs](training.md)

-   :material-server:{ .lg .middle } **Inference Services**

    ---

    Deploy inference services using VLLM and similar frameworks, with multi-replica and auto-scaling support.

    [:octicons-arrow-right-24: Inference Services](inference.md)

-   :material-notebook:{ .lg .middle } **Notebook**

    ---

    Launch a JupyterLab environment with GPU resources attached in one command, for rapid prototyping.

    [:octicons-arrow-right-24: Notebook Development](notebook.md)

-   :material-database:{ .lg .middle } **Persistent Storage**

    ---

    Transparent NFS storage: a persistent `/home/jovyan` and shared `/datasets` on every job, with zero config in your YAML.

    [:octicons-arrow-right-24: Persistent Storage](storage.md)

-   :material-cog:{ .lg .middle } **Compute Jobs**

    ---

    Deploy CPU services like nginx and redis without worrying about Kubernetes Deployment details.

    [:octicons-arrow-right-24: Compute Jobs](compute.md)

-   :material-pool:{ .lg .middle } **Resource Pool Management**

    ---

    Partition nodes into resource pools for training/inference isolation and fine-grained scheduling.

    [:octicons-arrow-right-24: Resource Pool Management](pool.md)

-   :material-gauge:{ .lg .middle } **Quotas & Namespaces**

    ---

    Set CPU, memory, and GPU quotas per team or user to prevent resource abuse.

    [:octicons-arrow-right-24: Quotas & Namespaces](quota.md)

</div>

---

## YAML Configuration Overview

All resources are defined through declarative YAML. The following describes the common fields:

```yaml
kind: training          # Job type: training / inference / notebook / compute / pool / quota
version: v0.1           # Version, currently fixed at v0.1

job:
  name: my-job          # Job name (also used as the K8s resource name)
  priority: medium      # Priority: high / medium / low
  description: "..."    # Optional description

environment:
  image: my-image:tag   # Container image
  imagePullSecret: xxx  # Image pull secret (optional)
  command: [...]        # Startup command
  args: [...]           # Command arguments (optional)
  env:                  # Environment variables (optional)
    - name: KEY
      value: VALUE

resources:
  pool: default         # Resource pool name (default: default)
  gpu: 0                # Number of GPUs (0 for CPU-only jobs)
  gpuType: A100-80G     # GPU model (optional, K8s schedules any GPU if omitted)
  cpu: 4                # CPU cores
  memory: 8Gi           # Memory size

service:                # Only applicable to inference / notebook / compute
  replicas: 1           # Number of replicas
  port: 8080            # Service port
  healthCheck: /health  # Health check path (optional)

storage:                # Optional & legacy hostPath mounts — most jobs omit this
  workdirs:             # (persistent /home/jovyan + /datasets are auto-mounted via NFS)
    - path: /scratch/cache
```

!!! tip "Persistent storage is automatic"
    You do **not** need a `storage` section for persistent data. When the operator has run `gpuctl init`, every job auto-mounts a per-namespace `/home/jovyan` (read-write) and a shared `/datasets` (read-only) over NFS. The `storage.workdirs` field is a separate, optional `hostPath` mechanism. See [Persistent Storage](storage.md).

!!! tip "Naming Rules"
    The `job.name` field is used directly as the Kubernetes resource `metadata.name`. Names must follow K8s naming conventions: lowercase letters, numbers, and hyphens only, max 63 characters.
