# Inference Services

Inference jobs (`kind: inference`) are designed for long-running model inference API services. They map to a Kubernetes **Deployment + NodePort Service**, with support for multi-replica deployment and auto-scaling.

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
  replicas: 2            # Number of replicas (default: 1)
  port: 8000             # Service port
  healthCheck: /health   # Health check path (optional)

resources:
  pool: inference-pool   # Dedicated inference resource pool
  gpu: 1
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
    When an inference job is deleted, the platform also deletes the associated K8s Deployment and NodePort Service, fully releasing the port resource.
