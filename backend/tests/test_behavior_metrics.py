"""Pure unit tests for real timing metrics derived from event timestamps."""

from __future__ import annotations

from app.schemas.journey import JourneyEvent
from app.services.behavior_metrics import (
    avg_dwell_seconds,
    cart_abandoned,
    session_duration_seconds,
    time_to_purchase_seconds,
)


def _ev(type_: str, ts: int | None) -> JourneyEvent:
    return JourneyEvent(type=type_, ts=ts)  # type: ignore[arg-type]


def test_all_metrics_are_none_without_any_timestamps():
    events = [_ev("view", None), _ev("cart", None)]
    assert session_duration_seconds(events) is None
    assert avg_dwell_seconds(events) is None
    assert time_to_purchase_seconds(events) is None
    assert cart_abandoned(events) is None


def test_session_duration_and_avg_dwell_from_deltas():
    events = [_ev("view", 0), _ev("click", 5_000), _ev("cart", 15_000)]
    assert session_duration_seconds(events) == 15.0
    assert avg_dwell_seconds(events) == 7.5  # mean of (5s, 10s)


def test_time_to_purchase_from_first_event_to_purchase():
    events = [_ev("view", 0), _ev("cart", 5_000), _ev("purchase", 20_000)]
    assert time_to_purchase_seconds(events) == 20.0


def test_time_to_purchase_is_none_without_a_purchase_event():
    events = [_ev("view", 0), _ev("cart", 5_000)]
    assert time_to_purchase_seconds(events) is None


def test_cart_abandoned_false_when_no_cart_event():
    assert cart_abandoned([_ev("view", 0)]) is False


def test_cart_abandoned_false_when_purchase_follows_cart():
    events = [_ev("cart", 0), _ev("purchase", 5_000)]
    assert cart_abandoned(events) is False


def test_cart_abandoned_true_when_cart_is_last_and_no_now_given():
    events = [_ev("view", 0), _ev("cart", 10_000)]
    assert cart_abandoned(events) is True


def test_cart_abandoned_uses_now_ms_when_cart_is_last_event():
    events = [_ev("view", 0), _ev("cart", 10_000)]
    # Checked moments after the cart action — not enough silence yet.
    assert cart_abandoned(events, now_ms=10_500) is False
    # Checked long after — the cart went quiet.
    assert cart_abandoned(events, now_ms=10_000 + 400_000) is True


def test_cart_abandoned_false_when_browsing_continues_shortly_after_cart():
    events = [_ev("cart", 0), _ev("view", 5_000)]
    assert cart_abandoned(events) is False


def test_cart_abandoned_true_when_gap_after_cart_exceeds_window():
    events = [_ev("cart", 0), _ev("view", 400_000)]
    assert cart_abandoned(events) is True
