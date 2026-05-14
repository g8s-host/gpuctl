"""SSH execution backend.

Deploys gpuctl jobs to bare GPU hosts reachable over SSH. See
``docs/design/ssh-backend.md`` for design context.

Submodules:
- ``inventory``: load + validate the node inventory YAML
- ``state``: SQLite-backed desired-state store
- ``runtime``: docker command builders (pure functions, no I/O)
- ``connection``: paramiko-based SSH executor (the only I/O module)
- ``scheduler``: pick a node for a JobSpec
- ``backend``: ``SshBackend`` glueing the above into the ``Backend`` protocol
"""

from gpuctl.backend.ssh.backend import SshBackend

__all__ = ["SshBackend"]
