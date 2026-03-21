# 快速开始

本指南帮助你在 5 分钟内完成 gpuctl 的安装，并提交第一个任务到 Kubernetes 集群。

## 前提条件

- Python 3.8+
- 可访问的 Kubernetes 集群（`kubectl` 已配置好 kubeconfig）
- 集群中至少有一个可用节点

## 第一步：安装 gpuctl

=== "从源码安装（推荐）"

    ```bash
    git clone https://github.com/g8s-host/gpuctl.git
    cd gpuctl
    pip install -e .
    ```

=== "二进制文件安装"

    ```bash
    # Linux x86_64
    wget https://github.com/g8s-host/gpuctl/releases/latest/download/gpuctl-linux-amd64 -O gpuctl
    chmod +x gpuctl
    sudo mv gpuctl /usr/local/bin/

    # macOS x86_64
    curl -L https://github.com/g8s-host/gpuctl/releases/latest/download/gpuctl-macos-amd64 -o gpuctl
    chmod +x gpuctl
    sudo mv gpuctl /usr/local/bin/
    ```

安装完成后验证：

```bash
gpuctl --help
```

## 第二步：验证集群连接

```bash
gpuctl get nodes
```

输出示例：

```
NODE NAME     STATUS   GPU TOTAL  GPU USED  GPU FREE  GPU TYPE    IP              POOL
node-1        Ready    8          0         8         A100-80G    192.168.1.101   default
node-2        Ready    4          0         4         A10-24G     192.168.1.102   default
```

## 第三步：提交第一个任务

以下示例使用 `nginx` 镜像（无需 GPU），快速验证平台工作正常：

**1. 创建 YAML 文件**

```yaml title="hello-gpuctl.yaml"
kind: compute
version: v0.1

job:
  name: hello-gpuctl
  priority: medium
  description: 第一个 gpuctl 任务

environment:
  image: nginx:latest
  command: []
  args: []

service:
  replicas: 1
  port: 80

resources:
  pool: default
  gpu: 0
  cpu: 1
  memory: 512Mi
```

**2. 提交任务**

```bash
gpuctl create -f hello-gpuctl.yaml
```

输出：

```
Job created successfully: hello-gpuctl
Namespace: default
```

**3. 查看任务状态**

```bash
gpuctl get jobs
```

```
JOB ID                              NAME          NAMESPACE  KIND     STATUS    READY  NODE    IP           AGE
hello-gpuctl-7d9c8b-xk2lp           hello-gpuctl  default    compute  Running   1/1    node-1  10.42.0.5    2m
```

**4. 查看任务详情**

```bash
gpuctl describe job hello-gpuctl
```

**5. 查看日志**

```bash
gpuctl logs hello-gpuctl
```

**6. 删除任务**

```bash
gpuctl delete job hello-gpuctl
```

## 第四步：提交 GPU 训练任务（可选）

如果集群有 GPU 节点，尝试提交一个简单的训练任务：

```yaml title="simple-training.yaml"
kind: training
version: v0.1

job:
  name: simple-training
  priority: medium

environment:
  image: pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime
  command: ["python", "-c", "import torch; print(f'GPU available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')"]

resources:
  pool: default
  gpu: 1
  cpu: 4
  memory: 16Gi
```

```bash
gpuctl create -f simple-training.yaml
gpuctl logs simple-training -f
```

## 常用命令速查

| 场景 | 命令 |
|------|------|
| 提交任务 | `gpuctl create -f job.yaml` |
| 查看所有任务 | `gpuctl get jobs` |
| 查看特定类型任务 | `gpuctl get jobs --kind training` |
| 实时日志 | `gpuctl logs <job-name> -f` |
| 任务详情 | `gpuctl describe job <job-name>` |
| 删除任务 | `gpuctl delete job <job-name>` |
| 查看资源池 | `gpuctl get pools` |
| 查看节点 | `gpuctl get nodes` |

## 下一步

- [训练任务](training.md) — 提交 LlamaFactory / DeepSpeed 分布式训练
- [推理服务](inference.md) — 部署 VLLM 推理 API 服务
- [资源池管理](pool.md) — 创建和管理 GPU 资源池
- [CLI 参考](../cli/index.md) — 完整命令文档
