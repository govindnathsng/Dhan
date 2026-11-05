from __future__ import annotations

from pathlib import Path

import pytest

from automator.config import AppConfig, ConfigError, Mode, ceilings, load_config, parse_config_text

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "config.example.yaml"


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AUTOMATOR_CONFIG", raising=False)


def test_default_mode_is_paper() -> None:
    assert AppConfig().mode is Mode.PAPER


def test_no_config_file_uses_paper_defaults() -> None:
    loaded = load_config()
    assert loaded.source is None
    assert loaded.config.mode is Mode.PAPER


def test_empty_file_is_paper() -> None:
    assert parse_config_text("").mode is Mode.PAPER


def test_example_config_is_valid_and_matches_owner_settings() -> None:
    cfg = load_config(EXAMPLE).config
    assert cfg.mode is Mode.PAPER
    assert cfg.capital.live_capital_cap_inr == 50_000
    assert cfg.risk.risk_per_trade_pct == 0.25
    assert cfg.risk.max_daily_loss_pct == 0.5
    assert cfg.risk.max_weekly_loss_pct == 1.5
    assert cfg.risk.max_drawdown_pct == 4
    assert cfg.risk.max_open_positions == 2
    assert cfg.risk.max_position_value_pct == 20
    assert cfg.risk.max_orders_per_day == 10
    assert cfg.timezone == "Asia/Kolkata"
    assert cfg.trading_window == "09:20-15:15"
    assert cfg.live.require_manual_approval is True
    assert cfg.risk_per_trade_inr == pytest.approx(125.0)


def test_example_equals_builtin_defaults() -> None:
    assert load_config(EXAMPLE).config == AppConfig()


def test_explicit_missing_file_is_error_not_fallback() -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config("does-not-exist.yaml")


def test_env_var_missing_file_is_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOMATOR_CONFIG", "nope.yaml")
    with pytest.raises(ConfigError):
        load_config()


@pytest.mark.parametrize(
    "text",
    [
        "mode: Live",
        "mode: LIVE",
        "mode: true",
        "mode: 1",
        "mode: ''",
        "mode: paper-ish",
        "mode: [live]",
    ],
)
def test_ambiguous_mode_is_rejected(text: str) -> None:
    with pytest.raises(ConfigError, match="mode"):
        parse_config_text(text)


def test_duplicate_keys_rejected() -> None:
    with pytest.raises(ConfigError, match="duplicate key 'mode'"):
        parse_config_text("mode: paper\nmode: live\n")


def test_nested_duplicate_keys_rejected() -> None:
    with pytest.raises(ConfigError, match="duplicate key"):
        parse_config_text("risk:\n  risk_per_trade_pct: 0.1\n  risk_per_trade_pct: 0.4\n")


def test_unknown_key_rejected() -> None:
    with pytest.raises(ConfigError, match="risk_per_trade_pc"):
        parse_config_text("risk:\n  risk_per_trade_pc: 0.1\n")


def test_string_number_rejected() -> None:
    with pytest.raises(ConfigError):
        parse_config_text("risk:\n  risk_per_trade_pct: '0.25'\n")


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
        "trading_window: '09:00-15:15'",
        "trading_window: '09:20-15:45'",
        "trading_window: '15:15-09:20'",
        "trading_window: '9:20-15:15'",
        "trading_window: '09:20-25:00'",
    ],
)
def test_time_settings_validated(text: str) -> None:
    with pytest.raises(ConfigError):
        parse_config_text(text)


def test_config_hash_changes_with_content() -> None:
    a = load_config(EXAMPLE).config_hash
    p = Path("c.yaml")
    p.write_text("risk:\n  risk_per_trade_pct: 0.1\n")
    assert load_config(p).config_hash != a


def test_window_times() -> None:
    start, end = AppConfig().window_times
    assert (start.hour, start.minute, end.hour, end.minute) == (9, 20, 15, 15)


@pytest.mark.parametrize("sym", ["<ETF or large-cap symbol 1>", "niftybees", "", "A B"])
def test_whitelist_symbols_validated(sym: str) -> None:
    with pytest.raises(ConfigError, match="whitelist"):
        parse_config_text(f"instruments:\n  whitelist: ['{sym}']\n")


def test_whitelist_empty_and_duplicates_rejected() -> None:
    with pytest.raises(ConfigError):
        parse_config_text("instruments:\n  whitelist: []\n")
    with pytest.raises(ConfigError, match="duplicate"):
        parse_config_text("instruments:\n  whitelist: [NIFTYBEES, NIFTYBEES]\n")


def test_ceilings_are_at_or_above_owner_defaults() -> None:
    d = AppConfig()
    assert d.risk.risk_per_trade_pct <= ceilings.MAX_RISK_PER_TRADE_PCT
    assert d.risk.max_daily_loss_pct <= ceilings.MAX_DAILY_LOSS_PCT
    assert d.risk.max_weekly_loss_pct <= ceilings.MAX_WEEKLY_LOSS_PCT
    assert d.risk.max_drawdown_pct <= ceilings.MAX_DRAWDOWN_PCT
    assert d.risk.max_open_positions <= ceilings.MAX_OPEN_POSITIONS
    assert d.risk.max_position_value_pct <= ceilings.MAX_POSITION_VALUE_PCT
    assert d.risk.max_orders_per_day <= ceilings.MAX_ORDERS_PER_DAY
    assert d.capital.live_capital_cap_inr <= ceilings.MAX_LIVE_CAPITAL_CAP_INR


def test_risk_per_trade_ceiling_is_half_percent() -> None:
    assert ceilings.MAX_RISK_PER_TRADE_PCT == 0.5
