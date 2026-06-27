# Training Jobs

Training jobs (`kind: training`) are designed for AI model training scenarios. They map to a Kubernetes **Job** resource and terminate automatically when the run completes. For `mode: multi-node` distributed jobs, they map to an **Indexed Job + Headless Service** (see [Multi-Node Distributed Training](#multi-node-distributed-training)).

## Full YAML Fields

```yaml
kind: training
version: v0.1

job:
  name: <job-name>          # Required, used as the K8s resource name
  priority: medium          # high / medium / low
  description: "..."        # Optional

environment:
  image: <image>            # Required
  notebook: <notebook-name> # Optional, reuse a Notebook's /home/jovyan (NFS) + conda envs
  conda: <env-name>         # Optional, conda env to activate before running command
  imagePullSecret: <secret> # Optional, for private registries
  command: [...]            # Startup command (string or list, see note below)
  args: [...]               # Command arguments (optional)
  env:                      # Environment variables (optional)
    - name: KEY
      value: VALUE

distributed:                # Optional, defaults to standalone (single-node)
  mode: standalone          # standalone | multi-node
  workers: 1                # Worker count (multi-node only; multi-node needs > 1)
  master_port: 29500        # DDP rendezvous port (multi-node only, default 29500)

resources:
  pool: default             # Resource pool, default: default
  gpu: 4                    # Number of GPUs (per worker in multi-node mode)
  gpuType: A100-80G         # GPU model (optional)
  cpu: 32                   # CPU cores
  memory: 128Gi             # Memory

storage:                    # Optional & legacy — see note below. Most jobs omit this.
  workdirs:                 # Host directory mounts (hostPath)
    - path: /scratch/cache
```

!!! tip "Persistent storage is automatic — no `storage` section needed"
    If the operator has run `gpuctl init`, every training job automatically mounts a persistent, per-namespace `/home/jovyan` (read-write) and a shared `/datasets` (read-only) over NFS. Write checkpoints to `/home/jovyan` and they survive job restarts and are visible to your other jobs. The `storage.workdirs` field above is a **separate, optional** `hostPath` mechanism — most jobs should omit it. See [Persistent Storage](storage.md) for details.

!!! note "`command` accepts a string or a list"
    A string is automatically wrapped as `bash -c`. These two forms are equivalent:

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

## Example 1: LlamaFactory LLM Fine-Tuning (Single-Node Multi-GPU)

Fine-tune Qwen2-7B with SFT using LlamaFactory + DeepSpeed on a single node with 4 GPUs. Base models live in the shared read-only `/datasets`; outputs and checkpoints are written to the persistent `/home/jovyan` (auto-mounted over NFS — no `storage` section needed).

```yaml title="qwen2-7b-sft.yaml"
kind: training
version: v0.1

job:
  name: qwen2-7b-llamafactory-sft
  priority: high
  description: "Qwen2-7B SFT fine-tuning (LlamaFactory + DeepSpeed)"

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

!!! info "What the platform handles for you"
    - **GPU binding.** Declaring `gpu: 4` requests 4 GPUs and runs the pod with the `nvidia` RuntimeClass so CUDA/`nvidia-smi` work inside the container.
    - **Persistent storage.** `/home/jovyan` and `/datasets` are mounted automatically (when NFS is initialized) — checkpoints under `/home/jovyan` survive restarts. See [Persistent Storage](storage.md).
    - **Single-node scope.** This is still one pod. Frameworks like DeepSpeed/torchrun launch one process per GPU **inside** that pod. To scale across **multiple nodes**, use `mode: multi-node` ([below](#multi-node-distributed-training)).

---

## Example 2: Reuse a Notebook Environment (conda)

If you already prepared a conda environment inside a Notebook, a training job can reuse the exact same `/home/jovyan` and conda env — no reinstalling dependencies. Set `environment.notebook` to resolve the NFS home from that Notebook's namespace, and `environment.conda` to the env name to activate.

```yaml title="reuse-notebook.yaml"
kind: training
version: v0.1

job:
  name: gpt2-finetune
  priority: medium

environment:
  notebook: alice-notebook      # reuse this Notebook's /home/jovyan (and its conda envs)
  conda: myenv                  # activate conda env "myenv" before running command
  image: pytorch/pytorch:2.1.0-cuda11.8-cudnn8-devel
  command: "python /home/jovyan/train.py"   # string form, auto-wrapped as bash -c

resources:
  pool: training-pool
  gpu: 2
  gpuType: A100-80G
  cpu: 16
  memory: 64Gi
```

When `conda` is set, the platform wraps your command so it runs inside an activated conda environment (`conda activate myenv && exec <command>`). Omit `conda` and your command runs directly with no wrapping. Conda envs created in a Notebook live under `/home/jovyan/.conda/envs/`, so they are visible to the training job through the shared NFS home.

---

## Multi-Node Distributed Training

For training that must span **multiple machines** (e.g. very large models), set `distributed.mode: multi-node` and the number of `workers`. The platform then:

- Creates an **Indexed Job** with `completions = parallelism = workers` (one indexed worker pod each).
- Creates a **Headless Service** (`<job-name>-headless`) so workers discover each other by stable DNS.
- **Auto-injects DDP rendezvous environment variables** into every worker (you do not declare these):

| Variable | Meaning | Example (4 workers × 2 GPU) |
|----------|---------|-----------------------------|
| `MASTER_ADDR` | DNS name of worker 0 (the master) | `llm-pretrain-0.llm-pretrain-headless.ml-team.svc.cluster.local` |
| `MASTER_PORT` | DDP rendezvous port | `29500` |
| `WORLD_SIZE` | Total number of workers | `4` |
| `RANK` | This worker's index (0 = master), from the pod's completion index | `0`, `1`, `2`, `3` |
| `LOCAL_RANK` | GPU index within the worker | `0` |
| `GPUCTL_NPROC_PER_NODE` | GPUs per worker (= `resources.gpu`) | `2` |

!!! warning "What is NOT auto-configured"
    The platform injects the rendezvous variables above and creates the networking — it does **not** set `NCCL_SOCKET_IFNAME`, generate a DeepSpeed hostfile, or pick a launcher for you. Your command (e.g. `torchrun`) consumes the injected variables. Set framework-specific tunables like `NCCL_SOCKET_IFNAME` yourself via `environment.env` if your network needs them.

!!! note "`mode: multi-node` requires `workers > 1`"
    With `workers: 1` (or `mode: standalone`), behavior is identical to a single-node job — no Indexed Job and no Headless Service are created. Total GPUs = `workers × resources.gpu`.

```yaml title="llm-pretrain-distributed.yaml"
kind: training
version: v0.1

job:
  name: llm-pretrain
  namespace: ml-team
  priority: high
  description: "Multi-node pretraining (4 workers × 2 GPU = 8 GPU)"

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
  gpu: 2            # GPUs PER worker → 4 × 2 = 8 GPUs total
  gpuType: A100-80g
  cpu: 16
  memory: 128Gi
  pool: training-pool
```

```bash
gpuctl create -f llm-pretrain-distributed.yaml
gpuctl get jobs --kind training -n ml-team   # 4 worker pods: llm-pretrain-0 .. llm-pretrain-3
gpuctl logs llm-pretrain -n ml-team -f
```

!!! tip "Checkpoints are shared automatically"
    All workers mount the **same** `/home/jovyan` over NFS, so every worker can write/read checkpoints to the same path with no inter-node file syncing. Deleting the job removes the Indexed Job **and** its Headless Service — no orphaned resources.

---

## Example 3: Hyperparameter Search

Submit multiple training jobs simultaneously for hyperparameter comparison:

```bash
# Batch submit (target the same pool to avoid contention with production jobs)
gpuctl create -f lr1e-4.yaml -f lr2e-4.yaml -f lr5e-4.yaml

# View experiment jobs
gpuctl get jobs --pool experiment-pool --kind training
```

---

## Monitoring Training Status

```bash
# List training jobs
gpuctl get jobs --kind training

# Stream logs (track training loss)
gpuctl logs qwen2-7b-llamafactory-sft -f

# Job details (including K8s Events)
gpuctl describe job qwen2-7b-llamafactory-sft
```

## Deleting Training Jobs

```bash
# Normal delete
gpuctl delete job qwen2-7b-llamafactory-sft

# Force delete (immediate termination)
gpuctl delete job qwen2-7b-llamafactory-sft --force
```

!!! warning "Training Jobs Cannot Be Paused"
    K8s Jobs do not support pause/resume semantics. To stop and resume training, implement checkpoint logic in your training script and write checkpoints to the persistent `/home/jovyan` (auto-mounted over NFS) so they survive a restart. See [Persistent Storage](storage.md).
