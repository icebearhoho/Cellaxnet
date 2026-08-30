"""Multi-marketplace seller accounts and shop connections.

Shape of the problem: one person signs up on this platform, owns one or more
*seller accounts*, and each seller account links one or more *shops* — a shop
being one storefront on one marketplace. Shopee and Lazada storefronts of the
same seller are two shops, not one, because each is authorised separately and
each hands back its own credentials.

Why the marketplace-specific bits stay out of these tables: every platform
names things differently (Shopee `item_id`/`model_id`, Lazada `item_id`/`sku_id`,
TikTok `product_id`/`sku_id`) and returns its own status vocabulary. Those are
translated in the adapter layer, so everything here is already canonical. The
untranslated payload is kept in `raw_json` next to it — when a mapping turns
out wrong, and on a first integration it always does somewhere, the rows can be
re-derived without asking the marketplace for the data again.

Credentials live in their own table on purpose; see ShopCredential.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# --------------------------------------------------------------------------- #
# Canonical vocabularies. Kept as module constants rather than DB enums so a new
# marketplace or status does not need a migration to add one.
# --------------------------------------------------------------------------- #

PLATFORMS = ("shopee", "lazada", "tiktok")

# Connection lifecycle. The distinction that matters operationally:
#   expired  -> our refresh token ran out; the seller must re-authorise
#   revoked  -> the seller cut access from the marketplace side
# Both need re-authorisation, but only `revoked` means the seller made a choice,
# so the UI should say different things.
CONNECTION_STATUSES = (
    "pending",       # seller was sent to the marketplace, no callback yet
    "connected",
    "expired",
    "revoked",
    "error",         # last sync failed; credentials may still be fine
    "disconnected",  # unlinked from our side
)

ORDER_STATUSES = (
    "unpaid",
    "awaiting_shipment",
    "shipped",
    "delivered",
    "completed",
    "cancelled",
    "returned",
    "unknown",       # a status the mapping has not seen — logged, never guessed
)


class SellerAccount(Base, TimestampMixin):
    """A seller's identity on this platform, independent of any marketplace."""

    __tablename__ = "seller_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Nullable while the platform's own auth is still a skeleton: a seller
    # account is usable before there is a user row to hang it off, and the
    # column can be backfilled without touching anything else.
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_type: Mapped[str] = mapped_column(
        String(16), default="individual", nullable=False
    )
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)

    shops: Mapped[list[ShopConnection]] = relationship(
        back_populates="seller_account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ShopConnection(Base, TimestampMixin):
    """One storefront on one marketplace, linked to one seller account."""

    __tablename__ = "shop_connections"
    __table_args__ = (
        # The same storefront must not be linked twice, even by two different
        # seller accounts — whoever authorised last owns the link.
        UniqueConstraint("platform", "external_shop_id", name="uq_shop_platform_ext"),
        Index("ix_shop_connections_account", "seller_account_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_account_id: Mapped[int] = mapped_column(
        ForeignKey("seller_accounts.id", ondelete="CASCADE"), nullable=False
    )

    platform: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    external_shop_id: Mapped[str] = mapped_column(String(64), nullable=False)
    shop_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Lazada and TikTok run one app across several countries and route calls by
    # region, so it has to be stored per shop rather than configured globally.
    region: Mapped[str] = mapped_column(String(8), default="VN", nullable=False)

    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    authorized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    seller_account: Mapped[SellerAccount] = relationship(back_populates="shops")
    credential: Mapped[ShopCredential | None] = relationship(
        back_populates="shop",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )


class ShopCredential(Base, TimestampMixin):
    """OAuth tokens for one shop, encrypted at rest.

    Separate from ShopConnection for two reasons that both bite in practice:

    1. A `SELECT *` on the connection row is something every list screen does.
       If tokens lived there, one careless serialiser would leak them through
       the API. They cannot leak from a table nothing selects by default.
    2. Tokens rotate on a timer (Shopee's access token lasts about four hours)
       while connection metadata barely changes, so the write patterns differ.

    Encryption is app-level (Fernet) with the key supplied by the environment.
    A production deployment should hold that key in a KMS rather than an env
    var; that is a deployment concern, called out so it is not mistaken for
    done.
    """

    __tablename__ = "shop_credentials"

    shop_connection_id: Mapped[int] = mapped_column(
        ForeignKey("shop_connections.id", ondelete="CASCADE"), primary_key=True
    )

    access_token_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    refresh_token_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # Anything the marketplace demands on later calls: TikTok's shop_cipher,
    # Lazada's account id. Encrypted too — it is credential material.
    extra_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refresh_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    shop: Mapped[ShopConnection] = relationship(back_populates="credential")


class OAuthState(Base):
    """Single-use CSRF token guarding the authorisation callback.

    Kept in the database rather than only in Redis so an authorisation started
    before a restart still completes. Rows are consumed, not deleted, so a
    replayed callback is distinguishable from an unknown one in the logs.
    """

    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    seller_account_id: Mapped[int] = mapped_column(
        ForeignKey("seller_accounts.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ShopProduct(Base):
    """A listing, flattened to one row per sellable variant."""

    __tablename__ = "shop_products"
    __table_args__ = (
        UniqueConstraint(
            "shop_connection_id", "external_product_id", "external_sku_id",
            name="uq_shop_product_sku",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_connection_id: Mapped[int] = mapped_column(
        ForeignKey("shop_connections.id", ondelete="CASCADE"), nullable=False, index=True
    )

    external_product_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # "" rather than NULL for products without variants: NULL breaks the unique
    # constraint above, since NULL is never equal to NULL in SQL.
    external_sku_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Smallest currency unit (đồng) as an integer. Money in floating point
    # accumulates rounding error the moment it is summed.
    price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    original_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="VND", nullable=False)

    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ShopInventory(Base):
    """Stock level per variant per warehouse.

    Its own table rather than a column on ShopProduct because every platform
    supports multiple warehouses, and a single `stock` column silently sums or
    silently drops all but one of them.
    """

    __tablename__ = "shop_inventory"
    __table_args__ = (
        UniqueConstraint(
            "shop_connection_id", "external_product_id", "external_sku_id",
            "warehouse_id", name="uq_shop_inventory_sku_wh",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_connection_id: Mapped[int] = mapped_column(
        ForeignKey("shop_connections.id", ondelete="CASCADE"), nullable=False, index=True
    )

    external_product_id: Mapped[str] = mapped_column(String(64), nullable=False)
    external_sku_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    warehouse_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    quantity_available: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ShopOrder(Base):
    """One order, with its marketplace status translated to a canonical one."""

    __tablename__ = "shop_orders"
    __table_args__ = (
        UniqueConstraint(
            "shop_connection_id", "external_order_id", name="uq_shop_order_ext"
        ),
        Index("ix_shop_orders_placed", "shop_connection_id", "placed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_connection_id: Mapped[int] = mapped_column(
        ForeignKey("shop_connections.id", ondelete="CASCADE"), nullable=False, index=True
    )

    external_order_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    # Kept verbatim beside the canonical value so an unmapped status can be
    # diagnosed from the row itself rather than from logs that have rotated.
    raw_status: Mapped[str | None] = mapped_column(String(64), nullable=True)

    payment_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="VND", nullable=False)

    # Salted hash of the marketplace's buyer id — enough to recognise a repeat
    # customer, useless for identifying a person. Names, phone numbers and
    # addresses are deliberately not stored.
    buyer_ref: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    placed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    platform_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    items: Mapped[list[ShopOrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class ShopOrderItem(Base):
    __tablename__ = "shop_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("shop_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )

    external_product_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_sku_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)

    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    subtotal: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    order: Mapped[ShopOrder] = relationship(back_populates="items")


class SyncRun(Base):
    """One pass of one data group over one shop.

    Exists so "why is this shop's data stale" has an answer that does not
    require reading application logs: what ran, when, how far it got, and what
    stopped it.
    """

    __tablename__ = "sync_runs"
    __table_args__ = (Index("ix_sync_runs_shop_started", "shop_connection_id", "started_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_connection_id: Mapped[int] = mapped_column(
        ForeignKey("shop_connections.id", ondelete="CASCADE"), nullable=False
    )
    data_type: Mapped[str] = mapped_column(String(16), nullable=False)  # shop|product|order|inventory
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    records_read: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_written: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Incremental sync watermark, so the next run asks only for what changed.
    cursor_from: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cursor_to: Mapped[str | None] = mapped_column(String(64), nullable=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)
