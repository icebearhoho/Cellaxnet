"""Per-feature routers. New feature? Add a new file here and wire it in
``app/api/v1/__init__.py``.
"""

from app.api.v1.endpoints import (
    auth,
    autopilot,
    channel_link,
    content_generator,
    datasets,
    health,
    ideas,
    kpis,
    marketplace,
    personal_shopper,
    recsys,
    restock,
    segmentation,
    seller_coach,
    users,
    workspaces,
)

__all__ = [
    "auth",
    "autopilot",
    "channel_link",
    "content_generator",
    "datasets",
    "health",
    "ideas",
    "kpis",
    "marketplace",
    "personal_shopper",
    "recsys",
    "restock",
    "segmentation",
    "seller_coach",
    "users",
    "workspaces",
]
