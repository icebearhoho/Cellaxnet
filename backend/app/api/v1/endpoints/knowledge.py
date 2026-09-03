"""Track 2, Đề 1 — Product Knowledge (causal sales explanation)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, PageMeta
from app.db.session import get_db
from app.schemas.knowledge import ProductKnowledgeRequest
from app.schemas.product_graph import ProductGraphRequest
from app.services import knowledge as service
from app.services import product_graph as graph_service

router = APIRouter()


@router.post("/", response_model=ApiResponse[dict])
async def explain(req: ProductKnowledgeRequest) -> ApiResponse[dict]:
    data = await service.explain_sales(req)
    return ApiResponse[dict](success=True, data=data.model_dump(), meta=PageMeta(), error=None)


@router.post("/graph", response_model=ApiResponse[dict])
async def graph(
    req: ProductGraphRequest, db: AsyncSession = Depends(get_db)
) -> ApiResponse[dict]:
    """Resolve a product's relationship graph + grounded sales explanation."""
    data = await graph_service.explore(db, req)
    return ApiResponse[dict](success=True, data=data.model_dump(), meta=PageMeta(), error=None)


@router.get("/graph/overview", response_model=ApiResponse[dict])
async def graph_overview(
    shop_connection_id: int | None = Query(default=None),
    days: int = Query(default=30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Rank categories/products using only persisted marketplace records."""
    data = await graph_service.overview(db, shop_connection_id, days)
    return ApiResponse[dict](success=True, data=data.model_dump(), meta=PageMeta(), error=None)


@router.get("/graph/products/{product_id}", response_model=ApiResponse[dict])
async def graph_product_detail(
    product_id: str,
    shop_connection_id: int | None = Query(default=None),
    days: int = Query(default=30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Compare one product with similar products in the same synced shop."""
    data = await graph_service.detail(db, product_id, shop_connection_id, days)
    return ApiResponse[dict](success=True, data=data.model_dump(), meta=PageMeta(), error=None)
