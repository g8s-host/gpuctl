# 面向算法工程师的AI算力调度平台 (gpuctl) 产品需求文档

# 1. 产品概述与核心目标

本产品旨在为算法工程师群体提供一个高度抽象、易于使用的AI算力调度平台，其核心目标是显著降低GPU算力的使用门槛。通过声明式的YAML配置和简单的gpuctl CLI命令，算法工程师无需掌握Kubernetes等底层基础设施的复杂知识，即可高效提交和管理AI训练与推理任务。

## 1.1 解决的核心痛点

- 算法工程师不熟悉Kubernetes，希望避免学习Pod、Deployment、Service等复杂概念。

- 简化GPU驱动、依赖库等繁琐环境的安装与配置。

- 提供高性能、高效率的算力执行环境，支持训练和推理场景。

- 实现在现有Kubernetes集群上通过声明式命令直接使用算力资源。

# 5. 声明式YAML规范设计

YAML设计的原则是面向算法工程，使用他们熟悉的术语，隐藏基础设施细节，新增`resources.pool`字段实现资源池化管理。

## 5.1 训练任务示例 (training-job.yaml)

```Plain Text


kind: training
version: v0.1

# 任务标识与描述（Llama Factory微调场景）
job:
  name: qwen2-7b-llamafactory-sft
  description: llama3推理任务
  epochs: 3
  batch_size: 8 # 单卡batch，平台自动聚合多卡总量
  priority: high


# 环境与镜像 - 集成Llama Factory 0.8.0 + DeepSpeed 0.14.0
environment:
  image: registry.example.com/llama-factory-deepspeed:v0.8.0
  imagePullSecret: my-secret
  # Llama Factory微调核心命令
  command: ["llama-factory-cli", "train", "--stage", "sft", "--model_name_or_path", "/models/qwen2-7b", "--dataset", "alpaca-qwen", "--dataset_dir", "/datasets", "--output_dir", "/output/qwen2-sft", "--per_device_train_batch_size", "8", "--gradient_accumulation_steps", "4", "--learning_rate", "2e-5", "--deepspeed", "ds_config.json"]
  env:
    - name: NVIDIA_FLASH_ATTENTION
      value: "1"
    - name: LLAMA_FACTORY_CACHE
      value: "/cache/llama-factory"

# 资源需求声明（4卡A100）
resources:
  pool: training-pool
  gpu: 4
  cpu: 32
  memory: 128Gi
  gpu_share: 2Gi


# 数据与模型配置
storage:
  workdirs:
    - path: /datasets/alpaca-qwen.json
    - path: /models/qwen2-7b    
    - path: /cache/models
    - path: /output/qwen2-sft
    - path: /output/qwen2-sft/checkpoints    
    
```

注：平台底层将此YAML转换为支持多卡分布式的Kubernetes Job资源，自动注入Deepspeed所需的环境变量与网络配置，基于`training-pool`调度资源。




## 5.2 推理任务示例 (inference-service.yaml)

```Plain Text

kind: inference
version: v0.1
  
# 任务标识
job:
  name: llama3-8b-inference
  priority: medium
  description: llama3推理任务
  
# 模型来源
model:
  source: model-registry
  name: llama3-8b
  version: v1.0
  format: safetensors # 模型文件格式
  cache: true # 启用模型缓存加速加载

# 环境与镜像（集成VLLM 0.5.0+）
environment:
  image: vllm/vllm-serving:v0.5.0 # 优化过的推理镜像
  command: ["python", "-m", "vllm.entrypoints.openai.api_server"] # 启动命令
  args:
    - "--model"
    - "{{model.name}}"
    - "--tensor-parallel-size"
    - "1"
    - "--paged-attention-version"
    - "v2"
    - "--max-num-seqs"
    - "256"

# 服务配置
service:
  replicas: 2
  port: 8000
  health_check: /health
  timeout: 30s # 推理超时时间
  request_limit: 1000 # 每秒请求限制

# 资源规格（新增pool字段）
resources:
  pool: inference-pool # 推理专属资源池
  gpu: 1
  gpu-type: a10-24g
  cpu: 8
  memory: 32Gi
  gpu_share: 1.0

# 自动扩缩容
autoscaling:
  enabled: true
  minReplicas: 1
  maxReplicas: 10
  targetGPUUtilization: 70
  targetMemoryUtilization: 85 # 新增显存利用率扩缩容阈值
  scaleUpDelay: 60s # 扩容冷却时间
  scaleDownDelay: 300s # 缩容冷却时间
```

注：平台底层将此YAML转换为Kubernetes Deployment、Service、HPA资源，基于`inference-pool`进行资源调度，确保推理服务与训练任务资源隔离。

## 5.3 调试任务示例（notebook-job.yaml)



```
kind: notebook
version: v0.1

job:
  name: data-prep-notebook
  
environment:
  image: registry.example.com/jupyter-ai:v1.0
  command: ["jupyter-lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=ai-gpuctl-2025", "--NotebookApp.password="]`
# 服务配置
service:
  port: 8000
resources:
  pool: dev-pool
  gpu: 1
  gpu-type: a10-24g
  cpu: 8
  memory: 32Gi
storage:
  workdirs:
    - path: /home/jovyan/work # 代码存储目录
```



## 5.3 资源池示例（train-pool.yaml）

```
kind: resource
version: v0.1

pool:
  name: train-pool
  description: "训练任务专用资源池"
	
nodes: 
  node1: 
    gpu-type: A100-100G
  node2:
    gpu-type: A800-20G
---
kind: resource
version: v0.1

pool:
  name: inference-pool
  description: "训练任务专用资源池"

nodes: 
  node1: 
    gpu-type: 4090-24G
  node2:
    gpu-type: 5090-20G
    
```

# 6. gpuctl CLI 命令设计

gpuctl 命令与 kubectl 对标，但语义更贴近算法工程师的使用场景，新增资源池相关命令以支撑精细化管理。gpuctl由go语言实现，编译之后移动到/usr/local/bin/目录下即可立即使用，底层由api_server/kubectl支撑。

|命令示例|功能描述|底层近似操作|
|---|---|---|
|gpuctl create -f train-job.yaml|提交一个训练任务|kubectl create -f <转换后的job.yaml>|
|gpuctl create -f task1.yaml -f task2.yaml|批量提交多个任务|批量执行kubectl create|
|gpuctl get jobs|列出所有任务（训练/推理）及核心指标|kubectl get pods,jobs,deployments -o custom-columns|
|gpuctl get jobs --pool training-pool|列出指定资源池的任务|kubectl get pods,jobs -l pool=training-pool|
|gpuctl describe job <job-id>|查看任务详细信息及资源使用曲线|kubectl describe <资源类型> <资源名> + 监控数据聚合|
|gpuctl logs <job-id> -f|实时查看任务日志，支持按关键词过滤|kubectl logs <pod名> -f --tail=1000|
|gpuctl delete -f job.yaml|删除/停止任务，支持--force强制删除|kubectl delete <资源类型> <资源名> --grace-period=0|
|gpuctl get pools|查询所有资源池及资源占用情况|聚合K8s节点标签与Prometheus监控数据|
|gpuctl create -f pool.yaml|暂停运行中的任务，保留资源占用|kubectl scale job <job-id> --replicas=0|
|gpuctl delete -f pool.yaml|恢复暂停的任务，延续之前的运行状态|kubectl scale job <job-id> --replicas=1|

节点查询类 gpuctl CLI 命令（按指定格式）

| 命令示例                                          | 功能描述                                                     | 底层近似操作                                                 |
| ------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| `gpuctl get nodes`                                | 列出集群所有节点的基础信息（名称、状态、GPU 总数、绑定资源池） | `kubectl get nodes -o wide` + 平台查询节点 - GPU 统计映射 + 资源池绑定关系 |
| `gpuctl get nodes --pool training-pool`           | 过滤查询指定资源池绑定的所有节点                             | `kubectl get nodes -l gpuctl/pool=training-pool`（平台自定义资源池 Label） + 基础信息聚合 |
| `gpuctl get nodes --gpu-type nvidia.com/a100-80g` | 过滤查询带有指定 GPU 类型的所有节点                          | `kubectl get nodes -l nvidia.com/gpu-type=a100-80g` + 节点状态校验 |
| `gpuctl describe node node-1`                     | 查看单个节点的详细信息（CPU/GPU 资源、GPU 类型 / 数量、Label 列表、绑定资源池、K8s 节点详情） | `kubectl describe node node-1` + 平台查询节点 GPU 类型统计 + Label 聚合 + 资源池关联信息 |
| `gpuctl get nodes --gpu-type nvidia.com/gpu-type` | 仅查询所有节点的 GPU 类型 Label（键值对形式）                | `kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.labels.nvidia\.com/gpu-type}{"\n"}{end}'` |

节点管理类 gpuctl CLI 命令（按指定格式）

| 命令示例                                                     | 功能描述                                                     | 底层近似操作                                                 |
| ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| `gpuctl label node node-1 nvidia.com/gpu-type=a100-80g`      | 给指定节点标记 GPU 类型 Label（默认 Label 键）               | `kubectl label nodes node-1 nvidia.com/gpu-type=a100-80g`    |
| `gpuctl label node node-2 node-3 company.com/gpu-model=a100-40g --overwrite` | 批量给多个节点标记自定义 GPU 类型 Label，支持覆盖已有同键 Label | `for node in node-2 node-3; do kubectl label nodes $node company.com/gpu-model=a100-40g --overwrite; done` |
| `gpuctl get label node-1 --key=nvidia.com/gpu-type`          | 查询指定节点的指定 GPU 类型 Label 值                         | `kubectl get node node-1 -o jsonpath='{.metadata.labels.nvidia\.com/gpu-type}'` |
| `gpuctl get gpu-type --all`                                  | 列出所有节点的 GPU 类型 Label 及绑定的资源池信息             | `kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.labels}{"\n"}{end}' + 平台筛选GPU相关Label及gpuctl/pool绑定标签` |
| `gpuctl label node node-1 nvidia.com/gpu-type --delete`      | 删除指定节点的指定 GPU 类型 Label                            | `kubectl label nodes node-1 nvidia.com/gpu-type-`（K8s 删除 Label 的标准语法） |



资源池节点管理类 gpuctl CLI 命令

| 命令示例                                             | 功能描述                 | 底层近似操作                                                 |
| :--------------------------------------------------- | :----------------------- | :----------------------------------------------------------- |
| gpuctl create -f train-pool.yaml                     | 创建新的资源池           | 创建K8s ConfigMap/CRD存储资源池定义，设置节点选择器          |
| gpuctl delete -f train-pool.yaml                     | 删除资源池               | 删除资源池定义，可选移除关联节点标签                         |
| `gpuctl get pools`                                   | 列出所有资源池及基本信息 | 查询所有资源池定义，聚合节点统计信息                         |
| `gpuctl describe pool training-pool`                 | 查看资源池详细信息       | 显示资源池配置、关联节点、资源使用情况                       |
| `gpuctl add node node-1 node-2 --pool training-pool` | 将节点添加到资源池       | 给节点打上资源池标签：`kubectl label nodes node-1 gpuctl/pool=training-pool` |
| `gpuctl remove node node-3 --pool training-pool`     | 从资源池移除节点         | 移除节点资源池标签：`kubectl label nodes node-3 gpuctl/pool-` |
| `gpuctl get nodes --pool training-pool`              | 列出指定资源池的所有节点 | 基于标签筛选：`kubectl get nodes -l gpuctl/pool=training-pool` |





# 7.API 设计

平台 API 作为 gpuctl CLI 的底层支撑，采用 RESTful 风格设计，提供标准化接口供客户端（CLI、第三方工具）调用，抽象 Kubernetes 底层细节，聚焦 AI 算力任务的全生命周期管理。

## 7.1 基础信息

- **基础路径**：`/api/v1`
- **数据格式**：请求 / 响应均采用 JSON 格式，YAML 配置通过`application/yaml`媒体类型传输
- **认证方式**：基于 Bearer Token 认证，通过 HTTP 请求头`Authorization: Bearer <token>`传递
- **版本控制**：URL 路径包含版本（如`v1`），支持多版本并行维护
- 状态码规范：
  - 200：请求成功
  - 201：资源创建成功
  - 400：请求参数无效（如 YAML 格式错误）
  - 401：未认证（Token 无效或过期）
  - 403：权限不足（如非管理员操作资源池）
  - 404：资源不存在（如任务 ID 无效）
  - 500：服务器内部错误（如 Kubernetes 集群异常）

## 7.2 核心 API 端点

### 7.2.1 任务管理 API

#### 1. 创建任务（对应`gpuctl create`）

- **URL**：`/jobs`

- **方法**：`POST`

- 请求体：json

  ```json
  {
    "yamlContent": "kind: training\nversion: v0.1\njob:\n  name: qwen2-7b-sft\n...", // 声明式YAML配置字符串
    "dryRun": false // 可选，true时仅验证YAML不实际创建任务
  }
  ```

- 响应（201 Created）：json

  ```json
  {
    "jobId": "qwen2-7b-sft-xxxxx", // 平台生成的唯一任务ID
    "name": "qwen2-7b-sft",
    "kind": "training",
    "status": "pending", // 初始状态：pending
    "createdAt": "2024-06-01T10:00:00Z",
    "message": "任务已提交至训练资源池"
  }
  ```

  

#### 2. 批量创建任务

- **URL**：`/jobs/batch`

- **方法**：`POST`

- 请求体：json

  ```json
  {
    "yamlContents": [
      "kind: training\nversion: v0.1\njob:\n  name: task1\n...",
      "kind: training\nversion: v0.1\njob:\n  name: task2\n..."
    ]
  }
  ```

  

- 响应（201 Created）：json

  ```json
  {
    "success": [
      {"jobId": "task1-xxxxx", "name": "task1"},
      {"jobId": "task2-xxxxx", "name": "task2"}
    ],
    "failed": [] // 若有失败任务，包含错误信息
  }
  ```

  

#### 3. 查询任务列表（对应`gpuctl get jobs`）

- **URL**：`/jobs`

- **方法**：`GET`

- 查询参数：

  - `kind`：可选，过滤任务类型（training/inference/notebook）
  - `pool`：可选，过滤资源池（如 training-pool）
  - `status`：可选，过滤状态（pending/running/succeeded/failed）
  - `page`：分页页码，默认 1
  - `pageSize`：每页数量，默认 20

- 响应（200 OK）：json

  ```json
  {
    "total": 42,
    "items": [
      {
        "jobId": "qwen2-7b-sft-xxxxx",
        "name": "qwen2-7b-sft",
        "kind": "training",
        "pool": "training-pool",
        "status": "running",
        "gpu": 4,
        "gpuType": "a100-80g",
        "startedAt": "2024-06-01T10:05:00Z",
        "progress": 65 // 训练任务进度（百分比）
      },
      // ... 更多任务
    ]
  }
  ```

  

#### 4. 查询任务详情（对应`gpuctl describe job`）

- **URL**：`/jobs/{jobId}`

- **方法**：`GET`

- 响应（200 OK）：json

  ```json
  {
    "jobId": "qwen2-7b-sft-xxxxx",
    "name": "qwen2-7b-sft",
    "kind": "training",
    "version": "v0.1",
    "yamlContent": "kind: training\nversion: v0.1\n...", // 原始YAML配置
    "status": "running",
    "pool": "training-pool",
    "resources": {
      "gpu": 4,
      "gpuType": "a100-80g",
      "cpu": 32,
      "memory": "128Gi"
    },
    "metrics": {
      "gpuUtilization": 89.2, // 平均GPU利用率（%）
      "memoryUsage": "68Gi/80Gi", // 显存使用
      "networkLatency": "1.8ms", // 分布式训练延迟
      "throughput": "245 tokens/sec" // 训练吞吐量
    },
    "createdAt": "2024-06-01T10:00:00Z",
    "startedAt": "2024-06-01T10:05:00Z",
    "k8sResources": {
      "jobName": "qwen2-7b-sft-xxxxx-k8s", // 底层K8s Job名称
      "pods": ["pod-1", "pod-2", "pod-3", "pod-4"] // 关联的Pod列表
    }
  }
  ```

  

#### 5. 删除任务（对应`gpuctl delete`）

- **URL**：`/jobs/{jobId}`

- **方法**：`DELETE`

- 查询参数：

  - `force`：可选，`true`时强制删除（对应`--force`）

- 响应（200 OK）：json

  ```json
  {
    "jobId": "qwen2-7b-sft-xxxxx",
    "status": "terminating",
    "message": "任务删除指令已下发"
  }
  ```

  

#### 6. 暂停 / 恢复任务（对应`gpuctl pause/resume`）

- **暂停 URL**：`/jobs/{jobId}/pause`

- **恢复 URL**：`/jobs/{jobId}/resume`

- **方法**：`POST`

- 响应（200 OK）：json

  ```json
  {
    "jobId": "qwen2-7b-sft-xxxxx",
    "status": "paused", // 或"resumed"
    "message": "任务已暂停，资源保留"
  }
  ```

### 7.2.2 资源池管理 API

#### 1. 查询资源池列表（对应`gpuctl query pools`）

- **URL**：`/pools`

- **方法**：`GET`

- 响应（200 OK）：json

  ```json
  {
    "items": [
      {
        "name": "training-pool",
        "description": "用于模型训练的资源池",
        "gpuTotal": 32,
        "gpuUsed": 16,
        "gpuType": ["a100-80g", "a100-40g"],
        "status": "active"
      },
      {
        "name": "inference-pool",
        "description": "用于推理服务的资源池",
        "gpuTotal": 16,
        "gpuUsed": 8,
        "gpuType": ["a10-24g"],
        "status": "active"
      }
    ]
  }
  ```

  

#### 2. 查询资源池详情

- **URL**：`/pools/{poolName}`

- **方法**：`GET`

- 响应（200 OK）：json

  ```json
  {
    "name": "training-pool",
    "description": "用于模型训练的资源池",
    "nodes": ["node-1", "node-2", "node-3"], // 关联的K8s节点
    "gpuTotal": 32,
    "gpuUsed": 16,
    "gpuFree": 16,
    "gpuType": {
      "a100-80g": 24,
      "a100-40g": 8
    },
    "quota": {
      "maxJobs": 100, // 最大任务数限制
      "maxGpuPerJob": 8 // 单任务最大GPU数限制
    },
    "jobs": [ // 当前运行的任务
      {"jobId": "qwen2-7b-sft-xxxxx", "name": "qwen2-7b-sft", "gpu": 4}
    ]
  }
  ```

  

#### 3. 创建资源池（管理员接口）

- **URL**：`/pools`

- **方法**：`POST`

- 请求体：json

  ```json
  {
    "name": "experiment-pool",
    "description": "用于实验调参的资源池",
    "nodes": ["node-4", "node-5"], // 绑定的节点
    "gpuType": ["t4"], // 允许的GPU类型
    "quota": {
      "maxJobs": 50,
      "maxGpuPerJob": 2
    }
  }
  ```

  

- 响应（201 Created）：json

  ```json
  {
    "name": "experiment-pool",
    "status": "created",
    "message": "资源池创建成功"
  }
  ```

### 7.2.3 监控与日志 API

#### 1. 获取任务实时日志（对应`gpuctl logs -f`）

- **URL**：`/jobs/{jobId}/logs`

- **方法**：`GET`

- 查询参数：

  - `follow`：可选，`true`时启用流式日志（WebSocket）
  - `tail`：可选，返回末尾 N 行日志，默认 100
  - `pod`：可选，指定 Pod（多卡任务可能有多个 Pod）

- 响应（200 OK）：json

  ```json
  {
    "logs": [
      "2024-06-01 10:06:00 [INFO] Starting training...",
      "2024-06-01 10:06:30 [INFO] Epoch 1/3, Step 100, Loss: 0.87"
    ],
    "lastTimestamp": "2024-06-01T10:06:30Z"
  }
  ```

  （注：follow=true时升级为 WebSocket 连接，实时推送新日志）

#### 2. 获取任务指标时序数据

- **URL**：`/jobs/{jobId}/metrics`

- **方法**：`GET`

- 查询参数：

  - `metric`：可选，指定指标（gpuUtilization/memoryUsage/throughput），默认返回全部
  - `startTime`：起始时间（UTC），如`2024-06-01T10:00:00Z`
  - `endTime`：结束时间，默认当前时间

- 响应（200 OK）：json

  ```json
  {
    "gpuUtilization": [
      {"timestamp": "2024-06-01T10:05:00Z", "value": 75.2},
      {"timestamp": "2024-06-01T10:10:00Z", "value": 89.2}
    ],
    "memoryUsage": [
      {"timestamp": "2024-06-01T10:05:00Z", "value": 65}, // 单位：GiB
      {"timestamp": "2024-06-01T10:10:00Z", "value": 68}
    ]
  }
  ```

### 7.2.4 权限管理 API

#### 1. 验证用户权限

- **URL**：`/auth/check`

- **方法**：`POST`

- 请求体：json

  ```json
  {
    "resource": "jobs", // 资源类型（jobs/pools）
    "action": "create", // 操作（create/get/delete）
    "pool": "training-pool" // 可选，资源池级权限验证
  }
  ```

  

- 响应（200 OK）：json

  ```json
  {
    "allowed": true,
    "message": "用户拥有training-pool的任务创建权限"
  }
  ```

### 7.2.5 节点查询类对应 API

#### 1. 列出集群所有节点基础信息

#### （对应 `gpuctl get nodes`，支持 `--pool`/`--gpu-type`/`--status` 过滤）

- **URL**：`/api/v1/nodes`

- **方法**：`GET`

- 查询参数：

  - `pool`：可选，过滤指定资源池绑定的节点（如 `training-pool`）
  - `gpuType`：可选，过滤指定 GPU 类型的节点（如 `a100-80g`）
  - `status`：可选，过滤节点状态（`active`/`maintaining`/`faulty`）
  - `page`：分页页码，默认 1
  - `pageSize`：每页数量，默认 20
  - `accept`：可选，指定响应格式（`application/json` 默认，`application/yaml` 对应 `gpuctl get nodes -o yaml`）

- 响应（200 OK）：json

  ```json
  {
    "total": 5,
    "items": [
      {
        "nodeName": "node-1",
        "status": "active",
        "gpuTotal": 8,
        "gpuUsed": 4,
        "gpuFree": 4,
        "boundPools": ["training-pool"],
        "cpu": "64",
        "memory": "256Gi",
        "gpuType": "a100-80g",
        "createdAt": "2024-06-01T09:00:00Z"
      },
      {
        "nodeName": "node-2",
        "status": "active",
        "gpuTotal": 8,
        "gpuUsed": 4,
        "gpuFree": 4,
        "boundPools": ["training-pool"],
        "cpu": "64",
        "memory": "256Gi",
        "gpuType": "a100-80g",
        "createdAt": "2024-06-01T09:00:00Z"
      },
      // ... 更多节点
    ]
  }
  ```

- **说明**：`-o yaml` 格式通过请求头 `Accept: application/yaml` 实现，响应结构与 JSON 一致，仅格式不同。

#### 2. 查看单个节点详细信息

#### （对应 `gpuctl describe node node-1`）

- **URL**：`/api/v1/nodes/{nodeName}`

- **方法**：`GET`

- 路径参数：

  - `nodeName`：节点名称（如 `node-1`）

- 响应（200 OK）：json

  ```json
  {
    "nodeName": "node-1",
    "status": "active",
    "k8sStatus": {
      "conditions": [
        {"type": "Ready", "status": "True", "lastHeartbeatTime": "2024-06-02T14:30:00Z"}
      ],
      "kernelVersion": "5.4.0-1090-ubuntu",
      "osImage": "Ubuntu 20.04 LTS"
    },
    "resources": {
      "cpuTotal": 64,
      "cpuUsed": 32,
      "memoryTotal": "256Gi",
      "memoryUsed": "128Gi",
      "gpuTotal": 8,
      "gpuUsed": 4,
      "gpuFree": 4
    },
    "gpuDetail": [
      {"gpuId": "gpu-0", "type": "a100-80g", "status": "used", "utilization": 89.2},
      {"gpuId": "gpu-1", "type": "a100-80g", "status": "used", "utilization": 91.5},
      {"gpuId": "gpu-2", "type": "a100-80g", "status": "free", "utilization": 0},
      // ... 更多 GPU
    ],
    "labels": [
      {"key": "nvidia.com/gpu-type", "value": "a100-80g"},
      {"key": "gpuctl/pool", "value": "training-pool"},
      {"key": "kubernetes.io/hostname", "value": "node-1"}
    ],
    "boundPools": ["training-pool"],
    "runningJobs": [
      {"jobId": "qwen2-7b-sft-xxxxx", "name": "qwen2-7b-sft", "gpu": 4}
    ],
    "createdAt": "2024-06-01T09:00:00Z",
    "lastUpdatedAt": "2024-06-02T14:30:00Z"
  }
  ```

  

#### 3. 列出所有节点的 GPU 详情

#### （对应 `gpuctl get nodes --gpu-detail`）

- **URL**：`/api/v1/nodes/gpu-detail`

- **方法**：`GET`

- 查询参数：

  - `page`：分页页码，默认 1
  - `pageSize`：每页数量，默认 20

- 响应（200 OK）：json

  ```json
  {
    "total": 5,
    "items": [
      {
        "nodeName": "node-1",
        "gpuCount": 8,
        "gpus": [
          {"gpuId": "gpu-0", "type": "a100-80g", "status": "used", "utilization": 89.2, "memoryUsage": "72Gi/80Gi"},
          {"gpuId": "gpu-1", "type": "a100-80g", "status": "used", "utilization": 91.5, "memoryUsage": "75Gi/80Gi"},
          {"gpuId": "gpu-2", "type": "a100-80g", "status": "free", "utilization": 0, "memoryUsage": "0Gi/80Gi"},
          // ... 更多 GPU
        ]
      },
      {
        "nodeName": "node-3",
        "gpuCount": 8,
        "gpus": [
          {"gpuId": "gpu-0", "type": "a100-40g", "status": "free", "utilization": 0, "memoryUsage": "0Gi/40Gi"},
          // ... 更多 GPU
        ]
      }
      // ... 更多节点
    ]
  }
  ```

  

#### 4. 查询所有节点的指定 Label

#### （对应 `gpuctl get nodes --label nvidia.com/gpu-type`）

- **URL**：`/api/v1/nodes/labels`

- **方法**：`GET`

- 查询参数：

  - `key`：必填，指定要查询的 Label 键（如 `nvidia.com/gpu-type`）
  - `page`：分页页码，默认 1
  - `pageSize`：每页数量，默认 20

- 响应（200 OK）：json

  ```json
  {
    "total": 5,
    "items": [
      {"nodeName": "node-1", "labelKey": "nvidia.com/gpu-type", "labelValue": "a100-80g"},
      {"nodeName": "node-2", "labelKey": "nvidia.com/gpu-type", "labelValue": "a100-80g"},
      {"nodeName": "node-3", "labelKey": "nvidia.com/gpu-type", "labelValue": "a100-40g"},
      {"nodeName": "node-4", "labelKey": "nvidia.com/gpu-type", "labelValue": "t4"},
      {"nodeName": "node-5", "labelKey": "nvidia.com/gpu-type", "labelValue": "t4"}
    ]
  }
  ```

### 7.2.6 Label 管理类 CLI 对应 API

#### 1. 给指定节点标记 GPU 类型 Label

#### （对应 `gpuctl label node node-1 nvidia.com/gpu-type=a100-80g`）

- **URL**：`/api/v1/nodes/{nodeName}/labels`

- **方法**：`POST`

- 路径参数：

  - `nodeName`：节点名称（如 `node-1`）

- 请求体：json

  ```json
  {
    "key": "nvidia.com/gpu-type", // Label 键（支持自定义）
    "value": "a100-80g",          // GPU 类型值
    "overwrite": false            // 可选，是否覆盖已有同键 Label，默认 false
  }
  ```

  

- 响应（200 OK）：json

  ```json
  {
    "nodeName": "node-1",
    "label": {
      "key": "nvidia.com/gpu-type",
      "value": "a100-80g"
    },
    "message": "节点 Label 标记成功"
  }
  ```

- 错误响应（409 Conflict）：json

  ```json
  {
    "error": "LabelConflict",
    "message": "节点 node-1 已存在键为 nvidia.com/gpu-type 的 Label，如需覆盖请设置 overwrite=true"
  }
  ```

  

#### 2. 批量给多个节点标记 Label

#### （对应 `gpuctl label node node-2 node-3 company.com/gpu-model=a100-40g --overwrite`）

- **URL**：`/api/v1/nodes/labels/batch`

- **方法**：`POST`

- 请求体：json

  ```json
  {
    "nodeNames": ["node-2", "node-3"], // 批量节点名称列表
    "key": "company.com/gpu-model",    // Label 键
    "value": "a100-40g",               // Label 值
    "overwrite": true                  // 是否覆盖已有同键 Label
  }
  ```

  

- 响应（200 OK）：json

  ```json
  {
    "success": ["node-2", "node-3"],
    "failed": [],
    "message": "批量标记节点 Label 成功"
  }
  ```

  

- 错误响应（200 OK，部分失败）：json

  ```json
  {
    "success": ["node-2"],
    "failed": [
      {
        "nodeName": "node-3",
        "error": "NodeNotFound",
        "message": "节点 node-3 不存在"
      }
    ],
    "message": "部分节点标记失败，请查看 failed 列表"
  }
  ```

  

#### 3. 查询指定节点的指定 Label

#### （对应 `gpuctl get node-labels node-1 --key=nvidia.com/gpu-type`）

- **URL**：`/api/v1/nodes/{nodeName}/labels/{key}`

- **方法**：`GET`

- 路径参数：

  - `nodeName`：节点名称（如 `node-1`）
  - `key`：Label 键（如 `nvidia.com/gpu-type`）

- 响应（200 OK）：json

  ```json
  {
    "nodeName": "node-1",
    "label": {
      "key": "nvidia.com/gpu-type",
      "value": "a100-80g",
      "createdAt": "2024-06-01T09:30:00Z",
      "lastUpdatedAt": "2024-06-01T09:30:00Z"
    }
  }
  ```

  

- 错误响应（404 Not Found）：json

  ```json
  {
    "error": "LabelNotFound",
    "message": "节点 node-1 未找到键为 nvidia.com/gpu-type 的 Label"
  }
  ```

  

#### 4. 列出所有节点的 GPU 相关 Label 及绑定资源池

#### （对应 `gpuctl get node-labels --all`）

- **URL**：`/api/v1/nodes/labels/all`

- **方法**：`GET`

- 查询参数：

  - `page`：分页页码，默认 1
  - `pageSize`：每页数量，默认 20

- 响应（200 OK）：json

  ```json
  {
    "total": 5,
    "items": [
      {
        "nodeName": "node-1",
        "gpuLabels": [
          {"key": "nvidia.com/gpu-type", "value": "a100-80g"}
        ],
        "boundPools": ["training-pool"]
      },
      {
        "nodeName": "node-4",
        "gpuLabels": [
          {"key": "company.com/gpu-model", "value": "t4"}
        ],
        "boundPools": ["experiment-pool"]
      }
      // ... 更多节点
    ]
  }
  ```

  

#### 5. 删除指定节点的指定 Label

#### （对应 `gpuctl label node node-1 nvidia.com/gpu-type --delete`）

- **URL**：`/api/v1/nodes/{nodeName}/labels/{key}`

- **方法**：`DELETE`

- 路径参数：

  - `nodeName`：节点名称（如 `node-1`）
  - `key`：Label 键（如 `nvidia.com/gpu-type`）

- 响应（200 OK）：json

  ```json
  {
    "nodeName": "node-1",
    "labelKey": "nvidia.com/gpu-type",
    "message": "节点 Label 删除成功"
  }
  ```

  

- 错误响应（404 Not Found）：json

  ```json
  {
    "error": "LabelNotFound",
    "message": "节点 node-1 未找到键为 nvidia.com/gpu-type 的 Label"
  }
  ```

## 7.3 接口文档与调试

- 提供 OpenAPI 3.0 规范的接口文档，可通过`/api/v1/docs`访问交互式 Swagger UI
- 支持请求示例生成、参数校验说明及错误码解释
- 提供 API 调用 SDK（Python/Go），封装认证、请求重试等逻辑，简化集成难度
