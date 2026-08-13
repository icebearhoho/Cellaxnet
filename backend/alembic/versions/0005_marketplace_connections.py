"""multi-marketplace seller accounts and shop connections

Revision ID: 0005_marketplace_connections
Revises: 0004_channel_connections
Create Date: 2026-08-09 00:00:00.000000

Leaves `channel_connections` (0004) in place. That table backs the aggregator
link that is currently the only source of live order data; removing it would
take the working path down to build the replacement. The two coexist until the
per-marketplace path has run against a real shop.
"""

import sqlalchemy as sa

from alembic import op

revision = "0005_marketplace_connections"
down_revision = "0004_channel_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seller_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("business_type", sa.String(length=16), nullable=False,
                  server_default="individual"),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_seller_accounts_user_id", "seller_accounts", ["user_id"])

    op.create_table(
        "shop_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seller_account_id", sa.Integer(),
                  sa.ForeignKey("seller_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("external_shop_id", sa.String(length=64), nullable=False),
        sa.Column("shop_name", sa.String(length=255), nullable=True),
        sa.Column("region", sa.String(length=8), nullable=False, server_default="VN"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_shop_connections_platform", "shop_connections", ["platform"])
    op.create_index("ix_shop_connections_account", "shop_connections", ["seller_account_id"])
    op.create_unique_constraint(
        "uq_shop_platform_ext", "shop_connections", ["platform", "external_shop_id"]
    )

    op.create_table(
        "shop_credentials",
        sa.Column("shop_connection_id", sa.Integer(),
                  sa.ForeignKey("shop_connections.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("access_token_enc", sa.LargeBinary(), nullable=False),
        sa.Column("refresh_token_enc", sa.LargeBinary(), nullable=True),
        sa.Column("extra_enc", sa.LargeBinary(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_table(
        "oauth_states",
        sa.Column("state", sa.String(length=64), primary_key=True),
        sa.Column("seller_account_id", sa.Integer(),
                  sa.ForeignKey("seller_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "shop_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shop_connection_id", sa.Integer(),
                  sa.ForeignKey("shop_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_product_id", sa.String(length=64), nullable=False),
        sa.Column("external_sku_id", sa.String(length=64), nullable=False,
                  server_default=""),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("category_path", sa.String(length=512), nullable=True),
        sa.Column("price", sa.BigInteger(), nullable=True),
        sa.Column("original_price", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VND"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_shop_products_conn", "shop_products", ["shop_connection_id"])
    op.create_unique_constraint(
        "uq_shop_product_sku", "shop_products",
        ["shop_connection_id", "external_product_id", "external_sku_id"],
    )

    op.create_table(
        "shop_inventory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shop_connection_id", sa.Integer(),
                  sa.ForeignKey("shop_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_product_id", sa.String(length=64), nullable=False),
        sa.Column("external_sku_id", sa.String(length=64), nullable=False,
                  server_default=""),
        sa.Column("warehouse_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("quantity_available", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quantity_reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_shop_inventory_conn", "shop_inventory", ["shop_connection_id"])
    op.create_unique_constraint(
        "uq_shop_inventory_sku_wh", "shop_inventory",
        ["shop_connection_id", "external_product_id", "external_sku_id", "warehouse_id"],
    )

    op.create_table(
        "shop_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shop_connection_id", sa.Integer(),
                  sa.ForeignKey("shop_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_order_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("raw_status", sa.String(length=64), nullable=True),
        sa.Column("payment_method", sa.String(length=64), nullable=True),
        sa.Column("total_amount", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VND"),
        sa.Column("buyer_ref", sa.String(length=64), nullable=True),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("platform_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_shop_orders_conn", "shop_orders", ["shop_connection_id"])
    op.create_index("ix_shop_orders_status", "shop_orders", ["status"])
    op.create_index("ix_shop_orders_buyer", "shop_orders", ["buyer_ref"])
    op.create_index("ix_shop_orders_placed", "shop_orders",
                    ["shop_connection_id", "placed_at"])
    op.create_unique_constraint(
        "uq_shop_order_ext", "shop_orders", ["shop_connection_id", "external_order_id"]
    )

    op.create_table(
        "shop_order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(),
                  sa.ForeignKey("shop_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_product_id", sa.String(length=64), nullable=True),
        sa.Column("external_sku_id", sa.String(length=64), nullable=True),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("subtotal", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.create_index("ix_shop_order_items_order", "shop_order_items", ["order_id"])

    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shop_connection_id", sa.Integer(),
                  sa.ForeignKey("shop_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_read", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_written", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cursor_from", sa.String(length=64), nullable=True),
        sa.Column("cursor_to", sa.String(length=64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_sync_runs_shop_started", "sync_runs",
                    ["shop_connection_id", "started_at"])


def downgrade() -> None:
    op.drop_table("sync_runs")
    op.drop_table("shop_order_items")
    op.drop_table("shop_orders")
    op.drop_table("shop_inventory")
    op.drop_table("shop_products")
    op.drop_table("oauth_states")
    op.drop_table("shop_credentials")
    op.drop_table("shop_connections")
    op.drop_table("seller_accounts")
