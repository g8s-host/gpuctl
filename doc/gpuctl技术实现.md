# gpuctl 与 Kubernetes 资源映射技术文档

## 1. 概述

gpuctl 是一个面向算法工程师的 AI 算力调度平台，通过声明式 YAML 配置和简单的 CLI 命令，隐藏了 Kubernetes 的复杂性。本文档详细分析了 gpuctl YAML 与 Kubernetes YAML 之间的字段对应关系，以及 gpuctl CLI 命令和 API 接口操作的 Kubernetes 资源。

## 2. 声明式 YAML 规范设计 - 字段对应关系

### 2.1 训练任务 (training)

gpuctl 训练任务 YAML 对应 Kubernetes Job 资源，转换关系如下：

| gpuctl YAML 字段 | Kubernetes Job 字段 | 说明 |
|----------------|--------------------|------|
| `kind: training` | `kind: Job` | 资源类型映射 |
| `job.name` | `metadata.name` | 任务名称 |
| `job.priority` | `metadata.labels["g8s.host/priority"]` | 任务优先级，通过标签实现 |
| `environment.image` | `spec.template.spec.containers[0].image` | 容器镜像 |
| `environment.imagePullSecret` | `spec.template.spec.imagePullSecrets` | 镜像拉取密钥 |
| `environment.command` | `spec.template.spec.containers[0].command` | 容器启动命令 |
| `environment.args` | `spec.template.spec.containers[0].args` | 容器启动参数 |
| `environment.env` | `spec.template.spec.containers[0].env` | 环境变量 |
| `resources.pool` | `spec.template.spec.nodeSelector["g8s.host/pool"]` | 资源池，通过节点选择器实现 |
| `resources.gpu` | `spec.template.spec.containers[0].resources.requests["nvidia.com/gpu"]` | GPU 数量 |
| `resources.gpu-type` | `spec.template.spec.nodeSelector["g8s.host/gpu-type"]` | GPU 类型，通过节点选择器实现 |
| `resources.cpu` | `spec.template.spec.containers[0].resources.requests.cpu` | CPU 需求 |
| `resources.memory` | `spec.template.spec.containers[0].resources.requests.memory` | 内存需求 |
| `storage.workdirs` | `spec.template.spec.volumes` 和 `spec.template.spec.containers[0].volumeMounts` | 存储挂载，转换为 Kubernetes Volume 和 VolumeMount |

**实际 YAML 案例**：
```yaml
kind: training
version: v0.1

# 任务标识与描述（Llama Factory微调场景）
job:
  name: qwen2-7b-llamafactory-sft
  priority: "high"
  description: "llama3推理任务"

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
  pool: training-pool #默认default
  gpu: 4
  gpu-type: A100-100G #可选，不填就k8s的调度
  cpu: 32
  memory: 128Gi
  gpu-share: 2Gi

# 数据与模型配置
storage:
  workdirs:
    - path: /datasets/alpaca-qwen.json
    - path: /models/qwen2-7b    
    - path: /cache/models
    - path: /output/qwen2-sft
    - path: /output/qwen2-sft/checkpoints    
```

### 2.2 推理任务 (inference)

gpuctl 推理任务 YAML 对应 Kubernetes Deployment + Service 资源，转换关系如下：

| gpuctl YAML 字段 | Kubernetes 资源 | Kubernetes 字段 | 说明 |
|----------------|----------------|----------------|------|
| `kind: inference` | Deployment | `kind: Deployment` | 资源类型映射 |
| `job.name` | Deployment | `metadata.name` | 部署名称 |
| `environment.image` | Deployment | `spec.template.spec.containers[0].image` | 容器镜像 |
| `environment.command` | Deployment | `spec.template.spec.containers[0].command` | 容器启动命令 |
| `service.replicas` | Deployment | `spec.replicas` | 副本数量 |
| `service.port` | Service | `spec.ports[0].port` 和 `spec.ports[0].targetPort` | 服务端口 |
| `service.health_check` | Deployment | `spec.template.spec.containers[0].livenessProbe` 和 `readinessProbe` | 健康检查 |
| `resources.gpu` | Deployment | `spec.template.spec.containers[0].resources.requests["nvidia.com/gpu"]` | GPU 数量 |
| `resources.pool` | Deployment | `spec.template.spec.nodeSelector["g8s.host/pool"]` | 资源池，通过节点选择器实现 |
| `resources.gpu-type` | Deployment | `spec.template.spec.nodeSelector["g8s.host/gpu-type"]` | GPU 类型，通过节点选择器实现 |
| `resources.cpu` | Deployment | `spec.template.spec.containers[0].resources.requests.cpu` | CPU 需求 |
| `resources.memory` | Deployment | `spec.template.spec.containers[0].resources.requests.memory` | 内存需求 |
| `storage.workdirs` | Deployment | `spec.template.spec.volumes` 和 `spec.template.spec.containers[0].volumeMounts` | 存储挂载，转换为 Kubernetes Volume 和 VolumeMount |

**实际 YAML 案例**：
```yaml
kind: inference
version: v0.1
  
# 任务标识
job:
  name: llama3-8b-inference
  priority: "medium"
  description: "llama3推理任务"

# 环境与镜像（集成VLLM 0.5.0+）
environment:
  image: vllm/vllm-serving:v0.5.0 # 优化过的推理镜像
  command: ["python", "-m", "vllm.entrypoints.openai.api_server"] # 启动命令
  args:
    - "--model"
    - "/home/data/models/llama3-8b"
    - "--tensor-parallel-size"
    - "1"
    - "--max-num-seqs"
    - "256"

# 服务配置
service:
  replicas: 2
  port: 8000
  health_check: /health

# 资源规格（新增pool字段）
resources:
  pool: inference-pool # 推理专属资源池,默认default
  gpu: 1
  gpu-type: A100-100G #可选，不填就k8s的调度
  cpu: 8
  memory: 32Gi
  gpu-share: 2Gi

storage:
  workdirs:
    - path: /home/data/ # 挂在本地存储目录
```

### 2.3 Notebook 任务 (notebook)

gpuctl Notebook 任务 YAML 对应 Kubernetes Deployment + Service 资源，转换关系如下：

| gpuctl YAML 字段 | Kubernetes 资源 | Kubernetes 字段 | 说明 |
|----------------|----------------|----------------|------|
| `kind: notebook` | Deployment | `kind: Deployment` | 资源类型映射 |
| `job.name` | Deployment | `metadata.name` | 部署名称 |
| `environment.image` | Deployment | `spec.template.spec.containers[0].image` | 容器镜像 |
| `environment.command` | Deployment | `spec.template.spec.containers[0].command` | 容器启动命令 |
| `service.port` | Service | `spec.ports[0].port` 和 `spec.ports[0].targetPort` | 服务端口 |
| `resources.gpu` | Deployment | `spec.template.spec.containers[0].resources.requests["nvidia.com/gpu"]` | GPU 数量 |
| `resources.pool` | Deployment | `spec.template.spec.nodeSelector["g8s.host/pool"]` | 资源池，通过节点选择器实现 |
| `resources.gpu-type` | Deployment | `spec.template.spec.nodeSelector["g8s.host/gpu-type"]` | GPU 类型，通过节点选择器实现 |
| `resources.cpu` | Deployment | `spec.template.spec.containers[0].resources.requests.cpu` | CPU 需求 |
| `resources.memory` | Deployment | `spec.template.spec.containers[0].resources.requests.memory` | 内存需求 |
| `storage.workdirs` | Deployment | `spec.template.spec.volumes` 和 `spec.template.spec.containers[0].volumeMounts` | 存储挂载，转换为 Kubernetes Volume 和 VolumeMount |

**实际 YAML 案例**：
```yaml
kind: notebook
version: v0.1

job:
  name: data-prep-notebook
  priority: medium
  description: llama3推理任务

environment:
  image: registry.example.com/jupyter-ai:v1.0
  command: ["jupyter-lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=ai-gpuctl-2025", "--NotebookApp.password="]

# 服务配置
service:
  port: 8888

resources:
  pool: dev-pool #默认default
  gpu: 1
  gpu-type: a10-24g #可选，不填就k8s的调度
  cpu: 8
  memory: 32Gi
  gpu-share: 2Gi

storage:
  workdirs:
    - path: /home/jovyan/work # 代码存储目录
```

### 2.4 资源池 (pool)

gpuctl 资源池通过节点标签实现，不使用额外的 Kubernetes 资源，转换关系如下：

| gpuctl YAML 字段 | Kubernetes 资源 | Kubernetes 字段 | 说明 |
|----------------|----------------|----------------|------|
| `kind: pool` | Node | `metadata.labels["g8s.host/pool"]` | 通过节点标签实现资源池管理 |
| `metadata.name` | Node | `metadata.labels["g8s.host/pool"]` | 资源池名称，作为节点标签值 |
| `metadata.description` | - | - | 资源池描述，仅用于 gpuctl 内部管理 |
| `nodes` | Node | `metadata.labels["g8s.host/pool"]` | 节点列表，通过标签将节点关联到资源池 |

**实际 YAML 案例**：
```yaml
kind: pool
version: v0.1

metadata:
  name: train-pool
  description: "训练任务专用资源池"

nodes: 
  node1: # 节点主机名
    gpu-type: A100-100G
  node2: # 节点主机名
    gpu-type: A800-20G
```

## 3. gpuctl CLI 命令 - Kubernetes 资源操作映射

### 3.1 任务管理命令

| gpuctl 命令 | 操作的 Kubernetes 资源 | 具体操作 |
|-------------|------------------------|----------|
| `gpuctl create -f train-job.yaml` | Job | 创建训练任务，转换为 Kubernetes Job |
| `gpuctl create -f task1.yaml -f task2.yaml` | Job | 批量创建训练任务 |
| `gpuctl get jobs` | Job, Deployment | 列出所有任务（训练/推理/Notebook） |
| `gpuctl get jobs --pool training-pool` | Job, Deployment | 按资源池过滤查询任务 |
| `gpuctl describe job <job-id>` | Job, Deployment, Pod | 查看任务详细信息及资源使用情况 |
| `gpuctl logs <job-id>` | Pod | 查看任务日志 |
| `gpuctl delete <job-id>` | Job, Deployment, Service | 删除任务及相关资源 |
| `gpuctl pause <job-id>` | Job | 暂停任务（通过调整 Job 配置实现） |
| `gpuctl resume <job-id>` | Job | 恢复任务 |

### 3.2 资源池管理命令

| gpuctl 命令 | 操作的 Kubernetes 资源 | 具体操作 |
|-------------|------------------------|----------|
| `gpuctl create -f pool.yaml` | Node | 创建资源池，为节点添加 `g8s.host/pool` 标签 |
| `gpuctl get pools` | Node | 列出所有资源池，通过聚合节点标签实现 |
| `gpuctl describe pool <pool-name>` | Node | 查看资源池详细信息，聚合节点信息 |
| `gpuctl delete -f pool.yaml` | Node | 删除资源池，移除节点的 `g8s.host/pool` 标签 |
| `gpuctl add node <node-name> --pool <pool-name>` | Node | 将节点添加到资源池（添加 `g8s.host/pool` 标签） |
| `gpuctl remove node <node-name> --pool <pool-name>` | Node | 从资源池移除节点（移除 `g8s.host/pool` 标签） |

### 3.3 节点管理命令

| gpuctl 命令 | 操作的 Kubernetes 资源 | 具体操作 |
|-------------|------------------------|----------|
| `gpuctl get nodes` | Node | 列出集群所有节点 |
| `gpuctl get nodes --pool <pool-name>` | Node | 按资源池过滤查询节点（通过 `g8s.host/pool` 标签） |
| `gpuctl get nodes --gpu-type <gpu-type>` | Node | 按 GPU 类型过滤查询节点（通过 `g8s.host/gpu-type` 标签） |
| `gpuctl describe node <node-name>` | Node | 查看节点详细信息 |
| `gpuctl label node <node-name> g8s.host/gpu-type=a100-80g` | Node | 给指定节点标记 GPU 类型 Label |
| `gpuctl label node <node-name> <label-key>=<label-value> --overwrite` | Node | 给指定节点标记 Label，支持覆盖已有同键 Label |
| `gpuctl get label <node-name> --key=g8s.host/gpu-type` | Node | 查询指定节点的指定 GPU 类型 Label 值 |
| `gpuctl label node <node-name> <label-key> --delete` | Node | 删除指定节点的指定 Label |

## 4. gpuctl API 接口 - Kubernetes 资源操作映射

### 4.1 任务管理 API

| API 端点 | 方法 | 操作的 Kubernetes 资源 | 具体操作 |
|----------|------|------------------------|----------|
| `/api/v1/jobs` | POST | Job, Deployment, Service | 创建任务 |
| `/api/v1/jobs/batch` | POST | Job, Deployment, Service | 批量创建任务 |
| `/api/v1/jobs` | GET | Job, Deployment | 查询任务列表 |
| `/api/v1/jobs/{jobId}` | GET | Job, Deployment, Pod | 查询任务详情 |
| `/api/v1/jobs/{jobId}` | DELETE | Job, Deployment, Service | 删除任务 |
| `/api/v1/jobs/{jobId}/logs` | GET | Pod | 获取任务日志 |
| `/api/v1/jobs/{jobId}/metrics` | GET | - | 获取任务指标（通过 Prometheus 查询） |

### 4.2 资源池管理 API

| API 端点 | 方法 | 操作的 Kubernetes 资源 | 具体操作 |
|----------|------|------------------------|----------|
| `/api/v1/pools` | GET | Node | 查询资源池列表（通过聚合节点标签） |
| `/api/v1/pools/{poolName}` | GET | Node | 查询资源池详情（聚合节点信息） |
| `/api/v1/pools` | POST | Node | 创建资源池（为节点添加标签） |
| `/api/v1/pools/{poolName}` | DELETE | Node | 删除资源池（移除节点标签） |

### 4.3 节点管理 API

| API 端点 | 方法 | 操作的 Kubernetes 资源 | 具体操作 |
|----------|------|------------------------|----------|
| `/api/v1/nodes` | GET | Node | 查询节点列表 |
| `/api/v1/nodes/{nodeName}` | GET | Node | 查询节点详情 |
| `/api/v1/nodes/{nodeName}/labels` | POST | Node | 给节点添加标签 |
| `/api/v1/nodes/labels` | GET | Node | 查询节点标签 |
| `/api/v1/nodes/{nodeName}/labels/{key}` | DELETE | Node | 删除节点标签 |

## 5. 转换机制

gpuctl 采用分层设计，实现了从声明式 YAML 到 Kubernetes 资源的转换：

1. **解析层**：解析 gpuctl YAML 文件，验证合法性
2. **构建层**：根据 YAML 类型构建对应的 Kubernetes 资源对象
3. **执行层**：调用 Kubernetes API 执行资源操作

转换过程中，gpuctl 自动处理了以下复杂逻辑：
- 资源池与节点的关联（通过标签）
- GPU 资源的调度（通过节点选择器）
- 分布式训练的环境变量注入
- 服务的配置和暴露
- 健康检查和探针配置

## 6. 示例转换流程

以训练任务为例，转换流程如下：

1. 算法工程师编写训练任务 YAML
2. 执行 `gpuctl create -f train-job.yaml` 命令
3. gpuctl 解析 YAML，验证合法性
4. 构建 Kubernetes Job 资源对象
5. 调用 Kubernetes API 创建 Job
6. Kubernetes 调度器将 Job 调度到匹配 `g8s.host/pool` 和 `g8s.host/gpu-type` 标签的节点上
7. Job 启动 Pod，执行训练任务

## 7. YAML 转换完整案例

### 7.1 训练任务 YAML 转换

#### gpuctl 训练任务 YAML
```yaml
kind: training
version: v0.1

job:
  name: qwen2-7b-llamafactory-sft
  priority: "high"
  description: "llama3推理任务"

environment:
  image: registry.example.com/llama-factory-deepspeed:v0.8.0
  imagePullSecret: my-secret
  command: ["llama-factory-cli", "train", "--stage", "sft", "--model_name_or_path", "/models/qwen2-7b", "--dataset", "alpaca-qwen", "--dataset_dir", "/datasets", "--output_dir", "/output/qwen2-sft", "--per_device_train_batch_size", "8", "--gradient_accumulation_steps", "4", "--learning_rate", "2e-5", "--deepspeed", "ds_config.json"]
  env:
    - name: NVIDIA_FLASH_ATTENTION
      value: "1"
    - name: LLAMA_FACTORY_CACHE
      value: "/cache/llama-factory"

resources:
  pool: training-pool
  gpu: 4
  gpu-type: A100-100G
  cpu: 32
  memory: 128Gi
  gpu-share: 2Gi

storage:
  workdirs:
    - path: /datasets/alpaca-qwen.json
    - path: /models/qwen2-7b    
    - path: /cache/models
    - path: /output/qwen2-sft
    - path: /output/qwen2-sft/checkpoints
```

#### 对应的 Kubernetes Job YAML
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: qwen2-7b-llamafactory-sft
  labels:
    g8s.host/job-type: training
    g8s.host/priority: high
    g8s.host/pool: training-pool
spec:
  template:
    metadata:
      labels:
        app: gpuctl-job
    spec:
      restartPolicy: Never
      imagePullSecrets:
      - name: my-secret
      nodeSelector:
        g8s.host/pool: training-pool
        g8s.host/gpu-type: A100-100G
      containers:
      - name: main
        image: registry.example.com/llama-factory-deepspeed:v0.8.0
        command: ["llama-factory-cli", "train", "--stage", "sft", "--model_name_or_path", "/models/qwen2-7b", "--dataset", "alpaca-qwen", "--dataset_dir", "/datasets", "--output_dir", "/output/qwen2-sft", "--per_device_train_batch_size", "8", "--gradient_accumulation_steps", "4", "--learning_rate", "2e-5", "--deepspeed", "ds_config.json"]
        env:
        - name: NVIDIA_FLASH_ATTENTION
          value: "1"
        - name: LLAMA_FACTORY_CACHE
          value: "/cache/llama-factory"
        resources:
          requests:
            cpu: 32
            memory: 128Gi
            nvidia.com/gpu: 4
          limits:
            cpu: 32
            memory: 128Gi
            nvidia.com/gpu: 4
        volumeMounts:
        - name: dataset-volume
          mountPath: /datasets/alpaca-qwen.json
        - name: model-volume
          mountPath: /models/qwen2-7b
        - name: cache-volume
          mountPath: /cache/models
        - name: output-volume
          mountPath: /output/qwen2-sft
        - name: checkpoints-volume
          mountPath: /output/qwen2-sft/checkpoints
      volumes:
      - name: dataset-volume
        hostPath:
          path: /datasets/alpaca-qwen.json
      - name: model-volume
        hostPath:
          path: /models/qwen2-7b
      - name: cache-volume
        hostPath:
          path: /cache/models
      - name: output-volume
        hostPath:
          path: /output/qwen2-sft
      - name: checkpoints-volume
        hostPath:
          path: /output/qwen2-sft/checkpoints
```

### 7.2 推理任务 YAML 转换

#### gpuctl 推理任务 YAML
```yaml
kind: inference
version: v0.1
  
job:
  name: llama3-8b-inference
  priority: "medium"
  description: "llama3推理任务"

environment:
  image: vllm/vllm-serving:v0.5.0
  command: ["python", "-m", "vllm.entrypoints.openai.api_server"]
  args:
    - "--model"
    - "/home/data/models/llama3-8b"
    - "--tensor-parallel-size"
    - "1"
    - "--max-num-seqs"
    - "256"

# 服务配置
service:
  replicas: 2
  port: 8000
  health_check: /health

resources:
  pool: inference-pool
  gpu: 1
  gpu-type: A100-100G
  cpu: 8
  memory: 32Gi
  gpu-share: 2Gi

storage:
  workdirs:
    - path: /home/data/
```

#### 对应的 Kubernetes Deployment YAML
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-llama3-8b-inference
  labels:
    g8s.host/job-type: inference
    g8s.host/priority: medium
    g8s.host/pool: inference-pool
spec:
  replicas: 2
  selector:
    matchLabels:
      app: inference-llama3-8b-inference
  template:
    metadata:
      labels:
        app: inference-llama3-8b-inference
    spec:
      restartPolicy: Always
      nodeSelector:
        g8s.host/pool: inference-pool
        g8s.host/gpu-type: A100-100G
      containers:
      - name: main
        image: vllm/vllm-serving:v0.5.0
        command: ["python", "-m", "vllm.entrypoints.openai.api_server"]
        args:
        - "--model"
        - "/home/data/models/llama3-8b"
        - "--tensor-parallel-size"
        - "1"
        - "--max-num-seqs"
        - "256"
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
        resources:
          requests:
            cpu: 8
            memory: 32Gi
            nvidia.com/gpu: 1
          limits:
            cpu: 8
            memory: 32Gi
            nvidia.com/gpu: 1
        volumeMounts:
        - name: data-volume
          mountPath: /home/data/
      volumes:
      - name: data-volume
        hostPath:
          path: /home/data/
```

#### 对应的 Kubernetes Service YAML
```yaml
apiVersion: v1
kind: Service
metadata:
  name: svc-llama3-8b-inference
  labels:
    g8s.host/job-type: inference
    g8s.host/pool: inference-pool
spec:
  selector:
    app: inference-llama3-8b-inference
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

### 7.3 Notebook 任务 YAML 转换

#### gpuctl Notebook 任务 YAML
```yaml
kind: notebook
version: v0.1

job:
  name: data-prep-notebook
  priority: medium
  description: llama3推理任务

environment:
  image: registry.example.com/jupyter-ai:v1.0
  command: ["jupyter-lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=ai-gpuctl-2025", "--NotebookApp.password="]

# 服务配置
service:
  port: 8888

resources:
  pool: dev-pool
  gpu: 1
  gpu-type: a10-24g
  cpu: 8
  memory: 32Gi
  gpu-share: 2Gi

storage:
  workdirs:
    - path: /home/jovyan/work
```

#### 对应的 Kubernetes Deployment YAML
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: notebook-data-prep-notebook
  labels:
    g8s.host/job-type: notebook
    g8s.host/priority: medium
    g8s.host/pool: dev-pool
spec:
  replicas: 1
  selector:
    matchLabels:
      app: notebook-data-prep-notebook
  template:
    metadata:
      labels:
        app: notebook-data-prep-notebook
    spec:
      restartPolicy: Always
      nodeSelector:
        g8s.host/pool: dev-pool
        g8s.host/gpu-type: a10-24g
      containers:
      - name: main
        image: registry.example.com/jupyter-ai:v1.0
        command: ["jupyter-lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=ai-gpuctl-2025", "--NotebookApp.password="]
        ports:
        - containerPort: 8888
        resources:
          requests:
            cpu: 8
            memory: 32Gi
            nvidia.com/gpu: 1
          limits:
            cpu: 8
            memory: 32Gi
            nvidia.com/gpu: 1
        volumeMounts:
        - name: work-volume
          mountPath: /home/jovyan/work
      volumes:
      - name: work-volume
        hostPath:
          path: /home/jovyan/work
```

#### 对应的 Kubernetes Service YAML
```yaml
apiVersion: v1
kind: Service
metadata:
  name: svc-data-prep-notebook
  labels:
    g8s.host/job-type: notebook
    g8s.host/pool: dev-pool
spec:
  selector:
    app: notebook-data-prep-notebook
  ports:
  - port: 8888
    targetPort: 8888
  type: NodePort
```

### 7.4 资源池管理机制

资源池通过节点标签 `g8s.host/pool` 实现，gpuctl 支持完整的资源池生命周期管理。

#### 7.4.1 资源池命令实现

1. **创建资源池**
   ```bash
   gpuctl create -f pool.yaml
   ```
   执行流程：
   - 解析 pool.yaml 文件
   - 验证节点存在性
   - 为指定节点添加标签：
     ```bash
     kubectl label nodes node1 g8s.host/pool=train-pool g8s.host/gpu-type=A100-100G
     kubectl label nodes node2 g8s.host/pool=train-pool g8s.host/gpu-type=A800-20G
     ```

2. **删除资源池**
   ```bash
   gpuctl delete -f pool.yaml
   ```
   执行流程：
   - 解析 pool.yaml 文件
   - 查找所有带有该资源池标签的节点
   - 移除节点上的资源池标签：
     ```bash
     kubectl label nodes node1 g8s.host/pool-
     kubectl label nodes node2 g8s.host/pool-
     ```

3. **添加节点到资源池**
   ```bash
   gpuctl add node node1 node2 --pool train-pool
   ```
   执行流程：
   - 验证节点存在性
   - 为指定节点添加资源池标签：
     ```bash
     kubectl label nodes node1 node2 g8s.host/pool=train-pool
     ```

4. **从资源池移除节点**
   ```bash
   gpuctl remove node node1 --pool train-pool
   ```
   执行流程：
   - 验证节点存在性
   - 移除节点上的资源池标签：
     ```bash
     kubectl label nodes node1 g8s.host/pool-
     ```

5. **查看资源池**
   ```bash
   gpuctl get pools
   ```
   执行流程：
   - 调用 Kubernetes API 获取所有节点
   - 提取节点上的 `g8s.host/pool` 标签
   - 去重后返回资源池列表

#### 7.4.2 资源池存储类型说明

storage.workdirs 默认使用 hostPath 存储类型，直接使用节点上的文件系统路径。对于需要其他存储类型的场景，gpuctl 将在后续版本中支持。

#### 7.4.3 资源池状态管理

资源池状态通过以下方式管理：

1. **节点健康检查**：定期检查资源池中的节点健康状态
2. **资源使用率监控**：监控资源池中的 CPU、内存、GPU 使用率
3. **容量规划**：根据资源池的资源使用情况，提供扩容建议
4. **自动恢复机制**：当节点故障时，自动将任务迁移到健康节点

#### 7.4.4 资源池约束条件

资源池支持以下约束条件：

1. **GPU 类型约束**：限制资源池只能使用特定类型的 GPU
2. **最低资源要求**：设置节点加入资源池的最低资源要求
3. **地理位置约束**：限制资源池中的节点位于特定区域
4. **可用性约束**：设置资源池的可用性级别要求