"""Shared test fixtures."""

import os

# Force test config BEFORE importing app modules.
os.environ["APP_ENV"] = "test"
os.environ["AREA303_DEBUG"] = "false"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["DEMO_MODE"] = "true"
os.environ["LLM_PROVIDER"] = "mock"
# The organisers' dataset lives on someone else's RDS. A developer with it in
# .env must not have unit tests reach across the network, so the suite runs
# against the demo catalogue unless a test opts in explicitly.
os.environ["BTC_DATABASE_URL"] = ""
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("REDIS_HOST", "localhost")

import pytest  # noqa: E402

from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_process_rate_limiter():
    """Keep per-process rate-limit state from leaking between unit tests."""
    from app.core import rate_limit

    rate_limit._LOCAL.clear()
    rate_limit._REDIS_DOWN_UNTIL = 0.0
    yield
    rate_limit._LOCAL.clear()


def _bearer(user_id: str, role: str, email: str) -> dict[str, str]:
    """Mint a real signed token — the same helper the login endpoint uses, so
    these fixtures exercise the actual claim shape rather than a stand-in."""
    token = create_access_token(
        user_id, extra={"role": role, "email": email, "name": role.title()}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return _bearer("1", "admin", "admin@test.dev")


@pytest.fixture
def buyer_headers() -> dict[str, str]:
    return _bearer("2", "buyer", "buyer@test.dev")


__all__ = ["admin_headers", "app", "buyer_headers"]
