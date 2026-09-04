"""Regression checks for migration histories deployed before the branch merge."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_legacy_marketplace_stamp_can_reach_the_current_head() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("path_separator", "os")
    scripts = ScriptDirectory.from_config(config)

    legacy = scripts.get_revision("0012_marketplace_connections")
    merge = scripts.get_revision("0013_merge_marketplace_heads")
    head = scripts.get_current_head()

    assert legacy is not None
    assert legacy.down_revision == (
        "0011_seller_autopilot",
        "0005_marketplace_connections",
    )
    assert merge is not None
    assert merge.down_revision == (
        "0012_marketplace_connections",
        "0012_voucher_booster",
    )
    assert head is not None
    assert {
        revision.revision for revision in scripts.iterate_revisions(head, "base")
    } >= {
        "0012_marketplace_connections",
        "0012_voucher_booster",
        "0013_merge_marketplace_heads",
    }
