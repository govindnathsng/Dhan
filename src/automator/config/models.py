"""Validated configuration schema.

Every model forbids unknown keys and uses strict types, so a typo or an
ambiguous value makes the config invalid instead of silently using a default.
"""

from __future__ import annotations

import re
from datetime import time
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from automator.config import ceilings


class Mode(StrEnum):
    PAPER = "paper"
    SANDBOX = "sandbox"
    LIVE = "live"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9&\-]{0,29}$")
_WINDOW_RE = re.compile(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$")


def _parse_hhmm(value: str) -> time:
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


class CapitalConfig(_Strict):
    live_capital_cap_inr: float = Field(default=50_000.0, gt=0)

    @field_validator("live_capital_cap_inr")
    @classmethod
    def _cap_ceiling(cls, v: float) -> float:
        if v > ceilings.MAX_LIVE_CAPITAL_CAP_INR:
            raise ValueError(
                f"live_capital_cap_inr={v} exceeds hard ceiling {ceilings.MAX_LIVE_CAPITAL_CAP_INR}"
            )
        return v


def _pct_ceiling(name: str, value: float, ceiling: float) -> float:
    if value > ceiling:
        raise ValueError(f"{name}={value} exceeds hard ceiling {ceiling}")
    return value


class RiskConfig(_Strict):
    risk_per_trade_pct: float = Field(default=0.25, gt=0)
    max_daily_loss_pct: float = Field(default=0.5, gt=0)
    max_weekly_loss_pct: float = Field(default=1.5, gt=0)
    max_drawdown_pct: float = Field(default=4.0, gt=0)
    max_open_positions: int = Field(default=2, ge=1)
    max_position_value_pct: float = Field(default=20.0, gt=0)
    max_orders_per_day: int = Field(default=10, ge=1)
    price_band_pct: float = Field(default=0.5, gt=0)
    stale_data_seconds: int = Field(default=60, ge=1, le=600)
    max_consecutive_errors: int = Field(default=3, ge=1, le=10)

    @field_validator("risk_per_trade_pct")
    @classmethod
    def _c_risk(cls, v: float) -> float:
        return _pct_ceiling("risk_per_trade_pct", v, ceilings.MAX_RISK_PER_TRADE_PCT)

    @field_validator("max_daily_loss_pct")
    @classmethod
    def _c_daily(cls, v: float) -> float:
        return _pct_ceiling("max_daily_loss_pct", v, ceilings.MAX_DAILY_LOSS_PCT)

    @field_validator("max_weekly_loss_pct")
    @classmethod
    def _c_weekly(cls, v: float) -> float:
        return _pct_ceiling("max_weekly_loss_pct", v, ceilings.MAX_WEEKLY_LOSS_PCT)

    @field_validator("max_drawdown_pct")
    @classmethod
    def _c_dd(cls, v: float) -> float:
        return _pct_ceiling("max_drawdown_pct", v, ceilings.MAX_DRAWDOWN_PCT)

    @field_validator("max_position_value_pct")
    @classmethod
    def _c_posval(cls, v: float) -> float:
        return _pct_ceiling("max_position_value_pct", v, ceilings.MAX_POSITION_VALUE_PCT)

    @field_validator("price_band_pct")
    @classmethod
    def _c_band(cls, v: float) -> float:
        return _pct_ceiling("price_band_pct", v, ceilings.MAX_PRICE_BAND_PCT)

    @field_validator("max_open_positions")
    @classmethod
    def _c_open(cls, v: int) -> int:
        if v > ceilings.MAX_OPEN_POSITIONS:
            raise ValueError(
                f"max_open_positions={v} exceeds hard ceiling {ceilings.MAX_OPEN_POSITIONS}"
            )
        return v

    @field_validator("max_orders_per_day")
    @classmethod
    def _c_orders(cls, v: int) -> int:
        if v > ceilings.MAX_ORDERS_PER_DAY:
            raise ValueError(
                f"max_orders_per_day={v} exceeds hard ceiling {ceilings.MAX_ORDERS_PER_DAY}"
            )
        return v

    @model_validator(mode="after")
    def _consistent(self) -> RiskConfig:
        if self.risk_per_trade_pct > self.max_daily_loss_pct:
            raise ValueError("risk_per_trade_pct must not exceed max_daily_loss_pct")
        if self.max_daily_loss_pct > self.max_weekly_loss_pct:
            raise ValueError("max_daily_loss_pct must not exceed max_weekly_loss_pct")
        if self.max_weekly_loss_pct > self.max_drawdown_pct:
            raise ValueError("max_weekly_loss_pct must not exceed max_drawdown_pct")
        return self


class OrderPolicyConfig(_Strict):
    """v1 order policy. Anything other than CNC / LIMIT / long-only is invalid."""

    exchange_segment: str = "NSE_EQ"
    allowed_product_types: tuple[str, ...] = ("CNC",)
    allowed_order_types: tuple[str, ...] = ("LIMIT",)
    allow_short: Literal[False] = False
    require_stop_loss: Literal[True] = True

    @field_validator("exchange_segment")
    @classmethod
    def _segment(cls, v: str) -> str:
        if v not in ceilings.ALLOWED_EXCHANGE_SEGMENTS:
            raise ValueError(f"exchange_segment {v!r} not allowed in v1 (only NSE_EQ)")
        return v

    @field_validator("allowed_product_types", mode="before")
    @classmethod
    def _products(cls, v: object) -> object:
        return _check_subset(v, ceilings.ALLOWED_PRODUCT_TYPES, "product type")

    @field_validator("allowed_order_types", mode="before")
    @classmethod
    def _orders(cls, v: object) -> object:
        return _check_subset(v, ceilings.ALLOWED_ORDER_TYPES, "order type")


def _check_subset(v: object, allowed: frozenset[str], label: str) -> tuple[str, ...]:
    if not isinstance(v, list | tuple) or not v:
        raise ValueError(f"allowed {label}s must be a non-empty list")
    items = tuple(v)
    for item in items:
        if not isinstance(item, str) or item not in allowed:
            raise ValueError(f"{label} {item!r} is not allowed in v1 (allowed: {sorted(allowed)})")
    return items


class InstrumentsConfig(_Strict):
    whitelist: tuple[str, ...] = Field(default=("NIFTYBEES", "JUNIORBEES"), min_length=1)

    @field_validator("whitelist", mode="before")
    @classmethod
    def _symbols(cls, v: object) -> object:
        if not isinstance(v, list | tuple):
            raise ValueError("whitelist must be a list of NSE symbols")
        seen: set[str] = set()
        for s in v:
            if not isinstance(s, str) or not _SYMBOL_RE.match(s):
                raise ValueError(f"invalid NSE symbol in whitelist: {s!r}")
            if s in seen:
                raise ValueError(f"duplicate symbol in whitelist: {s}")
            seen.add(s)
        return tuple(v)


class RateLimitConfig(_Strict):
    """Our own budget. Each value must be <= the broker-documented limit."""

    orders_per_second: int = Field(default=2, ge=1)
    orders_per_minute: int = Field(default=20, ge=1)
    orders_per_hour: int = Field(default=100, ge=1)
    orders_per_day: int = Field(default=200, ge=1)
    modifications_per_order: int = Field(default=10, ge=1)
    data_requests_per_second: int = Field(default=2, ge=1)
    data_requests_per_day: int = Field(default=10_000, ge=1)
    quote_requests_per_second: int = Field(default=1, ge=1)
    feed_max_connections: int = Field(default=1, ge=1)
    feed_max_instruments_per_connection: int = Field(default=100, ge=1)

    @model_validator(mode="after")
    def _within_broker_limits(self) -> RateLimitConfig:
        pairs = {
            "orders_per_second": ceilings.DHAN_ORDERS_PER_SECOND,
            "orders_per_minute": ceilings.DHAN_ORDERS_PER_MINUTE,
            "orders_per_hour": ceilings.DHAN_ORDERS_PER_HOUR,
            "orders_per_day": ceilings.DHAN_ORDERS_PER_DAY,
            "modifications_per_order": ceilings.DHAN_MODIFICATIONS_PER_ORDER,
            "data_requests_per_second": ceilings.DHAN_DATA_REQUESTS_PER_SECOND,
            "data_requests_per_day": ceilings.DHAN_DATA_REQUESTS_PER_DAY,
            "quote_requests_per_second": ceilings.DHAN_QUOTE_REQUESTS_PER_SECOND,
            "feed_max_connections": ceilings.DHAN_FEED_MAX_CONNECTIONS,
            "feed_max_instruments_per_connection": (
                ceilings.DHAN_FEED_MAX_INSTRUMENTS_PER_CONNECTION
            ),
        }
        for name, limit in pairs.items():
            if getattr(self, name) > limit:
                raise ValueError(f"rate_limits.{name} exceeds Dhan documented limit {limit}")
        return self


class LiveConfig(_Strict):
    require_manual_approval: bool = True
    min_paper_trading_days: int = Field(default=42, ge=1)


class PathsConfig(_Strict):
    state_dir: Path = Path("state")
    data_dir: Path = Path("data")
    reports_dir: Path = Path("reports")
    kill_file: Path = Path("state/KILL")
    lock_file: Path = Path("state/automator.lock")
    journal_db: Path = Path("state/journal.sqlite3")

    @field_validator("*", mode="before")
    @classmethod
    def _to_path(cls, v: object) -> object:
        return Path(v) if isinstance(v, str) else v


class LoggingConfig(_Strict):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    json_format: bool = True


class AppConfig(_Strict):
    mode: Mode = Mode.PAPER
    timezone: str = ceilings.ALLOWED_TIMEZONE
    trading_window: str = "09:20-15:15"
    capital: CapitalConfig = CapitalConfig()
    risk: RiskConfig = RiskConfig()
    orders: OrderPolicyConfig = OrderPolicyConfig()
    instruments: InstrumentsConfig = InstrumentsConfig()
    rate_limits: RateLimitConfig = RateLimitConfig()
    live: LiveConfig = LiveConfig()
    paths: PathsConfig = PathsConfig()
    logging: LoggingConfig = LoggingConfig()

    @field_validator("mode", mode="before")
    @classmethod
    def _mode(cls, v: object) -> object:
        # Exact lowercase strings only: "Live", "LIVE", True, 1 are all invalid.
        if isinstance(v, Mode):
            return v
        if not isinstance(v, str) or v not in {m.value for m in Mode}:
            raise ValueError(f"mode must be exactly one of paper|sandbox|live, got {v!r}")
        return Mode(v)

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        if v != ceilings.ALLOWED_TIMEZONE:
            raise ValueError(f"timezone must be {ceilings.ALLOWED_TIMEZONE}")
        return v

    @field_validator("trading_window")
    @classmethod
    def _window(cls, v: str) -> str:
        m = _WINDOW_RE.match(v)
        if not m:
            raise ValueError("trading_window must look like 'HH:MM-HH:MM'")
        try:
            start = time(int(m[1]), int(m[2]))
            end = time(int(m[3]), int(m[4]))
        except ValueError as exc:
            raise ValueError(f"trading_window has an invalid time: {v}") from exc
        if not start < end:
            raise ValueError("trading_window start must be before end")
        if start < _parse_hhmm(ceilings.NSE_SESSION_OPEN) or end > _parse_hhmm(
            ceilings.NSE_SESSION_CLOSE
        ):
            raise ValueError(
                f"trading_window must be inside the NSE session "
                f"{ceilings.NSE_SESSION_OPEN}-{ceilings.NSE_SESSION_CLOSE}"
            )
        return v

    @property
    def window_times(self) -> tuple[time, time]:
        start, end = self.trading_window.split("-")
        return _parse_hhmm(start), _parse_hhmm(end)

    @property
    def risk_per_trade_inr(self) -> float:
        return self.capital.live_capital_cap_inr * self.risk.risk_per_trade_pct / 100.0
