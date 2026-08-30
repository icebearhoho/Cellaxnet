"""Auth: register, login, and current-user lookup.

There is no ``/logout`` endpoint on purpose — the token is stateless, so
logging out is the client dropping its cookie. No refresh-token rotation,
email verification or password reset either; see the project scope.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_dep
from app.core.responses import ApiResponse, PageMeta
from app.schemas.auth import LoginRequest, RegisterRequest, UserOut
from app.services import user_service

router = APIRouter()


@router.post("/register", response_model=ApiResponse[dict])
async def register(
    req: RegisterRequest, db: AsyncSession = Depends(get_db_dep)
) -> ApiResponse[dict]:
    # `role` is never read from the request — self-signup is always a buyer.
    # Admin accounts come only from scripts/create_admin.py.
    user = await user_service.create_user(
        db, email=req.email, password=req.password, name=req.name
    )
    return ApiResponse[dict](
        success=True,
        data=user_service.issue_token_response(user),
        meta=PageMeta(),
        error=None,
    )


@router.post("/login", response_model=ApiResponse[dict])
async def login(
    req: LoginRequest, db: AsyncSession = Depends(get_db_dep)
) -> ApiResponse[dict]:
    user = await user_service.authenticate(db, email=req.email, password=req.password)
    return ApiResponse[dict](
        success=True,
        data=user_service.issue_token_response(user),
        meta=PageMeta(),
        error=None,
    )


@router.get("/me", response_model=ApiResponse[dict])
async def me(user: dict = Depends(get_current_user)) -> ApiResponse[dict]:
    """Echo the caller's identity straight from the token claims."""
    data = UserOut(
        id=int(user["sub"]),
        email=user.get("email", ""),
        name=user.get("name"),
        role=user.get("role", "buyer"),
    )
    return ApiResponse[dict](
        success=True, data=data.model_dump(), meta=PageMeta(), error=None
    )


@router.post("/refresh", response_model=ApiResponse[dict])
async def refresh_session(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dep),
) -> ApiResponse[dict]:
    """Re-issue a JWT from current database state after role changes."""
    account = await user_service.get_by_id(db, int(user["sub"]))
    if account is None:
        from app.core.exceptions import UnauthorizedError

        raise UnauthorizedError("Tài khoản không còn tồn tại.")
    return ApiResponse[dict](
        success=True,
        data=user_service.issue_token_response(account),
        meta=PageMeta(),
        error=None,
    )
