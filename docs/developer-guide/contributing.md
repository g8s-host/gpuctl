# 贡献指南

感谢你有兴趣为 gpuctl 贡献代码！本文档说明如何搭建开发环境、运行测试，以及提交 PR 的流程。

## 开发环境搭建

### 前提条件

- Python 3.8+
- Git
- 可访问的 Kubernetes 集群（用于集成测试，可选）

### 克隆与安装

```bash
# 1. Fork 仓库并克隆
git clone https://github.com/<你的用户名>/gpuctl.git
cd gpuctl

# 2. 安装开发依赖
pip install -e ".[dev]"

# 或使用 Poetry
poetry install
```

### 目录结构速览

```
gpuctl/
├── gpuctl/
│   ├── api/           # Pydantic 数据模型
│   ├── parser/        # YAML 解析
│   ├── builder/       # K8s 资源构建
│   ├── client/        # K8s API 调用
│   ├── kind/          # 场景化业务逻辑
│   ├── cli/           # CLI 命令实现
│   └── constants.py   # 全局常量
├── server/            # FastAPI 服务
├── tests/             # 测试用例
└── doc/               # 设计文档
```

---

## 运行测试

```bash
# 运行所有单元测试
pytest

# 运行指定测试文件
pytest tests/test_gpuctl.py

# 显示详细输出
pytest -v

# 生成覆盖率报告
pytest --cov=gpuctl --cov-report=html
```

---

## 代码规范

### 命名约定

- 函数/变量：`snake_case`
- 类名：`PascalCase`
- 常量：定义在 `gpuctl/constants.py` 中，不允许在其他模块硬编码魔法字符串

### 常量使用

```python
# 正确 ✅
from gpuctl.constants import Kind, Labels
label_value = Kind.TRAINING

# 错误 ❌
label_value = "training"
```

### 新增任务类型

如果要新增任务类型（例如 `batch`），需要按以下顺序修改：

1. **`gpuctl/constants.py`** — 在 `Kind` 枚举中添加新 Kind
2. **`gpuctl/api/`** — 新增对应的 Pydantic 模型文件
3. **`gpuctl/parser/`** — 新增或修改 parser 支持新 Kind
4. **`gpuctl/builder/`** — 新增 Builder，实现 `build()` 方法
5. **`gpuctl/client/job_client.py`** — 添加对新 K8s 资源类型的支持
6. **`gpuctl/cli/job.py`** — 在 CLI 命令中处理新 Kind
7. **`server/routes/jobs.py`** — 在 API 路由中处理新 Kind
8. **`tests/`** — 添加对应测试用例

---

## 提交 PR 流程

### 分支命名

```
feature/add-batch-job-support
fix/delete-service-on-cleanup
docs/update-cli-reference
```

### Commit 信息规范

```
feat: 添加 batch 任务类型支持
fix: 修复删除任务时 Service 未同步删除的问题
docs: 更新 CLI 命令参考文档
refactor: 将公共标签常量移至 constants.py
test: 新增 inference 类型端到端测试
```

### PR 提交步骤

```bash
# 1. 创建功能分支
git checkout -b feature/my-feature

# 2. 开发并提交
git add .
git commit -m "feat: 描述你的改动"

# 3. 推送到你的 Fork
git push origin feature/my-feature

# 4. 在 GitHub 上创建 Pull Request
```

### PR 检查清单

在提交 PR 前，请确认：

- [ ] 代码通过 `pytest` 所有测试
- [ ] 新功能有对应的测试用例
- [ ] 新增的魔法字符串已添加到 `constants.py`
- [ ] 更新了相关文档（如 CLI 参考、用户指南）
- [ ] PR 标题符合 Commit 规范

---

## 构建二进制文件

```bash
# 安装 PyInstaller
pip install pyinstaller

# 构建 Linux 二进制
pyinstaller --onefile --name="gpuctl-linux-amd64" \
  --hidden-import=yaml --hidden-import=PyYAML main.py

# 构建 Windows 二进制
pyinstaller --onefile --name="gpuctl-windows-amd64.exe" \
  --hidden-import=yaml --hidden-import=PyYAML main.py

# 构建产物在 dist/ 目录
ls dist/
```

---

## 文档贡献

本文档站点基于 MkDocs + Material 主题：

```bash
# 安装文档依赖
pip install mkdocs mkdocs-material

# 在项目根目录执行
mkdocs serve   # 本地预览
mkdocs build   # 构建静态文件（输出到 site/）
```

文档源文件位于 `docs/`，`mkdocs.yml` 配置在项目根目录，修改后提交 PR 即可更新官网。

---

## 获取帮助

如有问题，欢迎通过以下方式联系：

- **GitHub Issues**：[提交 Bug 或功能建议](https://github.com/g8s-host/gpuctl/issues)
- **GitHub Discussions**：[参与社区讨论](https://github.com/g8s-host/gpuctl/discussions)
