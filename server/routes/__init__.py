from .jobs import router as jobs_router
from .pools import router as pools_router
from .nodes import router as nodes_router
from .labels import router as labels_router, global_labels_router
from .auth import router as auth_router, permissions_router

__all__ = [
    "jobs_router",
    "pools_router",
    "nodes_router",
    "labels_router",
    "global_labels_router",
    "auth_router",
    "permissions_router"
]