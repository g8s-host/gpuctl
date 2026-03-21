---
hide:
  - navigation
  - toc
---

# GPUCTL · AI 算力调度平台

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle .card-icon } **无需了解 Kubernetes**

    ---

    用算法工程师熟悉的声明式 YAML，提交训练、推理、Notebook 任务，平台自动完成底层调度。

    [:octicons-arrow-right-24: 快速开始](user-guide/quickstart.md)

-   :material-chip:{ .lg .middle .card-icon } **GPU 资源池化管理**

    ---

    将集群 GPU 节点划分为逻辑资源池，实现训练/推理/实验资源隔离，避免争抢。

    [:octicons-arrow-right-24: 资源池管理](user-guide/pool.md)

-   :material-console:{ .lg .middle .card-icon } **简洁的 CLI 命令**

    ---

    `gpuctl create / get / logs / delete`，与 kubectl 对标但更贴近算法工程师使用习惯。

    [:octicons-arrow-right-24: CLI 参考](cli/index.md)

-   :material-api:{ .lg .middle .card-icon } **RESTful API**

    ---

    完整的 REST API 支持，可集成到现有 MLOps 平台或第三方工具链。

    [:octicons-arrow-right-24: API 文档](developer-guide/api.md)

</div>

---

## 产品简介

**gpuctl** 是一个面向算法工程师的 AI 算力调度平台，旨在**显著降低 GPU 算力的使用门槛**。

通过声明式 YAML 配置和简单的 CLI 命令，算法工程师无需掌握 Kubernetes 等底层基础设施的复杂知识，即可高效提交和管理 AI 训练与推理任务。

### 解决的核心痛点

| 痛点 | gpuctl 解法 |
|------|------------|
| 算法工程师不熟悉 K8s（Pod、Deployment、Service…） | 声明式 YAML，只需填写熟悉的字段 |
| GPU 驱动、依赖库安装配置繁琐 | 镜像中预装，platform 自动注入环境变量 |
| 多团队 GPU 资源争抢 | 资源池隔离 + 配额管理 |
| 分布式训练环境搭建复杂 | 声明 gpu 数量，自动注入 NCCL/DeepSpeed 配置 |

---

## 系统架构

<div style="text-align: center;">
<img src="assets/architect.png" alt="gpuctl 系统架构" style="width: 50%;">
</div>

---

## 支持的任务类型

=== "训练任务"

    适合 LLM 微调（LlamaFactory + DeepSpeed）、分布式训练等场景。底层转换为 K8s **Job**。

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

=== "推理服务"

    适合 VLLM 推理服务部署，支持自动扩缩容。底层转换为 K8s **Deployment + Service + HPA**。

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

    适合交互式调试开发，提供 JupyterLab 环境。底层转换为 K8s **StatefulSet + Service**。

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

=== "计算任务"

    适合纯 CPU 服务（nginx、redis 等）。底层转换为 K8s **Deployment + Service**。

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

## 快速体验

```bash
# 1. 安装
pip install -e .

# 2. 提交训练任务
gpuctl create -f training-job.yaml

# 3. 查看任务状态
gpuctl get jobs

# 4. 实时日志
gpuctl logs qwen2-7b-sft -f

# 5. 删除任务
gpuctl delete job qwen2-7b-sft
```

[:octicons-arrow-right-24: 查看完整快速开始指南](user-guide/quickstart.md){ .md-button .md-button--primary }
[:octicons-arrow-right-24: 查阅 CLI 命令参考](cli/index.md){ .md-button }
