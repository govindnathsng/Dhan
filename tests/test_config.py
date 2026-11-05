from __future__ import annotations

from pathlib import Path

import pytest

from automator.config import (
    AppConfig,
    ConfigError,
    Mode,
    ProfileKind,
    load_config,
    parse_config_text,
)
from tests.conftest import EXAMPLE_CONFIG


def test_default_mode_is_paper() -> None:
    cfg = AppConfig()
    assert cfg.mode is Mode.PAPER
    assert cfg.profile == "paper"
    assert cfg.active_profile.kind is ProfileKind.PAPER


def test_no_config_file_uses_paper_defaults(workdir: Path) -> None:
    loaded = load_config()
    assert loaded.source is None
    assert loaded.config.mode is Mode.PAPER


def test_empty_file_is_paper() -> None:
    assert parse_config_text("").mode is Mode.PAPER


def test_example_config_matches_owner_settings() -> None:
    cfg = load_config(EXAMPLE_CONFIG).config
    assert cfg.mode is Mode.PAPER
    assert cfg.entry_window == "09:30-14:30"
    paper = cfg.profiles["paper"]
    assert (paper.capital_inr, paper.risk_per_trade_inr, paper.max_daily_loss_inr) == (
        50_000,
        125,
        250,
    )
    assert (paper.max_weekly_loss_inr, paper.max_drawdown_halt_inr) == (750, 2000)
    assert (paper.max_open_positions, paper.max_position_value_inr) == (2, 10_000)
    assert (paper.max_total_invested_inr, paper.max_new_entries_per_week) == (20_000, 3)
    assert (paper.max_orders_per_day, paper.max_proposals_per_day) == (6, 3)
    canary = cfg.profiles["live_canary"]
    assert canary.kind is ProfileKind.LIVE
    assert (canary.capital_inr, canary.risk_per_trade_inr, canary.max_daily_loss_inr) == (
        25_000,
        60,
        125,
    )
    assert (canary.max_weekly_loss_inr, canary.max_drawdown_halt_inr) == (375, 1000)
    assert (canary.max_open_positions, canary.max_position_value_inr) == (1, 5000)
    assert (canary.max_total_invested_inr, canary.max_new_entries_per_week) == (5000, 2)
    assert (canary.max_orders_per_day, canary.max_proposals_per_day) == (4, 3)
    r = cfg.rules
    assert r.entry_price_band_pct == 0.75
    assert (r.stop_distance_min_pct, r.stop_distance_max_pct, r.stop_min_atr_multiple) == (
        1.0,
        6.0,
        0.75,
    )
    assert r.min_net_reward_to_risk == 1.5
    assert r.reentry_cooldown_days == 5
    assert (r.losing_streak_losses, r.losing_streak_pause_trading_days) == (3, 2)
    assert r.min_confidence == 0.6
    assert cfg.approval.paper_mode == "auto"


def test_example_equals_builtin_defaults() -> None:
    assert load_config(EXAMPLE_CONFIG).config == AppConfig()


def test_explicit_missing_file_is_error_not_fallback() -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config("does-not-exist.yaml")


def test_env_var_missing_file_is_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOMATOR_CONFIG", "nope.yaml")
    with pytest.raises(ConfigError):
        load_config()


def test_missing_whitelist_refuses(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="whitelist file not found"):
        load_config()


@pytest.mark.parametrize(
    "text",
    ["mode: Live", "mode: LIVE", "mode: true", "mode: 1", "mode: ''", "mode: [live]"],
)
def test_ambiguous_mode_is_rejected(text: str) -> None:
    with pytest.raises(ConfigError, match="mode"):
        parse_config_text(text)


def test_live_mode_with_paper_profile_rejected() -> None:
    with pytest.raises(ConfigError, match="kind 'live'"):
        parse_config_text("mode: live\nprofile: paper\n")


def test_unknown_profile_rejected() -> None:
    with pytest.raises(ConfigError, match="not defined"):
        parse_config_text("profile: aggressive\n")


def test_paper_mode_may_practise_with_canary_profile() -> None:
    cfg = parse_config_text("profile: live_canary\n")
    assert cfg.mode is Mode.PAPER
    assert cfg.active_profile.capital_inr == 25_000


def test_duplicate_keys_rejected() -> None:
    with pytest.raises(ConfigError, match="duplicate key 'mode'"):
        parse_config_text("mode: paper\nmode: live\n")


def test_nested_duplicate_keys_rejected() -> None:
    with pytest.raises(ConfigError, match="duplicate key"):
        parse_config_text("rules:\n  min_confidence: 0.7\n  min_confidence: 0.5\n")


def test_unknown_key_rejected() -> None:
    with pytest.raises(ConfigError, match="min_confidenc"):
        parse_config_text("rules:\n  min_confidenc: 0.7\n")


def test_string_number_rejected() -> None:
    with pytest.raises(ConfigError):
        parse_config_text("rules:\n  min_confidence: '0.7'\n")


def test_invalid_yaml_rejected() -> None:
    with pytest.raises(ConfigError, match="YAML"):
        parse_config_text("mode: [paper\n")


def test_non_mapping_root_rejected() -> None:
    with pytest.raises(ConfigError, match="mapping"):
        parse_config_text("- paper\n")


def test_yaml_python_tags_rejected() -> None:
    with pytest.raises(ConfigError):
        parse_config_text("mode: !!python/object/apply:os.system ['echo hi']\n")


@pytest.mark.parametrize(
    "text",
    [
        "timezone: UTC",
        "entry_window: '09:00-14:30'",
        "entry_window: '09:30-15:45'",
        "entry_window: '14:30-09:30'",
        "entry_window: '9:30-14:30'",
        "entry_window: '09:30-25:00'",
        "approval:\n  latest_approval_time: '15:01'",
        "approval:\n  latest_approval_time: '3pm'",
    ],
)
def test_time_settings_validated(text: str) -> None:
    with pytest.raises(ConfigError):
        parse_config_text(text)


def test_config_hash_changes_with_content(workdir: Path) -> None:
    a = load_config().config_hash
    p = workdir / "c.yaml"
    p.write_text("rules:\n  min_confidence: 0.7\n")
    assert load_config(p).config_hash != a


def test_config_hash_covers_whitelist(workdir: Path) -> None:
    a = load_config().config_hash
    (workdir / "config" / "whitelist.yaml").write_text(
        "version: 1\ninstruments:\n  - {symbol: NIFTYBEES, kind: ETF}\n"
    )
    assert load_config().config_hash != a


def test_window_times() -> None:
    start, end = AppConfig().window_times
    assert (start.hour, start.minute, end.hour, end.minute) == (9, 30, 14, 30)


def test_blackout_entry_validated(workdir: Path) -> None:
    good = workdir / "good.yaml"
    good.write_text(
        "instruments:\n  blackout:\n"
        "    - {symbol: INFY, start: 2026-11-10, end: 2026-11-12, reason: results}\n"
    )
    assert len(load_config(good).config.instruments.blackout) == 1

    unknown = workdir / "unknown.yaml"
    unknown.write_text(
        "instruments:\n  blackout:\n"
        "    - {symbol: NOTLISTED, start: 2026-11-10, end: 2026-11-12, reason: x}\n"
    )
    with pytest.raises(ConfigError, match="not in the whitelist"):
        load_config(unknown)

    with pytest.raises(ConfigError, match="end must not be before start"):
        parse_config_text(
            "instruments:\n  blackout:\n"
            "    - {symbol: INFY, start: 2026-11-12, end: 2026-11-10, reason: x}\n"
        )
