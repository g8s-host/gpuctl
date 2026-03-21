# gpuctl 自然语言单元测试用例

## 1. 测试概述

本文件包含了 gpuctl CLI 命令的自然语言单元测试用例，用于验证每个命令的功能、选项和边界条件。测试用例分为以下几类：

- **基本功能测试**：验证命令的基本功能是否正常
- **选项组合测试**：验证不同选项组合的功能是否正常
- **错误处理测试**：验证命令在错误情况下的处理是否正确
- **边界条件测试**：验证命令在边界条件下的表现

## 2. 测试环境

- **操作系统**：Linux Ubuntu 20.04
- **Python 版本**：3.8+
- **Kubernetes 版本**：1.24+
- **gpuctl 版本**：最新版本

## 3. 测试用例

### 3.1 `create` 命令测试

#### 基本功能测试
1. **测试目的**：验证从单个 YAML 文件创建作业的功能
   **测试步骤**：
   - 执行命令：`gpuctl create -f tests/yamls/compute/test-nginx.yaml`
   **预期结果**：
   - 作业创建成功
   - 输出包含作业名称、命名空间和作业 ID
   - 使用 `kubectl get pods` 可以看到创建的 pod

2. **测试目的**：验证从多个 YAML 文件创建作业的功能
   **测试步骤**：
   - 执行命令：`gpuctl create -f tests/yamls/compute/test-nginx.yaml -f tests/yamls/compute/test-redis.yaml`
   **预期结果**：
   - 两个作业都创建成功
   - 输出包含两个作业的名称、命名空间和作业 ID
   - 使用 `kubectl get pods` 可以看到两个作业的 pod

#### 选项组合测试
3. **测试目的**：验证指定命名空间创建作业的功能
   **测试步骤**：
   - 执行命令：`gpuctl create -f tests/yamls/compute/test-nginx.yaml -n test-namespace`
   **预期结果**：
   - 作业在 `test-namespace` 命名空间中创建成功
   - 输出包含作业名称、命名空间（test-namespace）和作业 ID
   - 使用 `kubectl get pods -n test-namespace` 可以看到创建的 pod

4. **测试目的**：验证 JSON 格式输出的功能
   **测试步骤**：
   - 执行命令：`gpuctl create -f tests/yamls/compute/test-nginx.yaml --json`
   **预期结果**：
   - 作业创建成功
   - 输出为 JSON 格式，包含作业的详细信息
   - JSON 格式正确，可以被解析

#### 错误处理测试
5. **测试目的**：验证文件不存在时的错误处理
   **测试步骤**：
   - 执行命令：`gpuctl create -f nonexistent.yaml`
   **预期结果**：
   - 命令失败，返回非零退出码
   - 输出包含错误信息，提示文件不存在

6. **测试目的**：验证 YAML 格式错误时的错误处理
   **测试步骤**：
   - 创建一个格式错误的 YAML 文件 `invalid.yaml`
   - 执行命令：`gpuctl create -f invalid.yaml`
   **预期结果**：
   - 命令失败，返回非零退出码
   - 输出包含错误信息，提示 YAML 格式错误

### 3.2 `get` 命令测试

#### 基本功能测试
7. **测试目的**：验证获取所有作业的功能
   **测试步骤**：
   - 执行命令：`gpuctl get jobs`
   **预期结果**：
   - 命令成功，返回零退出码
   - 输出包含所有作业的列表，包括名称、命名空间、类型、资源池、状态和创建时间
   - 格式清晰，易于阅读

8. **测试目的**：验证获取资源池列表的功能
   **测试步骤**：
   - 执行命令：`gpuctl get pools`
   **预期结果**：
   - 命令成功，返回零退出码
   - 输出包含所有资源池的列表，包括名称、状态和节点数量

9. **测试目的**：验证获取节点列表的功能
   **测试步骤**：
   - 执行命令：`gpuctl get nodes`
   **预期结果**：
   - 命令成功，返回零退出码
   - 输出包含所有节点的列表，包括名称、状态、GPU 类型、GPU 数量和绑定的资源池

10. **测试目的**：验证获取命名空间列表的功能
    **测试步骤**：
    - 执行命令：`gpuctl get ns`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含所有命名空间的列表
    - 使用 `gpuctl get namespaces` 命令应得到相同结果

#### 选项组合测试
11. **测试目的**：验证按命名空间过滤作业的功能
    **测试步骤**：
    - 执行命令：`gpuctl get jobs -n default`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出只包含 `default` 命名空间中的作业

12. **测试目的**：验证按资源池过滤作业的功能
    **测试步骤**：
    - 执行命令：`gpuctl get jobs --pool test-pool`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出只包含 `test-pool` 资源池中的作业

13. **测试目的**：验证按作业类型过滤作业的功能
    **测试步骤**：
    - 执行命令：`gpuctl get jobs --kind compute`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出只包含 `compute` 类型的作业

14. **测试目的**：验证查看 pod 级别作业信息的功能
    **测试步骤**：
    - 执行命令：`gpuctl get jobs --pods`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含 pod 级别的作业信息，而非 deployment/statefulset 级别

15. **测试目的**：验证获取节点标签的功能
    **测试步骤**：
    - 执行命令：`gpuctl get labels node-1`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含节点 `node-1` 的所有标签

16. **测试目的**：验证按标签键过滤节点标签的功能
    **测试步骤**：
    - 执行命令：`gpuctl get labels node-1 --key=runwhere.ai/gpu-type`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出只包含键为 `runwhere.ai/gpu-type` 的标签

17. **测试目的**：验证获取指定命名空间配额的功能
    **测试步骤**：
    - 执行命令：`gpuctl get quotas default`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出只包含 `default` 命名空间的配额

#### 错误处理测试
18. **测试目的**：验证获取不存在节点的标签时的错误处理
    **测试步骤**：
    - 执行命令：`gpuctl get labels nonexistent-node`
    **预期结果**：
    - 命令失败，返回非零退出码
    - 输出包含错误信息，提示节点不存在

### 3.3 `apply` 命令测试

#### 基本功能测试
19. **测试目的**：验证应用单个 YAML 文件创建作业的功能
    **测试步骤**：
    - 执行命令：`gpuctl apply -f tests/yamls/compute/test-nginx.yaml`
    **预期结果**：
    - 作业创建成功
    - 输出包含作业名称和命名空间
    - 使用 `kubectl get pods` 可以看到创建的 pod

20. **测试目的**：验证应用 YAML 文件更新作业的功能
    **测试步骤**：
    - 先使用 `gpuctl create -f tests/yamls/compute/test-nginx.yaml` 创建作业
    - 修改 YAML 文件，例如增加 replicas 数量
    - 执行命令：`gpuctl apply -f modified-test-nginx.yaml`
    **预期结果**：
    - 作业更新成功
    - 输出包含作业名称和命名空间
    - 使用 `kubectl get pods` 可以看到 pod 数量增加

#### 选项组合测试
21. **测试目的**：验证指定命名空间应用配置的功能
    **测试步骤**：
    - 执行命令：`gpuctl apply -f tests/yamls/compute/test-nginx.yaml -n test-namespace`
    **预期结果**：
    - 作业在 `test-namespace` 命名空间中创建成功
    - 输出包含作业名称和命名空间（test-namespace）
    - 使用 `kubectl get pods -n test-namespace` 可以看到创建的 pod

22. **测试目的**：验证 JSON 格式输出的功能
    **测试步骤**：
    - 执行命令：`gpuctl apply -f tests/yamls/compute/test-nginx.yaml --json`
    **预期结果**：
    - 作业创建成功
    - 输出为 JSON 格式，包含作业的详细信息
    - JSON 格式正确，可以被解析

### 3.4 `delete` 命令测试

#### 基本功能测试
23. **测试目的**：验证通过 YAML 文件删除资源的功能
    **测试步骤**：
    - 先使用 `gpuctl create -f tests/yamls/compute/test-nginx.yaml` 创建作业
    - 执行命令：`gpuctl delete -f tests/yamls/compute/test-nginx.yaml`
    **预期结果**：
    - 作业删除成功
    - 输出包含作业名称和命名空间
    - 使用 `kubectl get pods` 看不到该作业的 pod

24. **测试目的**：验证通过作业名称删除作业的功能
    **测试步骤**：
    - 先使用 `gpuctl create -f tests/yamls/compute/test-nginx.yaml` 创建作业
    - 执行命令：`gpuctl delete job test-nginx`
    **预期结果**：
    - 作业删除成功
    - 输出包含作业名称和命名空间
    - 使用 `kubectl get pods` 看不到该作业的 pod

#### 选项组合测试
25. **测试目的**：验证删除指定命名空间作业的功能
    **测试步骤**：
    - 先使用 `gpuctl create -f tests/yamls/compute/test-nginx.yaml -n test-namespace` 创建作业
    - 执行命令：`gpuctl delete job test-nginx -n test-namespace`
    **预期结果**：
    - 作业删除成功
    - 输出包含作业名称和命名空间（test-namespace）
    - 使用 `kubectl get pods -n test-namespace` 看不到该作业的 pod

26. **测试目的**：验证强制删除作业的功能
    **测试步骤**：
    - 先使用 `gpuctl create -f tests/yamls/compute/test-nginx.yaml` 创建作业
    - 执行命令：`gpuctl delete job test-nginx --force`
    **预期结果**：
    - 作业强制删除成功
    - 输出包含作业名称和命名空间
    - 使用 `kubectl get pods` 看不到该作业的 pod

27. **测试目的**：验证删除命名空间的功能
    **测试步骤**：
    - 先创建一个测试命名空间
    - 执行命令：`gpuctl delete ns test-namespace`
    **预期结果**：
    - 命名空间删除成功
    - 输出包含命名空间名称
    - 使用 `kubectl get ns` 看不到该命名空间

    或使用完整命令：
    - 执行命令：`gpuctl delete namespace test-namespace`
    **预期结果**：
    - 命名空间删除成功
    - 输出包含命名空间名称
    - 使用 `kubectl get ns` 看不到该命名空间

28. **测试目的**：验证强制删除命名空间的功能
    **测试步骤**：
    - 先创建一个测试命名空间
    - 在该命名空间中创建一些资源
    - 执行命令：`gpuctl delete ns test-namespace --force`
    **预期结果**：
    - 命名空间强制删除成功
    - 输出包含命名空间名称
    - 使用 `kubectl get ns` 看不到该命名空间

#### 错误处理测试
29. **测试目的**：验证删除不存在作业时的错误处理
    **测试步骤**：
    - 执行命令：`gpuctl delete job nonexistent-job`
    **预期结果**：
    - 命令失败，返回非零退出码
    - 输出包含错误信息，提示作业不存在

30. **测试目的**：验证删除不存在命名空间时的错误处理
    **测试步骤**：
    - 执行命令：`gpuctl delete ns nonexistent-namespace`
    **预期结果**：
    - 命令失败，返回非零退出码
    - 输出包含错误信息，提示命名空间不存在

### 3.5 `logs` 命令测试

#### 基本功能测试
31. **测试目的**：验证获取作业日志的功能
    **测试步骤**：
    - 先使用 `gpuctl create -f tests/yamls/compute/test-nginx.yaml` 创建作业
    - 执行命令：`gpuctl logs test-nginx`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含作业的日志信息
    - 日志内容与 `kubectl logs <pod-name>` 一致

#### 选项组合测试
32. **测试目的**：验证获取指定命名空间作业日志的功能
    **测试步骤**：
    - 先使用 `gpuctl create -f tests/yamls/compute/test-nginx.yaml -n test-namespace` 创建作业
    - 执行命令：`gpuctl logs test-nginx -n test-namespace`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含作业的日志信息
    - 日志内容与 `kubectl logs <pod-name> -n test-namespace` 一致

33. **测试目的**：验证跟踪作业日志的功能
    **测试步骤**：
    - 先使用 `gpuctl create -f tests/yamls/compute/test-nginx.yaml` 创建作业
    - 执行命令：`gpuctl logs test-nginx -f`
    - 在另一个终端向作业发送请求，产生新的日志
    **预期结果**：
    - 命令成功，持续输出日志
    - 能看到新产生的日志实时输出
    - 使用 Ctrl+C 可以中断日志跟踪

34. **测试目的**：验证 JSON 格式输出日志的功能
    **测试步骤**：
    - 先使用 `gpuctl create -f tests/yamls/compute/test-nginx.yaml` 创建作业
    - 执行命令：`gpuctl logs test-nginx --json`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出为 JSON 格式，包含日志信息
    - JSON 格式正确，可以被解析

#### 错误处理测试
35. **测试目的**：验证获取不存在作业日志时的错误处理
    **测试步骤**：
    - 执行命令：`gpuctl logs nonexistent-job`
    **预期结果**：
    - 命令失败，返回非零退出码
    - 输出包含错误信息，提示作业不存在

### 3.6 `label` 命令测试

#### 基本功能测试
36. **测试目的**：验证为单个节点添加标签的功能
    **测试步骤**：
    - 执行命令：`gpuctl label node runwhere.ai/gpu-type=a100-80g node-1`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含节点名称和标签信息
    - 使用 `kubectl get node node-1 --show-labels` 可以看到添加的标签

37. **测试目的**：验证为多个节点添加标签的功能
    **测试步骤**：
    - 执行命令：`gpuctl label node pool=test-pool node-1 node-2`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含节点名称和标签信息
    - 使用 `kubectl get nodes node-1 node-2 --show-labels` 可以看到添加的标签

#### 选项组合测试
38. **测试目的**：验证覆盖现有标签的功能
    **测试步骤**：
    - 先执行 `gpuctl label node pool=test-pool node-1` 为节点添加标签
    - 执行命令：`gpuctl label node pool=new-pool node-1 --overwrite`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含节点名称和新标签信息
    - 使用 `kubectl get node node-1 --show-labels` 可以看到标签已更新

39. **测试目的**：验证删除节点标签的功能
    **测试步骤**：
    - 先执行 `gpuctl label node pool=test-pool node-1` 为节点添加标签
    - 执行命令：`gpuctl label node pool node-1 --delete`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含节点名称和删除的标签信息
    - 使用 `kubectl get node node-1 --show-labels` 看不到该标签

40. **测试目的**：验证 JSON 格式输出的功能
    **测试步骤**：
    - 执行命令：`gpuctl label node pool=test-pool node-1 --json`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出为 JSON 格式，包含标签操作的详细信息
    - JSON 格式正确，可以被解析

#### 错误处理测试
41. **测试目的**：验证为不存在节点添加标签时的错误处理
    **测试步骤**：
    - 执行命令：`gpuctl label node pool=test-pool nonexistent-node`
    **预期结果**：
    - 命令失败，返回非零退出码
    - 输出包含错误信息，提示节点不存在

42. **测试目的**：验证覆盖标签但未指定 `--overwrite` 选项时的错误处理
    **测试步骤**：
    - 先执行 `gpuctl label node pool=test-pool node-1` 为节点添加标签
    - 执行命令：`gpuctl label node pool=new-pool node-1`（不使用 --overwrite 选项）
    **预期结果**：
    - 命令失败，返回非零退出码
    - 输出包含错误信息，提示标签已存在，需要使用 --overwrite 选项

### 3.7 `describe` 命令测试

#### 基本功能测试
43. **测试目的**：验证查看作业详情的功能
    **测试步骤**：
    - 先使用 `gpuctl create -f tests/yamls/compute/test-nginx.yaml` 创建作业
    - 执行命令：`gpuctl describe job test-nginx`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含作业的详细信息，包括名称、命名空间、类型、资源池、状态、资源配置、服务配置、环境配置和存储配置
    - 信息完整，格式清晰

44. **测试目的**：验证查看资源池详情的功能
    **测试步骤**：
    - 执行命令：`gpuctl describe pool test-pool`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含资源池的详细信息，包括名称、状态、节点列表和资源配置

45. **测试目的**：验证查看节点详情的功能
    **测试步骤**：
    - 执行命令：`gpuctl describe node node-1`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含节点的详细信息，包括名称、状态、GPU 类型、GPU 数量、标签列表、绑定的资源池和 Kubernetes 节点详情

46. **测试目的**：验证查看配额详情的功能
    **测试步骤**：
    - 执行命令：`gpuctl describe quota default`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含配额的详细信息，包括命名空间、CPU 配额、内存配额、GPU 配额和使用情况

47. **测试目的**：验证查看命名空间详情的功能
    **测试步骤**：
    - 执行命令：`gpuctl describe ns default`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含命名空间的详细信息，包括名称、状态、创建时间和资源使用情况

    或使用完整命令：
    - 执行命令：`gpuctl describe namespace default`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含命名空间的详细信息，与使用 `describe ns` 命令相同

#### 选项组合测试
48. **测试目的**：验证查看指定命名空间作业详情的功能
    **测试步骤**：
    - 先使用 `gpuctl create -f tests/yamls/compute/test-nginx.yaml -n test-namespace` 创建作业
    - 执行命令：`gpuctl describe job test-nginx -n test-namespace`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出包含作业的详细信息，命名空间为 test-namespace

49. **测试目的**：验证 JSON 格式输出的功能
    **测试步骤**：
    - 执行命令：`gpuctl describe job test-nginx --json`
    **预期结果**：
    - 命令成功，返回零退出码
    - 输出为 JSON 格式，包含作业的详细信息
    - JSON 格式正确，可以被解析

#### 错误处理测试
50. **测试目的**：验证查看不存在作业详情时的错误处理
    **测试步骤**：
    - 执行命令：`gpuctl describe job nonexistent-job`
    **预期结果**：
    - 命令失败，返回非零退出码
    - 输出包含错误信息，提示作业不存在

51. **测试目的**：验证查看不存在节点详情时的错误处理
    **测试步骤**：
    - 执行命令：`gpuctl describe node nonexistent-node`
    **预期结果**：
    - 命令失败，返回非零退出码
    - 输出包含错误信息，提示节点不存在

52. **测试目的**：验证查看不存在命名空间详情时的错误处理
    **测试步骤**：
    - 执行命令：`gpuctl describe ns nonexistent-namespace`
    **预期结果**：
    - 命令失败，返回非零退出码
    - 输出包含错误信息，提示命名空间不存在

## 4. 测试执行与结果记录

### 4.1 测试执行流程

1. **测试准备**：
   - 确保测试环境已准备好
   - 确保 gpuctl 已正确安装
   - 确保 Kubernetes 集群可访问

2. **测试执行**：
   - 按照测试用例顺序执行每个测试
   - 记录每个测试的执行结果
   - 记录测试过程中遇到的问题

3. **测试结果分析**：
   - 分析测试结果，判断测试是否通过
   - 对于失败的测试，分析原因并记录
   - 生成测试报告

### 4.2 测试结果记录模板

| 测试用例 ID | 测试用例名称 | 执行结果 | 执行时间 | 备注 |
|-------------|--------------|----------|----------|------|
| 1 | 从单个 YAML 文件创建作业 | PASS | 2024-01-08 10:00:00 | - |
| 2 | 从多个 YAML 文件创建作业 | PASS | 2024-01-08 10:05:00 | - |
| 3 | 指定命名空间创建作业 | FAIL | 2024-01-08 10:10:00 | 命名空间不存在 |

## 5. 测试报告生成

测试执行完成后，根据测试结果记录生成测试报告，包括以下内容：

- 测试概述
- 测试环境
- 测试用例执行结果统计
- 测试通过情况
- 测试失败情况及原因分析
- 测试建议和改进方向

## 6. 注意事项

1. **测试顺序**：建议按照测试用例顺序执行，因为后面的测试可能依赖前面的测试结果
2. **测试环境**：确保测试环境干净，避免之前的测试残留影响当前测试
3. **资源清理**：测试完成后，及时清理测试创建的资源，避免占用集群资源
4. **日志记录**：详细记录测试过程和结果，便于后续分析和问题定位
5. **版本一致性**：确保 gpuctl 版本与测试用例匹配，避免版本差异导致测试失败

## 7. 测试维护

1. **定期更新**：当 gpuctl 版本更新时，及时更新测试用例，确保测试覆盖新功能和变更
2. **测试用例评审**：定期评审测试用例，确保测试覆盖全面，没有冗余和遗漏
3. **测试结果分析**：定期分析测试结果，识别系统瓶颈和问题，推动系统改进

---

**gpuctl 自然语言单元测试用例 - 版本 1.0**
**最后更新：2024-01-08**