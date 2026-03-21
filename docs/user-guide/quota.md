# 配额与命名空间管理

gpuctl 通过 Kubernetes ResourceQuota 机制，为每个命名空间（团队/用户）设置 CPU、内存、GPU 资源上限，防止资源滥用，实现多租户隔离。

## 核心概念

- **命名空间（Namespace）**：K8s 的逻辑隔离单元，每个团队/用户分配一个独立命名空间
- **配额（Quota）**：限制命名空间内可使用的最大资源量（CPU/内存/GPU/Pod 数）
- **自动创建**：通过 `gpuctl create -f quota.yaml` 会自动创建命名空间 + 资源配额

---

## 创建配额

### 配额 YAML 格式

```yaml title="team-quota.yaml"
kind: quota
version: v0.1

quota:
  name: team-resource-quota
  description: "各团队资源配额配置"

namespace:
  team-alice:          # 命名空间名称（自动创建）
    cpu: 16            # CPU 核数上限
    memory: 64Gi       # 内存上限
    gpu: 8             # GPU 数量上限
  team-bob:
    cpu: 8
    memory: 32Gi
    gpu: 4
  team-charlie:
    cpu: 4
    memory: 16Gi
    gpu: 2
```

```bash
gpuctl create -f team-quota.yaml
```

平台会自动：
1. 创建 `team-alice`、`team-bob`、`team-charlie` 三个命名空间
2. 在每个命名空间内创建对应的 `ResourceQuota`
3. 标记命名空间为 gpuctl 管理（label `runwhere.ai/namespace=true`）

---

## 查询配额

```bash
# 列出所有配额
gpuctl get quotas
```

输出示例：

```
NAMESPACE       CPU (USED/TOTAL)   MEMORY (USED/TOTAL)   GPU (USED/TOTAL)   STATUS
team-alice      4/16               12Gi/64Gi             2/8                Active
team-bob        2/8                8Gi/32Gi              1/4                Active
team-charlie    0/4                0/16Gi                0/2                Active
default         -                  -                     -                  Active
```

```bash
# 查看指定命名空间配额
gpuctl get quotas team-alice

# 查看配额详情（含使用率）
gpuctl describe quota team-alice
```

---

## 在指定命名空间提交任务

配额创建后，团队成员在提交任务时通过 `-n` 指定命名空间：

```bash
# Alice 团队提交训练任务
gpuctl create -f training-job.yaml -n team-alice

# 查看 Alice 团队的任务
gpuctl get jobs -n team-alice
```

---

## 查询命名空间

```bash
# 列出所有由 gpuctl 管理的命名空间
gpuctl get ns
# 或
gpuctl get namespaces
```

输出示例：

```
NAME            STATUS   AGE
team-alice      Active   5d
team-bob        Active   5d
team-charlie    Active   2d
default         Active   30d
```

```bash
# 查看命名空间详情（含配额信息）
gpuctl describe ns team-alice
```

输出示例：

```
Name:    team-alice
Status:  Active
Age:     5d

Labels:
  runwhere.ai/namespace: true

Quota:
  CPU:    4/16
  Memory: 12Gi/64Gi
  GPU:    2/8
```

---

## 删除配额

```bash
# 通过 YAML 文件删除（批量删除 YAML 中定义的所有配额）
gpuctl delete -f team-quota.yaml

# 删除指定命名空间的配额
gpuctl delete quota team-charlie

# 删除命名空间（同时删除其中所有资源）
gpuctl delete ns team-charlie

# 强制删除（跳过确认提示）
gpuctl delete ns team-charlie --force
```

!!! danger "删除命名空间"
    删除命名空间会**删除该命名空间内的所有资源**（包括正在运行的任务、Service 等），此操作**不可逆**。请先确认已备份重要数据。

!!! tip "只能管理 gpuctl 创建的命名空间"
    gpuctl 只管理带有 `runwhere.ai/namespace=true` 标签的命名空间（由 gpuctl 创建），以及 `default` 命名空间。`kube-system` 等系统命名空间不在管理范围内。
