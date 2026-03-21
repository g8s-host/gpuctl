# 开发者指南

欢迎来到 gpuctl 开发者文档！本章面向希望了解 gpuctl 内部实现、进行二次开发或贡献代码的工程师。

## 技术栈

| 层次 | 技术 |
|------|------|
| CLI | Python 3.8+ + argparse |
| API 服务 | FastAPI + uvicorn |
| 数据模型 | Pydantic v2 |
| K8s 交互 | kubernetes-client/python |
| 配置解析 | PyYAML |
| 打包 | PyInstaller（二进制）/ Poetry（Python 包） |

---

## 代码模块总览

```
gpuctl/
├── gpuctl/
│   ├── api/           数据模型层（Pydantic）
│   ├── parser/        YAML 解析与校验
│   ├── builder/       模型 → K8s 资源构建
│   ├── client/        K8s API 操作封装
│   ├── kind/          场景化业务逻辑
│   ├── cli/           命令行入口（argparse）
│   └── constants.py   全局常量
├── server/
│   ├── main.py        FastAPI 应用入口
│   ├── models.py      API 请求/响应模型
│   └── routes/        路由分组
├── tests/             测试用例
├── doc/               原始设计文档
├── mkdocs.yml         文档站点配置
└── docs/              文档源文件（公开文档 + 内部设计文档）
```

---

## 数据流

用户的 YAML 文件经过以下链路处理后提交到 Kubernetes：

```
用户 YAML 文件
      │
      ▼ BaseParser.parse_yaml_file()
 Pydantic 数据模型（api/）
      │
      ▼ XxxBuilder.build()
 K8s 资源对象（kubernetes-client 对象）
      │
      ▼ XxxClient.create()
 Kubernetes API Server
```

---

## 本章内容

<div class="grid cards" markdown>

-   :material-layers:{ .lg .middle } **系统架构**

    ---

    详细的分层架构设计、模块依赖关系、Label 体系和 K8s 资源映射规则。

    [:octicons-arrow-right-24: 系统架构](architecture.md)

-   :material-api:{ .lg .middle } **REST API**

    ---

    完整的 REST API 接口文档，包含请求/响应格式、参数说明和错误码。

    [:octicons-arrow-right-24: REST API](api.md)

-   :material-source-pull:{ .lg .middle } **贡献指南**

    ---

    开发环境搭建、代码规范、测试运行和 PR 提交流程。

    [:octicons-arrow-right-24: 贡献指南](contributing.md)

</div>

---

## 快速开发环境搭建

```bash
# 克隆仓库
git clone https://github.com/runwhere-ai/gpuctl.git
cd gpuctl

# 安装开发依赖
pip install -e ".[dev]"
# 或使用 Poetry
poetry install

# 运行测试
pytest

# 启动 API 服务（开发模式）
python server/main.py
```
