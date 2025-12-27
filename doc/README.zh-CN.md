# gpuctl - AI 算力调度平台

[简体中文](doc/README.zh-CN.md) | [English](README.md)

## 项目介绍

gpuctl 是一个面向算法工程师的 AI 算力调度平台，旨在降低 GPU 算力的使用门槛。通过声明式 YAML 配置和简单的 CLI 命令，算法工程师无需掌握 Kubernetes 等底层基础设施的复杂知识，即可高效提交和管理 AI 训练与推理任务。

### 核心痛点解决

- 无需学习 Kubernetes 复杂概念（Pod、Deployment、Service 等）
- 简化 GPU 驱动、依赖库等繁琐环境的安装与配置
- 提供高性能、高效率的算力执行环境，支持训练和推理场景
- 实现在现有 Kubernetes 集群上通过声明式命令直接使用算力资源

## 系统架构

平台采用分层设计，对用户暴露友好的抽象层，底层则基于成熟的Kubernetes和容器化技术构建，新增资源池管理模块以支撑资源精细化调度。

```
┌─────────────────────────────────────────────────────────────────────┐
│                         算法工程师                                    │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           接入层                                      │
│                   (gpuctl CLI / REST API)                          │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        抽象与转换层                                   │
│  (解析YAML → 验证合法性 → 转换为K8s资源定义 → 封装K8s复杂性)          │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        调度与执行层                                   │
│  (基于Kubernetes及生态实现资源池化管理，按池分配GPU资源)                │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        监控与反馈层                                   │
│  (基于Prometheus+Grafana构建监控体系，收集任务运行全量数据)            │
└─────────────────────────────────────────────────────────────────────┘
```

## 核心功能

### 1. 多类型任务支持

- **训练任务**：支持分布式训练，集成 DeepSpeed 等加速框架
- **推理服务**：支持模型部署，自动扩缩容
- **调试任务**：提供 Jupyter Notebook 环境，方便调试
- **计算任务**：支持纯CPU计算任务，如nginx、redis、mysql等服务

### 2. 资源池管理

- 支持创建和管理资源池
- 节点与资源池的灵活绑定与解绑
- 资源池级别的资源隔离与配额管理

### 3. 资源配额管理

- 声明式 YAML 配置资源配额
- 为每个用户/命名空间设置资源限制（CPU、内存、GPU）
- 查看配额使用率和消耗情况
- 自动为每个用户创建独立命名空间

### 4. 声明式配置

- 使用算法工程师熟悉的术语
- 隐藏底层基础设施细节
- 支持 YAML 格式的任务定义

### 5. 丰富的 CLI 命令

- 任务生命周期管理
- 节点与资源池管理
- 实时日志查看
- 资源使用监控

## 安装

### 前提条件

- Python 3.8+
- Kubernetes 集群访问权限

### 安装方式

#### 方式一：使用二进制文件（推荐）

从 GitHub Releases 下载适合您系统的二进制文件：

```bash
# Linux x86_64架构
wget https://github.com/your-org/gpuctl/releases/latest/download/gpuctl-linux-amd64 -O gpuctl

# macOS x86_64架构
curl -L https://github.com/your-org/gpuctl/releases/latest/download/gpuctl-macos-amd64 -o gpuctl

chmod +x gpuctl
sudo mv gpuctl /usr/local/bin/
gpuctl --help
```

#### 方式二：从源码安装（推荐）

1. 克隆代码库

```bash
git clone https://github.com/your-org/gpuctl.git
cd gpuctl
```

2. 安装依赖并将 gpuctl 安装为系统命令

```bash
pip install -e .
```

3. 运行 gpuctl

```bash
gpuctl --help
# 或使用原始方式
python main.py --help
```

### 配置 Kubernetes 访问

确保 `kubectl` 已正确配置并能访问目标 Kubernetes 集群。

## 快速开始

### 1. 创建资源池

```yaml
# train-pool.yaml
kind: pool
version: v0.1

metadata:
  name: training-pool
  description: "训练任务专用资源池"

nodes: 
  node1: 
    gpu-type: A100-100G
  node2:
    gpu-type: A800-20G
```

```bash
gpuctl create -f train-pool.yaml
```

### 2. 提交训练任务

```yaml
# training-job.yaml
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

```bash
gpuctl create -f training-job.yaml
```

### 3. 提交推理任务

```yaml
# inference-service.yaml
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
    - "v2"
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

```bash
gpuctl create -f inference-service.yaml
```

### 4. 提交Notebook任务

```yaml
# notebook-job.yaml
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

```bash
gpuctl create -f notebook-job.yaml
```

### 5. 提交Compute任务

```yaml
# nginx-job.yaml
kind: compute
version: v0.1

# 任务标识与描述
job:
  name: test-nginx
  priority: "medium"
  description: "测试nginx web服务"

# 环境与镜像
environment:
  image: nginx:latest
  command: []
  args: []
  env:
    - name: NGINX_PORT
      value: "80"

# 服务配置
service:
  replicas: 2
  port: 80
  health_check: /health

# 资源规格
resources:
  pool: test-pool
  gpu: 0  # CPU任务，设置为0
  cpu: 2
  memory: 4Gi

# 数据与存储配置
storage:
  workdirs:
    - path: /etc/nginx/conf.d
    - path: /var/www/html
```

```bash
gpuctl create -f nginx-job.yaml
```

### 6. 配置资源配额

```yaml
# quota-config.yaml
kind: quota
version: v0.1

metadata:
  name: team-resource-quota
  description: "团队资源配额配置"

# 用户资源配置（自动为每个用户创建命名空间）
users:
  elon-musk:
    cpu: 10
    memory: 20Gi
    gpu: 4
  sam-altman:
    cpu: 10
    memory: 20Gi
    gpu: 4
```

```bash
gpuctl create -f quota-config.yaml
```

### 7. 查询任务状态

```bash
gpuctl get jobs
```

### 7. 查看任务日志

```bash
gpuctl logs qwen2-7b-llamafactory-sft -f
```

## CLI 命令参考

### 任务管理

| 命令示例                                          | 功能描述 |
|--------------------------------------------------|---------|
| `gpuctl create -f train-job.yaml`                | 提交一个训练任务 |
| `gpuctl create -f task1.yaml -f task2.yaml`      | 批量提交多个任务 |
| `gpuctl get jobs`                                | 列出所有任务（训练/推理）及核心指标 |
| `gpuctl get jobs --pool training-pool`           | 列出指定资源池的任务 |
| `gpuctl get jobs --pods`                         | 显示Pod实例级别信息 |
| `gpuctl get jobs --type training`                | 按任务类型过滤 |
| `gpuctl describe job <job-id>`                   | 查看任务详细信息及资源使用曲线 |
| `gpuctl logs <job-id> -f`                        | 实时查看任务日志，支持按关键词过滤 |
| `gpuctl delete -f job.yaml`                      | 删除/停止任务，支持--force强制删除 |
| `gpuctl delete job <job-name>`                   | 直接通过任务名称删除任务 |
| `gpuctl pause <job-id>`                          | 暂停运行中的任务 |
| `gpuctl resume <job-id>`                         | 恢复暂停的任务 |

### 资源池管理

| 命令示例                                          | 功能描述 |
|--------------------------------------------------|---------|
| `gpuctl get pools`                               | 列出所有资源池及基本信息 |
| `gpuctl create -f pool.yaml`                     | 创建新的资源池 |
| `gpuctl delete -f pool.yaml`                     | 删除资源池 |
| `gpuctl describe pool <pool-name>`               | 查看资源池详细信息 |
| `gpuctl add node <node-name> --pool <pool-name>` | 将节点添加到资源池 |
| `gpuctl remove node <node-name> --pool <pool-name>` | 从资源池移除节点 |

### 节点管理

| 命令示例                                                      | 功能描述 |
|-------------------------------------------------------------|---------|
| `gpuctl get nodes`                                          | 列出集群所有节点的基础信息（名称、状态、GPU总数、绑定资源池） |
| `gpuctl get nodes --pool <pool-name>`                       | 过滤查询指定资源池绑定的所有节点 |
| `gpuctl get nodes --gpu-type <gpu-type>`                    | 过滤查询带有指定GPU类型的所有节点 |
| `gpuctl describe node <node-name>`                          | 查看单个节点的详细信息（CPU/GPU资源、GPU类型/数量、Label列表、绑定资源池、K8s节点详情） |
| `gpuctl label node <node-name> g8s.host/gpu-type=a100-80g` | 给指定节点标记GPU类型Label（默认Label键） |
| `gpuctl label node <node-name> <label-key>=<label-value> --overwrite` | 给指定节点标记Label，支持覆盖已有同键Label |
| `gpuctl get label <node-name> --key=g8s.host/gpu-type`     | 查询指定节点的指定GPU类型Label值 |
| `gpuctl label node <node-name> <label-key> --delete`       | 删除指定节点的指定Label |

### 资源配额管理

| 命令示例 | 功能描述 |
|----------|---------|
| `gpuctl create -f quota.yaml` | 创建资源配额配置 |
| `gpuctl get quotas` | 列出所有资源配额 |
| `gpuctl get quotas <用户名>` | 查看指定用户的配额 |
| `gpuctl describe quota <用户名>` | 查看配额使用率（已用/总量） |
| `gpuctl delete -f quota.yaml` | 删除资源配额 |

## API 文档

平台提供 RESTful API 接口，可用于构建第三方工具或集成到现有系统中。

### 基础信息

- **基础路径**：`/api/v1`
- **数据格式**：请求/响应均采用 JSON 格式，YAML 配置通过`application/yaml`媒体类型传输
- **认证方式**：基于 Bearer Token 认证，通过 HTTP 请求头`Authorization: Bearer <token>`传递
- **版本控制**：URL 路径包含版本（如`v1`），支持多版本并行维护
- **状态码规范**：
  - 200：请求成功
  - 201：资源创建成功
  - 400：请求参数无效（如 YAML 格式错误）
  - 401：未认证（Token 无效或过期）
  - 403：权限不足（如非管理员操作资源池）
  - 404：资源不存在（如任务 ID 无效）
  - 500：服务器内部错误（如 Kubernetes 集群异常）

### 核心 API 端点

#### 任务管理 API

| 端点                        | 方法   | 功能                         |
|-----------------------------|--------|------------------------------|
| `/jobs`                     | POST   | 创建任务                     |
| `/jobs/batch`               | POST   | 批量创建任务                 |
| `/jobs`                     | GET    | 查询任务列表                 |
| `/jobs/{jobId}`             | GET    | 查询任务详情                 |
| `/jobs/{jobId}`             | DELETE | 删除任务                     |
| `/jobs/{jobId}/logs`        | GET    | 获取任务实时日志             |
| `/jobs/{jobId}/metrics`     | GET    | 获取任务指标时序数据         |

#### 资源池管理 API

| 端点                        | 方法   | 功能                         |
|-----------------------------|--------|------------------------------|
| `/pools`                    | GET    | 查询资源池列表               |
| `/pools/{poolName}`         | GET    | 查询资源池详情               |
| `/pools`                    | POST   | 创建资源池                   |
| `/pools/{poolName}`         | DELETE | 删除资源池                   |

#### 节点管理 API

| 端点                              | 方法   | 功能                         |
|-----------------------------------|--------|------------------------------|
| `/nodes`                          | GET    | 查询节点列表                 |
| `/nodes/{nodeName}`               | GET    | 查询节点详情                 |
| `/nodes/{nodeName}/labels`        | POST   | 给节点添加标签               |
| `/nodes/labels`                   | GET    | 查询节点标签                 |
| `/nodes/{nodeName}/labels/{key}`  | DELETE | 删除节点标签                 |

#### 资源配额管理 API

| 端点                        | 方法   | 功能                         |
|-----------------------------|--------|------------------------------|
| `/quotas`                   | GET    | 查询配额列表                 |
| `/quotas/{userName}`        | GET    | 查询配额详情（含使用率）     |
| `/quotas`                   | POST   | 创建资源配额                 |
| `/quotas/{userName}`        | DELETE | 删除资源配额                 |

### 交互式 API 文档

启动服务器后，可通过以下地址访问交互式 Swagger UI：

```
http://localhost:8000/api/v1/docs
```

## 开发指南

### 目录结构

```
gpuctl/
├── api/                      # 数据模型层（新增抽象资源字段，兼容多芯片）
│   ├── training.py           # 训练任务模型
│   ├── inference.py          # 推理任务模型
│   ├── notebook.py           # Notebook任务模型
│   ├── compute.py            # Compute任务模型
│   ├── quota.py              # 资源配额模型
│   ├── pool.py               # 资源池模型
│   └── common.py             # 公共数据模型
├── parser/                   # YAML解析与校验
│   ├── base_parser.py        # 基础解析逻辑
│   ├── training_parser.py    # 训练任务解析
│   ├── inference_parser.py   # 推理任务解析
│   ├── compute_parser.py     # 计算任务解析
│   ├── quota_parser.py       # 资源配额解析
│   └── pool_parser.py        # 资源池解析
├── builder/                  # 模型转K8s资源
│   ├── training_builder.py   # 训练任务→K8s Job
│   ├── inference_builder.py  # 推理任务→Deployment+HPA
│   ├── notebook_builder.py   # Notebook→StatefulSet+Service
│   ├── compute_builder.py    # Compute任务→Deployment
│   └── base_builder.py       # 基础构建逻辑
├── client/                   # K8s操作封装
│   ├── base_client.py        # 基础K8s客户端
│   ├── job_client.py         # 任务管理
│   ├── quota_client.py       # 资源配额管理
│   ├── pool_client.py        # 资源池管理
│   └── log_client.py         # 日志获取
├── kind/                     # 场景化逻辑
│   ├── training_kind.py      # 多卡训练/分布式调度
│   ├── inference_kind.py     # 推理服务扩缩容
│   ├── notebook_kind.py      # Notebook生命周期管理
│   └── compute_kind.py       # Compute任务生命周期管理
├── cli/                      # 命令行入口
│   ├── main.py               # 主命令入口
│   ├── job.py                # 任务相关命令
│   ├── pool.py               # 资源池相关命令
│   ├── quota.py              # 资源配额命令
│   └── node.py               # 节点相关命令
├── server/                   # API服务器
│   ├── main.py               # 服务器入口
│   ├── models.py             # 数据模型
│   ├── auth.py               # 认证授权
│   ├── dependencies.py       # 依赖注入
│   └── routes/               # API路由
│       ├── jobs.py           # 任务管理路由
│       ├── pools.py          # 资源池管理路由
│       ├── quotas.py         # 资源配额路由
│       ├── nodes.py          # 节点管理路由
│       ├── labels.py         # 标签管理路由
│       └── auth.py           # 认证路由
├── tests/                    # 测试用例
│   ├── conftest.py           # 测试配置
│   ├── test_gpuctl.py        # 核心功能测试
│   ├── api/                  # API测试
│   │   ├── test_jobs.py      # 任务API测试
│   │   ├── test_pools.py     # 资源池API测试
│   │   ├── test_nodes.py     # 节点API测试
│   │   └── test_labels.py    # 标签API测试
│   └── cli/                  # CLI测试
│       ├── test_job_commands.py    # 任务命令测试
│       ├── test_pool_commands.py   # 资源池命令测试
│       └── test_node_commands.py   # 节点命令测试
├── main.py                   # 主入口
├── INSTALLATION_GUIDE.md     # 安装指南
└── pyproject.toml            # 项目配置
```

### 启动开发服务器

```bash
python server/main.py
```

### 运行测试

```bash
pytest
```

### 构建二进制文件

您可以使用 PyInstaller 构建独立的二进制文件，这样您就可以在没有 Python 环境的情况下运行 gpuctl。

#### 前提条件

- PyInstaller 5.0+
- Python 3.12（推荐）

#### 构建步骤

1. 安装依赖

```bash
pip install kubernetes>=24.2.0 PyYAML>=6.0 pydantic>=2.0 pyinstaller
```

2. 为 Linux/macOS 构建二进制文件

```bash
# 为 Linux 构建
pyinstaller --onefile --name="gpuctl-linux-amd64" --hidden-import=yaml --hidden-import=PyYAML main.py

# 为 macOS 构建
pyinstaller --onefile --name="gpuctl-macos-amd64" --hidden-import=yaml --hidden-import=PyYAML main.py
```

3. 为 Windows 构建二进制文件

```bash
pyinstaller --onefile --name="gpuctl-windows-amd64.exe" --hidden-import=yaml --hidden-import=PyYAML main.py
```

4. 查找构建的二进制文件

```bash
ls -la dist/
```

构建的二进制文件将在 `dist/` 目录中。

5. 使用二进制文件

```bash
# Linux/macOS
chmod +x dist/gpuctl-linux-amd64
./dist/gpuctl-linux-amd64 --help

# Windows
./dist/gpuctl-windows-amd64.exe --help
```

## 贡献指南

1. Fork 代码库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目主页：https://github.com/your-org/gpuctl
- 问题反馈：https://github.com/your-org/gpuctl/issues
- 文档地址：https://github.com/your-org/gpuctl/tree/main/doc

## 致谢

感谢所有为项目做出贡献的开发者和用户！
