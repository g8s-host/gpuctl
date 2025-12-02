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

```
┌─────────────────────────────────────────────────────────────────┐
│                        算法工程师                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        gpuctl CLI                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        gpuctl API                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes 集群                              │
└─────────────────────────────────────────────────────────────────┘
```

## 核心功能

### 1. 多类型任务支持

- **训练任务**：支持分布式训练，集成 DeepSpeed 等加速框架
- **推理服务**：支持模型部署，自动扩缩容
- **调试任务**：提供 Jupyter Notebook 环境，方便调试

### 2. 资源池管理

- 支持创建和管理资源池
- 节点与资源池的灵活绑定与解绑
- 资源池级别的资源隔离与配额管理

### 3. 声明式配置

- 使用算法工程师熟悉的术语
- 隐藏底层基础设施细节
- 支持 YAML 格式的任务定义

### 4. 丰富的 CLI 命令

- 任务生命周期管理
- 节点与资源池管理
- 实时日志查看
- 资源使用监控

## 安装

### 前提条件

- Python 3.8+
- Kubernetes 集群访问权限
- Poetry （用于依赖管理）

### 安装步骤

1. 克隆代码库

```bash
git clone https://github.com/your-org/gpuctl.git
cd gpuctl
```

2. 安装依赖

```bash
poetry install
```

3. 激活虚拟环境

```bash
poetry shell
```

4. 配置 Kubernetes 访问

确保 `kubectl` 已正确配置并能访问目标 Kubernetes 集群。

## 快速开始

### 1. 创建资源池

```yaml
# train-pool.yaml
kind: resource
version: v0.1

pool:
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

job:
  name: qwen2-7b-llamafactory-sft
  description: llama3推理任务
  epochs: 3
  batch_size: 8
  priority: high

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
  cpu: 32
  memory: 128Gi
  gpu_share: 2Gi

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

### 3. 查询任务状态

```bash
gpuctl get jobs
```

### 4. 查看任务日志

```bash
gpuctl logs qwen2-7b-llamafactory-sft -f
```

## CLI 命令参考

### 任务管理

| 命令示例 | 功能描述 |
|---------|---------|
| `gpuctl create -f train-job.yaml` | 提交一个训练任务 |
| `gpuctl get jobs` | 列出所有任务及核心指标 |
| `gpuctl describe job <job-id>` | 查看任务详细信息及资源使用曲线 |
| `gpuctl logs <job-id> -f` | 实时查看任务日志 |
| `gpuctl delete -f job.yaml` | 删除/停止任务 |
| `gpuctl pause job <job-id>` | 暂停运行中的任务 |
| `gpuctl resume job <job-id>` | 恢复暂停的任务 |

### 资源池管理

| 命令示例 | 功能描述 |
|---------|---------|
| `gpuctl get pools` | 查询所有资源池及资源占用情况 |
| `gpuctl create -f pool.yaml` | 创建新的资源池 |
| `gpuctl delete -f pool.yaml` | 删除资源池 |
| `gpuctl describe pool <pool-name>` | 查看资源池详细信息 |
| `gpuctl add node <node-name> --pool <pool-name>` | 将节点添加到资源池 |
| `gpuctl remove node <node-name> --pool <pool-name>` | 从资源池移除节点 |

### 节点管理

| 命令示例 | 功能描述 |
|---------|---------|
| `gpuctl get nodes` | 列出集群所有节点的基础信息 |
| `gpuctl get nodes --pool <pool-name>` | 过滤查询指定资源池绑定的所有节点 |
| `gpuctl get nodes --gpu-type <gpu-type>` | 过滤查询带有指定 GPU 类型的所有节点 |
| `gpuctl describe node <node-name>` | 查看单个节点的详细信息 |
| `gpuctl label node <node-name> <label-key>=<label-value>` | 给指定节点标记 Label |
| `gpuctl label node <node-name> <label-key> --delete` | 删除指定节点的指定 Label |

## API 文档

平台提供 RESTful API 接口，可用于构建第三方工具或集成到现有系统中。

### 基础信息

- **基础路径**：`/api/v1`
- **数据格式**：JSON/YAML
- **认证方式**：Bearer Token
- **版本控制**：URL 路径包含版本号

### 核心 API 端点

- **任务管理**：`/jobs`
- **资源池管理**：`/pools`
- **节点管理**：`/nodes`
- **Label 管理**：`/nodes/labels`
- **监控指标**：`/jobs/{jobId}/metrics`
- **日志查询**：`/jobs/{jobId}/logs`

### 交互式 API 文档

启动服务器后，可通过以下地址访问交互式 Swagger UI：

```
http://localhost:8000/api/v1/docs
```

## 开发指南

### 目录结构

```
gpuctl/
├── api/             # API 定义
├── builder/         # 任务构建器
├── cli/             # CLI 命令实现
├── client/          # 客户端实现
├── kind/            # 任务类型定义
├── parser/          # YAML 解析器
├── server/          # 服务器实现
├── tests/           # 测试用例
├── main.py          # 主入口
├── poetry.lock      # 依赖锁定文件
└── pyproject.toml   # 项目配置
```

### 启动开发服务器

```bash
poetry run python server/main.py
```

### 运行测试

```bash
poetry run pytest
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