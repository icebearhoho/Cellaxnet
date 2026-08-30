"""ORM models live here. Add one file per aggregate (user.py, idea.py, ...)."""

from app.models.autopilot import AutopilotAuditEvent, AutopilotOpportunity
from app.models.behavior_event import BehaviorEvent
from app.models.channel_link import ChannelConnection
from app.models.competitor import CompetitorSnapshot, TrackedCompetitor
from app.models.idea import Idea
from app.models.marketplace import (
    OAuthState,
    SellerAccount,
    ShopConnection,
    ShopCredential,
    ShopInventory,
    ShopOrder,
    ShopOrderItem,
    ShopProduct,
    SyncRun,
)
from app.models.marketplace_shop import MarketplaceShop
from app.models.order import Order, OrderItem
from app.models.product_stock import ProductStock
from app.models.review import Review
from app.models.shopee_session import ShopeeSession
from app.models.user import User
from app.models.voucher import VoucherCampaign, VoucherCampaignEvent
from app.models.workspace import SellerWorkspace, WorkspaceMember

__all__ = [
    "BehaviorEvent",
    "ChannelConnection",
    "AutopilotOpportunity",
    "AutopilotAuditEvent",
    "CompetitorSnapshot",
    "Idea",
    "MarketplaceShop",
    "OAuthState",
    "Order",
    "OrderItem",
    "ProductStock",
    "Review",
    "SellerAccount",
    "ShopConnection",
    "ShopCredential",
    "ShopInventory",
    "ShopOrder",
    "ShopOrderItem",
    "ShopProduct",
    "ShopeeSession",
    "TrackedCompetitor",
    "SyncRun",
    "User",
    "VoucherCampaign",
    "VoucherCampaignEvent",
    "SellerWorkspace",
    "WorkspaceMember",
]
