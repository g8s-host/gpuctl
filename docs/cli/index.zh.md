# CLI 命令参考

gpuctl CLI 与 `kubectl` 对标，但语义更贴近算法工程师的使用习惯。

## 命令概览

| 命令 | 说明 |
|------|------|
| `create` | 从 YAML 创建资源（任务、资源池、配额） |
| `apply` | 应用配置（创建或更新，等价于先删后建） |
| `get` | 查询资源列表 |
| `describe` | 查看资源详情 |
| `delete` | 删除资源 |
| `logs` | 查看任务日志 |
| `label` | 管理节点标签 |

---

## create

从 YAML 文件创建资源。

```bash
gpuctl create -f <file> [-n <namespace>] [--json]
```

| 选项 | 说明 | 是否必填 |
|------|------|---------|
| `-f, --file` | YAML 文件路径（可多次指定） | 是 |
| `-n, --namespace` | 命名空间（默认：`default`） | 否 |
| `--json` | 以 JSON 格式输出 | 否 |

**示例：**

```bash
# 提交单个任务
gpuctl create -f training-job.yaml

# 批量提交多个任务
gpuctl create -f task1.yaml -f task2.yaml

# 指定命名空间
gpuctl create -f job.yaml -n team-alice

# JSON 格式输出
gpuctl create -f job.yaml --json
```

---

## apply

应用资源配置（先删除旧资源，再创建新资源）。

```bash
gpuctl apply -f <file> [-n <namespace>] [--json]
```

| 选项 | 说明 | 是否必填 |
|------|------|---------|
| `-f, --file` | YAML 文件路径（可多次指定） | 是 |
| `-n, --namespace` | 命名空间（默认：`default`） | 否 |
| `--json` | 以 JSON 格式输出 | 否 |

**示例：**

```bash
# 更新任务配置
gpuctl apply -f job.yaml

# 更新并指定命名空间
gpuctl apply -f job.yaml -n team-alice
```

---

## get

查询资源列表。支持多种资源类型和过滤条件。

### get jobs

```bash
gpuctl get jobs [-n <namespace>] [--pool <pool>] [--kind <kind>] [--pods] [--json]
```

| 选项 | 说明 |
|------|------|
| `-n, --namespace` | 指定命名空间（不指定则查询所有） |
| `--pool` | 按资源池过滤 |
| `--kind` | 按任务类型过滤：`training` / `inference` / `notebook` / `compute` |
| `--pods` | 显示 Pod 级别信息（而非 Deployment/StatefulSet 级别） |
| `--json` | JSON 格式输出 |

**输出列说明：**

| 列 | 含义 |
|----|------|
| JOB ID | Pod 名称（含 K8s 自动生成的 hash 后缀） |
| NAME | YAML 中的 `job.name` |
| NAMESPACE | 所在命名空间 |
| KIND | 任务类型 |
| STATUS | Pod 运行状态 |
| READY | 就绪/总容器数（如 `1/1`） |
| NODE | 调度到的节点 |
| IP | Pod IP |
| AGE | 创建至今的时长 |

**示例：**

```bash
gpuctl get jobs
gpuctl get jobs -n team-alice
gpuctl get jobs --pool training-pool
gpuctl get jobs --kind training
gpuctl get jobs --pods
```

### get pools

```bash
gpuctl get pools [--json]
```

**示例：**

```bash
gpuctl get pools
```

### get nodes

```bash
gpuctl get nodes [--pool <pool>] [--gpu-type <type>] [--json]
```

| 选项 | 说明 |
|------|------|
| `--pool` | 按资源池过滤 |
| `--gpu-type` | 按 GPU 型号过滤 |

**示例：**

```bash
gpuctl get nodes
gpuctl get nodes --pool training-pool
gpuctl get nodes --gpu-type A100-100G
```

### get labels

```bash
gpuctl get labels [<node_name>] [--key <key>] [--json]
```

**示例：**

```bash
# 查看节点所有标签
gpuctl get labels node-1

# 查看特定标签
gpuctl get labels node-1 --key=runwhere.ai/gpu-type
```

### get quotas

```bash
gpuctl get quotas [<namespace>] [--json]
```

**示例：**

```bash
gpuctl get quotas
gpuctl get quotas team-alice
```

### get ns / namespaces

```bash
gpuctl get ns [--json]
gpuctl get namespaces [--json]
```

---

## describe

查看资源详细信息。

### describe job

```bash
gpuctl describe job <job_name> [-n <namespace>] [--json]
```

**输出内容：**

- 基本信息：Name、Kind、Resource Type、Namespace、Status、Age、Priority、Pool
- 资源配置：CPU、Memory、GPU
- 原始 YAML：从 K8s 资源反映射回的 gpuctl YAML 配置
- Events：最近 10 条 K8s 事件
- Access Methods（仅 inference / notebook / compute）：Pod IP 和 NodePort 访问地址

**示例：**

```bash
gpuctl describe job my-training-job
gpuctl describe job my-training-job -n team-alice
```

### describe pool

```bash
gpuctl describe pool <pool_name> [--json]
```

**示例：**

```bash
gpuctl describe pool training-pool
```

### describe node

```bash
gpuctl describe node <node_name> [--json]
```

**示例：**

```bash
gpuctl describe node node-1
```

### describe quota / ns / namespace

```bash
gpuctl describe quota <namespace_name> [--json]
gpuctl describe ns <namespace_name> [--json]
gpuctl describe namespace <namespace_name> [--json]
```

**示例：**

```bash
gpuctl describe quota team-alice
gpuctl describe ns team-alice
```

---

## delete

删除资源。

### 通过 YAML 文件删除

```bash
gpuctl delete -f <file> [-n <namespace>] [--force] [--json]
```

**示例：**

```bash
gpuctl delete -f training-job.yaml
gpuctl delete -f pool.yaml
gpuctl delete -f quota.yaml
```

### delete job

```bash
gpuctl delete job <job_name> [-n <namespace>] [--force] [--json]
```

**示例：**

```bash
gpuctl delete job my-training-job
gpuctl delete job my-training-job -n team-alice
gpuctl delete job my-training-job --force
```

### delete quota

```bash
gpuctl delete quota <namespace_name> [--force] [--json]
```

**示例：**

```bash
gpuctl delete quota team-alice
```

### delete ns / namespace

```bash
gpuctl delete ns <namespace_name> [--force] [--json]
gpuctl delete namespace <namespace_name> [--force] [--json]
```

**示例：**

```bash
gpuctl delete ns team-alice
gpuctl delete ns team-alice --force
```

### delete pool

```bash
gpuctl delete pool <pool_name> [--force] [--json]
```

**示例：**

```bash
gpuctl delete pool training-pool
```

!!! warning "删除任务的行为"
    删除任务时，平台会同时删除：
    
    - K8s 主资源（Job / Deployment / StatefulSet）
    - 关联的 NodePort Service（training 任务无 Service）
    - K8s 控制器会自动级联删除关联的 Pod

---

## logs

获取任务日志。

```bash
gpuctl logs <job_name> [-n <namespace>] [-f] [--json]
```

| 选项 | 说明 |
|------|------|
| `<job_name>` | 任务名称 |
| `-n, --namespace` | 命名空间（默认：`default`） |
| `-f, --follow` | 实时跟踪日志（类似 `tail -f`） |
| `--json` | JSON 格式输出 |

**示例：**

```bash
# 查看最近日志（默认最后 100 行）
gpuctl logs my-training-job

# 实时跟踪
gpuctl logs my-training-job -f

# 指定命名空间
gpuctl logs my-training-job -n team-alice -f
```

---

## label

管理节点标签。

```bash
gpuctl label <node_name> [node_name...] <label> [--delete] [--overwrite] [--json]
```

!!! warning "标签键规范"
    gpuctl 管理的标签键**必须以 `runwhere.ai/` 开头**，避免与其他系统冲突。

| 选项 | 说明 |
|------|------|
| `<node_name>` | 节点名称（可指定多个） |
| `<label>` | `key=value` 格式（添加）或 `key` 格式（删除时使用） |
| `--delete` | 删除标签 |
| `--overwrite` | 覆盖已有同键标签 |

**示例：**

```bash
# 给单个节点添加 GPU 型号标签
gpuctl label node-1 runwhere.ai/gpu-type=A100-100G

# 给多个节点添加标签（注意：node_name 在命令中的位置）
gpuctl label node-1 node-2 runwhere.ai/gpu-type=A100-100G

# 覆盖已有标签
gpuctl label node-1 runwhere.ai/gpu-type=A10-24G --overwrite

# 删除标签
gpuctl label node-1 runwhere.ai/gpu-type --delete

# 绑定资源池
gpuctl label node-1 runwhere.ai/pool=training-pool
```

---

## 全局选项

| 选项 | 说明 |
|------|------|
| `--help` | 显示帮助信息 |
| `--json` | 以 JSON 格式输出（大多数命令支持） |

---

## 完整工作流示例

### 训练任务生命周期

```bash
# 1. 查看可用资源
gpuctl get nodes
gpuctl get pools

# 2. 提交训练任务
gpuctl create -f training-job.yaml -n team-alice

# 3. 监控状态
gpuctl get jobs -n team-alice

# 4. 实时查看日志
gpuctl logs my-training -n team-alice -f

# 5. 查看详细信息
gpuctl describe job my-training -n team-alice

# 6. 任务完成后清理
gpuctl delete job my-training -n team-alice
```

### 节点与资源池管理

```bash
# 1. 查看所有节点
gpuctl get nodes

# 2. 给节点打 GPU 型号标签
gpuctl label node-5 runwhere.ai/gpu-type=A100-100G

# 3. 创建资源池（将节点绑定）
gpuctl create -f training-pool.yaml

# 4. 查看资源池
gpuctl get pools
gpuctl describe pool training-pool

# 5. 查看池内节点
gpuctl get nodes --pool training-pool
```
