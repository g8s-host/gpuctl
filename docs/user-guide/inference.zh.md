# 推理服务

推理任务（`kind: inference`）适用于长期运行的模型推理 API 服务,默认对应 Kubernetes **Deployment + NodePort Service**,支持多副本部署。当模型大到一台机器放不下时,设 `nodes: N`,任务改为对应 **StatefulSet + Headless Service**(见[分布式推理](#distributed-inference))。

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
  replicas: 2            # 副本数（默认 1;数据并行的多份拷贝）
  port: 8000             # 服务端口
  healthCheck: /health   # 健康检查路径（可选）

resources:
  pool: inference-pool   # 推理专属资源池
  nodes: 1               # 一个副本横跨几个节点(默认 1)。>1 = 多机 serving
                         #   (一个大模型跨节点切分)。见「分布式推理」。
  gpu: 1                 # 每个 Pod 的 GPU 数(单机张量并行只需调大这个)
  gpuType: A100-100G    # 可选
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
  gpuType: A100-100G
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

## 分布式推理 {#distributed-inference}

「分布式推理」其实是三件不同的事 —— 按瓶颈在哪选:

| 形态 | 声明 | 落到什么资源 |
|------|------|------|
| **单机多卡**(张量并行;模型一台放得下) | `resources.gpu: N` + 框架参数(如 vLLM `--tensor-parallel-size N`) | Deployment,单 Pod N 卡 |
| **数据并行多副本**(扩吞吐) | `service.replicas: N` | Deployment,N 个互相独立的 Pod |
| **多机**(一个模型跨节点切分) | `resources.nodes: N` | StatefulSet + Headless Service |

`resources.nodes` 和 `service.replicas` 正交:`nodes` = 一个副本占几台机(模型并行),`replicas` = 几个副本(数据并行);总 pod = `replicas × nodes`。v1 支持 `nodes=1 × replicas=N` 和 `nodes=N × replicas=1`;罕见的 **`nodes>1` 且 `replicas>1` 会直接报错**(那是 N 组×M 台 —— 多 StatefulSet / LeaderWorkerSet 的活,留作扩展)。

### 单机多卡(最常见)

模型在一台机器的多卡上放得下,就**不需要** `nodes`。申请 GPU + 传框架的并行参数即可,单 Pod N 卡:

```yaml
resources:
  gpu: 4                 # 一个节点 4 卡
environment:
  command: ["vllm", "serve", "/models/qwen2-72b", "--tensor-parallel-size", "4"]
```

### 多机 serving(`resources.nodes: N`)

当单个模型大到一台放不下、必须跨机器切分时,设 `resources.nodes: N`(跟 gpu/cpu/memory 并列)。平台随即:

- 建 **StatefulSet**,`replicas = nodes`(一个逻辑副本 = N 个 Pod);
- 建 **Headless Service**(`<name>-headless`,带 `publishNotReadyAddresses`),让 worker 在 head 就绪前就能解析到它;
- 建一个**只指向 head(pod `-0`)的 NodePort Service** —— 只有 head 对外提供 API;
- 注入引导环境变量;**head/worker 的分工由你的命令决定**(如 rank 0 起 Ray head,其余加入)—— 和训练里你自己写 `torchrun` 一样。

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
        # worker 重试直到 head 的 Ray 可达,然后阻塞
        until ray start --address="$RUNWHERE_HEAD_ADDR:6379" --block; do sleep 5; done
      fi

resources:
  pool: inference-pool
  nodes: 2               # 一个副本横跨 2 个节点(跟 gpu/cpu/memory 并列)
  gpu: 8                 # 每节点 8 卡 → 共 16(TP 8 × PP 2)
  cpu: 32
  memory: 256Gi
service:
  replicas: 1            # 一个逻辑副本(这 2 节点的整体);nodes>1 时必须为 1
  port: 8000             # 只在 head 上暴露
```

**平台注入的环境变量**(仅多机;你的命令来消费):

| 变量 | 含义 | 示例 |
|------|------|------|
| `RUNWHERE_NUM_NODES` | 本副本的节点数 | `2` |
| `RUNWHERE_NODE_RANK` | 本 Pod 序号(`0`=head) | `0`、`1` |
| `RUNWHERE_HEAD_ADDR` | head Pod 的稳定 DNS | `qwen-235b-0.qwen-235b-headless.alice.svc.cluster.local` |
| `RUNWHERE_GPUS_PER_NODE` | 每 Pod 卡数(= `resources.gpu`) | `8` |

!!! warning "多机 serving 要注意的几点"
    - **不设 HTTP 健康探针**:只有 head 跑 API,给 worker 套 http liveness 会把它们反复杀掉;此模式下不做 readiness 门控。
    - `resources.nodes > 1` 时 **`service.replicas` 必须为 1**(StatefulSet 副本数就是 `nodes` = 一个 serving 实例)。两者同时 >1 会**直接报错** —— 跑多个多机副本(N 组×M 台)是留作扩展的。
    - `RUNWHERE_NODE_RANK` 取自 `apps.kubernetes.io/pod-index` 标签,该标签由 StatefulSet 控制器在 **Kubernetes 1.28+** 注入。
    - worker 要容忍 head 尚未起来 —— 重试加入(示例里用循环 `ray start` 直到成功)。

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
    删除推理任务时,平台会同时删除对应的 K8s 资源(Deployment;或 `nodes > 1` 时的 StatefulSet + Headless Service)和 NodePort Service,确保端口资源完全释放。
