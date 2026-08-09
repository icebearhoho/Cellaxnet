"""Real timing metrics derived from a session's event timestamps — dwell time,
cart-abandon, checkout timing (mentor feedback: predictions need actual
behaviour data, not just event-type counts).

Pure functions, no DB/I-O: every value is ``None`` whenever the events carry
no ``ts`` at all, so callers degrade gracefully instead of faking a number.
"""

from __future__ import annotations

from app.schemas.journey import JourneyEvent

# A cart with nothing after it for this long (and no purchase) counts as
# abandoned. Short enough that a closed demo/replay session (no further
# events at all) reads as abandoned immediately.
DEFAULT_ABANDON_WINDOW_SECONDS = 300


def _sorted_ts(events: list[JourneyEvent]) -> list[tuple[JourneyEvent, int]]:
    timed = [(e, e.ts) for e in events if e.ts is not None]
    timed.sort(key=lambda pair: pair[1])
    return timed  # type: ignore[return-value]


def session_duration_seconds(events: list[JourneyEvent]) -> float | None:
    timed = _sorted_ts(events)
    if len(timed) < 2:
        return None
    return round((timed[-1][1] - timed[0][1]) / 1000, 1)


def avg_dwell_seconds(events: list[JourneyEvent]) -> float | None:
    """Mean gap between consecutive actions — the "time on page" signal in
    the absence of an explicit page-leave beacon."""
    timed = _sorted_ts(events)
    if len(timed) < 2:
        return None
    deltas = [(timed[i + 1][1] - timed[i][1]) / 1000 for i in range(len(timed) - 1)]
    return round(sum(deltas) / len(deltas), 1)


def time_to_purchase_seconds(events: list[JourneyEvent]) -> float | None:
    timed = _sorted_ts(events)
    if not timed:
        return None
    purchase_ts = next((t for e, t in timed if e.type == "purchase"), None)
    if purchase_ts is None:
        return None
    return round((purchase_ts - timed[0][1]) / 1000, 1)


def cart_abandoned(
    events: list[JourneyEvent],
    *,
    window_seconds: int = DEFAULT_ABANDON_WINDOW_SECONDS,
    now_ms: int | None = None,
) -> bool | None:
    """A cart event with no purchase after it, once enough time has passed
    with nothing following it — ``None`` if there's no timing data at all."""
    timed = _sorted_ts(events)
    if not timed:
        return None
    cart_events = [(e, t) for e, t in timed if e.type == "cart"]
    if not cart_events:
        return False

    last_cart_ts = max(t for _, t in cart_events)
    if any(e.type == "purchase" and t >= last_cart_ts for e, t in timed):
        return False  # converted after (or at) the last cart action

    events_after_cart = [t for _, t in timed if t > last_cart_ts]
    if events_after_cart:
        gap = max(events_after_cart) - last_cart_ts
        return gap >= window_seconds * 1000

    # Cart is the most recent recorded action.
    if now_ms is not None:
        return (now_ms - last_cart_ts) >= window_seconds * 1000
    return True  # closed/static session (e.g. a demo replay) ending on "cart"
