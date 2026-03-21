---
hide:
  - navigation
  - toc
---

# GPUCTL · AI GPU Scheduling Platform

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle .card-icon } **No Kubernetes Knowledge Required**

    ---

    Submit training, inference, and Notebook jobs using declarative YAML familiar to ML engineers. The platform handles all underlying scheduling automatically.

    [:octicons-arrow-right-24: Quickstart](user-guide/quickstart.md)

-   :material-chip:{ .lg .middle .card-icon } **GPU Resource Pool Management**

    ---

    Partition cluster GPU nodes into logical resource pools, providing isolation between training, inference, and development workloads.

    [:octicons-arrow-right-24: Resource Pool](user-guide/pool.md)

-   :material-console:{ .lg .middle .card-icon } **Simple CLI Commands**

    ---

    `gpuctl create / get / logs / delete` — mirroring kubectl but optimized for ML engineers' workflows.

    [:octicons-arrow-right-24: CLI Reference](cli/index.md)

-   :material-api:{ .lg .middle .card-icon } **RESTful API**

    ---

    Full REST API support for integration with existing MLOps platforms or third-party toolchains.

    [:octicons-arrow-right-24: API Docs](developer-guide/api.md)

-   :material-eye:{ .lg .middle .card-icon } **Unified Observability**

    ---

    View logs, events, and resource usage in one place. `gpuctl logs <job-name>` works directly — no more hunting for Pod names with `kubectl get pods`.

    [:octicons-arrow-right-24: Monitoring Guide](user-guide/index.md)

-   :material-shield-check:{ .lg .middle .card-icon } **Automatic Quota Management**

    ---

    Namespace-level quotas created automatically. CPU / Memory / GPU limits visible at a glance. Requests exceeding quota are blocked with friendly error messages.

    [:octicons-arrow-right-24: Quota Management](user-guide/quota.md)

</div>

---

## Overview

**gpuctl** is an AI compute scheduling platform designed for ML engineers, built to **dramatically lower the barrier to GPU resource usage**.

Through declarative YAML configuration and simple CLI commands, ML engineers can efficiently submit and manage AI training and inference jobs without needing to learn Kubernetes internals.

### Core Problems Solved

<table width="100%">
  <tr>
    <th width="25%">Pain Point</th>
    <th width="35%">Impact</th>
    <th width="40%">gpuctl Solution</th>
  </tr>
  <tr>
    <td><b>😰 High Kubernetes Learning Curve</b><br>Pod, Deployment, Service concepts are complex</td>
    <td>ML engineers spend weeks learning Kubernetes concepts — PodSpec, ResourceRequirements, VolumeMounts. Submitting a job requires 100+ lines of YAML across multiple resource objects (Secret, ConfigMap, Job)</td>
    <td><b>Declarative YAML with familiar fields</b><br>Describe jobs using fields ML engineers already know: kind, job.name, resources.gpu. 15–20 lines of config to submit a training job, no K8s internals required</td>
  </tr>
  <tr>
    <td><b>😤 Complex GPU Environment Setup</b><br>Driver, CUDA, NCCL dependencies are fragile</td>
    <td>Every new environment requires manually installing GPU drivers, CUDA Toolkit, cuDNN, configuring NCCL multi-GPU env vars, and installing DeepSpeed/VLLM. Version conflicts are common; setup can take hours or days</td>
    <td><b>Pre-installed images, env vars injected automatically</b><br>Official images with DeepSpeed, VLLM, LlamaFactory pre-installed. Platform injects NCCL_SOCKET_IFNAME, MASTER_ADDR, WORLD_SIZE automatically — no manual distributed training config needed</td>
  </tr>
  <tr>
    <td><b>😫 Multi-team GPU Resource Contention</b><br>No resource isolation</td>
    <td>Training, inference, and experiment jobs share one cluster with no isolation. High-priority jobs get preempted by low-priority ones. One team running large-model training can monopolize all GPUs, blocking others</td>
    <td><b>Resource pool isolation + quota management</b><br>Partition the cluster into training, inference, and dev pools for physical isolation. Per-namespace CPU/Memory/GPU quotas are enforced automatically, ensuring fair resource allocation across teams</td>
  </tr>
  <tr>
    <td><b>😵 Complex Multi-GPU Training Configuration</b><br>NCCL and DeepSpeed params are verbose</td>
    <td>Single-node multi-GPU training requires manually configuring NCCL env vars, DeepSpeed hostfile, and PyTorch launch args. Misconfiguration leads to training hangs or low efficiency</td>
    <td><b>Declare GPU count, NCCL/DeepSpeed config injected automatically</b><br>Just set resources.gpu: 4 in YAML. The platform generates DeepSpeed config, injects NCCL env vars, and initializes process groups automatically</td>
  </tr>
  <tr>
    <td><b>😵‍💫 Tedious Job Status Inspection</b><br>Random Pod names are hard to remember</td>
    <td>With kubectl you must look up the random Pod name (e.g. training-job-7d9f4b8c5-x2mnp), run get pods, then describe pod. Pod restarts change names and require re-lookup</td>
    <td><b>Operate by job name, Pod changes tracked automatically</b><br>gpuctl get jobs shows all job statuses; gpuctl logs job-name streams logs directly with multi-replica aggregation. ML engineers only need to remember the job name they defined</td>
  </tr>
</table>

---

## Architecture

<div style="text-align: center;">
<img src="assets/architect.png" alt="gpuctl system architecture" style="width: 50%;">
</div>

---

## Supported Job Types

=== "Training Jobs"

    Ideal for LLM fine-tuning (LlamaFactory + DeepSpeed) and distributed training. Translates to a Kubernetes **Job**.

    ```yaml
    kind: training
    version: v0.1
    job:
      name: qwen2-7b-sft
      priority: high
    environment:
      image: registry.example.com/llama-factory-deepspeed:v0.8.0
      command: ["llama-factory-cli", "train", "--stage", "sft", "--model_name_or_path", "/models/qwen2-7b"]
    resources:
      pool: training-pool
      gpu: 4
      gpu-type: A100-100G
      cpu: 32
      memory: 128Gi
    ```

=== "Inference Services"

    Deploy VLLM inference services with auto-scaling support. Translates to a Kubernetes **Deployment + Service + HPA**.

    ```yaml
    kind: inference
    version: v0.1
    job:
      name: llama3-8b-inference
    environment:
      image: vllm/vllm-serving:v0.5.0
      command: ["python", "-m", "vllm.entrypoints.openai.api_server"]
    service:
      replicas: 2
      port: 8000
    resources:
      pool: inference-pool
      gpu: 1
      cpu: 8
      memory: 32Gi
    ```

=== "Notebook"

    Interactive development with JupyterLab. Translates to a Kubernetes **StatefulSet + Service**.

    ```yaml
    kind: notebook
    version: v0.1
    job:
      name: dev-notebook
    environment:
      image: registry.example.com/jupyter-ai:v1.0
    service:
      port: 8888
    resources:
      pool: dev-pool
      gpu: 1
      cpu: 8
      memory: 32Gi
    ```

=== "Compute Jobs"

    CPU-only services (nginx, redis, etc.). Translates to a Kubernetes **Deployment + Service**.

    ```yaml
    kind: compute
    version: v0.1
    job:
      name: test-nginx
    environment:
      image: nginx:latest
    service:
      replicas: 2
      port: 80
    resources:
      pool: test-pool
      gpu: 0
      cpu: 2
      memory: 4Gi
    ```

---

## Quick Start

```bash
# 1. Install
pip install -e .

# 2. Submit a training job
gpuctl create -f training-job.yaml

# 3. Check job status
gpuctl get jobs

# 4. Stream logs
gpuctl logs qwen2-7b-sft -f

# 5. Delete job
gpuctl delete job qwen2-7b-sft
```

[:octicons-arrow-right-24: Full Quickstart Guide](user-guide/quickstart.md){ .md-button .md-button--primary }
[:octicons-arrow-right-24: CLI Command Reference](cli/index.md){ .md-button }
