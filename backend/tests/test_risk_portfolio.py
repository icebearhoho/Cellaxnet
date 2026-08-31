"""The customer risk queue.

Churn, return and regret measure different things at different grains — a
customer's future, one order, one purchase's aftertaste — so the screen's job
is to pick the one worth acting on and say what to do, not to show three
percentages side by side as if they added up.
"""

from __future__ import annotations

from app.services import portfolio


def test_regret_alone_never_puts_a_customer_in_the_queue() -> None:
    """Regret scores barely separate anyone, so they cannot lead a row.

    The scorer starts at 0.48 for any impulsive purchase and adds up to 1.7
    more in z, which lands most of the base in the "high" band — letting it
    lead would mark well over half the customers as urgent and rank none of
    them against each other.
    """
    rows = portfolio.risk_portfolio()["customers"]

    assert rows, "the demo store should produce customers"
    assert all(r["lead_kind"] in {"churn", "return"} for r in rows)


def test_every_flagged_row_says_what_to_do() -> None:
    """A queue that names a risk without an action is a list, not a queue."""
    rows = portfolio.risk_portfolio()["customers"]
    flagged = [r for r in rows if r["lead_band"] in {"high", "medium"}]

    assert flagged, "some demo customers should need attention"
    for row in flagged:
        assert row["lead_reason"], f"{row['customer']} has no reason"
        assert row["lead_action"], f"{row['customer']} has no action"


def test_the_queue_is_ordered_by_money_not_by_score() -> None:
    """A 0.62 risk on a 4.7M customer outranks a 0.66 on a 330k one."""
    rows = portfolio.risk_portfolio()["customers"]
    stakes = [r["value_at_stake_vnd"] for r in rows]

    assert stakes == sorted(stakes, reverse=True)


def test_churn_risks_the_relationship_return_risks_one_order() -> None:
    """What is at stake differs by risk, so the amounts must be derived
    differently: losing the customer costs their lifetime value, a return
    costs that order."""
    rows = portfolio.risk_portfolio()["customers"]

    for row in rows:
        if row["lead_kind"] == "churn" and row["lead_risk"]:
            expected = round(row["lifetime_value_vnd"] * row["lead_risk"])
            assert row["value_at_stake_vnd"] == expected
            assert row["value_at_stake_vnd"] <= row["lifetime_value_vnd"]


def test_the_urgent_count_is_a_believable_share_of_the_base() -> None:
    """Sixty-two percent of customers about to leave would mean the shop is
    already dead. The count that drives the header has to be a share a seller
    can actually work through."""
    data = portfolio.risk_portfolio()

    share = data["needs_action_count"] / data["total"]
    assert 0 <= share < 0.25


def test_the_headline_total_is_the_sum_of_the_rows() -> None:
    """The number at the top has to reconcile with the list under it."""
    data = portfolio.risk_portfolio()

    assert data["total_at_stake_vnd"] == sum(
        r["value_at_stake_vnd"] for r in data["customers"]
    )
    assert data["total"] == len(data["customers"])


def test_advice_is_written_in_the_language_of_the_ui() -> None:
    """The panel is Vietnamese; an English action would be dead text there."""
    rows = portfolio.risk_portfolio()["customers"]
    actions = {r["lead_action"] for r in rows if r["lead_action"]}

    assert actions
    for action in actions:
        assert not any(
            word in action for word in ("Send", "Nurture", "Proactively", "Include")
        ), action


def test_every_customer_lands_in_exactly_one_group() -> None:
    data = portfolio.risk_portfolio()
    counts = {g["key"]: g["count"] for g in data["groups"]}

    assert sum(counts.values()) == data["total"]
    assert all(r.get("group_key") in counts for r in data["customers"])


def test_each_band_carries_one_suggested_action() -> None:
    """The header shows a single instruction per band, so one must exist.

    Severity is not a statement about work — the medium band mixes customers
    drifting away with orders likely to come back — so this only holds that an
    action is present and named, not that it suits every member.
    """
    groups = portfolio.risk_portfolio()["groups"]

    assert len(groups) == 3
    for group in groups:
        assert group["action"], group["label"]
        assert group["label"]


def test_the_urgent_band_is_the_smallest_one() -> None:
    """A queue where everything is urgent is not a queue."""
    data = portfolio.risk_portfolio()
    urgent = next(g for g in data["groups"] if g["key"] == "high")

    assert 0 < urgent["count"] < data["total"] * 0.1


def test_group_stakes_add_up_to_the_headline() -> None:
    data = portfolio.risk_portfolio()

    assert sum(g["value_at_stake_vnd"] for g in data["groups"]) == data["total_at_stake_vnd"]
