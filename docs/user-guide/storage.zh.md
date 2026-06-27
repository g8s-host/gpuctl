# 持久化存储

gpuctl 提供基于 NFS 的**透明持久化存储**。运维只需注册一次 NFS 共享,之后用户提交的**每一个**任务都会自动获得一个持久化的家目录和一个共享的只读数据集目录 —— 用户的任务 YAML 中**无需任何存储配置**。

!!! tip "设计目标"
    工程师应该专注于训练代码,而不是存储配置。用户任务 YAML 中存储相关配置为 **0 行**:不填挂载路径、不声明 StorageClass、不写 PVC。写入 `/home/jovyan` 的文件在任务重启后依然存在,并在该用户的所有任务之间共享。

---

## 工作原理一览

```text
                gpuctl init  (运维，仅一次)
                      │
                      ▼
        ConfigMap kube-system/gpuctl-config
            nfs.server: <IP>
            nfs.path:   /exports
                      │
        每个任务 (training / inference / notebook / compute)
                      │  构建时读取该 ConfigMap
                      ▼
   ┌──────────────────────────────────────────────────┐
   │ Pod                                                │
   │   /home/jovyan  ←─ nfs:<server>:/exports/home/<ns> │  读写，按 namespace 隔离
   │   /datasets     ←─ nfs:<server>:/exports/datasets  │  只读，全员共享
   └──────────────────────────────────────────────────┘
```

- 用户的 namespace **即**用户身份。每个 namespace 独享自己的 `home/<namespace>` 目录。
- 挂载由平台对所有任务类型自动注入 —— YAML 里什么都不用声明。
- 若未配置 NFS,任务依然正常运行,只是没有这些挂载(见[向后兼容](#向后兼容))。

---

## 第一步:运维注册 NFS 共享(仅一次)

NFS 存储通过一条命令注册。gpuctl **不会**自己搭建 NFS 服务,它只记录已有共享的地址。

```bash
gpuctl init --nfs-server <IP_OR_HOST> --nfs-path <EXPORT_ROOT>
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--nfs-server` | 是 | NFS 服务器 IP 或主机名 |
| `--nfs-path` | 是 | NFS 导出根路径(必须以 `/` 开头) |

**示例:**

```bash
gpuctl init --nfs-server 192.168.1.100 --nfs-path /exports
```

输出:

```
NFS storage initialized:
  Server: 192.168.1.100
  Path:   /exports
  Config stored in: kube-system/gpuctl-config
```

配置存储在 `kube-system/gpuctl-config` ConfigMap 中。

!!! info "幂等且即时生效"
    再次执行 `gpuctl init` 会更新已有 ConfigMap(patch)。新值对**新创建**的任务立即生效 —— 无需重启任何服务。已在运行的任务不受影响。

---

## 第二步:用户自动获得持久化存储

NFS 注册后,平台会向每个任务的容器注入两个挂载路径 —— 无需改动 YAML:

| 路径 | 后端 | 权限 | 范围 |
|------|------|------|------|
| `/home/jovyan` | `nfs:<server>:<path>/home/<namespace>` | **读写** | 按 namespace(按用户)隔离 |
| `/datasets` | `nfs:<server>:<path>/datasets` | **只读** | 全体用户共享 |

实际意义:

- **重启不丢。** 写入 `/home/jovyan` 的内容在任务结束或重建后依然存在。
- **跨任务共享。** 同一 namespace 下的 Training 任务和 Notebook 看到的是完全相同的 `/home/jovyan` —— 无需拷贝或同步。Notebook 准备好代码/数据/conda 环境,Training 任务可直接读取。参见[训练任务 → 复用 conda 环境](training.md#example-2-reuse-a-notebook-environment-conda)。
- **按用户隔离。** `alice` 的 `/home/jovyan` 与 `bob` 的 `/home/jovyan` 是不同目录(`home/alice` vs `home/bob`),互不可见。
- **数据集只读。** `/datasets` 由运维管理内容,在各处以只读方式挂载。

一个自动获得持久化存储的最小任务 —— 注意它**完全没有** `storage` 段:

```yaml title="notebook.yaml"
kind: notebook
version: v0.1

job:
  name: alice-dev

environment:
  image: jupyter/scipy-notebook:latest

service:
  port: 8888

resources:
  pool: dev-pool
  gpu: 1
  cpu: 8
  memory: 32Gi
```

```bash
# 提交到该用户的 namespace
gpuctl create -f notebook.yaml -n alice
```

该 Notebook 写到 `/home/jovyan` 下的文件会持久保存,并对 `alice` 提交的其他任何任务可见。

---

## 配额分配时自动建立用户家目录

运维为新用户分配配额时,该用户的存储目录会同步建立 —— 无需单独操作。

```bash
gpuctl apply -f quota.yaml
```

当 `apply` 创建新 namespace 时,gpuctl 会在 `kube-system` 中起一个临时 `busybox` Job,在 NFS 共享上 `mkdir -p` 出该用户的 `home/<namespace>` 目录。等用户提交第一个任务时,`/home/jovyan` 已就绪且可写。

- **幂等。** 对已存在用户重复 apply 配额不会动到已有文件。
- **对称清理。** 删除 namespace(`gpuctl delete ns <name>`)时会起一个对应的 `busybox` Job 删除该用户家目录,不留孤儿数据。
- **无 NFS 时为空操作。** 若未注册 NFS,配额创建会跳过建目录步骤,行为与之前完全一致。

!!! warning "删除 namespace 会删除该用户的文件"
    因为清理会对 `home/<namespace>` 执行 `rm -rf`,删除 namespace 会永久移除该用户的持久数据。如需保留请先备份。

---

## 向后兼容

透明存储是纯增量特性,绝不破坏现有任务:

- **未注册 NFS:** 各类任务照常提交运行;不挂载 NFS 卷;不报错。
- **旧 YAML 无 `storage` 段:** 行为不变,且在已注册 NFS 时自动叠加 NFS 挂载。
- **旧 YAML 含 `storage.workdirs`:** `hostPath` workdir 继续挂载;NFS 挂载额外叠加(若已注册)。区别见下一节。

---

## `storage.workdirs` 与透明 NFS 的区别

这是两套**独立**机制。对大多数用户来说,透明 NFS 已经够用,`storage.workdirs` 可以完全省略。

| | 透明 NFS(`/home/jovyan`、`/datasets`) | `storage.workdirs` |
|---|---|---|
| 需要在 YAML 声明吗? | 否 —— 全自动 | 是 —— 需逐条列出路径 |
| 底层卷 | NFS(网络、共享、持久) | `hostPath`(节点本地磁盘) |
| 重新调度到其他节点后还在吗? | 在 | 不在 —— `hostPath` 是节点本地的 |
| 多机分布式共享? | 支持 —— 所有 Worker 看到相同文件 | 不支持 |
| 何时使用 | 持久用户数据和共享数据集的默认选择 | 需要指定节点本地路径的高级场景 |

```yaml
# storage.workdirs 是可选的，仅用于 hostPath 挂载。
# 大多数任务应省略此段，直接依赖透明 NFS。
storage:
  workdirs:
    - path: /scratch/local-cache
```

---

## 参见

- [CLI 参考中的 `gpuctl init`](../cli/index.md#init)
- [训练任务](training.md) —— 使用 `/home/jovyan` 保存 checkpoint,包括所有 Worker 共享同一家目录的多机分布式训练
- [配额与命名空间](quota.md) —— 创建 namespace 时触发家目录建立
