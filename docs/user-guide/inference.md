# 推理服务

推理任务（`kind: inference`）适用于长期运行的模型推理 API 服务，底层对应 Kubernetes **Deployment + NodePort Service**，支持多副本部署和自动扩缩容。

## YAML 完整字段

```yaml
kind: inference
version: v0.1

job:
  name: <服务名称>
  priority: medium
  description: "描述"

environment:
  image: <镜像地址>
  command: [...]
  args: [...]
  env:
    - name: KEY
      value: VALUE

service:
  replicas: 2            # 副本数（默认 1）
  port: 8000             # 服务端口
  healthCheck: /health   # 健康检查路径（可选）

resources:
  pool: inference-pool   # 推理专属资源池
  gpu: 1
  gpu-type: A100-100G    # 可选
  cpu: 8
  memory: 32Gi

storage:
  workdirs:
    - path: /models
```

---

## 场景一：VLLM 高并发推理服务

部署 Llama3-8B 模型，使用 VLLM 提供高吞吐量 OpenAI 兼容 API。

```yaml title="llama3-inference.yaml"
kind: inference
version: v0.1

job:
  name: llama3-8b-inference
  priority: medium
  description: "Llama3-8B VLLM 推理服务"

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
  gpu-type: A100-100G
  cpu: 8
  memory: 32Gi

storage:
  workdirs:
    - path: /models/llama3-8b
```

```bash
# 部署推理服务
gpuctl create -f llama3-inference.yaml

# 查看服务状态
gpuctl get jobs --kind inference

# 查看服务访问地址
gpuctl describe job llama3-8b-inference
```

**`describe` 输出中的访问地址示例：**

```
Access Methods:
  Pod IP Access:    http://10.42.0.43:8000
  Node Port Access: http://192.168.1.101:30125
```

---

## 场景二：多副本高可用部署

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
  replicas: 3          # 3 副本保证高可用
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

## 更新推理服务

使用 `apply` 命令更新服务配置（等价于先删后建）：

```bash
# 修改 YAML（如调整副本数、环境变量等）后执行：
gpuctl apply -f qwen2-ha-inference.yaml
```

## 查看推理服务日志

```bash
# 查看最近 100 行日志
gpuctl logs llama3-8b-inference

# 实时跟踪日志
gpuctl logs llama3-8b-inference -f
```

## 删除推理服务

```bash
gpuctl delete job llama3-8b-inference
```

!!! note "Service 会一并删除"
    删除推理任务时，平台会同时删除对应的 K8s Deployment 和 NodePort Service，确保端口资源完全释放。
