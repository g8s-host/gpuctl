# 训练任务

训练任务（`kind: training`）适用于 AI 模型训练场景，底层对应 Kubernetes **Job** 资源，任务运行完成后自动结束。`mode: multi-node` 分布式任务则对应 **Indexed Job + Headless Service**（见[多机多卡分布式训练](#multi-node-distributed-training)）。

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
  notebook: <notebook名称>   # 可选，复用某 Notebook 的 /home/jovyan(NFS) 与 conda 环境
  conda: <环境名>            # 可选，运行 command 前激活的 conda 环境
  imagePullSecret: <secret> # 可选，私有镜像拉取 Secret
  command: [...]             # 启动命令（字符串或列表，见下方说明）
  args: [...]                # 命令参数（可选）
  env:                       # 环境变量（可选）
    - name: KEY
      value: VALUE

distributed:                 # 可选，默认 standalone（单机）
  mode: standalone           # standalone | multi-node
  workers: 1                 # Worker 数（仅 multi-node 有意义；多机需 > 1）
  master_port: 29500         # DDP 通信端口（仅 multi-node，默认 29500）

resources:
  pool: default              # 资源池，默认 default
  gpu: 4                     # GPU 数量（multi-node 模式下为每个 Worker 的 GPU 数）
  gpuType: A100-80G          # GPU 型号（可选）
  cpu: 32                    # CPU 核数
  memory: 128Gi              # 内存

storage:                     # 可选，旧式机制 —— 见下方说明，大多数任务无需填写
  workdirs:                  # 宿主机目录挂载（hostPath）
    - path: /scratch/cache
```

!!! tip "持久化存储是自动的 —— 无需 `storage` 段"
    若运维已执行 `gpuctl init`，每个训练任务都会自动挂载按 namespace 隔离、可持久化的 `/home/jovyan`（读写）和共享的 `/datasets`（只读），均走 NFS。把 checkpoint 写到 `/home/jovyan`，重启后依然存在，也对你的其他任务可见。上面的 `storage.workdirs` 是**另一套独立、可选**的 `hostPath` 机制 —— 大多数任务应省略。详见[持久化存储](storage.md)。

!!! note "`command` 接受字符串或列表"
    字符串会被自动包装为 `bash -c`。以下两种写法等价：

    ```yaml
    command: "torchrun --nproc_per_node=8 /home/jovyan/train.py"
    ```
    ```yaml
    command:
      - bash
      - -c
      - "torchrun --nproc_per_node=8 /home/jovyan/train.py"
    ```

---

## 场景一：LlamaFactory 大模型微调（单机多卡）

在单节点 4 卡上用 LlamaFactory + DeepSpeed 对 Qwen2-7B 做 SFT 微调。基础模型放在共享只读的 `/datasets`，输出和 checkpoint 写到持久化的 `/home/jovyan`（走 NFS 自动挂载 —— 无需 `storage` 段）。

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
    - "/datasets/models/qwen2-7b"
    - "--dataset"
    - "alpaca-qwen"
    - "--dataset_dir"
    - "/datasets"
    - "--output_dir"
    - "/home/jovyan/output/qwen2-sft"
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

resources:
  pool: training-pool
  gpu: 4
  gpuType: A100-80G
  cpu: 32
  memory: 128Gi
```

```bash
gpuctl create -f qwen2-7b-sft.yaml -n ml-team
gpuctl logs qwen2-7b-llamafactory-sft -n ml-team -f
```

!!! info "平台为你处理了什么"
    - **GPU 绑定。** 声明 `gpu: 4` 即申请 4 块卡，并用 `nvidia` RuntimeClass 运行 Pod，使容器内 CUDA/`nvidia-smi` 可用。
    - **持久化存储。** `/home/jovyan` 和 `/datasets` 自动挂载（NFS 已初始化时）—— 写到 `/home/jovyan` 的 checkpoint 重启后不丢。见[持久化存储](storage.md)。
    - **仍是单机。** 这依然是一个 Pod。DeepSpeed/torchrun 等框架会在该 Pod **内部**每卡拉起一个进程。要扩展到**多个节点**，请用 `mode: multi-node`（[见下文](#multi-node-distributed-training)）。

---

## 场景二：复用 Notebook 环境（conda） {#example-2-reuse-a-notebook-environment-conda}

如果你已经在 Notebook 中准备好了 conda 环境，训练任务可以直接复用同一个 `/home/jovyan` 和 conda 环境，无需重装依赖。设置 `environment.notebook` 以从该 Notebook 的 namespace 解析 NFS home，设置 `environment.conda` 为要激活的环境名。

```yaml title="reuse-notebook.yaml"
kind: training
version: v0.1

job:
  name: gpt2-finetune
  priority: medium

environment:
  notebook: alice-notebook      # 复用此 Notebook 的 /home/jovyan（及其 conda 环境）
  conda: myenv                  # 运行 command 前激活 conda 环境 "myenv"
  image: pytorch/pytorch:2.1.0-cuda11.8-cudnn8-devel
  command: "python /home/jovyan/train.py"   # 字符串形式，自动包装为 bash -c

resources:
  pool: training-pool
  gpu: 2
  gpuType: A100-80G
  cpu: 16
  memory: 64Gi
```

设置了 `conda` 后，平台会把你的命令包装为在激活的 conda 环境中运行（`conda activate myenv && exec <命令>`）。不设 `conda` 则直接执行命令，不做任何包装。Notebook 中创建的 conda 环境默认位于 `/home/jovyan/.conda/envs/`，因此通过共享的 NFS home 对训练任务可见。

---

## 多机多卡分布式训练 {#multi-node-distributed-training}

对于需要跨**多台机器**的训练（如超大模型），设置 `distributed.mode: multi-node` 和 `workers` 数量。平台随即：

- 创建 **Indexed Job**，`completions = parallelism = workers`（每个带编号的 Worker 一个 Pod）。
- 创建 **Headless Service**（`<job-name>-headless`），让 Worker 之间通过稳定 DNS 互相发现。
- **自动向每个 Worker 注入 DDP 通信环境变量**（这些你无需声明）：

| 变量 | 含义 | 示例（4 workers × 2 GPU） |
|------|------|---------------------------|
| `MASTER_ADDR` | 0 号 Worker（主节点）的 DNS 名 | `llm-pretrain-0.llm-pretrain-headless.ml-team.svc.cluster.local` |
| `MASTER_PORT` | DDP 通信端口 | `29500` |
| `WORLD_SIZE` | Worker 总数 | `4` |
| `RANK` | 当前 Worker 编号（0=主节点），取自 Pod 的 completion index | `0`、`1`、`2`、`3` |
| `LOCAL_RANK` | Worker 内 GPU 编号 | `0` |
| `GPUCTL_NPROC_PER_NODE` | 每 Worker GPU 数（= `resources.gpu`） | `2` |

!!! warning "哪些不会自动配置"
    平台注入上述通信变量并创建网络资源 —— 但**不会**设置 `NCCL_SOCKET_IFNAME`、生成 DeepSpeed hostfile，也不会替你选择启动器。你的命令（如 `torchrun`）负责消费这些注入的变量。若你的网络需要，请通过 `environment.env` 自行设置 `NCCL_SOCKET_IFNAME` 等框架专属调优项。

!!! note "`mode: multi-node` 需要 `workers > 1`"
    当 `workers: 1`（或 `mode: standalone`）时，行为与单机任务完全一致 —— 不创建 Indexed Job，也不创建 Headless Service。总 GPU 数 = `workers × resources.gpu`。

```yaml title="llm-pretrain-distributed.yaml"
kind: training
version: v0.1

job:
  name: llm-pretrain
  namespace: ml-team
  priority: high
  description: "多机预训练（4 workers × 2 GPU = 8 GPU）"

environment:
  notebook: alice-notebook
  conda: myenv
  image: pytorch/pytorch:2.1.0-cuda11.8-cudnn8-devel
  command:
    - bash
    - -c
    - |
      torchrun \
        --nnodes=$WORLD_SIZE --node_rank=$RANK \
        --nproc_per_node=$GPUCTL_NPROC_PER_NODE \
        --master_addr=$MASTER_ADDR --master_port=$MASTER_PORT \
        /home/jovyan/pretrain.py

distributed:
  mode: multi-node
  workers: 4

resources:
  gpu: 2            # 每个 Worker 的 GPU 数 → 4 × 2 = 共 8 卡
  gpuType: A100-80g
  cpu: 16
  memory: 128Gi
  pool: training-pool
```

```bash
gpuctl create -f llm-pretrain-distributed.yaml
gpuctl get jobs --kind training -n ml-team   # 4 个 Worker Pod：llm-pretrain-0 .. llm-pretrain-3
gpuctl logs llm-pretrain -n ml-team -f
```

!!! tip "checkpoint 自动共享"
    所有 Worker 都挂载**同一块** NFS `/home/jovyan`，因此每个 Worker 都能往同一路径读写 checkpoint，无需节点间文件同步。删除该任务会同时删除 Indexed Job **和**它的 Headless Service —— 不留孤儿资源。

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
    K8s Job 不支持暂停/恢复语义。如需停止后继续训练，请在训练脚本中实现 checkpoint 断点续训逻辑，并把 checkpoint 写到持久化的 `/home/jovyan`（走 NFS 自动挂载），重启后即可续训。见[持久化存储](storage.md)。
