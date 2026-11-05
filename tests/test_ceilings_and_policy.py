from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from automator.config import ConfigError, parse_config_text
from automator.config import ceilings as C
from automator.config.models import DEFAULT_PROFILES

PAPER = DEFAULT_PROFILES["paper"].model_dump(mode="json")
CANARY = DEFAULT_PROFILES["live_canary"].model_dump(mode="json")


def _profile_yaml(name: str, base: dict[str, object], **overrides: object) -> str:
    fields = {**base, **overrides}
    body = "\n".join(f"    {k}: {v}" for k, v in fields.items())
    return f"profile: {name}\nprofiles:\n  {name}:\n{body}\n"


def test_owner_ceilings_for_risk_per_trade_are_250_and_125() -> None:
    assert DEFAULT_PROFILES["paper"].ceiling_inr("risk_per_trade_inr") == 250
    assert DEFAULT_PROFILES["live_canary"].ceiling_inr("risk_per_trade_inr") == 125


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("risk_per_trade_inr", 251),
        ("max_daily_loss_inr", 501),
        ("max_weekly_loss_inr", 1501),
        ("max_drawdown_halt_inr", 4001),
        ("max_position_value_inr", 20_001),
        ("max_total_invested_inr", 40_001),
        ("max_open_positions", 5),
        ("max_new_entries_per_week", 6),
        ("max_orders_per_day", 11),
        ("max_proposals_per_day", 6),
        ("capital_inr", 50_001),
    ],
)
def test_paper_profile_values_above_ceiling_rejected(field: str, value: float) -> None:
    with pytest.raises(ConfigError, match=field):
        parse_config_text(_profile_yaml("paper", PAPER, **{field: value}))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("risk_per_trade_inr", 126),
        ("max_daily_loss_inr", 251),
        ("max_position_value_inr", 10_001),
    ],
)
def test_canary_ceilings_scale_with_capital(field: str, value: float) -> None:
    with pytest.raises(ConfigError, match=field):
        parse_config_text(_profile_yaml("live_canary", CANARY, **{field: value}))


def test_values_at_ceiling_accepted() -> None:
    cfg = parse_config_text(_profile_yaml("paper", PAPER, risk_per_trade_inr=250))
    assert cfg.active_profile.risk_per_trade_inr == 250


@pytest.mark.parametrize(
    ("field", "value"),
    [("risk_per_trade_inr", 0), ("max_daily_loss_inr", -1), ("max_open_positions", 0)],
)
def test_non_positive_limits_rejected(field: str, value: float) -> None:
    with pytest.raises(ConfigError):
        parse_config_text(_profile_yaml("paper", PAPER, **{field: value}))


def test_loss_limits_must_be_ordered() -> None:
    with pytest.raises(ConfigError, match="max_daily_loss_inr must not exceed"):
        parse_config_text(_profile_yaml("paper", PAPER, max_weekly_loss_inr=200))


def test_position_value_not_above_total_invested() -> None:
    with pytest.raises(ConfigError, match="max_position_value_inr"):
        parse_config_text(_profile_yaml("paper", PAPER, max_total_invested_inr=5000))


def test_profile_missing_field_rejected() -> None:
    base = {k: v for k, v in PAPER.items() if k != "max_daily_loss_inr"}
    with pytest.raises(ConfigError, match="max_daily_loss_inr"):
        parse_config_text(_profile_yaml("paper", base))


@pytest.mark.parametrize("kind", ["Live", "LIVE", "true", "real"])
def test_profile_kind_exact(kind: str) -> None:
    with pytest.raises(ConfigError, match="kind"):
        parse_config_text(_profile_yaml("paper", PAPER, kind=kind))


@given(st.floats(min_value=250.0001, max_value=1e9, allow_nan=False))
def test_any_risk_per_trade_above_ceiling_rejected(value: float) -> None:
    with pytest.raises(ConfigError):
        parse_config_text(_profile_yaml("paper", PAPER, risk_per_trade_inr=repr(value)))


@given(
    capital=st.floats(min_value=1000, max_value=C.MAX_PROFILE_CAPITAL_INR),
    frac=st.floats(min_value=0.0, max_value=1.0),
)
def test_accepted_risk_never_exceeds_half_percent(capital: float, frac: float) -> None:
    risk = max(0.01, capital * frac / 100.0)
    fields = {
        **PAPER,
        "capital_inr": repr(capital),
        "risk_per_trade_inr": repr(risk),
        "max_daily_loss_inr": repr(risk),
        "max_weekly_loss_inr": repr(risk),
        "max_drawdown_halt_inr": repr(risk),
        "max_position_value_inr": repr(capital * 0.1),
        "max_total_invested_inr": repr(capital * 0.2),
    }
    try:
        cfg = parse_config_text(_profile_yaml("paper", fields))
    except ConfigError:
        return
    p = cfg.active_profile
    assert p.risk_per_trade_inr <= p.capital_inr * C.MAX_RISK_PER_TRADE_PCT / 100 + 1e-6


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("entry_price_band_pct", 1.01),
        ("stop_distance_min_pct", 0.99),
        ("stop_distance_max_pct", 6.01),
        ("stop_min_atr_multiple", 0.74),
        ("min_net_reward_to_risk", 1.49),
        ("reentry_cooldown_days", 4),
        ("losing_streak_losses", 4),
        ("losing_streak_pause_trading_days", 1),
        ("losing_streak_requires_review_note", "false"),
        ("min_confidence", 0.49),
        ("min_confidence", 1.01),
        ("atr_period", 10),
    ],
)
def test_protective_rules_cannot_be_loosened(key: str, value: object) -> None:
    with pytest.raises(ConfigError, match=key):
        parse_config_text(f"rules:\n  {key}: {value}\n")


def test_protective_rules_can_be_tightened() -> None:
    cfg = parse_config_text(
        "rules:\n  min_net_reward_to_risk: 2.0\n  reentry_cooldown_days: 10\n"
        "  stop_distance_min_pct: 1.5\n  losing_streak_losses: 2\n"
    )
    assert cfg.rules.min_net_reward_to_risk == 2.0


def test_stop_range_must_be_ordered() -> None:
    with pytest.raises(ConfigError):
        parse_config_text("rules:\n  stop_distance_min_pct: 5\n  stop_distance_max_pct: 4\n")


@pytest.mark.parametrize("product", sorted(C.FORBIDDEN_PRODUCT_TYPES))
def test_forbidden_product_types_rejected(product: str) -> None:
    with pytest.raises(ConfigError, match="product type"):
        parse_config_text(f"orders:\n  allowed_product_types: [CNC, {product}]\n")


@pytest.mark.parametrize("otype", sorted(C.FORBIDDEN_ORDER_TYPES))
def test_market_orders_rejected(otype: str) -> None:
    with pytest.raises(ConfigError, match="order type"):
        parse_config_text(f"orders:\n  allowed_order_types: [{otype}]\n")


@pytest.mark.parametrize("seg", sorted(C.FORBIDDEN_SEGMENTS))
def test_non_cash_segments_rejected(seg: str) -> None:
    with pytest.raises(ConfigError, match="exchange_segment"):
        parse_config_text(f"orders:\n  exchange_segment: {seg}\n")


def test_shorting_cannot_be_enabled() -> None:
    with pytest.raises(ConfigError):
        parse_config_text("orders:\n  allow_short: true\n")


def test_protective_stop_cannot_be_disabled() -> None:
    with pytest.raises(ConfigError):
        parse_config_text("orders:\n  require_protective_stop: false\n")


@pytest.mark.parametrize(
    "text",
    [
        "approval:\n  live_mode: auto",
        "approval:\n  paper_mode: none",
        "approval:\n  expiry_minutes: 121",
        "approval:\n  auto_approve_live: true",
    ],
)
def test_no_way_to_configure_live_auto_approval(text: str) -> None:
    with pytest.raises(ConfigError):
        parse_config_text(text)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("orders_per_second", 11),
        ("orders_per_minute", 251),
        ("orders_per_day", 7001),
        ("modifications_per_order", 26),
        ("data_requests_per_second", 6),
        ("quote_requests_per_second", 2),
        ("feed_max_connections", 6),
    ],
)
def test_rate_limits_cannot_exceed_broker_limits(key: str, value: int) -> None:
    with pytest.raises(ConfigError, match=key):
        parse_config_text(f"rate_limits:\n  {key}: {value}\n")
