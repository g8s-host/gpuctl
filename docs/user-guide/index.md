# 用户指南

欢迎使用 gpuctl！本指南将帮助你从零开始掌握 gpuctl 的核心功能，高效管理 GPU 算力资源。

## 本章内容

<div class="grid cards" markdown>

-   :material-clock-fast:{ .lg .middle } **快速开始**

    ---

    5 分钟内完成安装配置并提交你的第一个任务。

    [:octicons-arrow-right-24: 快速开始](quickstart.md)

-   :material-brain:{ .lg .middle } **训练任务**

    ---

    支持 LlamaFactory、DeepSpeed 分布式训练，单机多卡 & 多机多卡场景完整示例。

    [:octicons-arrow-right-24: 训练任务](training.md)

-   :material-server:{ .lg .middle } **推理服务**

    ---

    基于 VLLM 等框架部署推理服务，支持多副本 + 自动扩缩容。

    [:octicons-arrow-right-24: 推理服务](inference.md)

-   :material-notebook:{ .lg .middle } **Notebook 开发**

    ---

    一键启动 JupyterLab 环境，挂载 GPU 资源，快速原型验证。

    [:octicons-arrow-right-24: Notebook 开发](notebook.md)

-   :material-cog:{ .lg .middle } **计算任务**

    ---

    部署 nginx、redis 等 CPU 服务，无需关注 K8s Deployment 细节。

    [:octicons-arrow-right-24: 计算任务](compute.md)

-   :material-pool:{ .lg .middle } **资源池管理**

    ---

    将节点划分为资源池，实现训练/推理资源隔离与精细化调度。

    [:octicons-arrow-right-24: 资源池管理](pool.md)

-   :material-gauge:{ .lg .middle } **配额与命名空间**

    ---

    为每个团队/用户设置 CPU、内存、GPU 配额，防止资源滥用。

    [:octicons-arrow-right-24: 配额与命名空间](quota.md)

</div>

---

## YAML 配置总览

所有资源都通过声明式 YAML 定义。以下是各字段的通用说明：

```yaml
kind: training          # 任务类型：training / inference / notebook / compute / pool / quota
version: v0.1           # 版本号，当前固定为 v0.1

job:
  name: my-job          # 任务名称（同时作为 K8s 资源名）
  priority: medium      # 优先级：high / medium / low
  description: "描述"   # 可选描述

environment:
  image: my-image:tag   # 容器镜像地址
  imagePullSecret: xxx  # 镜像拉取 Secret（可选）
  command: [...]        # 启动命令
  args: [...]           # 命令参数（可选）
  env:                  # 环境变量（可选）
    - name: KEY
      value: VALUE

resources:
  pool: default         # 资源池名称（默认 default）
  gpu: 0                # GPU 数量（0 表示纯 CPU 任务）
  gpu-type: A100-100G   # GPU 型号（可选，不填由 K8s 调度）
  cpu: 4                # CPU 核数
  memory: 8Gi           # 内存大小

service:                # 仅 inference / notebook / compute 有效
  replicas: 1           # 副本数
  port: 8080            # 服务端口
  healthCheck: /health  # 健康检查路径（可选）

storage:
  workdirs:             # 宿主机目录挂载列表
    - path: /data/models
    - path: /output
```

!!! tip "命名规则"
    `job.name` 字段直接作为 K8s 资源的 `metadata.name`，命名需符合 K8s 命名规范：只含小写字母、数字和连字符，长度不超过 63 个字符。
