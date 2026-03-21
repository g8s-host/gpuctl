# 系统架构

本文档详细描述 gpuctl 的分层架构设计、核心模块职责、数据模型与 K8s 资源映射关系，以及 Label 体系规范。

---

## 整体架构

gpuctl 采用分层设计，每一层职责清晰：

```
┌────────────────────────────────────────────────────┐
│                     用户层                           │
│  gpuctl CLI（argparse）  ·  REST API（FastAPI）      │
└────────────────────────┬───────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────┐
│                   解析与验证层                        │
│  parser/base_parser.py                              │
│  · 读取 YAML 文件                                    │
│  · 根据 kind 分发到对应的 Pydantic 模型               │
│  · 字段校验（必填、范围、格式）                        │
└────────────────────────┬───────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────┐
│                   构建层（Builder）                   │
│  builder/training_builder.py  → K8s Job            │
│  builder/inference_builder.py → K8s Deployment     │
│  builder/notebook_builder.py  → K8s StatefulSet    │
│  builder/compute_builder.py   → K8s Deployment     │
│  builder/base_builder.py      → 公共方法             │
└────────────────────────┬───────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────┐
│                   K8s 客户端层（Client）              │
│  client/job_client.py    任务 CRUD                  │
│  client/pool_client.py   资源池（ConfigMap + Label） │
│  client/quota_client.py  ResourceQuota + Namespace  │
│  client/log_client.py    Pod 日志（流式）             │
│  client/base_client.py   K8s 连接和通用操作          │
└────────────────────────┬───────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────┐
│              Kubernetes API Server                   │
│         Job · Deployment · StatefulSet              │
│         Service · ConfigMap · ResourceQuota         │
└────────────────────────────────────────────────────┘
```

---

## Kind → K8s 资源映射

| Kind | K8s 主资源 | API Group | 附属 Service | 说明 |
|------|-----------|-----------|-------------|------|
| `training` | `Job` | `batch/v1` | 无 | 一次性训练，运行完结束 |
| `inference` | `Deployment` | `apps/v1` | `svc-{name}` (NodePort) | 长期推理服务 |
| `notebook` | `StatefulSet` | `apps/v1` | `svc-{name}` (NodePort) | 有状态开发环境 |
| `compute` | `Deployment` | `apps/v1` | `svc-{name}` (NodePort) | 通用 CPU 服务 |

---

## 命名规则

所有命名以 YAML `job.name` 为源头：

| 资源 | 命名规则 | 示例（`job.name: my-inference`） |
|------|---------|--------------------------------|
| 主资源 | `{name}` | `my-inference` |
| Service | `svc-{name}` | `svc-my-inference` |
| Pod（training） | `{name}-{random5}` | `my-training-zlflg` |
| Pod（inference） | `{name}-{rs-hash}-{pod-hash}` | `my-inference-854c6c5cd-kfh77` |
| Pod（notebook） | `{name}-{序号}` | `my-notebook-0` |

---

## Label 体系

### 通用 Label（所有 Kind 共享）

| Label Key | 值 | 用途 |
|-----------|---|------|
| `runwhere.ai/job-type` | `training` / `inference` / `notebook` / `compute` | 区分任务类型 |
| `runwhere.ai/priority` | `high` / `medium` / `low` | 调度优先级 |
| `runwhere.ai/pool` | 资源池名 或 `default` | 绑定资源池 |
| `runwhere.ai/namespace` | namespace 名称 | 记录所属命名空间 |

### 反查 Label（从 Pod 找回 job.name）

`get jobs` 显示 NAME 列时，通过此 Label 从 Pod 反查原始任务名：

| Kind | Label Key | 设置方式 |
|------|-----------|---------|
| inference / notebook / compute | `app: {name}` | Builder 手动在 Pod template 中设置 |
| training | `job-name: {name}` | K8s Job 控制器自动设置 |

代码实现：

```python
def _get_job_name(labels: dict) -> str:
    return labels.get('app') or labels.get('job-name') or ''
```

### 节点 Label（资源池 & GPU 型号）

| Label Key | 用途 |
|-----------|------|
| `runwhere.ai/pool` | 标记节点所属资源池 |
| `runwhere.ai/gpuType` | 标记节点 GPU 型号（gpuctl 内部使用） |
| `runwhere.ai/gpu-type` | 标记节点 GPU 型号（用户标记使用） |

---

## Storage 挂载机制

`storage.workdirs` 中的每个 `path` 会展开为一对 `Volume + VolumeMount`（hostPath 类型）：

```
# gpuctl YAML（用户写的）
storage:
  workdirs:
    - path: /models
    - path: /output

         ↓ Builder 展开

# K8s Pod Spec（平台自动生成）
spec:
  volumes:
    - name: workdir-0
      hostPath: { path: /models, type: DirectoryOrCreate }
    - name: workdir-1
      hostPath: { path: /output, type: DirectoryOrCreate }
  containers:
    - volumeMounts:
        - { name: workdir-0, mountPath: /models }
        - { name: workdir-1, mountPath: /output }
```

**关键点**：`path` 同时作为宿主机路径和容器内挂载路径，两者完全一致。

---

## `get jobs` 输出列

`get jobs` 直接查询 Pod，每行代表一个 Pod 实例：

| 列 | 含义 | 数据来源 |
|----|------|---------|
| JOB ID | Pod 名称（含 hash） | `pod.metadata.name` |
| NAME | YAML `job.name` | `_get_job_name(pod.labels)` |
| NAMESPACE | 所在命名空间 | `pod.metadata.namespace` |
| KIND | 任务类型 | label `runwhere.ai/job-type` |
| STATUS | Pod 状态 | `pod.status.phase` + container status |
| READY | 就绪/总容器数 | `container_statuses` |
| NODE | 调度到的节点 | `pod.spec.node_name` |
| IP | Pod IP | `pod.status.pod_ip` |
| AGE | 创建至今时长 | `pod.metadata.creation_timestamp` |

---

## apply 语义

`gpuctl apply -f xxx.yaml` 等价于：

```
delete（删除旧资源 + Service）
    +
create（重新创建资源 + Service）
```

即**先删后建**，实现配置更新语义。

---

## 状态计算规则

`describe job` 显示的 Status 字段由 K8s 资源状态计算得出：

| 资源类型 | 状态判定逻辑 |
|---------|------------|
| Job | `succeeded > 0` → Succeeded，`failed > 0` → Failed，`active > 0` → Running，否则 Pending |
| Deployment | `ready == desired && > 0` → Running，`ready > 0` → Partially Running，否则 Pending |
| StatefulSet | `readyReplicas >= replicas && > 0` → Running，`readyReplicas > 0` → Partially Running，否则 Pending |

---

## 常量文件

[`gpuctl/constants.py`](https://github.com/g8s-host/gpuctl/blob/main/gpuctl/constants.py) 集中定义了所有魔法字符串，包括：

- `Kind` 枚举：TRAINING / INFERENCE / NOTEBOOK / COMPUTE
- `Labels` 类：所有 Label Key 常量
- `KIND_TO_RESOURCE` 映射：Kind → K8s 资源类型
- `CONTAINER_WAITING_REASONS`：容器等待状态 → 用户友好状态字符串
- `DEFAULT_NAMESPACE / DEFAULT_POOL`：默认值

所有模块应从此文件导入常量，而非在各处硬编码字符串。
