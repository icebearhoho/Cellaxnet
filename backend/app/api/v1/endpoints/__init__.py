"""Per-feature routers. New feature? Add a new file here and wire it in
``app/api/v1/__init__.py``.
"""

from app.api.v1.endpoints import (
    auth,
    autopilot,
    content_generator,
    datasets,
    health,
    ideas,
    kpis,
    personal_shopper,
    recsys,
    segmentation,
    seller_coach,
    users,
    workspaces,
)

__all__ = [
    "auth",
    "autopilot",
    "content_generator",
    "datasets",
    "health",
    "ideas",
    "kpis",
    "personal_shopper",
    "recsys",
    "segmentation",
    "seller_coach",
    "users",
    "workspaces",
]
