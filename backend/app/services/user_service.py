"""User account persistence + credential checking."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import TokenResponse, UserOut

DEFAULT_ROLE = "buyer"


def issue_token_response(user: User) -> dict:
    """Issue a fresh JWT after login or an account-role transition."""
    token = create_access_token(
        user.id,
        extra={"role": user.role, "email": user.email, "name": user.name},
    )
    return TokenResponse(
        access_token=token,
        user=UserOut.model_validate(user, from_attributes=True),
    ).model_dump()


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.strip().lower()))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    name: str | None = None,
    role: str = DEFAULT_ROLE,
) -> User:
    """Create an account. ``role`` defaults to buyer and is a keyword-only arg
    so no request handler can pass a client-supplied value by accident — only
    scripts/create_admin.py passes ``role="admin"``."""
    email = email.strip().lower()
    if await get_by_email(db, email) is not None:
        raise ConflictError("Email đã được sử dụng.")

    row = User(email=email, password_hash=hash_password(password), name=name, role=role)
    db.add(row)
    try:
        await db.commit()
    except IntegrityError as exc:
        # The pre-check above leaves a race open; the unique index is the real
        # guard, so translate its violation into the same domain error.
        await db.rollback()
        raise ConflictError("Email đã được sử dụng.") from exc
    await db.refresh(row)
    return row


async def authenticate(db: AsyncSession, *, email: str, password: str) -> User:
    """Return the user for valid credentials, else raise.

    Unknown email and wrong password deliberately produce the *same* error so
    the response can't be used to enumerate registered accounts.
    """
    user = await get_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Email hoặc mật khẩu không đúng.")
    return user


async def list_users(db: AsyncSession, limit: int = 50) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(limit))
    return list(result.scalars().all())
