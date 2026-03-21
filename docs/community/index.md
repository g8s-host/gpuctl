# Community

gpuctl is an open source project — everyone is welcome! Whether you're reporting a bug, proposing a new feature, or contributing code, we're glad to have you.

## Quick Links

<div class="grid cards" markdown>

-   :fontawesome-brands-github:{ .lg .middle } **GitHub Repository**

    ---

    Browse the source code, open Issues, and submit Pull Requests.

    [github.com/runwhere-ai/gpuctl](https://github.com/runwhere-ai/gpuctl){ .md-button }

-   :material-bug:{ .lg .middle } **Report a Bug**

    ---

    Found a problem? Describe the reproduction steps in a GitHub Issue and help us keep improving.

    [Submit a Bug Report](https://github.com/runwhere-ai/gpuctl/issues/new?template=bug_report.md){ .md-button }

-   :material-lightbulb:{ .lg .middle } **Feature Requests**

    ---

    Have a great idea? Open a feature request in Issues or start a discussion in Discussions.

    [Submit a Feature Request](https://github.com/runwhere-ai/gpuctl/issues/new?template=feature_request.md){ .md-button }

-   :material-forum:{ .lg .middle } **Community Discussions**

    ---

    Join technical discussions, share your experience, and get help.

    [Open Discussions](https://github.com/runwhere-ai/gpuctl/discussions){ .md-button }

</div>

---

## How to Contribute

### Contributing Code

1. **Fork** the repository to your GitHub account
2. **Clone** it locally: `git clone https://github.com/<your-username>/gpuctl.git`
3. **Create a branch**: `git checkout -b feature/my-feature`
4. **Develop and test**: `pytest`
5. **Submit a PR**: describe your changes and motivation

See the [Contributing Guide](../developer-guide/contributing.md) for detailed steps.

### Contributing Documentation

Found an error or improvement opportunity in the docs?

1. Click the **Edit** icon in the top-right corner of any documentation page
2. Edit the Markdown file directly on GitHub
3. Submit a Pull Request

### Contributing Tests

Help make the project more robust by improving test coverage:

```bash
# Run existing tests
pytest tests/

# View coverage
pytest --cov=gpuctl --cov-report=html
open htmlcov/index.html
```

---

## Issue Submission Guidelines

To help us quickly diagnose and resolve problems, please include the following when opening an Issue:

### Bug Reports

```markdown
**Environment**
- gpuctl version: 1.0.0
- Python version: 3.10
- Kubernetes version: 1.28
- OS: Ubuntu 22.04

**Steps to Reproduce**
1. Create the following YAML file...
2. Run: gpuctl create -f xxx.yaml
3. Observe the following error...

**Expected Behavior**
The job should be created and start running.

**Actual Behavior**
Error: XXX

**Error Logs**
(paste full error output)
```

### Feature Requests

```markdown
**Use Case**
Describe the problem you're facing or the goal you want to achieve.

**Proposed Solution**
Describe the feature or behavior you'd like to see.

**Alternatives Considered**
Have you considered any other approaches?
```

---

## Releases

gpuctl follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible new features
- **PATCH**: Backwards-compatible bug fixes

View all releases: [GitHub Releases](https://github.com/runwhere-ai/gpuctl/releases)

---

## Roadmap

The following are gpuctl's near-term planned directions (continuously updated):

| Feature | Status | Notes |
|---------|--------|-------|
| Multi-node distributed training | In progress | K8s multi-Pod Job support |
| Checkpoint resume | Planned | `gpuctl resume job <name>` |
| GPU utilization monitoring | Planned | Prometheus + Grafana integration |
| Web management UI | Planned | Visual job management dashboard |
| Multi-cluster support | Planned | Cross-cluster resource scheduling |
| Helm Chart | Planned | Deploy API service via Helm |

---

## Contact Us

- **GitHub Issues**: [Technical questions and bugs](https://github.com/runwhere-ai/gpuctl/issues)
- **GitHub Discussions**: [Feature discussions and experience sharing](https://github.com/runwhere-ai/gpuctl/discussions)
- **Email**: team@gpuctl.com

---

## License

gpuctl is open source under the [MIT License](https://github.com/runwhere-ai/gpuctl/blob/main/LICENSE) — you are free to use, modify, and distribute it.

```
MIT License

Copyright (c) 2025 GPU Control Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

Thank you to all developers and users who have contributed to gpuctl!
