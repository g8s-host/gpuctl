"""Backend-agnostic error hierarchy.

Backends translate their native errors (Kubernetes ``ApiException``, SSH
``paramiko`` errors, etc.) into one of these so callers don't depend on a
specific backend.
"""


class BackendError(Exception):
    """Base class for all backend errors."""


class BackendNotConfiguredError(BackendError):
    """Raised when the configured backend cannot be initialised.

    Examples: missing kubeconfig for the kubernetes backend, missing
    inventory for the SSH backend.
    """


class JobNotFoundError(BackendError):
    """The named job does not exist on the backend."""

    def __init__(self, name: str, namespace: str):
        super().__init__(f"Job '{name}' not found in namespace '{namespace}'")
        self.name = name
        self.namespace = namespace


class JobAlreadyExistsError(BackendError):
    """A job with the same (name, namespace) already exists."""

    def __init__(self, name: str, namespace: str):
        super().__init__(
            f"Job '{name}' already exists in namespace '{namespace}'"
        )
        self.name = name
        self.namespace = namespace


class NoCapacityError(BackendError):
    """No node in the selected pool can satisfy the spec.

    Carries a short ``reason`` string suitable for surfacing to the user.
    """

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class UnsupportedFeatureError(BackendError):
    """The current backend does not support a feature requested by the spec.

    Example: SSH backend does not yet support ``replicas > 1`` for inference.
    """
