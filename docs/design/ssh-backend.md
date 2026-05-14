# SSH 部署后端设计

> Status: Draft · Target: gpuctl 0.10.x · Owner: TBD

## 1. 目标与非目标

### 目标

为 gpuctl 增加一个 **不依赖 Kubernetes 的 SSH 部署后端**，让用户能用同一份
声明式 YAML 把作业投递到「一组裸 GPU 机器」上，跑训练、推理、Notebook、通用
容器。在 k8s 真的过重的场景下可替代 k3s/k8s。

### 非目标 (v1)

- **多节点分布式训练**（NCCL bootstrap、master 选举、IB/NVLink 拓扑感知调度）。
  v1 一个作业 = 一个节点。多节点训练建议接 Slurm。
- **零停机蓝绿/金丝雀**。v1 直接 `docker rm -f` 再起，停机几秒。后续可接
  `kamal-proxy` 作流量切换。
- **跨数据中心高可用**。v1 假设 gpuctl 控制节点和被管节点同处一个可达网络。
- **完整的资源 quota / multi-tenancy**。v1 quota 只做软提示，不强制。
- **替换现有 Kubernetes 后端**。两者并存，用户按场景选。

## 2. 为什么不直接用 k3s / kamal / ansible

- **k3s**：轻量 k8s，对很多场景确实够用。SSH 后端的存在意义是 *彻底无 k8s*
  的场景：合规要求不允许跑 k8s、共享主机不允许装 daemon、只有 SSH 一条入口
  的远程算力等。
- **Kamal**：Ruby CLI，不是库；且面向 Web 服务零停机，不直接覆盖训练 job
  生命周期。设计模式可以借鉴，代码不直接复用。
- **Ansible**：声明式不彻底（task-level idempotency 不是 reconciliation
  loop），嵌入 Python 进程要 shell-out 到 `ansible-runner`，重。
- **Pyinfra**：作为 lib 可以用，但抽象层级偏低，仍需自己写 reconciler。
  v1 直接用 paramiko，必要时再考虑迁移。

结论：**自研 SSH 执行层 + 声明 spec + 简易 reconciler**，关键依赖只增加
`paramiko`（可选 extras）。

## 3. 工作负载支持矩阵 (v1)

| Kind        | v1 支持 | 实现方式                          | 备注                                     |
|-------------|---------|-----------------------------------|------------------------------------------|
| training    | ✅      | `docker run --gpus … --rm`        | 单节点一次性容器；ttl 后清理             |
| compute     | ✅      | `docker run -d --gpus … -p …:…`   | 长跑服务；`replicas=1` 强制              |
| inference   | ⚠️      | 同 compute + health check 轮询    | `replicas>1` 在 v1 报错                  |
| notebook    | ⚠️      | 同 compute，固定 port 8888        | 不做持久 PVC，挂宿主目录                 |

## 4. 整体架构

```
            ┌────────────────────────────────────────────────────┐
            │                     CLI / FastAPI                  │
            └──────────────────────┬─────────────────────────────┘
                                   │ parse YAML → API model
                                   ▼
            ┌────────────────────────────────────────────────────┐
            │  Kind handlers  (training_kind / inference_kind …) │
            │      to_job_spec()    →    JobSpec (backend-neutral)│
            └──────────────────────┬─────────────────────────────┘
                                   │
              ┌────────────────────┼─────────────────────┐
              ▼                                          ▼
    ┌──────────────────────┐                  ┌──────────────────────┐
    │  KubernetesBackend   │                  │      SshBackend      │
    │  (wraps existing     │                  │                      │
    │   builders+clients)  │                  │ ┌──────────────────┐ │
    └──────────────────────┘                  │ │ Scheduler        │ │
              │                               │ │  (pool→node)     │ │
              ▼                               │ ├──────────────────┤ │
       Kubernetes API                         │ │ ConnectionPool   │ │
                                              │ │  (paramiko)      │ │
                                              │ ├──────────────────┤ │
                                              │ │ DockerRuntime    │ │
                                              │ │  (cmd builders)  │ │
                                              │ ├──────────────────┤ │
                                              │ │ StateStore       │ │
                                              │ │  (sqlite)        │ │
                                              │ ├──────────────────┤ │
                                              │ │ Inventory        │ │
                                              │ │  (~/.gpuctl/…)   │ │
                                              │ └──────────────────┘ │
                                              └──────────────────────┘
                                                        │
                                                        ▼
                                                 SSH → docker
```

### 4.1 后端接口

```python
class Backend(Protocol):
    name: str

    def create_job(self, spec: JobSpec) -> JobHandle: ...
    def delete_job(self, name: str, namespace: str) -> None: ...
    def get_job(self, name: str, namespace: str) -> JobStatus: ...
    def list_jobs(self, namespace: str, labels: dict[str, str] | None = None) -> list[JobStatus]: ...
    def stream_logs(self, name: str, namespace: str, follow: bool = False) -> Iterator[str]: ...
```

后端通过 `gpuctl.backend.registry.get_backend()` 获取，由环境变量
`GPUCTL_BACKEND={kubernetes,ssh}` 控制（默认 `kubernetes`，保持向后兼容）。

### 4.2 JobSpec (backend-neutral)

```python
@dataclass(frozen=True)
class JobSpec:
    name: str
    namespace: str
    kind: Kind                # training / inference / notebook / compute
    image: str
    command: list[str]
    args: list[str]
    env: list[tuple[str, str]]
    image_pull_secret: str | None
    cpu_millicores: int       # 8 → 8000
    memory_bytes: int         # "32Gi" → 34_359_738_368
    gpu_count: int
    gpu_type: str | None
    pool: str | None
    replicas: int
    port: int | None
    health_check: str | None
    workdirs: list[VolumeMount]
    priority: Priority
    labels: dict[str, str]
    annotations: dict[str, str]
    long_running: bool        # training=False, others=True
    restart_policy: str       # Never / OnFailure / Always
```

每个 kind handler 实现 `to_job_spec(api_model, namespace) -> JobSpec`，
backend 只看 JobSpec。

## 5. SshBackend 内部组件

### 5.1 Inventory (`~/.gpuctl/inventory.yaml`)

```yaml
version: v1
nodes:
  - name: gpu-01
    host: 10.0.0.11
    port: 22
    user: ubuntu
    key_path: ~/.ssh/gpu_cluster
    pool: training-pool
    gpu_count: 8
    gpu_type: a100-80g
    labels:
      runwhere.ai/zone: cn-north-1a
  - name: gpu-02
    host: 10.0.0.12
    ...
```

通过 `gpuctl node add/remove/list` 增删（v1 可手工编辑）。注意：节点的
`gpu_count/gpu_type` 来自 inventory 声明，**不是** SSH 探测到的，避免每次
调度都跑一次 `nvidia-smi`。后台周期性 reconcile 时再更新真实值。

### 5.2 Scheduler

输入：JobSpec。输出：选中节点（或 `NoCapacity`）。

v1 算法：
1. 筛选 pool 匹配（`spec.pool or 'default'`）。
2. 筛选 gpu_type 匹配（若指定）。
3. 计算每个节点的剩余 GPU（`gpu_count - 已分配`，从 StateStore 查）。
4. 选 GPU 剩余最多的节点；GPU=0 的作业按 CPU 剩余最多。
5. 取不到节点 → `NoCapacityError`。

故意不做 bin-packing、亲和性、抢占 —— v2 再说。

### 5.3 ConnectionPool

`paramiko.SSHClient` 池，按 `(user, host, port)` 复用；每节点最多 4 个并发连接。
exec_command 包一层 timeout + stderr 抓取，错误转 `SshExecError`。

### 5.4 DockerRuntime

只生成命令，不直接执行（便于测试）。例：

```python
runtime.run_cmd(spec, container_name) →
  "docker run -d --name gpuctl-foo --restart=unless-stopped "
  "--gpus 'count=2' --cpus=8 --memory=32g "
  "-e PYTHONUNBUFFERED=1 -p 8000:8000 "
  "--label runwhere.ai/job-type=training "
  "--label runwhere.ai/managed-by=gpuctl "
  "-v /data:/data "
  "myimage:tag /bin/bash -c '…'"
```

容器名约定：`gpuctl-{namespace}-{kind}-{name}` (≤63 字符，自动截断 + hash)。
所有 label 加 `runwhere.ai/managed-by=gpuctl` 用于过滤。

GPU 调度：直接传 `--gpus 'count=N'`（NVIDIA Container Toolkit）。
没有 `nvidia-container-cli` 的节点在 inventory 加载时报错。

### 5.5 StateStore (SQLite)

路径：`~/.gpuctl/state.db`（可由 `GPUCTL_STATE_DIR` 覆盖）。

表结构：

```sql
CREATE TABLE jobs (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    namespace     TEXT NOT NULL,
    kind          TEXT NOT NULL,
    node          TEXT NOT NULL,
    container_id  TEXT,
    container_name TEXT NOT NULL,
    spec_json     TEXT NOT NULL,
    status        TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    UNIQUE(name, namespace)
);

CREATE TABLE nodes_runtime (
    name           TEXT PRIMARY KEY,
    last_seen      TEXT NOT NULL,
    gpu_count_real INTEGER,
    docker_version TEXT
);
```

**SQLite 写并发**：开 WAL + `PRAGMA busy_timeout=5000`；单用户 CLI 场景够用。
多个 gpuctl 进程同时改同一作业由 UNIQUE 约束兜底。

### 5.6 状态查询（get_job / list_jobs）

混合策略：

1. 从 StateStore 拉本地认为存在的作业（desired state）。
2. SSH 到该节点跑 `docker inspect <container_id>` 拉真实状态（actual state）。
3. 合并：本地有但远端没有 → `status=Lost`；远端 exit 非 0 → `status=Failed`；
   远端 running → `status=Running`。

为了 `list_jobs` 不太慢，按节点并发 ssh（ThreadPool，默认 8）；
单个节点的 inspect 合并成一次调用（`docker inspect c1 c2 c3 …`）。

### 5.7 日志（stream_logs）

`docker logs --tail=N [-f] <container>` 通过 paramiko 的 `exec_command`，
把 stdout 行式 yield 出去。`-f` 时 channel.recv loop，gpuctl 进程退出会关连接。

## 6. 与现有代码的衔接

### 6.1 现有 k8s 路径完全保留

CLI 默认走 `kubernetes` 后端，行为 0 变化。Server 路由同。
`KubernetesBackend` 是个薄壳，内部仍调原来的 `TrainingBuilder` / `JobClient`。
**没有** 把现有 builder/client 大改 —— 那是不必要的破坏性改动。

### 6.2 kind handlers 改造

每个 `*_kind.py` 增加：

```python
def create_xxx_job(self, model, namespace):
    backend = get_backend()
    if backend.name == "kubernetes":
        return self._create_k8s(model, namespace)   # 原有路径
    spec = self.to_job_spec(model, namespace)
    handle = backend.create_job(spec)
    return self._format_result(handle, model)
```

V1 只改 `training_kind.py` 作 PoC，其他三个 kind 后续 PR 补。

### 6.3 CLI pre-flight 检查

`cli/job.py` 里的 namespace/quota/pool 检查目前直接 hit k8s。
SSH 后端下：

- **namespace 检查**：SSH 后端把 namespace 当 label，**始终通过**。
- **quota 检查**：v1 跳过（quota 是 k8s 概念）。
- **pool 检查**：查 inventory，确认 pool 至少有一个节点。

实现：把这三段检查包成 `precheck.check(parsed_obj, namespace, backend)`，
backend 决定如何检查。

### 6.4 配置

| 变量                  | 作用                                    | 默认                  |
|-----------------------|-----------------------------------------|-----------------------|
| `GPUCTL_BACKEND`      | `kubernetes` / `ssh`                    | `kubernetes`          |
| `GPUCTL_STATE_DIR`    | SQLite + inventory 目录                 | `~/.gpuctl`           |
| `GPUCTL_SSH_TIMEOUT`  | 单次 SSH exec 默认超时秒                | `30`                  |
| `GPUCTL_SSH_PARALLEL` | list/get 时并发 SSH 节点数              | `8`                   |

## 7. 依赖

`pyproject.toml` 新增可选 extras：

```toml
[project.optional-dependencies]
ssh = ["paramiko>=3.0,<4.0"]
```

安装：`pip install gpuctl[ssh]`。不装也不影响 k8s 路径。

`paramiko` 选型理由：纯 Python 实现、生态最广、不引入 async 依赖。
`asyncssh` 更现代但需要事件循环；当前 CLI 是同步的，先不引入。

## 8. 测试策略

- **单元测试**：
  - `DockerRuntime.run_cmd()` 输入 JobSpec → 输出 shell 字符串，纯字符串断言。
  - `Scheduler.select()` 对静态 inventory + 静态状态，选节点结果可断言。
  - `StateStore` 用 `:memory:` SQLite，CRUD/并发写测试。
- **集成测试**（标 `@pytest.mark.ssh_integration`，默认 skip）：
  - 用 `docker run -d --name fake-ssh -p 2222 lscr.io/linuxserver/openssh-server`
    起一个本地 sshd 容器，配置 inventory 指向 `127.0.0.1:2222`，跑完整路径。
  - CI 不跑，只在本地或专属 runner 跑。
- **mock SSH**：连接层抽象成 `Transport` 接口，单测注入 `FakeTransport`
  返回预设输出，不真的发包。

## 9. 安全

- SSH 私钥只读取，不写；不接收用户传入的密码（强制 key auth）。
- 远端命令构造严格用列表 + `shlex.quote`，**不拼字符串**，避免命令注入。
  尤其是 image 名、env value、workdir path 这种用户控制的字段。
- 容器以 inventory 指定 `user` 身份执行；如需 root container，需 inventory
  显式标 `allow_privileged: true`，否则 backend 拒绝带 `--privileged` 的 spec。
- StateStore 文件权限设 0600；inventory 文件 0644 但敏感字段（如 key_path）
  只存路径不存密钥。

## 10. Roadmap

| 阶段 | 范围                                                                                          |
|------|-----------------------------------------------------------------------------------------------|
| v0.10 (本 PR) | Backend 抽象 + JobSpec + KubernetesBackend 包装 + SshBackend(training) + 单测           |
| v0.11        | SshBackend 支持 compute / inference(replicas=1) / notebook；CLI pre-check 重构              |
| v0.12        | 节点状态后台 reconcile loop（systemd timer 或 gpuctl daemon）；log streaming 完整             |
| v0.13        | inference 多副本（同节点端口范围 / 多节点轮询） + kamal-proxy 集成做零停机切换                 |
| v1.0         | 节点拓扑感知调度、抢占、quota 强约束、Web UI 显示 SSH 后端节点                                |

多节点训练（NCCL/torchrun）单开议题，初步思路是接 Slurm；不在 SSH 后端内卷。
