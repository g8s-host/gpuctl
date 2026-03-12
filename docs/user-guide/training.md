# 训练任务

训练任务（`kind: training`）适用于 AI 模型训练场景，底层对应 Kubernetes **Job** 资源，任务运行完成后自动结束。

## YAML 完整字段

```yaml
kind: training
version: v0.1

job:
  name: <任务名称>          # 必填，K8s 资源名
  priority: medium          # high / medium / low
  description: "描述"       # 可选

environment:
  image: <镜像地址>          # 必填
  imagePullSecret: <secret> # 可选，私有镜像拉取 Secret
  command: [...]             # 启动命令
  args: [...]                # 命令参数（可选）
  env:                       # 环境变量（可选）
    - name: KEY
      value: VALUE

resources:
  pool: default              # 资源池，默认 default
  gpu: 4                     # GPU 数量
  gpu-type: A100-100G        # GPU 型号（可选）
  cpu: 32                    # CPU 核数
  memory: 128Gi              # 内存

storage:
  workdirs:                  # 宿主机目录挂载（hostPath）
    - path: /datasets
    - path: /models
    - path: /output
```

---

## 场景一：LlamaFactory 大模型微调（单机多卡）

使用 LlamaFactory 0.8.0 + DeepSpeed 0.14.0 对 Qwen2-7B 进行 SFT 微调。

```yaml title="qwen2-7b-sft.yaml"
kind: training
version: v0.1

job:
  name: qwen2-7b-llamafactory-sft
  priority: high
  description: "Qwen2-7B SFT 微调（LlamaFactory + DeepSpeed）"

environment:
  image: registry.example.com/llama-factory-deepspeed:v0.8.0
  imagePullSecret: my-registry-secret
  command:
    - "llama-factory-cli"
    - "train"
    - "--stage"
    - "sft"
    - "--model_name_or_path"
    - "/models/qwen2-7b"
    - "--dataset"
    - "alpaca-qwen"
    - "--dataset_dir"
    - "/datasets"
    - "--output_dir"
    - "/output/qwen2-sft"
    - "--per_device_train_batch_size"
    - "8"
    - "--gradient_accumulation_steps"
    - "4"
    - "--learning_rate"
    - "2e-5"
    - "--num_train_epochs"
    - "3"
    - "--deepspeed"
    - "ds_config.json"
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

storage:
  workdirs:
    - path: /datasets
    - path: /models/qwen2-7b
    - path: /cache/llama-factory
    - path: /output/qwen2-sft
    - path: /output/qwen2-sft/checkpoints
```

```bash
gpuctl create -f qwen2-7b-sft.yaml
gpuctl logs qwen2-7b-llamafactory-sft -f
```

!!! info "平台自动处理"
    声明 `gpu: 4` 后，平台自动完成：NVLink 网络配置、GPU 设备绑定、DeepSpeed 环境变量注入，无需手动编写 K8s 分布式 Job。

---

## 场景二：全参数微调（多机多卡，ZeRO-3）

适用于 Qwen2-72B、Llama3-70B 等超大模型的全量参数更新。

```yaml title="qwen2-72b-fullft.yaml"
kind: training
version: v0.1

job:
  name: qwen2-72b-fullft
  priority: high
  description: "Qwen2-72B 全参数微调（ZeRO-3 + 多机多卡）"

environment:
  image: registry.example.com/deepspeed-zero3:v1.2
  command:
    - "python"
    - "full_ft_train.py"
    - "--model_name_or_path"
    - "/models/qwen2-72b"
    - "--dataset"
    - "/datasets/domain-large-10M"
    - "--output_dir"
    - "/output/qwen2-72b-domain"
    - "--per_device_train_batch_size"
    - "2"
    - "--gradient_accumulation_steps"
    - "8"
    - "--learning_rate"
    - "5e-6"
    - "--num_train_epochs"
    - "2"
    - "--deepspeed"
    - "zero3_config.json"
    - "--bf16"
    - "true"
    - "--gradient_checkpointing"
    - "true"
  env:
    - name: NCCL_SOCKET_IFNAME
      value: "eth0"

resources:
  pool: training-pool
  gpu: 8
  gpu-type: A100-100G
  cpu: 64
  memory: 512Gi

storage:
  workdirs:
    - path: /models/qwen2-72b
    - path: /datasets/domain-large-10M
    - path: /output/qwen2-72b-domain
```

---

## 场景三：批量超参实验

同时提交多个训练任务进行超参对比实验：

```bash
# 批量提交（指定同一资源池，避免与生产任务争抢）
gpuctl create -f lr1e-4.yaml -f lr2e-4.yaml -f lr5e-4.yaml

# 查看实验任务
gpuctl get jobs --pool experiment-pool --kind training
```

---

## 监控训练状态

```bash
# 查看任务列表
gpuctl get jobs --kind training

# 实时日志（跟踪训练 loss）
gpuctl logs qwen2-7b-llamafactory-sft -f

# 任务详情（含 Events 事件）
gpuctl describe job qwen2-7b-llamafactory-sft
```

## 删除训练任务

```bash
# 正常删除
gpuctl delete job qwen2-7b-llamafactory-sft

# 强制删除（立即终止）
gpuctl delete job qwen2-7b-llamafactory-sft --force
```

!!! warning "训练任务无法暂停"
    K8s Job 不支持暂停/恢复语义。如需停止后继续训练，请在训练脚本中实现 checkpoint 断点续训逻辑，并通过 `storage.workdirs` 挂载 checkpoint 目录。
