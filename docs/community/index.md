# 社区

gpuctl 是一个开源项目，欢迎所有人参与！无论是提交 Bug、提议新功能还是贡献代码，我们都非常欢迎。

## 快速链接

<div class="grid cards" markdown>

-   :fontawesome-brands-github:{ .lg .middle } **GitHub 仓库**

    ---

    查看源代码、提交 Issue、提交 Pull Request。

    [github.com/g8s-host/gpuctl](https://github.com/g8s-host/gpuctl){ .md-button }

-   :material-bug:{ .lg .middle } **报告 Bug**

    ---

    发现了问题？在 GitHub Issues 中描述复现步骤，帮助我们持续改进。

    [提交 Bug 报告](https://github.com/g8s-host/gpuctl/issues/new?template=bug_report.md){ .md-button }

-   :material-lightbulb:{ .lg .middle } **功能建议**

    ---

    有好的想法？在 Issues 中提出功能请求，或在 Discussions 中发起讨论。

    [提出功能建议](https://github.com/g8s-host/gpuctl/issues/new?template=feature_request.md){ .md-button }

-   :material-forum:{ .lg .middle } **社区讨论**

    ---

    参与技术讨论、分享使用经验、寻求帮助。

    [进入 Discussions](https://github.com/g8s-host/gpuctl/discussions){ .md-button }

</div>

---

## 如何贡献

### 贡献代码

1. **Fork** 项目仓库到你的 GitHub 账号
2. **Clone** 到本地：`git clone https://github.com/<你的用户名>/gpuctl.git`
3. **创建分支**：`git checkout -b feature/my-feature`
4. **开发并测试**：`pytest`
5. **提交 PR**：描述你的改动和动机

详细步骤请参考[贡献指南](../developer-guide/contributing.md)。

### 贡献文档

发现文档有误或可以改进？

1. 点击任意文档页面右上角的 **编辑** 图标
2. 在 GitHub 上直接修改 Markdown 文件
3. 提交 Pull Request

### 贡献测试用例

提高测试覆盖率，让项目更加健壮：

```bash
# 运行现有测试
pytest tests/

# 查看覆盖率
pytest --cov=gpuctl --cov-report=html
open htmlcov/index.html
```

---

## 提交 Issue 指南

为了帮助我们快速定位和解决问题，提交 Issue 时请包含：

### Bug 报告

```markdown
**环境信息**
- gpuctl 版本：1.0.0
- Python 版本：3.10
- Kubernetes 版本：1.28
- 操作系统：Ubuntu 22.04

**复现步骤**
1. 创建以下 YAML 文件...
2. 执行命令：gpuctl create -f xxx.yaml
3. 观察到以下错误...

**期望行为**
任务应该正常创建并运行。

**实际行为**
报错：XXX

**错误日志**
（粘贴完整错误输出）
```

### 功能建议

```markdown
**使用场景**
描述你遇到的问题或想实现的目标。

**建议的解决方案**
描述你期望的功能或行为。

**替代方案**
你是否考虑过其他解决方案？
```

---

## 版本发布

gpuctl 遵循[语义化版本](https://semver.org/lang/zh-CN/)规范：

- **MAJOR**：不兼容的 API 变更
- **MINOR**：向后兼容的新功能
- **PATCH**：向后兼容的 Bug 修复

查看所有版本：[GitHub Releases](https://github.com/g8s-host/gpuctl/releases)

---

## 路线图

以下是 gpuctl 的近期规划方向（持续更新）：

| 功能 | 状态 | 说明 |
|------|------|------|
| 多机多卡分布式训练 | 进行中 | 支持 K8s Job 多 Pod 分布式 |
| 断点续训支持 | 规划中 | `gpuctl resume job <name>` |
| GPU 利用率监控 | 规划中 | 集成 Prometheus + Grafana |
| Web 管理界面 | 规划中 | 可视化任务管理面板 |
| 多集群支持 | 规划中 | 跨集群资源调度 |
| Helm Chart | 规划中 | 通过 Helm 部署 API 服务 |

---

## 联系我们

- **GitHub Issues**：[技术问题和 Bug](https://github.com/g8s-host/gpuctl/issues)
- **GitHub Discussions**：[功能讨论和使用经验分享](https://github.com/g8s-host/gpuctl/discussions)
- **Email**：team@gpuctl.com

---

## 许可证

gpuctl 采用 [MIT 许可证](https://github.com/g8s-host/gpuctl/blob/main/LICENSE)开源，你可以自由使用、修改和分发。

```
MIT License

Copyright (c) 2025 GPU Control Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

感谢所有为 gpuctl 做出贡献的开发者和用户！ 🙏
