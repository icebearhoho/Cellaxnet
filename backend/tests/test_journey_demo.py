"""Customer Journey demo video and review-signal contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas.journey import JourneyEvent, JourneyRequest
from app.services import commerce_store, portfolio
from app.services.journey import analyze_journey

EXPECTED_VIDEO_NAMES = {
    "s1-serum.webm",
    "s2-vay.webm",
    "s3-cushion-purchase.webm",
    "s4-tui-abandon.webm",
    "s5-ao-len-hoodie.webm",
    "s6-tui-cheo-purchase.webm",
    "s7-kem-chong-nang-compare.webm",
    "s8-blazer-bounce.webm",
    "s9-multi-item-checkout.webm",
    "s10-vong-tay-then-dong-ho.webm",
}


def test_prebuilt_sessions_reference_nonempty_webm_files():
    repo_root = Path(__file__).resolve().parents[2]
    sessions = commerce_store.all_sessions()

    assert len(sessions) == 10
    assert {Path(session["video_url"]).name for session in sessions} == EXPECTED_VIDEO_NAMES
    for session in sessions:
        video = repo_root / "frontend" / "public" / session["video_url"].lstrip("/")
        assert video.is_file(), f"{session['id']} references missing {video.name}"
        assert video.stat().st_size > 100_000
        assert video.read_bytes()[:4] == b"\x1aE\xdf\xa3"


def test_abandon_and_livestream_demo_events_match_their_replays():
    sessions = {session["id"]: session for session in commerce_store.all_sessions()}

    assert [event["type"] for event in sessions["S4"]["events"]][-1] == "cart"
    assert "purchase" not in {event["type"] for event in sessions["S4"]["events"]}
    assert "livestream" in {event["type"] for event in sessions["S5"]["events"]}
    assert "cart" in {event["type"] for event in sessions["S5"]["events"]}


@pytest.mark.asyncio
async def test_reading_a_review_increases_purchase_probability():
    base_events = [
        JourneyEvent(type="click", category="Mỹ phẩm"),
        JourneyEvent(type="view", category="Mỹ phẩm"),
    ]
    without_review = await analyze_journey(JourneyRequest(events=base_events))
    with_review = await analyze_journey(
        JourneyRequest(events=[*base_events, JourneyEvent(type="review", category="Mỹ phẩm")])
    )

    assert with_review.purchase_probability > without_review.purchase_probability


@pytest.mark.asyncio
async def test_demo_sessions_flag_cart_abandonment_correctly():
    result = await portfolio.journey_sessions()
    by_id = {s["id"]: s["analysis"]["cart_abandoned"] for s in result["sessions"]}

    # S4 = "bỏ giỏ giữa chừng — nguy cơ rời": cart with nothing after, checked
    # long after the fact — the mentor-requested real abandon signal.
    assert by_id["S4"] is True
    # S1 also ends on "cart" but means "vừa thêm giỏ" (just added) — checked
    # moments later, so it must NOT read as abandoned.
    assert by_id["S1"] is False
    # S3/S6/S9 convert (cart -> purchase) — never abandoned.
    assert by_id["S3"] is False
    assert by_id["S6"] is False
    assert by_id["S9"] is False
    # S8 never adds to cart at all — abandonment doesn't apply.
    assert by_id["S8"] is False


@pytest.mark.asyncio
async def test_prebuilt_sessions_use_fast_deterministic_reasoning(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("prebuilt sessions must not wait for LLM reasoning")

    monkeypatch.setattr("app.services.journey._reason", fail_if_called)
    result = await portfolio.journey_sessions()
    assert result["total"] == 10
    assert all(session["analysis"]["reasoning"] for session in result["sessions"])
