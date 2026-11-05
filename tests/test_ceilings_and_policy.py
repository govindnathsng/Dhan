from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from automator.config import ConfigError, ceilings, parse_config_text


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("risk_per_trade_pct", 0.51),
        ("risk_per_trade_pct", 5),
        ("max_daily_loss_pct", 1.01),
        ("max_weekly_loss_pct", 3.5),
        ("max_drawdown_pct", 9),
        ("max_open_positions", 5),
        ("max_position_value_pct", 41),
        ("max_orders_per_day", 21),
        ("price_band_pct", 1.5),
    ],
)
def test_values_above_hard_ceiling_are_rejected(key: str, value: float) -> None:
    with pytest.raises(ConfigError, match=key):
        parse_config_text(f"risk:\n  {key}: {value}\n")


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("risk_per_trade_pct", 0),
        ("risk_per_trade_pct", -0.1),
        ("max_daily_loss_pct", 0),
        ("max_open_positions", 0),
        ("max_orders_per_day", 0),
    ],
)
def test_non_positive_limits_rejected(key: str, value: float) -> None:
    with pytest.raises(ConfigError):
        parse_config_text(f"risk:\n  {key}: {value}\n")


def test_capital_cap_ceiling() -> None:
    with pytest.raises(ConfigError, match="live_capital_cap_inr"):
        parse_config_text("capital:\n  live_capital_cap_inr: 100001\n")
    with pytest.raises(ConfigError):
        parse_config_text("capital:\n  live_capital_cap_inr: 0\n")


def test_risk_limits_must_be_ordered() -> None:
    with pytest.raises(ConfigError, match="max_daily_loss_pct"):
        parse_config_text("risk:\n  risk_per_trade_pct: 0.5\n  max_daily_loss_pct: 0.4\n")


@given(st.floats(min_value=0.5000001, max_value=1e9, allow_nan=False))
def test_any_risk_per_trade_above_ceiling_rejected(value: float) -> None:
    with pytest.raises(ConfigError):
        parse_config_text(f"risk:\n  risk_per_trade_pct: {value!r}\n")


@pytest.mark.parametrize("product", sorted(ceilings.FORBIDDEN_PRODUCT_TYPES))
def test_forbidden_product_types_rejected(product: str) -> None:
    with pytest.raises(ConfigError, match="product type"):
        parse_config_text(f"orders:\n  allowed_product_types: [CNC, {product}]\n")


@pytest.mark.parametrize("otype", sorted(ceilings.FORBIDDEN_ORDER_TYPES))
def test_market_orders_rejected(otype: str) -> None:
    with pytest.raises(ConfigError, match="order type"):
        parse_config_text(f"orders:\n  allowed_order_types: [{otype}]\n")


@pytest.mark.parametrize("seg", ["NSE_FNO", "BSE_EQ", "MCX_COMM", "NSE_CURRENCY"])
def test_non_cash_segments_rejected(seg: str) -> None:
    with pytest.raises(ConfigError, match="exchange_segment"):
        parse_config_text(f"orders:\n  exchange_segment: {seg}\n")


def test_shorting_cannot_be_enabled() -> None:
    with pytest.raises(ConfigError):
        parse_config_text("orders:\n  allow_short: true\n")


def test_stop_loss_cannot_be_disabled() -> None:
    with pytest.raises(ConfigError):
        parse_config_text("orders:\n  require_stop_loss: false\n")


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
