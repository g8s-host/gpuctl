# gpuctl 模型结构

本文档描述 gpuctl 中 Kind、K8s 资源、命名规则、标签体系之间的映射关系，是所有 CLI/API 行为的设计依据。

## 一、Kind → K8s 资源映射

| Kind | K8s 主资源 | 附属 Service | 说明 |
|------|-----------|-------------|------|
| **training** | `Job` (batch/v1) | 无 | 一次性训练任务，运行完即结束 |
| **inference** | `Deployment` (apps/v1) | `svc-{name}` (NodePort) | 长期运行的推理服务 |
| **notebook** | `StatefulSet` (apps/v1) | `svc-{name}` (NodePort) | 交互式开发环境，有状态 |
| **compute** | `Deployment` (apps/v1) | `svc-{name}` (NodePort) | 通用计算服务 |

## 二、命名规则

所有命名的源头是 YAML 文件中的 `job.name` 字段（下文简称 `{name}`）。

### 2.1 K8s 资源命名

| 资源类型 | 命名规则 | 示例（`job.name: new-test-inference-job`） |
|---------|---------|------------------------------------------|
| 主资源（Deployment/Job/StatefulSet） | `{name}` | `new-test-inference-job` |
| Service | `svc-{name}` | `svc-new-test-inference-job` |

主资源的 `metadata.name` 与 YAML `job.name` **完全相同**，不做任何变换。

### 2.2 Pod 命名（K8s 自动生成）

Pod 名称由 K8s 控制器自动在主资源名后追加后缀，规则因资源类型而异：

| Kind | Pod 命名规则 | 示例 |
|------|-------------|------|
| training | `{name}-{random5}` | `test-training-job-zlflg` |
| inference | `{name}-{rs-hash}-{pod-hash}` | `new-test-inference-job-854c6c5cd-kfh77` |
| notebook | `{name}-{序号}` | `new-test-notebook-job-0` |
| compute | `{name}-{rs-hash}-{pod-hash}` | `test-nginx-848cbf4cf5-2h4ss` |

> Pod 名称是 K8s 内部标识，用户不需要记忆或使用。

## 三、Label 体系

### 3.1 通用 Label（所有 Kind 共享）

| Label | 值 | 用途 |
|-------|---|------|
| `g8s.host/job-type` | `training` / `inference` / `notebook` / `compute` | 区分任务类型 |
| `g8s.host/priority` | `high` / `medium` / `low` | 调度优先级 |
| `g8s.host/pool` | 资源池名 或 `default` | 绑定资源池 |
| `g8s.host/namespace` | namespace 名称 | 记录所属命名空间，便于跨 namespace 快速定位 |

### 3.2 反查 Label（从 Pod 找回 `job.name`）

这是 `get jobs` 显示 NAME 列的数据来源：

| Kind | Label | 设置方式 |
|------|-------|---------|
| inference / notebook / compute | `app: {name}` | Builder 在 Pod template 中手动设置 |
| training | `job-name: {name}` | K8s Job 控制器自动设置 |

代码中通过 `_get_job_name(labels)` 函数统一读取：

```python
def _get_job_name(labels: dict) -> str:
    return labels.get('app') or labels.get('job-name') or ''
```

## 四、Storage（存储挂载）

`storage.workdirs` 是 gpuctl YAML 中声明**宿主机目录挂载**的字段。它告诉 K8s：把节点上的某个目录挂进容器，让容器可以读写宿主机上的数据集、模型文件等。

### 4.1 三者对照：YAML → K8s → kubectl 看到的

```
# gpuctl YAML（你写的）
storage:
  workdirs:
    - path: /home/data/
    - path: /checkpoints/

              ↓ Builder 展开（每条 path 生成一对 Volume + VolumeMount）

# K8s Pod Spec（自动生成）
spec:
  volumes:
  - name: workdir-0
    hostPath:
      path: /home/data/
      type: DirectoryOrCreate
  - name: workdir-1
    hostPath:
      path: /checkpoints/
      type: DirectoryOrCreate
  containers:
  - name: main
    volumeMounts:
    - name: workdir-0
      mountPath: /home/data/
    - name: workdir-1
      mountPath: /checkpoints/
```

**关键点：`path` 同时作为宿主机路径和容器内挂载路径**，即容器看到的目录结构与宿主机上完全一致。如果目录不存在，K8s 会自动创建（`DirectoryOrCreate`）。

### 4.2 命名规则

| 顺序 | Volume 名 | 挂载路径 |
|------|----------|---------|
| 第 0 条 | `workdir-0` | `path` 字段的值 |
| 第 1 条 | `workdir-1` | `path` 字段的值 |
| 第 i 条 | `workdir-{i}` | `path` 字段的值 |

### 4.3 describe 时的还原

`describe job` 显示 **Original YAML Key Content** 时，会从 Pod spec 中反向还原 `storage.workdirs`：扫描所有 `hostPath` 类型的 Volume，将其 `path` 依次写回列表。

## 五、`get jobs` 输出列

`get jobs` 通过 `include_pods=True` 直接查询 Pod，输出列含义如下：

| 列 | 含义 | 数据来源 |
|----|------|---------|
| **JOB ID** | Pod 的 K8s 名称 | `pod.metadata.name` |
| **NAME** | YAML 中的 `job.name` | `_get_job_name(pod.labels)` |
| **NAMESPACE** | Pod 所在命名空间 | `pod.metadata.namespace` |
| **KIND** | 任务类型 | label `g8s.host/job-type` |
| **STATUS** | Pod 运行状态 | `pod.status.phase` + container status |
| **READY** | 就绪/总容器数 | `container_statuses` |
| **NODE** | 调度到的节点 | `pod.spec.node_name` |
| **IP** | Pod IP 地址 | `pod.status.pod_ip` |
| **AGE** | 创建至今的时长 | `pod.metadata.creation_timestamp` |

## 六、`describe job` 输出字段

`describe job` 查询父资源（Deployment/Job/StatefulSet），输出详细信息：

### 6.1 基本信息

| 字段 | 含义 | 数据来源 |
|------|------|---------|
| **Name** | YAML `job.name` / K8s 资源名 | `resource.metadata.name` |
| **Kind** | 任务类型 | label `g8s.host/job-type` |
| **Resource Type** | K8s 资源类型 | `Job` / `Deployment` / `StatefulSet` |
| **Namespace** | 所在命名空间 | `resource.metadata.namespace` |
| **Status** | 运行状态 | 根据 resource type 计算（见下） |
| **Age** | 创建至今时长 | `resource.metadata.creation_timestamp` |
| **Started** | 启动时间 | `resource.status.start_time` |
| **Completed** | 完成时间（仅 training） | `resource.status.completion_time` |
| **Priority** | 优先级 | label `g8s.host/priority` |
| **Pool** | 资源池 | label `g8s.host/pool` |

### 6.2 状态计算规则

| Resource Type | 状态判定逻辑 |
|--------------|-------------|
| **Job** | `succeeded > 0` → Succeeded, `failed > 0` → Failed, `active > 0` → Running, 否则 Pending |
| **Deployment** | `ready == desired && > 0` → Running, `ready > 0` → Partially Running, 否则 Pending |
| **StatefulSet** | `readyReplicas >= replicas && > 0` → Running, `readyReplicas > 0` → Partially Running, 否则 Pending |

### 6.3 Deployment 特有字段

| 字段 | 含义 |
|------|------|
| Ready Replicas | 就绪副本数 |
| Unavailable Replicas | 不可用副本数 |
| Current Replicas | 当前副本数 |
| Desired Replicas | 期望副本数 |

### 6.4 Original YAML Key Content

通过 `job_mapper` 将 K8s 资源反向映射回 gpuctl YAML 格式，展示 environment、resources、storage 等原始配置。

### 6.5 Events

查询关联的 K8s Events（最近 10 条），包含：

| 字段 | 含义 |
|------|------|
| Age | 事件发生时间 |
| Type | Normal / Warning |
| Reason | 事件原因（如 Scheduled, Pulling, Created, Started） |
| From | 事件来源组件（如 default-scheduler, kubelet） |
| Object | 关联的 K8s 对象 |
| Message | 事件详细信息 |

### 6.6 Access Methods（仅 inference / notebook / compute）

| 字段 | 含义 | 数据来源 |
|------|------|---------|
| Pod IP | Pod 内部 IP | `pod.status.pod_ip` |
| Pod Port | 容器端口 | Service `targetPort` |
| Node IP | 节点 IP | `node.status.addresses[InternalIP]` |
| NodePort | 节点端口 | Service `nodePort` |

## 七、其他 `get` / `describe` 命令输出

### 7.1 `get nodes` 输出列

| 列 | 含义 | 数据来源 |
|----|------|---------|
| **NODE NAME** | 节点名称 | `node.metadata.name` |
| **STATUS** | 节点状态 | `node.status.conditions` |
| **GPU TOTAL** | GPU 总数 | `node.status.capacity` |
| **GPU USED** | 已用 GPU | 通过 Pod 资源请求计算 |
| **GPU FREE** | 可用 GPU | total - used |
| **GPU TYPE** | GPU 型号 | label `g8s.host/gpuType` |
| **IP** | 节点 IP | `node.status.addresses[InternalIP]` |
| **POOL** | 所属资源池 | label `g8s.host/pool` |

### 7.2 `get pools` 输出列

| 列 | 含义 | 数据来源 |
|----|------|---------|
| **POOL NAME** | 资源池名称 | ConfigMap `metadata.name` |
| **STATUS** | 资源池状态 | 根据节点状态计算 |
| **GPU TOTAL** | GPU 总数 | 池内节点 GPU 总和 |
| **GPU USED** | 已用 GPU | 池内节点已用 GPU 总和 |
| **GPU FREE** | 可用 GPU | total - used |
| **NODE COUNT** | 节点数量 | 池内节点列表长度 |

### 7.3 `get namespaces` 输出列

| 列 | 含义 | 数据来源 |
|----|------|---------|
| **NAME** | 命名空间名称 | `namespace.metadata.name` |
| **STATUS** | 命名空间状态 | `namespace.status.phase` |
| **AGE** | 创建时间 | `namespace.metadata.creation_timestamp` |

> 仅显示 gpuctl 创建的命名空间（label `g8s.host/namespace=true`）+ default。

### 7.4 `describe namespace` 输出字段

| 字段 | 含义 | 数据来源 |
|------|------|---------|
| **Name** | 命名空间名称 | `namespace.metadata.name` |
| **Status** | 命名空间状态 | `namespace.status.phase` |
| **Age** | 创建时间 | `namespace.metadata.creation_timestamp` |
| **Labels** | 标签集合 | `namespace.metadata.labels` |
| **Quota - CPU** | CPU 配额（已用/总量） | `ResourceQuota.hard.cpu` / `used.cpu` |
| **Quota - Memory** | 内存配额（已用/总量） | `ResourceQuota.hard.memory` / `used.memory` |
| **Quota - GPU** | GPU 配额（已用/总量） | `ResourceQuota.hard.nvidia.com/gpu` / `used` |

### 7.5 `describe pool` 输出字段

| 字段 | 含义 |
|------|------|
| **Name** | 资源池名称 |
| **Description** | 资源池描述 |
| **Status** | 状态 |
| **GPU Total/Used/Free** | GPU 使用情况 |
| **GPU Types** | GPU 型号列表 |
| **Node Count** | 节点数量 |
| **Nodes** | 节点名称列表 |
| **Running Jobs** | 运行中的作业列表 |

## 八、CLI 命令与资源的对应关系

### 8.1 create

```
gpuctl create -f xxx.yaml [-n namespace]
```

- 解析 YAML，根据 `kind` 调用对应的 Builder 构建 K8s 资源
- **前置检查**：namespace 是否存在、quota 是否配置、pool 是否有节点、**同名资源是否已存在**
- 创建主资源 + Service（training 无 Service）

### 8.2 delete

```
gpuctl delete job <job.name> [-n namespace] [--force]
```

- 用户输入的是 YAML `job.name`，等于 K8s 主资源的 `metadata.name`
- **精确匹配**：在所有（或指定）namespace 中搜索 `metadata.name == job.name` 的父资源
- 跨 namespace 同名时报歧义，需通过 `--namespace` 消歧
- 删除父资源（K8s 控制器自动级联删除 Pod）+ 删除 Service
- **孤儿 Pod 兜底**：若父资源已不存在但 Pod 仍在，通过 `_get_job_name(pod.labels)` 匹配并清理

### 8.3 apply

```
gpuctl apply -f xxx.yaml [-n namespace]
```

- 先删后建（delete + create），等价于 update

### 8.4 describe

```
gpuctl describe job <job.name> [-n namespace]
```

- 查询父资源详情 + 关联 Pod 状态 + Events + Access Methods（详见第六节）

## 九、命名关系链示例

以 `tests/yamls/inference/test-inference.yaml`（`job.name: new-test-inference-job`）为例：

```
YAML
  job.name = "new-test-inference-job"
      │
      ▼
K8s 资源
  Deployment.metadata.name  = "new-test-inference-job"
  Service.metadata.name     = "svc-new-test-inference-job"
      │
      ▼ (K8s 控制器自动创建)
Pod
  pod.metadata.name         = "new-test-inference-job-854c6c5cd-kfh77"
  pod.labels.app            = "new-test-inference-job"   ← 指回 job.name
  pod.labels.g8s.host/job-type = "inference"
  pod.labels.g8s.host/namespace = "default"             ← 记录所属 namespace
      │
      ▼
get jobs 输出
  JOB ID = "new-test-inference-job-854c6c5cd-kfh77"  (Pod 名)
  NAME   = "new-test-inference-job"                   (从 label 读取)
```

## 十、delete 操作对照表

| Kind | delete 删除的资源 | Pod 清理方式 |
|------|-----------------|-------------|
| training | `Job {name}` | K8s Job 控制器级联删除 |
| inference | `Deployment {name}` + `Service svc-{name}` | K8s Deployment 控制器级联删除 |
| notebook | `StatefulSet {name}` + `Service svc-{name}` | K8s StatefulSet 控制器级联删除 |
| compute | `Deployment {name}` + `Service svc-{name}` | K8s Deployment 控制器级联删除 |
