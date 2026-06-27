# Inference Services

Inference jobs (`kind: inference`) are designed for long-running model inference API services. By default they map to a Kubernetes **Deployment + NodePort Service**, with support for multi-replica deployment. For a model too large for a single node, set `nodes: N` and the job maps to a **StatefulSet + Headless Service** instead (see [Distributed Inference](#distributed-inference)).

## Full YAML Fields

```yaml
kind: inference
version: v0.1

job:
  name: <service-name>
  priority: medium
  description: "..."

environment:
  image: <image>
  command: [...]
  args: [...]
  env:
    - name: KEY
      value: VALUE

service:
  replicas: 2            # Number of replicas (default: 1; data-parallel copies)
  port: 8000             # Service port
  healthCheck: /health   # Health check path (optional)

resources:
  pool: inference-pool   # Dedicated inference resource pool
  nodes: 1               # Nodes ONE replica spans (default 1). >1 = multi-node serving
                         #   (model sharded across nodes). See "Distributed Inference".
  gpu: 1                 # GPUs per pod (tensor-parallel within a node = just raise this)
  gpuType: A100-100G    # Optional
  cpu: 8
  memory: 32Gi

storage:
  workdirs:
    - path: /models
```

---

## Example 1: VLLM High-Throughput Inference Service

Deploy Llama3-8B with VLLM to provide a high-throughput OpenAI-compatible API.

```yaml title="llama3-inference.yaml"
kind: inference
version: v0.1

job:
  name: llama3-8b-inference
  priority: medium
  description: "Llama3-8B VLLM inference service"

environment:
  image: vllm/vllm-serving:v0.5.0
  command:
    - "python"
    - "-m"
    - "vllm.entrypoints.openai.api_server"
  args:
    - "--model"
    - "/models/llama3-8b"
    - "--tensor-parallel-size"
    - "1"
    - "--max-num-seqs"
    - "256"
    - "--port"
    - "8000"
  env:
    - name: CUDA_VISIBLE_DEVICES
      value: "0"

service:
  replicas: 2
  port: 8000
  healthCheck: /health

resources:
  pool: inference-pool
  gpu: 1
  gpuType: A100-100G
  cpu: 8
  memory: 32Gi

storage:
  workdirs:
    - path: /models/llama3-8b
```

```bash
# Deploy the inference service
gpuctl create -f llama3-inference.yaml

# Check service status
gpuctl get jobs --kind inference

# View service access addresses
gpuctl describe job llama3-8b-inference
```

**Example access addresses from `describe` output:**

```
Access Methods:
  Pod IP Access:    http://10.42.0.43:8000
  Node Port Access: http://192.168.1.101:30125
```

---

## Example 2: Multi-Replica High-Availability Deployment

```yaml title="qwen2-ha-inference.yaml"
kind: inference
version: v0.1

job:
  name: qwen2-7b-ha-service
  priority: high

environment:
  image: vllm/vllm-serving:latest
  command: ["python", "-m", "vllm.entrypoints.openai.api_server"]
  args:
    - "--model"
    - "/models/qwen2-7b"
    - "--port"
    - "8000"

service:
  replicas: 3          # 3 replicas for high availability
  port: 8000
  healthCheck: /health

resources:
  pool: inference-pool
  gpu: 1
  cpu: 8
  memory: 32Gi

storage:
  workdirs:
    - path: /models/qwen2-7b
```

---

## Distributed Inference

"Distributed inference" is three different things — pick by where the bottleneck is:

| Flavor | Declaration | Maps to |
|--------|-------------|---------|
| **Single-node, multi-GPU** (tensor parallel; model fits one node) | `resources.gpu: N` + framework flag (e.g. vLLM `--tensor-parallel-size N`) | Deployment, one pod with N GPUs |
| **Data-parallel replicas** (more throughput) | `service.replicas: N` | Deployment, N independent pods |
| **Multi-node** (one model sharded across nodes) | `resources.nodes: N` | StatefulSet + Headless Service |

`resources.nodes` and `service.replicas` are orthogonal: `nodes` = machines **per** replica (model-parallel), `replicas` = number of replicas (data-parallel); total pods = `replicas × nodes`. v1 supports `nodes=1 × replicas=N` and `nodes=N × replicas=1`; the rare combo **`nodes>1` AND `replicas>1` is rejected** with a clear error (it would be N groups of M pods — N StatefulSets / LeaderWorkerSet territory, deferred).

### Single-node multi-GPU (the common case)

If the model fits on one machine's GPUs, you do **not** need `nodes`. Just request the GPUs and pass the framework's parallelism flag — one pod, N GPUs:

```yaml
resources:
  gpu: 4                 # 4 GPUs on one node
environment:
  command: ["vllm", "serve", "/models/qwen2-72b", "--tensor-parallel-size", "4"]
```

### Multi-node serving (`resources.nodes: N`)

When a single model is too large for one node and must be sharded across machines, set `resources.nodes: N` (alongside `gpu`/`cpu`/`memory`). The platform then:

- creates a **StatefulSet** with `replicas = nodes` (one logical serving replica = N pods);
- creates a **Headless Service** (`<name>-headless`, with `publishNotReadyAddresses`) so workers can resolve the head before it is ready;
- exposes a **NodePort Service that targets only the head** (pod `-0`) — only the head serves the API;
- injects bootstrap env vars; **your command does the head/worker split** (e.g. start a Ray head on rank 0, join it on the others), exactly like you write `torchrun` yourself for training.

```yaml title="qwen-235b-multinode.yaml"
kind: inference
version: v0.1

job:
  name: qwen-235b
  namespace: alice

environment:
  image: vllm/vllm-openai:latest
  command:
    - bash
    - -c
    - |
      if [ "$RUNWHERE_NODE_RANK" = "0" ]; then
        ray start --head --port=6379
        vllm serve /datasets/models/Qwen2-235B \
          --tensor-parallel-size 8 --pipeline-parallel-size 2 \
          --host 0.0.0.0 --port 8000
      else
        # workers retry until the head's Ray is reachable, then block
        until ray start --address="$RUNWHERE_HEAD_ADDR:6379" --block; do sleep 5; done
      fi

resources:
  pool: inference-pool
  nodes: 2               # one replica spanning 2 nodes (alongside gpu/cpu/memory)
  gpu: 8                 # GPUs per node → total 16 (TP 8 × PP 2)
  cpu: 32
  memory: 256Gi
service:
  replicas: 1            # one logical replica (the 2-node group); must be 1 when nodes > 1
  port: 8000             # exposed on the head only
```

**Platform-injected env vars** (multi-node only — your command consumes them):

| Variable | Meaning | Example |
|----------|---------|---------|
| `RUNWHERE_NUM_NODES` | Nodes in this replica | `2` |
| `RUNWHERE_NODE_RANK` | This pod's ordinal (`0` = head) | `0`, `1` |
| `RUNWHERE_HEAD_ADDR` | Stable DNS of the head pod | `qwen-235b-0.qwen-235b-headless.alice.svc.cluster.local` |
| `RUNWHERE_GPUS_PER_NODE` | GPUs per pod (= `resources.gpu`) | `8` |

!!! warning "Things to know about multi-node serving"
    - **No HTTP health probes** are set on multi-node pods (only the head serves the API; an HTTP liveness probe would kill the workers). Readiness gating isn't applied in this mode.
    - **`service.replicas` must be 1** when `resources.nodes > 1` (the StatefulSet's replica count *is* `nodes` = one serving instance). Setting both `>1` is **rejected** with a clear error — running several multi-node replicas (N groups of M) is a deferred extension.
    - `RUNWHERE_NODE_RANK` is sourced from the `apps.kubernetes.io/pod-index` label, which the StatefulSet controller sets on **Kubernetes 1.28+**.
    - Workers must tolerate the head not being up yet — retry the join (the example loops `ray start` until it succeeds).

---

## Updating an Inference Service

Use `apply` to update service configuration (equivalent to delete + create):

```bash
# After modifying the YAML (e.g. changing replica count or env vars):
gpuctl apply -f qwen2-ha-inference.yaml
```

## Viewing Inference Logs

```bash
# View last 100 lines of logs
gpuctl logs llama3-8b-inference

# Stream logs in real time
gpuctl logs llama3-8b-inference -f
```

## Deleting an Inference Service

```bash
gpuctl delete job llama3-8b-inference
```

!!! note "Service Is Also Deleted"
    When an inference job is deleted, the platform also deletes the associated K8s resource (Deployment, or the StatefulSet + Headless Service for `nodes > 1`) and the NodePort Service, fully releasing the port resource.
