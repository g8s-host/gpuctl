# Contributing

Thank you for your interest in contributing to gpuctl! This document explains how to set up a development environment, run tests, and submit a PR.

## Development Environment Setup

### Prerequisites

- Python 3.8+
- Git
- Access to a Kubernetes cluster (for integration tests, optional)

### Clone and Install

```bash
# 1. Fork the repo and clone
git clone https://github.com/<your-username>/gpuctl.git
cd gpuctl

# 2. Install dev dependencies
pip install -e ".[dev]"

# Or with Poetry
poetry install
```

### Directory Structure

```
gpuctl/
├── gpuctl/
│   ├── api/           # Pydantic data models
│   ├── parser/        # YAML parsing
│   ├── builder/       # K8s resource building
│   ├── client/        # K8s API calls
│   ├── kind/          # Scenario-specific business logic
│   ├── cli/           # CLI command implementations
│   └── constants.py   # Global constants
├── server/            # FastAPI service
├── tests/             # Test cases
└── doc/               # Design documents
```

---

## Running Tests

```bash
# Run all unit tests
pytest

# Run a specific test file
pytest tests/test_gpuctl.py

# Verbose output
pytest -v

# Generate coverage report
pytest --cov=gpuctl --cov-report=html
```

---

## Code Conventions

### Naming

- Functions/variables: `snake_case`
- Class names: `PascalCase`
- Constants: defined in `gpuctl/constants.py` — hardcoding magic strings in other modules is not allowed

### Using Constants

```python
# Correct ✅
from gpuctl.constants import Kind, Labels
label_value = Kind.TRAINING

# Incorrect ❌
label_value = "training"
```

### Adding a New Job Type

To add a new job type (e.g. `batch`), modify files in this order:

1. **`gpuctl/constants.py`** — add the new Kind to the `Kind` enum
2. **`gpuctl/api/`** — add the corresponding Pydantic model file
3. **`gpuctl/parser/`** — add or update the parser to support the new Kind
4. **`gpuctl/builder/`** — add a Builder implementing the `build()` method
5. **`gpuctl/client/job_client.py`** — add support for the new K8s resource type
6. **`gpuctl/cli/job.py`** — handle the new Kind in CLI commands
7. **`server/routes/jobs.py`** — handle the new Kind in API routes
8. **`tests/`** — add corresponding test cases

---

## Submitting a PR

### Branch Naming

```
feature/add-batch-job-support
fix/delete-service-on-cleanup
docs/update-cli-reference
```

### Commit Message Format

```
feat: add batch job type support
fix: fix service not deleted on job cleanup
docs: update CLI command reference
refactor: move shared label constants to constants.py
test: add inference end-to-end tests
```

### PR Steps

```bash
# 1. Create a feature branch
git checkout -b feature/my-feature

# 2. Develop and commit
git add .
git commit -m "feat: describe your change"

# 3. Push to your fork
git push origin feature/my-feature

# 4. Open a Pull Request on GitHub
```

### PR Checklist

Before submitting, confirm:

- [ ] All `pytest` tests pass
- [ ] New functionality has corresponding test cases
- [ ] New magic strings are added to `constants.py`
- [ ] Relevant documentation is updated (CLI reference, user guide, etc.)
- [ ] PR title follows the commit message format

---

## Building Binaries

```bash
# Install PyInstaller
pip install pyinstaller

# Build Linux binary
pyinstaller --onefile --name="gpuctl-linux-amd64" \
  --hidden-import=yaml --hidden-import=PyYAML main.py

# Build Windows binary
pyinstaller --onefile --name="gpuctl-windows-amd64.exe" \
  --hidden-import=yaml --hidden-import=PyYAML main.py

# Output is in the dist/ directory
ls dist/
```

---

## Contributing to Documentation

This documentation site is built with MkDocs + Material theme:

```bash
# Install doc dependencies
pip install mkdocs mkdocs-material mkdocs-static-i18n

# From the project root
mkdocs serve   # Local preview
mkdocs build   # Build static files (output to site/)
```

Documentation source files are in `docs/`, with `mkdocs.yml` at the project root. Submit a PR with your changes to update the live site.

---

## Getting Help

If you have questions, feel free to reach out:

- **GitHub Issues**: [Submit a bug or feature request](https://github.com/runwhere-ai/gpuctl/issues)
- **GitHub Discussions**: [Join the community discussion](https://github.com/runwhere-ai/gpuctl/discussions)
