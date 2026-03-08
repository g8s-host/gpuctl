# gpuctl CLI 命令使用手册

## 1. 简介

gpuctl 是一个 AI 算力调度平台的命令行工具，用于管理 GPU 资源、作业和命名空间等。本手册详细介绍了所有 gpuctl CLI 命令的用法、选项和示例。

## 2. 命令概述

gpuctl 支持以下命令：

| 命令 | 描述 |
|------|------|
| `create` | 从 YAML 创建作业 |
| `get` | 获取资源信息 |
| `apply` | 应用资源配置（创建或更新） |
| `delete` | 删除资源 |
| `logs` | 获取作业日志 |
| `label` | 管理节点标签 |
| `describe` | 查看资源详情 |

## 3. 命令详细说明

### 3.1 `create` 命令

从 YAML 文件创建作业。

#### 语法
```bash
gpuctl create -f <file> [-n <namespace>] [--json]
```

#### 选项
| 选项 | 描述 | 必需 |
|------|------|------|
| `-f, --file` | YAML 文件路径（可多次指定） | 是 |
| `-n, --namespace` | Kubernetes 命名空间（默认值：default） | 否 |
| `--json` | 以 JSON 格式输出结果 | 否 |

#### 示例

1. 从单个 YAML 文件创建作业：
   ```bash
   gpuctl create -f tests/yamls/compute/test-nginx.yaml
   ```

2. 从多个 YAML 文件创建作业：
   ```bash
   gpuctl create -f job1.yaml -f job2.yaml
   ```

3. 指定命名空间创建作业：
   ```bash
   gpuctl create -f job.yaml -n test-namespace
   ```

4. 以 JSON 格式输出结果：
   ```bash
   gpuctl create -f job.yaml --json
   ```

#### 输出示例

```
Job created successfully: test-nginx
Namespace: default
Job ID: test-nginx-default
```

### 3.2 `get` 命令

获取各种资源的信息。

#### 语法
```bash
gpuctl get <resource> [options]
```

#### 资源类型
| 资源类型 | 描述 |
|----------|------|
| `jobs` | 获取作业列表 |
| `pools` | 获取资源池列表 |
| `nodes` | 获取节点列表 |
| `labels` | 获取节点标签 |
| `quotas` | 获取配额列表 |
| `ns`/`namespaces` | 获取命名空间列表 |

#### 作业相关选项（`get jobs`）
| 选项 | 描述 | 必需 |
|------|------|------|
| `-n, --namespace` | 命名空间（可选，不指定则显示所有命名空间的作业） | 否 |
| `--pool` | 按资源池过滤 | 否 |
| `--kind` | 按作业类型过滤（可选值：training, inference, notebook, compute） | 否 |
| `--pods` | 显示 pod 级别的信息，而非 deployment/statefulset 级别 | 否 |
| `--json` | 以 JSON 格式输出结果 | 否 |

#### 资源池相关选项（`get pools`）
| 选项 | 描述 | 必需 |
|------|------|------|
| `--json` | 以 JSON 格式输出结果 | 否 |

#### 节点相关选项（`get nodes`）
| 选项 | 描述 | 必需 |
|------|------|------|
| `--pool` | 按资源池过滤 | 否 |
| `--gpu-type` | 按 GPU 类型过滤 | 否 |
| `--json` | 以 JSON 格式输出结果 | 否 |

#### 标签相关选项（`get labels`）
| 选项 | 描述 | 必需 |
|------|------|------|
| `node_name` | 节点名称 | 是 |
| `--key` | 标签键（可选，用于过滤） | 否 |
| `--json` | 以 JSON 格式输出结果 | 否 |

#### 配额相关选项（`get quotas`）
| 选项 | 描述 | 必需 |
|------|------|------|
| `namespace` | 命名空间名称（可选，用于过滤） | 否 |
| `--json` | 以 JSON 格式输出结果 | 否 |

#### 命名空间相关选项（`get ns`/`get namespaces`）
| 选项 | 描述 | 必需 |
|------|------|------|
| `--json` | 以 JSON 格式输出结果 | 否 |

#### 示例

1. 获取所有作业：
   ```bash
   gpuctl get jobs
   ```

2. 获取指定命名空间的作业：
   ```bash
   gpuctl get jobs -n test-namespace
   ```

3. 按资源池过滤作业：
   ```bash
   gpuctl get jobs --pool test-pool
   ```

4. 按作业类型过滤作业：
   ```bash
   gpuctl get jobs --kind compute
   ```

5. 显示 pod 级别的作业信息：
   ```bash
   gpuctl get jobs --pods
   ```

6. 获取资源池列表：
   ```bash
   gpuctl get pools
   ```

7. 获取节点列表：
   ```bash
   gpuctl get nodes
   ```

8. 按 GPU 类型过滤节点：
   ```bash
   gpuctl get nodes --gpu-type nvidia-tesla-t4
   ```

9. 获取节点标签：
   ```bash
   gpuctl get labels node-1
   ```

10. 获取指定标签键的节点标签：
    ```bash
    gpuctl get labels node-1 --key=g8s.host/gpu-type
    ```

11. 获取配额列表：
    ```bash
    gpuctl get quotas
    ```

12. 获取指定命名空间的配额：
    ```bash
    gpuctl get quotas test-namespace
    ```

13. 获取命名空间列表：
    ```bash
    gpuctl get ns
    ```
    或
    ```bash
    gpuctl get namespaces
    ```

#### 输出示例

```
NAME           NAMESPACE  KIND     POOL        STATUS    AGE
test-nginx     default    compute  test-pool   Running   1h
redis-test     test-ns    compute  default     Running   30m
```

### 3.3 `apply` 命令

应用资源配置（创建或更新）。

#### 语法
```bash
gpuctl apply -f <file> [-n <namespace>] [--json]
```

#### 选项
| 选项 | 描述 | 必需 |
|------|------|------|
| `-f, --file` | YAML 文件路径（可多次指定） | 是 |
| `-n, --namespace` | Kubernetes 命名空间（默认值：default） | 否 |
| `--json` | 以 JSON 格式输出结果 | 否 |

#### 示例

1. 应用单个 YAML 文件：
   ```bash
   gpuctl apply -f job.yaml
   ```

2. 应用多个 YAML 文件：
   ```bash
   gpuctl apply -f job1.yaml -f job2.yaml
   ```

3. 指定命名空间应用配置：
   ```bash
   gpuctl apply -f job.yaml -n test-namespace
   ```

#### 输出示例

```
Job applied successfully: test-nginx
Namespace: default
```

### 3.4 `delete` 命令

删除资源。

#### 语法
```bash
gpuctl delete [resource] [resource-name] [-f <file>] [-n <namespace>] [--force] [--json]
```

#### 资源类型
| 资源类型 | 描述 |
|----------|------|
| `job` | 删除作业 |
| `quota` | 删除配额 |
| `ns`/`namespace` | 删除命名空间 |

#### 选项
| 选项 | 描述 | 必需 |
|------|------|------|
| `-f, --file` | YAML 文件路径（替代指定资源类型） | 否 |
| `-n, --namespace` | Kubernetes 命名空间（默认值：default） | 否 |
| `--force` | 强制删除资源 | 否 |
| `--json` | 以 JSON 格式输出结果 | 否 |

#### 示例

1. 通过 YAML 文件删除资源：
   ```bash
   gpuctl delete -f job.yaml
   ```

2. 删除指定作业：
   ```bash
   gpuctl delete job test-nginx
   ```

3. 删除指定命名空间的作业：
   ```bash
   gpuctl delete job test-nginx -n test-namespace
   ```

4. 强制删除作业：
   ```bash
   gpuctl delete job test-nginx --force
   ```

5. 删除指定命名空间的配额：
   ```bash
   gpuctl delete quota test-namespace
   ```

6. 删除命名空间：
   ```bash
   gpuctl delete ns test-namespace
   ```
   或
   ```bash
   gpuctl delete namespace test-namespace
   ```

7. 强制删除命名空间：
   ```bash
   gpuctl delete ns test-namespace --force
   ```

#### 输出示例

```
Job deleted successfully: test-nginx
Namespace: default
```

### 3.5 `logs` 命令

获取作业日志。

#### 语法
```bash
gpuctl logs <job_name> [-n <namespace>] [-f] [--json]
```

#### 选项
| 选项 | 描述 | 必需 |
|------|------|------|
| `<job_name>` | 作业名称 | 是 |
| `-n, --namespace` | Kubernetes 命名空间（默认值：default） | 否 |
| `-f, --follow` | 跟踪日志输出 | 否 |
| `--json` | 以 JSON 格式输出结果 | 否 |

#### 示例

1. 获取作业日志：
   ```bash
   gpuctl logs test-nginx
   ```

2. 获取指定命名空间的作业日志：
   ```bash
   gpuctl logs test-nginx -n test-namespace
   ```

3. 跟踪作业日志：
   ```bash
   gpuctl logs test-nginx -f
   ```

#### 输出示例

```
[2024-01-08 10:00:00] INFO: Nginx starting...
[2024-01-08 10:00:01] INFO: Listening on port 80
[2024-01-08 10:00:02] INFO: Server ready
```

### 3.6 `label` 命令

管理节点标签。

#### 语法
```bash
gpuctl label node <label> <node_name> [node_name...] [--delete] [--overwrite] [--json]
```

#### 选项
| 选项 | 描述 | 必需 |
|------|------|------|
| `<label>` | 标签键值对（如 `key=value`）或要删除的标签键 | 是 |
| `<node_name>` | 节点名称（可指定多个） | 是 |
| `--delete` | 删除标签 | 否 |
| `--overwrite` | 覆盖现有标签 | 否 |
| `--json` | 以 JSON 格式输出结果 | 否 |

#### 示例

1. 为单个节点添加标签：
   ```bash
   gpuctl label node g8s.host/gpu-type=a100-80g node-1
   ```

2. 为多个节点添加标签：
   ```bash
   gpuctl label node pool=test-pool node-1 node-2 node-3
   ```

3. 覆盖现有标签：
   ```bash
   gpuctl label node pool=new-pool node-1 --overwrite
   ```

4. 删除节点标签：
   ```bash
   gpuctl label node pool node-1 --delete
   ```

#### 输出示例

```
Label updated successfully for node: node-1
Label: g8s.host/gpu-type=a100-80g
```

### 3.7 `describe` 命令

查看资源详情。

#### 语法
```bash
gpuctl describe <resource> <resource_name> [-n <namespace>] [--json]
```

#### 资源类型
| 资源类型 | 描述 |
|----------|------|
| `job` | 查看作业详情 |
| `pool` | 查看资源池详情 |
| `node` | 查看节点详情 |
| `quota` | 查看配额详情 |
| `ns`/`namespace` | 查看命名空间详情 |

#### 选项
| 选项 | 描述 | 必需 |
|------|------|------|
| `<resource_name>` | 资源名称 | 是 |
| `-n, --namespace` | Kubernetes 命名空间（默认值：default） | 否 |
| `--json` | 以 JSON 格式输出结果 | 否 |

#### 示例

1. 查看作业详情：
   ```bash
   gpuctl describe job test-nginx
   ```

2. 查看指定命名空间的作业详情：
   ```bash
   gpuctl describe job test-nginx -n test-namespace
   ```

3. 查看资源池详情：
   ```bash
   gpuctl describe pool test-pool
   ```

4. 查看节点详情：
   ```bash
   gpuctl describe node node-1
   ```

5. 查看配额详情：
   ```bash
   gpuctl describe quota test-namespace
   ```

6. 查看命名空间详情：
   ```bash
   gpuctl describe ns test-namespace
   ```
   或
   ```bash
   gpuctl describe namespace test-namespace
   ```

#### 输出示例

```
Job Details:
Name: test-nginx
Namespace: default
Kind: compute
Pool: test-pool
Status: Running
Created: 2024-01-08 10:00:00
Age: 1h

Resources:
- CPU: 1
- Memory: 2Gi
- GPU: 0

Service:
Type: NodePort
Port: 80
TargetPort: 80
Protocol: TCP

Environment:
Image: nginx:latest
Command: ["nginx", "-g", "daemon off;"]

Storage:
- Name: data
  MountPath: /usr/share/nginx/html
  Size: 1Gi
```

## 4. 输出格式

所有命令都支持 `--json` 选项，以 JSON 格式输出结果。以下是 JSON 输出的示例：

```json
{
  "apiVersion": "v1",
  "items": [
    {
      "metadata": {
        "name": "test-nginx",
        "namespace": "default"
      },
      "status": "Running",
      "kind": "compute",
      "pool": "test-pool",
      "age": "1h"
    }
  ],
  "kind": "List"
}
```

## 5. 常见问题

### 5.1 如何获取帮助？

使用 `gpuctl --help` 获取所有命令的帮助信息，或使用 `gpuctl <command> --help` 获取特定命令的帮助信息。

### 5.2 如何指定命名空间？

大多数命令支持 `-n, --namespace` 选项来指定命名空间。如果不指定，默认使用 `default` 命名空间。

### 5.3 如何强制删除资源？

使用 `--force` 选项可以强制删除资源，例如：`gpuctl delete job test-nginx --force`。

### 5.4 如何查看实时日志？

使用 `logs` 命令的 `-f, --follow` 选项可以查看实时日志，例如：`gpuctl logs test-nginx -f`。

## 6. 示例工作流

### 6.1 基本作业生命周期管理

1. 创建作业：
   ```bash
   gpuctl create -f job.yaml
   ```

2. 查看作业列表：
   ```bash
   gpuctl get jobs
   ```

3. 查看作业详情：
   ```bash
   gpuctl describe job job-name
   ```

4. 查看作业日志：
   ```bash
   gpuctl logs job-name
   ```

5. 更新作业：
   ```bash
   gpuctl apply -f updated-job.yaml
   ```

6. 删除作业：
   ```bash
   gpuctl delete job job-name
   ```

### 6.2 资源池与节点管理

1. 查看资源池列表：
   ```bash
   gpuctl get pools
   ```

2. 查看节点列表：
   ```bash
   gpuctl get nodes
   ```

3. 为节点添加标签：
   ```bash
   gpuctl label node pool=test-pool node-1
   ```

4. 查看节点详情：
   ```bash
   gpuctl describe node node-1
   ```

### 6.3 命名空间与配额管理

1. 查看命名空间列表：
   ```bash
   gpuctl get ns
   ```

2. 查看配额列表：
   ```bash
   gpuctl get quotas
   ```

3. 查看指定命名空间的配额：
   ```bash
   gpuctl get quotas test-namespace
   ```

4. 查看命名空间详情：
   ```bash
   gpuctl describe ns test-namespace
   ```

5. 删除命名空间：
   ```bash
   gpuctl delete ns test-namespace
   ```

## 7. 注意事项

1. 确保您有足够的权限访问 Kubernetes 集群。
2. 使用 `--json` 选项可以方便地将输出用于脚本或其他工具。
3. 对于长时间运行的作业，使用 `logs -f` 选项可以实时监控日志。
4. 删除资源前请仔细确认，某些删除操作是不可逆的。
5. 使用 `apply` 命令可以安全地更新资源，而不必先删除再创建。

## 8. 版本历史

本手册基于 gpuctl 最新版本编写。如果您使用的是旧版本，某些命令或选项可能有所不同。请使用 `gpuctl --version` 查看您的 gpuctl 版本，并参考相应版本的文档。

## 9. 反馈与贡献

如果您发现本手册有任何错误或遗漏，或有任何改进建议，欢迎通过 GitHub Issues 或 Pull Requests 提出。

---

**gpuctl CLI 命令使用手册 - 版本 1.0**
**最后更新：2024-01-08**