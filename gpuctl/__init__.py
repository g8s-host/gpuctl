# Default Kubernetes namespace for all resources
import os

DEFAULT_NAMESPACE = os.getenv("DEFAULT_NAMESPACE", "default")