# gpuctl CLI 使用手册

## 1. 产品简介

gpuctl 是面向算法工程师的 AI 算力调度平台命令行工具，让您无需掌握 Kubernetes 等底层基础设施知识，即可高效提交和管理 AI 训练与推理任务。

### 核心特性

- ∙🚀 **简单易用**：声明式 YAML 配置，直观的 CLI 命令
- ∙⚡ **高性能**：深度优化 Deepspeed、VLLM 等主流工具性能
- ∙🔧 **工具兼容**：全面支持 Llama Factory、SGLang 等 AI 工具链
- ∙📊 **资源可视**：实时监控 GPU 利用率、训练进度等关键指标
- ∙🔒 **资源隔离**：基于资源池的精细化管理，避免任务争抢

## 2. 安装与配置

### 2.1 安装 gpuctl

```
# 下载最新版本 (示例版本号)
wget https://download.example.com/gpuctl/gpuctl-v1.0.0-linux-amd64 -O /usr/local/bin/gpuctl

# 添加执行权限
chmod +x /usr/local/bin/gpuctl

# 验证安装
gpuctl version

# 预期输出：
# gpuctl version v1.0.0
# Build Date: 2024-06-01
# Git Commit: a1b2c3d4
# Platform: linux/amd64
```

### 2.2 配置认证

```
# 配置 API 服务器地址和认证令牌
gpuctl config set-context production \
  --server=https://gpuctl.example.com \
  --token=your-bearer-token-here

# 查看当前配置
gpuctl config view

# 预期输出：
# CURRENT CONTEXT: production
# SERVER: https://gpuctl.example.com
# TOKEN: ************abcd
# USER: alice@example.com
# NAMESPACE: default
```

### 2.3 验证连接

```
# 测试与平台的连接状态
gpuctl cluster-info

# 预期输出：
# Cluster: production
# Server Version: v1.0.0
# API Server: https://gpuctl.example.com
# Status: Connected ✓

# 预期输出：
Cluster: production
Server Version: v1.0.0
API Server: https://gpuctl.example.com
Platform Status: Healthy ✓
GPU Nodes: 8 nodes (64 GPUs total)
Scheduler: Running
Last Heartbeat: 2024-06-01 10:30:00 UTC
```

## 3. 快速开始

### 3.1 您的第一个训练任务

**步骤 1：创建训练配置文件** (`qwen-sft.yaml`)

```
kind: training
version: v0.1

job:
  name: my-first-llama-training
  epochs: 3
  batch_size: 8
  priority: medium

environment:
  image: registry.example.com/llama-factory-deepspeed:v0.8.0
  command: ["llama-factory-cli", "train", "--stage", "sft", "--model_name_or_path", "/models/qwen2-7b", "--dataset", "alpaca-qwen", "--output_dir", "/output"]

resources:
#  pool: training-pool
  gpu: 2
  cpu: 16
  memory: 64Gi
```

**步骤 2：提交任务**

```
gpuctl create -f qwen-sft.yaml

# 预期输出：
✅ Job created successfully!
Job ID: my-first-llama-training-abc123
Name: my-first-llama-training
Kind: training
Status: Pending
Pool: training-pool
Estimated Start: within 30 seconds
View details: gpuctl describe job my-first-llama-training-abc123
```



**步骤 3：查看任务状态**

```
# 查看任务列表
gpuctl get jobs

# 预期输出：
# NAME                      KIND       POOL           STATUS    GPU   PROGRESS  AGE
# my-first-llama-training   training   training-pool  running   2     0%        30s
```



**步骤 4：实时监控进度**

```
# 查看任务详情
gpuctl describe job my-first-llama-training
```

```
# 预期输出：
Job Details: my-first-llama-training-abc123
─────────────────────────────────────────────
Basic Information:
  Name: my-first-llama-training
  ID: my-first-llama-training-abc123
  Kind: training
  Status: Running ✓
  Priority: medium
  Created: 2024-06-01 10:00:00 UTC (2 minutes ago)
  Started: 2024-06-01 10:00:30 UTC

Resource Configuration:
  Pool: training-pool
  GPU: 2 x A100-80G
  CPU: 16 cores
  Memory: 64 GiB
  Node: gpu-node-3

Current Metrics:
  GPU Utilization: ██████████ 89.2%
  Memory Usage: 58 GiB / 80 GiB (72.5%)
  Training Progress: ████∙∙∙∙∙∙ 15.3%
  Throughput: 245 tokens/second
  Current Epoch: 1/3
  Steps: 150/980

Associated Pods:
  • my-first-llama-training-abc123-pod-1 (Running)
  • my-first-llama-training-abc123-pod-2 (Running)

Next Steps:
  View logs: gpuctl logs my-first-llama-training-abc123 -f
  Monitor: watch gpuctl describe job my-first-llama-training-abc123
```



```
# 实时查看日志
gpuctl logs  -f my-first-llama-training
```

```
[2024-06-01 10:01:30] INFO: Starting training with 2 GPUs
[2024-06-01 10:01:31] INFO: Using DeepSpeed ZeRO-2 optimization
[2024-06-01 10:01:35] INFO: Epoch 1/3, Step 10/980, Loss: 2.345, LR: 2.00e-05
[2024-06-01 10:02:15] INFO: Epoch 1/3, Step 20/980, Loss: 1.987, LR: 2.00e-05
[2024-06-01 10:02:55] INFO: Epoch 1/3, Step 30/980, Loss: 1.734, LR: 2.00e-05
...
```



## 4. 核心命令详解

### 4.1 任务管理命令

#### 创建任务

```
# 创建单个任务
gpuctl create -f training-job.yaml

# 预期输出：
✅ Job created successfully!
Job ID: custom-training-xyz789
Name: custom-training
Kind: training
Status: Pending
Pool: training-pool
Estimated Start: within 45 seconds
View details: gpuctl describe job custom-training-xyz789


# 批量创建多个任务
gpuctl create -f task1.yaml -f task2.yaml -f task3.yaml

# 预期输出：
🔄 Creating 3 jobs...
✅ task1-experiment-001: Created successfully
✅ task2-experiment-002: Created successfully  
✅ task3-experiment-003: Created successfully

Summary:
• Created: 3 jobs
• Pending: 3 jobs
• Failed: 0 jobs
View all jobs: gpuctl get jobs --name task1,task2,task3
```

#### 查看任务

```
# 查看所有任务
gpuctl get jobs

# 预期输出：
NAME                          KIND       POOL           STATUS    GPU   PROGRESS  AGE
my-first-llama-training       training   training-pool  running   2     15%       2m
qwen2-7b-sft-xyz789           training   training-pool  completed 4     100%      1h


# 按资源池筛选任务
gpuctl get jobs --pool training-pool

# 预期输出：
NAME                          KIND       POOL           STATUS    GPU   PROGRESS  AGE
my-first-llama-training       training   training-pool  running   2     15%       2m
qwen2-7b-sft-xyz789           training   training-pool  completed 4     100%      1h

# 按任务类型筛选
gpuctl get jobs --kind training
NAME                          KIND       POOL           STATUS    GPU   PROGRESS  AGE
my-first-llama-training       training   training-pool  running   2     15%       2m
qwen2-7b-sft-xyz789           training   training-pool  completed 4     100%      1h

gpuctl get jobs --kind inference
gpuctl get jobs --kind notebook

# 按状态筛选
gpuctl get jobs --status running
gpuctl get jobs --status pending
gpuctl get jobs --status completed
gpuctl get jobs --status failed

# 组合筛选条件
gpuctl get jobs --pool training-pool --status running --kind training

# 自定义输出格式
gpuctl get jobs -o wide        # 显示详细信息
gpuctl get jobs -o yaml        # YAML格式输出
gpuctl get jobs --sort-by=age  # 按创建时间排序
gpuctl get jobs --sort-by=gpu  # 按GPU数量排序

# 持续查看
watch gpuctl get jobs -o wide
watch gpuctl get jobs
```

#### 任务详情与监控

```
# 查看任务详细信息
gpuctl describe job <job-id>

# 预期输出：
Job Details: my-first-llama-training-abc123
─────────────────────────────────────────────
Basic Information:
  Name: my-first-llama-training
  ID: my-first-llama-training-abc123
  Kind: training
  Status: Running ✓
  Priority: medium
  Created: 2024-06-01 10:00:00 UTC (2 minutes ago)
  Started: 2024-06-01 10:00:30 UTC

Resource Configuration:
  Pool: training-pool
  GPU: 2 x A100-80G
  CPU: 16 cores
  Memory: 64 GiB
  Node: gpu-node-3

Current Metrics:
  GPU Utilization: ██████████ 89.2%
  Memory Usage: 58 GiB / 80 GiB (72.5%)
  Training Progress: ████∙∙∙∙∙∙ 15.3%
  Throughput: 245 tokens/second
  Current Epoch: 1/3
  Steps: 150/980

Associated Pods:
  • my-first-llama-training-abc123-pod-1 (Running)
  • my-first-llama-training-abc123-pod-2 (Running)

Next Steps:
  View logs: gpuctl logs my-first-llama-training-abc123 -f
  Monitor: watch gpuctl describe job my-first-llama-training-abc123

```

```
# 实时查看任务日志
gpuctl logs <job-id> -f

# 预期输出：
[2024-06-01 10:01:30] INFO: Starting training with 2 GPUs
[2024-06-01 10:01:31] INFO: Using DeepSpeed ZeRO-2 optimization
[2024-06-01 10:01:35] INFO: Epoch 1/3, Step 10/980, Loss: 2.345, LR: 2.00e-05
[2024-06-01 10:02:15] INFO: Epoch 1/3, Step 20/980, Loss: 1.987, LR: 2.00e-05
[2024-06-01 10:02:55] INFO: Epoch 1/3, Step 30/980, Loss: 1.734, LR: 2.00e-05
...

```



```

# 查看最近100行日志
gpuctl logs <job-id> --tail=100

# 预期输出：
=== Last 100 lines of logs ===
[2024-06-01 10:05:30] INFO: Epoch 1/3, Step 80/980, Loss: 1.234, LR: 2.00e-05
[2024-06-01 10:06:10] INFO: Epoch 1/3, Step 90/980, Loss: 1.198, LR: 2.00e-05
[2024-06-01 10:06:50] INFO: Epoch 1/3, Step 100/980, Loss: 1.165, LR: 2.00e-05
...

# 按时间范围查看日志
gpuctl logs <job-id> --since=1h
gpuctl logs <job-id> --since-time="2024-01-01T10:00:00Z"

# 日志关键词过滤
gpuctl logs <job-id> | grep "ERROR"
gpuctl logs <job-id> | grep -i "epoch"
```



#### 任务生命周期管理

```
# 暂停运行中的任务（保留资源）
gpuctl pause job <job-id>

# 恢复暂停的任务
gpuctl resume job <job-id>

# 删除任务
gpuctl delete job <job-id>



# 强制删除（立即释放资源）
gpuctl delete job <job-id> --force

# 批量删除任务
gpuctl delete job job1 job2 job3

# 通过配置文件删除
gpuctl delete -f job.yaml

# 预期输出：
🗑️  Deleting job: my-first-llama-training-abc123
⚠️  This will terminate the training process and release all resources
❓ Are you sure you want to continue? [y/N]: y
🔄 Stopping training process...
🔄 Cleaning up temporary files...
✅ Job deleted successfully
Released resources: 2 GPUs, 16 CPU cores, 64Gi memory
```

### 4.2 资源池管理



#### 资源池操作（管理员权限）

```
# 创建资源池
gpuctl create -f <your-pool-name>.yaml
✅ Resource pool created successfully!
Name: training-pool
Description: 高性能训练资源池，用于大模型训练任务

Status: Active
Nodes: 0 nodes (0 GPUs) - Use 'gpuctl add node' to assign nodes
View details: gpuctl describe pool training-pool
```



```
# 删除资源池
gpuctl delete -f <your-pool-name>.yaml
🗑️  Deleting resource pool: training-pool
⚠️  This action cannot be undone. The following will be affected:
• 8 nodes will be removed from the pool
• 32 running jobs will be moved to default-pool
#• Resource quotas will be removed

❓ Are you sure you want to continue? [y/N]: y
🔄 Moving running jobs to default-pool...
🔄 Removing node labels...
🔄 Cleaning up pool configuration...
✅ Resource pool 'training-pool' deleted successfully
#Released: 8 nodes, 64 GPUs
Affected jobs: 32 jobs moved to default-pool
```





#### 查看资源池

```
# 查看所有资源池及资源使用情况
gpuctl get pools

# 预期输出：
POOL NAME         TYPE       NODES  GPU_TOTAL  GPU_USED  GPU_FREE  UTILIZATION  STATUS    AGE
training-pool     training   4      32         16        16        50%          ✅ Active   30d
inference-pool    inference  2      16         8         8         50%          ✅ Active   30d
dev-pool          development 2     8          4         4         50%          ✅ Active   15d
experiment-pool   research   2      16         0         16        0%           ✅ Active   7d
default-pool      mixed      0      0          0         0         0%           ✅ Active   30d

💡 Use 'gpuctl describe pool <name>' for detailed information
```



```
# 查看特定资源池详情
gpuctl describe pool training-pool

# 预期输出：
Resource Pool: training-pool
─────────────────────────────
Description: 高性能训练资源池，用于大模型训练任务
Type: Training
Status: Active ✅
Created: 2024-05-01 10:00:00 UTC (30 days ago)
Updated: 2024-06-01 09:00:00 UTC (1 hour ago)

Resource Configuration:
• Total Nodes: 4 nodes
• Total GPU: 32 (16 used, 16 free)
• GPU Types: A100-80G (24), A100-40G (8)
• Total CPU: 256 cores
• Total Memory: 1 TiB

Current Utilization:
• GPU Usage: █████████∙ 50.0%
• Active Jobs: 12 jobs
• Avg GPU Utilization: 78.3%
• Peak Utilization: 92.1% (2024-05-15 14:30:00)

Quota Limits:
• Max Jobs: 50
• Max GPU per Job: 8
• Max Concurrent Users: 20
• Preemption: Allowed for high priority jobs

Associated Nodes (4):
• gpu-node-1: 8 GPUs (4 used) - A100-80G
• gpu-node-2: 8 GPUs (4 used) - A100-80G
• gpu-node-3: 8 GPUs (4 used) - A100-80G
• gpu-node-4: 8 GPUs (4 used) - A100-40G

Active Jobs (12):
• qwen2-7b-sft-abc123 (4 GPUs, 45% progress, high priority)
• llama3-training-def456 (2 GPUs, 78% progress, medium priority)
• ...

```

```
# 查看资源池中的任务
gpuctl get jobs --pool training-pool

# 预期输出：
NAME                          KIND       POOL           STATUS    GPU   PROGRESS  AGE
my-first-llama-training       training   training-pool  running   2     15%       2m
qwen2-7b-sft-xyz789           training   training-pool  completed 4     100%      1h
```



### 4.3 节点管理

#### 查看节点信息

```
# 查看所有节点
gpuctl get nodes

# 查看节点详细信息
gpuctl describe node <node-name>

# 按资源池查看节点
gpuctl get nodes --pool training-pool

# 按GPU类型查看节点
gpuctl get nodes --gpu-type a100-80g

# 查看节点GPU详情
gpuctl get nodes --gpu-detail

# 查看节点标签
gpuctl get node-labels --all
```

#### 节点标签管理（管理员权限）

```
# 给节点添加标签
gpuctl label node node-1 nvidia.com/gpu-type=a100-80g

# 批量添加标签
gpuctl label node node-2 node-3 company.com/gpu-model=a100-40g

# 覆盖现有标签
gpuctl label node node-1 nvidia.com/gpu-type=a100-40g --overwrite

# 查看特定标签
gpuctl get node-labels node-1 --key=nvidia.com/gpu-type

# 删除标签
gpuctl label node node-1 nvidia.com/gpu-type --delete
```



## 2. 节点管理命令

### 添加节点到资源池

```
# 添加单个节点到资源池
gpuctl add node gpu-node-1 --pool training-pool

# 批量添加多个节点
gpuctl add node gpu-node-2 gpu-node-3 gpu-node-4 --pool training-pool

# 添加节点并指定GPU类型
gpuctl add node gpu-node-5  --gpu-type A100-80G --pool training-pool
```

**返回示例：**

```
🔧 Adding nodes to training-pool...
✅ gpu-node-1: Successfully added (8 x A100-80G GPUs)
✅ gpu-node-2: Successfully added (8 x A100-80G GPUs)  
✅ gpu-node-3: Successfully added (8 x A100-80G GPUs)
✅ gpu-node-4: Successfully added (8 x A100-40G GPUs)

Summary:
• Added: 4 nodes
• Total GPU: 32 GPUs (24 x A100-80G, 8 x A100-40G)
• Pool Status: Active with 32/32 GPUs available
• Next: Submit jobs using 'gpuctl create -f job.yaml'

Updated Pool Status:
training-pool: 4 nodes, 32 GPUs, 0% utilization
```

### 从资源池移除节点

```
# 从资源池移除单个节点
gpuctl remove node gpu-node-3 --pool training-pool

# 批量移除多个节点
gpuctl remove node gpu-node-4 gpu-node-5 --pool training-pool

# 强制移除（即使节点上有运行的任务）
gpuctl remove node gpu-node-1 --pool training-pool --force
```

**返回示例：**

```
🔧 Removing nodes from training-pool...
⚠️  gpu-node-3 has 2 running jobs (using 4 GPUs):
   • job-abc123 (2 GPUs, training, 45% progress)
   • job-def456 (2 GPUs, training, 15% progress)

Summary:
• Removed: 1 node (gpu-node-3)
• GPUs Removed: 8 x A100-80G
• Jobs Affected: 2 jobs completed normally
• Pool Status: training-pool now has 24 GPUs (75% capacity)
```

**强制移除的返回示例：**

```
🔧 Force removing node from training-pool...
🚨 FORCE REMOVAL: This will terminate all running jobs on gpu-node-1
Running jobs to be terminated:
• job-abc123 (4 GPUs, training, 60% progress) - WILL BE LOST
• job-def456 (2 GPUs, training, 30% progress) - WILL BE LOST

❓ Are you absolutely sure? This cannot be undone. [y/N]: y

🔄 Force removing gpu-node-1...
🔄 Terminating 2 running jobs...
🔄 Removing node labels...
✅ gpu-node-1: Force removed from training-pool

Summary:
• Removed: 1 node (gpu-node-1) 
• GPUs Removed: 8 x A100-80G
• Jobs Terminated: 2 jobs (6 GPUs total)
• Data Loss: Training progress from terminated jobs is not recoverable
• Pool Status: training-pool now has 24 GPUs
```

### 查看资源池节点列表

```
# 列出指定资源池的所有节点
gpuctl get nodes --pool training-pool
```

**返回示例：**

```
NODE NAME     STATUS   GPU_TOTAL  GPU_USED  GPU_FREE  GPU_TYPE    UTILIZATION  JOBS  AGE
gpu-node-1    Ready    8          4         4         A100-80G   85%          2    30d
gpu-node-2    Ready    8          4         4         A100-80G   78%          3    30d
gpu-node-3    Ready    8          4         4         A100-80G   92%          1    30d
gpu-node-4    Ready    8          4         4         A100-40G   65%          2    30d

TOTAL: 4 nodes, 32 GPUs (16 used, 16 free) - 50.0% utilization
# 详细查看资源池节点信息
gpuctl get nodes --pool training-pool -o wide
```

**返回示例：**

```
NODE NAME     STATUS   GPU_TOTAL  GPU_USED  GPU_FREE  GPU_TYPE    CPU  MEMORY   JOBS  UTILIZATION  TEMPERATURE  AGE
gpu-node-1    Ready    8          4         4         A100-80G   64   256Gi    2     85%          72°C         30d
gpu-node-2    Ready    8          4         4         A100-80G   64   256Gi    3     78%          68°C         30d
gpu-node-3    Ready    8          4         4         A100-80G   64   256Gi    1     92%          75°C         30d
gpu-node-4    Ready    8          4         4         A100-40G   64   256Gi    2     65%          62°C         30d

SUMMARY:
• Nodes: 4 (all Ready)
• GPUs: 32 total (16 used, 16 free) - 50.0% utilization
• Jobs: 8 running jobs
• Avg Utilization: 80.0%
• Health: All nodes operating within normal parameters
```

## 5. 实用场景示例

### 5.1 大模型微调完整流程

```
# 1. 提交微调任务
gpuctl create -f qwen2-7b-sft.yaml

# 2. 监控任务启动
gpuctl get jobs --name qwen2-7b-sft -w

# 3. 实时查看训练日志
gpuctl logs -f qwen2-7b-sft-xxxxx

# 4. 监控训练指标
watch gpuctl describe job qwen2-7b-sft-xxxxx

# 5. 训练完成后下载结果
gpuctl cp qwen2-7b-sft-xxxxx:/output ./training-results/

# 6. 停止训练任务
gpuctl apply -f qwen2-7b-sft.yaml
```

### 5.2 多实验对比

```
# 1. 准备多个实验配置
gpuctl create -f exp1.yaml exp2.yaml exp3.yaml

# 2. 监控所有实验进度
watch 'gpuctl get jobs --pool experiment-pool'

# 3. 比较实验资源使用
gpuctl get jobs --pool experiment-pool -o wide

# 4. 批量管理实验任务
# 暂停所有实验
gpuctl get jobs --pool experiment-pool --status running -o name | xargs -I {} gpuctl pause job {}

# 删除失败的任务
gpuctl get jobs --pool experiment-pool --status failed -o name | xargs -I {} gpuctl delete job {}
```

### 5.3 交互式开发

```
# 1. 启动Notebook环境
gpuctl create -f notebook.yaml

# 2. 获取访问地址
gpuctl describe job data-prep-notebook

# 3. 动态调整资源
gpuctl scale job data-prep-notebook --gpu=2

# 4. 文件传输
gpuctl cp ./local-script.py data-prep-notebook:/home/jovyan/work/

# 5. 关闭环境
gpuctl delete job data-prep-notebook
```



## 6. 高级功能

### 6.1 自动补全配置

```
# 配置Bash自动补全
echo 'source <(gpuctl completion bash)' >> ~/.bashrc
source ~/.bashrc

# 配置Zsh自动补全
echo 'source <(gpuctl completion zsh)' >> ~/.zshrc
source ~/.zshrc
```

### 6.2 输出格式定制

```
# JSON格式输出，便于脚本处理
gpuctl get jobs -o json | jq '.items[] | select(.status == "running")'

# 自定义列显示
gpuctl get jobs -o custom-columns=NAME:.name,STATUS:.status,GPU:.gpu,POOL:.pool

# 导出为YAML文件
gpuctl get job <job-id> -o yaml > job-backup.yaml
```

### 6.3 批量操作技巧

```
# 使用xargs进行批量操作
gpuctl get jobs --status completed -o name | xargs -I {} gpuctl delete job {}

# 并行提交多个任务
find ./experiments -name "*.yaml" | xargs -I {} -P 4 gpuctl create -f {}

# 条件批量操作
gpuctl get jobs --pool training-pool --status running --sort-by=age | \
  tail -n +6 | \  # 跳过最近5个任务
  awk '{print $1}' | \
  xargs -I {} gpuctl pause job {}
```

## 7. 故障排查与调试

### 7.1 常见问题诊断

```
# 检查集群状态
gpuctl cluster-info

# 查看平台组件状态
gpuctl get components

# 检查资源池可用性
gpuctl query pools

# 验证任务配置
gpuctl create -f job.yaml --dry-run --verbose
```

### 7.2 任务调试技巧

```
# 查看任务事件（有助于诊断调度问题）
gpuctl describe job <job-id> | grep -A 10 -B 5 Events

# 实时监控资源使用
watch 'gpuctl describe job <job-id> | grep -A 5 "Metrics"'

# 进入调试模式（增加详细日志）
gpuctl --v=3 create -f job.yaml  # 级别1-5，数字越大越详细
```

### 7.3 获取帮助

```
# 查看所有命令
gpuctl --help

# 查看特定命令帮助
gpuctl create --help
gpuctl get --help
gpuctl describe --help

# 查看命令用法示例
gpuctl examples

# 查看版本信息
gpuctl version --client --server
```

## 8. 最佳实践

### 8.1 资源配置建议

```
# 训练任务推荐配置
resources:
  pool: training-pool
  gpu: 4              # 多卡训练提升效率
  cpu: 32             # CPU核心数建议为GPU数的8倍
  memory: 128Gi       # 内存建议为GPU显存的1.5倍

# 推理任务推荐配置  
resources:
  pool: inference-pool
  gpu: 1              # 单卡推理，通过副本数扩展
  cpu: 8              # 适量CPU支持预处理
  memory: 32Gi        # 根据模型大小调整
```

### 8.2 任务优先级管理

```
job:
  name: production-training
  priority: high      # 生产任务设为高优先级
  
job:
  name: experiment-tuning  
  priority: medium    # 实验任务设为中优先级

job:
  name: background-processing
  priority: low       # 后台任务设为低优先级
```

### 8.3 监控与告警设置

```
# 设置资源使用阈值监控
gpuctl get jobs --watch | while read line; do
  if echo "$line" | grep -q "GPU.*9[0-9]%"; then
    echo "高GPU使用率告警: $line"
  fi
done

# 定期检查任务健康状态
while true; do
  gpuctl get jobs --status failed && echo "有任务失败，请检查"
  sleep 300
done
```

## 9. 技术支持

### 获取帮助

- ∙📖 查看详细文档：`gpuctl docs`
- ∙🐛 报告问题：`gpuctl bug-report`
- ∙💬 社区支持：访问 [社区论坛](https://forum.example.com/)

### 故障反馈模板

```
# 生成诊断报告
gpuctl bug-report --output=diagnostic.tar.gz

# 包含的信息：
# - 客户端版本
# - 集群状态
# - 最近任务记录
# - 系统配置信息
```

------

**温馨提示**：本手册内容会随版本更新而调整，请使用 `gpuctl docs --latest`获取最新文档。祝您使用愉快！ 🎉