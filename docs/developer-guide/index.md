# Developer Guide

Welcome to the gpuctl developer documentation! This section is for engineers who want to understand gpuctl's internals, extend it, or contribute code.

## Tech Stack

| Layer | Technology |
|-------|------------|
| CLI | Python 3.8+ + argparse |
| API Service | FastAPI + uvicorn |
| Data Models | Pydantic v2 |
| K8s Interaction | kubernetes-client/python |
| Config Parsing | PyYAML |
| Packaging | PyInstaller (binary) / Poetry (Python package) |

---

## Code Module Overview

```
gpuctl/
├── gpuctl/
│   ├── api/           Data model layer (Pydantic)
│   ├── parser/        YAML parsing and validation
│   ├── builder/       Model → K8s resource building
│   ├── client/        K8s API operation wrappers
│   ├── kind/          Scenario-specific business logic
│   ├── cli/           CLI entry points (argparse)
│   └── constants.py   Global constants
├── server/
│   ├── main.py        FastAPI application entry point
│   ├── models.py      API request/response models
│   └── routes/        Route groups
├── tests/             Test cases
├── doc/               Original design documents
├── mkdocs.yml         Documentation site config
└── docs/              Documentation source files
```

---

## Data Flow

User YAML files are processed through the following pipeline before being submitted to Kubernetes:

```
User YAML File
      │
      ▼ BaseParser.parse_yaml_file()
 Pydantic Data Model (api/)
      │
      ▼ XxxBuilder.build()
 K8s Resource Object (kubernetes-client object)
      │
      ▼ XxxClient.create()
 Kubernetes API Server
```

---

## Contents

<div class="grid cards" markdown>

-   :material-layers:{ .lg .middle } **Architecture**

    ---

    Detailed layered architecture design, module dependency relationships, Label system, and K8s resource mapping rules.

    [:octicons-arrow-right-24: Architecture](architecture.md)

-   :material-api:{ .lg .middle } **REST API**

    ---

    Complete REST API documentation including request/response formats, parameter descriptions, and error codes.

    [:octicons-arrow-right-24: REST API](api.md)

-   :material-source-pull:{ .lg .middle } **Contributing**

    ---

    Development environment setup, code conventions, running tests, and the PR submission process.

    [:octicons-arrow-right-24: Contributing](contributing.md)

</div>

---

## Quick Dev Environment Setup

```bash
# Clone the repo
git clone https://github.com/runwhere-ai/gpuctl.git
cd gpuctl

# Install dev dependencies
pip install -e ".[dev]"
# Or with Poetry
poetry install

# Run tests
pytest

# Start the API server (dev mode)
python server/main.py
```
