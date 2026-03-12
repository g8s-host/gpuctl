# gpuctl 场景测试用例

## 1. 测试概述

本文件包含了 gpuctl CLI 命令的场景测试用例，用于验证多个命令组合使用的完整流程。场景测试模拟了用户的实际使用场景，覆盖了 gpuctl 的主要功能和工作流程。

## 2. 测试环境

- **操作系统**：Linux Ubuntu 20.04
- **Python 版本**：3.8+
- **Kubernetes 版本**：1.24+
- **gpuctl 版本**：最新版本

## 3. 场景测试用例

### 3.1 场景 1：基本作业生命周期管理

#### 场景名称
基本作业生命周期管理

#### 场景目的
验证从创建命名空间、资源池、配额，到创建、查看、更新、删除作业的完整流程。

#### 前置条件
- Kubernetes 集群可访问
- gpuctl 已正确安装
- 测试环境干净，没有残留的测试资源

#### 测试步骤

1. **创建测试命名空间**：
   - 执行命令：`kubectl create namespace test-lifecycle`
   **预期结果**：命名空间创建成功

2. **创建资源池配置文件** `test-pool.yaml`：
   ```yaml
   kind: pool
   version: v1
   metadata:
     name: test-lifecycle-pool
   spec:
     description: "Test pool for lifecycle management"
   ```

3. **创建资源池**：
   - 执行命令：`gpuctl apply -f test-pool.yaml`
   **预期结果**：资源池创建成功

4. **创建配额配置文件** `test-quota.yaml`：
   ```yaml
   kind: quota
   version: v1
   metadata:
     name: test-lifecycle
     namespace: test-lifecycle
   spec:
     cpu: 10
     memory: 20Gi
     gpu: 2
   ```

5. **创建配额**：
   - 执行命令：`gpuctl create -f test-quota.yaml`
   **预期结果**：配额创建成功

6. **创建作业配置文件** `test-job.yaml`：
   ```yaml
   kind: compute
   version: v1
   job:
     name: test-lifecycle-job
     namespace: test-lifecycle
     description: "Test job for lifecycle management"

   environment:
     image: nginx:latest
     command: ["nginx", "-g", "daemon off;"]

   service:
     replicas: 1
     port: 80
     targetPort: 80
     protocol: TCP
     type: NodePort

   resources:
     pool: test-lifecycle-pool
     gpu: 0
     cpu: 1
     memory: 1Gi
   ```

7. **创建作业**：
   - 执行命令：`gpuctl create -f test-job.yaml`
   **预期结果**：作业创建成功

8. **查看作业列表**：
   - 执行命令：`gpuctl get jobs -n test-lifecycle`
   **预期结果**：能看到刚创建的作业，状态为 Running

9. **查看作业详情**：
   - 执行命令：`gpuctl describe job test-lifecycle-job -n test-lifecycle`
   **预期结果**：能看到作业的详细信息，包括资源配置、服务配置等

10. **查看作业日志**：
    - 执行命令：`gpuctl logs test-lifecycle-job -n test-lifecycle`
    **预期结果**：能看到作业的日志信息

11. **更新作业配置**：
    - 修改 `test-job.yaml`，将 replicas 改为 2
    - 执行命令：`gpuctl apply -f test-job.yaml`
    **预期结果**：作业更新成功

12. **验证作业更新**：
    - 执行命令：`gpuctl get jobs --pods -n test-lifecycle`
    **预期结果**：能看到作业有 2 个 pod 运行

13. **删除作业**：
    - 执行命令：`gpuctl delete job test-lifecycle-job -n test-lifecycle`
    **预期结果**：作业删除成功

14. **删除配额**：
    - 执行命令：`gpuctl delete quota test-lifecycle`
    **预期结果**：配额删除成功

15. **删除资源池**：
    - 执行命令：`gpuctl delete -f test-pool.yaml`
    **预期结果**：资源池删除成功

16. **删除命名空间**：
    - 执行命令：`kubectl delete namespace test-lifecycle`
    **预期结果**：命名空间删除成功

#### 验证方法
- 每个步骤执行后，检查命令输出是否符合预期
- 使用 `kubectl` 命令验证资源的实际状态
- 检查资源创建、更新和删除的正确性

#### 清理步骤
- 删除测试创建的所有资源
- 确保测试环境恢复到初始状态

### 3.2 场景 2：多类型作业管理

#### 场景名称
多类型作业管理

#### 场景目的
验证在不同命名空间创建不同类型的作业，然后查看和管理这些作业。

#### 前置条件
- Kubernetes 集群可访问
- gpuctl 已正确安装
- 测试环境干净，没有残留的测试资源

#### 测试步骤

1. **创建两个测试命名空间**：
   - 执行命令：`kubectl create namespace test-multi-1`
   - 执行命令：`kubectl create namespace test-multi-2`
   **预期结果**：两个命名空间创建成功

2. **创建 compute 类型作业配置文件** `test-compute.yaml`：
   ```yaml
   kind: compute
   version: v1
   job:
     name: test-compute-job
     namespace: test-multi-1
     description: "Test compute job"

   environment:
     image: nginx:latest
     command: ["nginx", "-g", "daemon off;"]

   service:
     replicas: 1
     port: 80
     targetPort: 80
     protocol: TCP
     type: NodePort

   resources:
     pool: default
     gpu: 0
     cpu: 1
     memory: 1Gi
   ```

3. **创建 training 类型作业配置文件** `test-training.yaml`：
   ```yaml
   kind: training
   version: v1
   job:
     name: test-training-job
     namespace: test-multi-2
     description: "Test training job"

   environment:
     image: pytorch/pytorch:latest
     command: ["python", "-c", "print('Training job completed')"]

   resources:
     pool: default
     gpu: 1
     cpu: 2
     memory: 4Gi
   ```

4. **创建 inference 类型作业配置文件** `test-inference.yaml`：
   ```yaml
   kind: inference
   version: v1
   job:
     name: test-inference-job
     namespace: test-multi-1
     description: "Test inference job"

   environment:
     image: vllm/vllm-serving:latest
     command: ["python", "-m", "vllm.entrypoints.api_server", "--model", "facebook/opt-125m", "--port", "8000"]

   service:
     replicas: 1
     port: 8000
     targetPort: 8000
     protocol: TCP
     type: NodePort

   resources:
     pool: default
     gpu: 1
     cpu: 2
     memory: 8Gi
   ```

5. **创建 compute 类型作业**：
   - 执行命令：`gpuctl create -f test-compute.yaml`
   **预期结果**：compute 作业创建成功

6. **创建 training 类型作业**：
   - 执行命令：`gpuctl create -f test-training.yaml`
   **预期结果**：training 作业创建成功

7. **创建 inference 类型作业**：
   - 执行命令：`gpuctl create -f test-inference.yaml`
   **预期结果**：inference 作业创建成功

8. **查看所有作业**：
   - 执行命令：`gpuctl get jobs`
   **预期结果**：能看到所有三个作业

9. **按命名空间过滤查看作业**：
   - 执行命令：`gpuctl get jobs -n test-multi-1`
   **预期结果**：能看到 test-multi-1 命名空间中的两个作业

10. **按作业类型过滤查看作业**：
    - 执行命令：`gpuctl get jobs --kind training`
    **预期结果**：能看到 training 类型的作业

11. **按命名空间和类型组合过滤查看作业**：
    - 执行命令：`gpuctl get jobs -n test-multi-1 --kind inference`
    **预期结果**：能看到 test-multi-1 命名空间中的 inference 类型作业

12. **删除所有作业**：
    - 执行命令：`gpuctl delete job test-compute-job -n test-multi-1`
    - 执行命令：`gpuctl delete job test-training-job -n test-multi-2`
    - 执行命令：`gpuctl delete job test-inference-job -n test-multi-1`
    **预期结果**：所有作业删除成功

13. **删除测试命名空间**：
    - 执行命令：`kubectl delete namespace test-multi-1`
    - 执行命令：`kubectl delete namespace test-multi-2`
    **预期结果**：两个命名空间删除成功

#### 验证方法
- 每个步骤执行后，检查命令输出是否符合预期
- 使用 `kubectl` 命令验证资源的实际状态
- 检查资源创建、查询和删除的正确性

#### 清理步骤
- 删除测试创建的所有资源
- 确保测试环境恢复到初始状态

### 3.3 场景 3：资源池与节点管理

#### 场景名称
资源池与节点管理

#### 场景目的
验证创建资源池，管理节点标签，然后查看资源池和节点状态的完整流程。

#### 前置条件
- Kubernetes 集群可访问
- gpuctl 已正确安装
- 集群中有至少一个可用节点
- 测试环境干净，没有残留的测试资源

#### 测试步骤

1. **查看集群节点**：
   - 执行命令：`gpuctl get nodes`
   **预期结果**：能看到集群中的所有节点

2. **选择一个测试节点**：
   - 假设选择节点 `node-1` 进行测试

3. **创建资源池配置文件** `test-node-pool.yaml`：
   ```yaml
   kind: pool
   version: v1
   metadata:
     name: test-node-pool
   spec:
     description: "Test pool for node management"
   ```

4. **创建资源池**：
   - 执行命令：`gpuctl apply -f test-node-pool.yaml`
   **预期结果**：资源池创建成功

5. **为节点添加资源池标签**：
   - 执行命令：`gpuctl label node pool=test-node-pool node-1`
   **预期结果**：节点标签添加成功

6. **查看节点标签**：
   - 执行命令：`gpuctl get labels node-1`
   **预期结果**：能看到刚添加的 `pool=test-node-pool` 标签

7. **查看资源池**：
   - 执行命令：`gpuctl get pools`
   **预期结果**：能看到刚创建的资源池

8. **查看资源池详情**：
   - 执行命令：`gpuctl describe pool test-node-pool`
   **预期结果**：能看到资源池的详细信息，包括绑定的节点

9. **查看节点详情**：
   - 执行命令：`gpuctl describe node node-1`
   **预期结果**：能看到节点的详细信息，包括绑定的资源池

10. **更新节点标签**：
    - 执行命令：`gpuctl label node pool=new-pool node-1 --overwrite`
    **预期结果**：节点标签更新成功

11. **验证标签更新**：
    - 执行命令：`gpuctl get labels node-1 --key=pool`
    **预期结果**：能看到标签已更新为 `pool=new-pool`

12. **删除节点标签**：
    - 执行命令：`gpuctl label node pool node-1 --delete`
    **预期结果**：节点标签删除成功

13. **验证标签删除**：
    - 执行命令：`gpuctl get labels node-1 --key=pool`
    **预期结果**：看不到 `pool` 标签

14. **删除资源池**：
    - 执行命令：`gpuctl delete -f test-node-pool.yaml`
    **预期结果**：资源池删除成功

#### 验证方法
- 每个步骤执行后，检查命令输出是否符合预期
- 使用 `kubectl` 命令验证资源的实际状态
- 检查资源创建、标签管理和删除的正确性

#### 清理步骤
- 删除测试创建的所有资源
- 确保测试环境恢复到初始状态

### 3.4 场景 4：配额与命名空间管理

#### 场景名称
配额与命名空间管理

#### 场景目的
验证创建命名空间和配额，查看配额使用情况，然后删除配额和命名空间的完整流程。

#### 前置条件
- Kubernetes 集群可访问
- gpuctl 已正确安装
- 测试环境干净，没有残留的测试资源

#### 测试步骤

1. **创建测试命名空间**：
   - 执行命令：`kubectl create namespace test-quota-ns`
   **预期结果**：命名空间创建成功

2. **创建配额配置文件** `test-quota-ns.yaml`：
   ```yaml
   kind: quota
   version: v1
   metadata:
     name: test-quota-ns
     namespace: test-quota-ns
   spec:
     cpu: 5
     memory: 10Gi
     gpu: 2
   ```

3. **创建配额**：
   - 执行命令：`gpuctl create -f test-quota-ns.yaml`
   **预期结果**：配额创建成功

4. **查看配额列表**：
   - 执行命令：`gpuctl get quotas`
   **预期结果**：能看到刚创建的配额

5. **查看指定命名空间的配额**：
   - 执行命令：`gpuctl get quotas test-quota-ns`
   **预期结果**：能看到 test-quota-ns 命名空间的配额

6. **查看配额详情**：
   - 执行命令：`gpuctl describe quota test-quota-ns`
   **预期结果**：能看到配额的详细信息，包括已用和总配额

7. **创建作业配置文件** `test-quota-job.yaml`：
   ```yaml
   kind: compute
   version: v1
   job:
     name: test-quota-job
     namespace: test-quota-ns
     description: "Test job for quota management"

   environment:
     image: nginx:latest
     command: ["nginx", "-g", "daemon off;"]

   service:
     replicas: 1
     port: 80
     targetPort: 80
     protocol: TCP
     type: NodePort

   resources:
     pool: default
     gpu: 0
     cpu: 1
     memory: 1Gi
   ```

8. **创建作业**：
   - 执行命令：`gpuctl create -f test-quota-job.yaml`
   **预期结果**：作业创建成功

9. **查看配额使用情况**：
   - 执行命令：`gpuctl describe quota test-quota-ns`
   **预期结果**：能看到配额已被使用，已用 CPU 为 1，已用内存为 1Gi

10. **删除作业**：
    - 执行命令：`gpuctl delete job test-quota-job -n test-quota-ns`
    **预期结果**：作业删除成功

11. **查看配额使用情况**：
    - 执行命令：`gpuctl describe quota test-quota-ns`
    **预期结果**：能看到配额已释放，已用资源为 0

12. **删除配额**：
    - 执行命令：`gpuctl delete quota test-quota-ns`
    **预期结果**：配额删除成功

13. **删除命名空间**：
    - 执行命令：`kubectl delete namespace test-quota-ns`
    **预期结果**：命名空间删除成功

#### 验证方法
- 每个步骤执行后，检查命令输出是否符合预期
- 使用 `kubectl` 命令验证资源的实际状态
- 检查配额创建、使用和删除的正确性

#### 清理步骤
- 删除测试创建的所有资源
- 确保测试环境恢复到初始状态

### 3.5 场景 5：复杂作业场景

#### 场景名称
复杂作业场景

#### 场景目的
验证创建一个需要存储配置的复杂作业，然后查看作业详情和日志的流程。

#### 前置条件
- Kubernetes 集群可访问
- gpuctl 已正确安装
- 集群中已配置存储类（StorageClass）
- 测试环境干净，没有残留的测试资源

#### 测试步骤

1. **创建测试命名空间**：
   - 执行命令：`kubectl create namespace test-complex`
   **预期结果**：命名空间创建成功

2. **创建复杂作业配置文件** `test-complex-job.yaml`：
   ```yaml
   kind: compute
   version: v1
   job:
     name: test-complex-job
     namespace: test-complex
     description: "Test complex job with storage"

   environment:
     image: nginx:latest
     command: ["nginx", "-g", "daemon off;"]
     env:
       - name: NGINX_HOST
         value: "test.example.com"
       - name: NGINX_PORT
         value: "80"

   service:
     replicas: 2
     port: 80
     targetPort: 80
     protocol: TCP
     type: NodePort

   resources:
     pool: default
     gpu: 0
     cpu: 1
     memory: 2Gi

   storage:
     data:
       mountPath: /usr/share/nginx/html
       size: 2Gi
       storageClass: standard
     logs:
       mountPath: /var/log/nginx
       size: 1Gi
       storageClass: standard
   ```

3. **创建复杂作业**：
   - 执行命令：`gpuctl create -f test-complex-job.yaml`
   **预期结果**：作业创建成功

4. **查看作业列表**：
   - 执行命令：`gpuctl get jobs -n test-complex`
   **预期结果**：能看到刚创建的作业，状态为 Running

5. **查看作业详情**：
   - 执行命令：`gpuctl describe job test-complex-job -n test-complex`
   **预期结果**：能看到作业的详细信息，包括环境变量、资源配置、服务配置和存储配置

6. **查看作业 pod**：
   - 执行命令：`kubectl get pods -n test-complex`
   **预期结果**：能看到两个运行中的 pod

7. **查看作业日志**：
   - 执行命令：`gpuctl logs test-complex-job -n test-complex`
   **预期结果**：能看到作业的日志信息

8. **跟踪作业日志**：
   - 执行命令：`gpuctl logs test-complex-job -n test-complex -f`
   - 在另一个终端向作业发送请求：`curl <node-ip>:<node-port>`
   **预期结果**：能看到新产生的日志实时输出
   - 按 Ctrl+C 中断日志跟踪

9. **删除作业**：
   - 执行命令：`gpuctl delete job test-complex-job -n test-complex`
   **预期结果**：作业删除成功

10. **验证作业删除**：
    - 执行命令：`gpuctl get jobs -n test-complex`
    **预期结果**：看不到刚删除的作业

11. **删除命名空间**：
    - 执行命令：`kubectl delete namespace test-complex`
    **预期结果**：命名空间删除成功

#### 验证方法
- 每个步骤执行后，检查命令输出是否符合预期
- 使用 `kubectl` 命令验证资源的实际状态
- 检查作业创建、配置和删除的正确性
- 验证存储配置是否生效

#### 清理步骤
- 删除测试创建的所有资源
- 确保测试环境恢复到初始状态

## 4. 测试执行与结果记录

### 4.1 测试执行流程

1. **测试准备**：
   - 确保测试环境已准备好
   - 确保 gpuctl 已正确安装
   - 确保 Kubernetes 集群可访问

2. **测试执行**：
   - 按照场景测试用例顺序执行每个场景
   - 记录每个场景的执行结果
   - 记录测试过程中遇到的问题

3. **测试结果分析**：
   - 分析测试结果，判断场景测试是否通过
   - 对于失败的场景，分析原因并记录
   - 生成测试报告

### 4.2 测试结果记录模板

| 场景 ID | 场景名称 | 执行结果 | 执行时间 | 备注 |
|---------|----------|----------|----------|------|
| 1 | 基本作业生命周期管理 | PASS | 2024-01-08 10:00:00 | - |
| 2 | 多类型作业管理 | PASS | 2024-01-08 11:00:00 | - |
| 3 | 资源池与节点管理 | FAIL | 2024-01-08 12:00:00 | 节点标签添加失败 |

## 5. 测试报告生成

测试执行完成后，根据测试结果记录生成测试报告，包括以下内容：

- 测试概述
- 测试环境
- 场景测试执行结果统计
- 测试通过情况
- 测试失败情况及原因分析
- 测试建议和改进方向

## 6. 注意事项

1. **测试顺序**：建议按照场景测试用例顺序执行，因为后面的场景可能依赖前面的场景结果
2. **测试环境**：确保测试环境干净，避免之前的测试残留影响当前测试
3. **资源清理**：测试完成后，及时清理测试创建的资源，避免占用集群资源
4. **日志记录**：详细记录测试过程和结果，便于后续分析和问题定位
5. **版本一致性**：确保 gpuctl 版本与测试用例匹配，避免版本差异导致测试失败
6. **权限检查**：确保执行测试的用户有足够的权限访问 Kubernetes 集群和资源

## 7. 测试维护

1. **定期更新**：当 gpuctl 版本更新时，及时更新场景测试用例，确保测试覆盖新功能和变更
2. **场景评审**：定期评审场景测试用例，确保测试覆盖全面，没有冗余和遗漏
3. **结果分析**：定期分析测试结果，识别系统瓶颈和问题，推动系统改进

---

**gpuctl 场景测试用例 - 版本 1.0**
**最后更新：2024-01-08**