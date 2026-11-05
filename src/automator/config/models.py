"""Validated configuration schema.

Every model forbids unknown keys and uses strict types, so a typo or an ambiguous
value makes the config invalid instead of silently using a default. Bounds come
from automator.config.ceilings and cannot be crossed by editing YAML.
"""

from __future__ import annotations

import re
from datetime import date, time
from enum import StrEnum
from itertools import pairwise
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from automator.config import ceilings as C


class Mode(StrEnum):
    PAPER = "paper"
    SANDBOX = "sandbox"
    LIVE = "live"


class ProfileKind(StrEnum):
    PAPER = "paper"
    LIVE = "live"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9&\-]{0,29}$")
_PROFILE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,30}$")
_WINDOW_RE = re.compile(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$")
_HHMM_RE = re.compile(r"^(\d{2}):(\d{2})$")


def parse_hhmm(value: str) -> time:
    m = _HHMM_RE.match(value)
    if not m:
        raise ValueError(f"time must look like 'HH:MM', got {value!r}")
    return time(int(m[1]), int(m[2]))


class RiskProfile(_Strict):
    """Rupee limits for one capital profile. Ceilings scale with capital_inr."""

    kind: ProfileKind
    capital_inr: float = Field(gt=0, le=C.MAX_PROFILE_CAPITAL_INR)
    risk_per_trade_inr: float = Field(gt=0)
    max_daily_loss_inr: float = Field(gt=0)
    max_weekly_loss_inr: float = Field(gt=0)
    max_drawdown_halt_inr: float = Field(gt=0)
    max_open_positions: int = Field(ge=1, le=C.MAX_OPEN_POSITIONS)
    max_position_value_inr: float = Field(gt=0)
    max_total_invested_inr: float = Field(gt=0)
    max_new_entries_per_week: int = Field(ge=1, le=C.MAX_NEW_ENTRIES_PER_WEEK)
    max_orders_per_day: int = Field(ge=1, le=C.MAX_ORDERS_PER_DAY)
    max_proposals_per_day: int = Field(ge=1, le=C.MAX_PROPOSALS_PER_DAY)

    @field_validator("kind", mode="before")
    @classmethod
    def _kind(cls, v: object) -> object:
        if isinstance(v, ProfileKind):
            return v
        if not isinstance(v, str) or v not in {k.value for k in ProfileKind}:
            raise ValueError(f"kind must be exactly 'paper' or 'live', got {v!r}")
        return ProfileKind(v)

    def ceiling_inr(self, field: str) -> float:
        pct = _PCT_CEILINGS[field]
        return self.capital_inr * pct / 100.0

    @model_validator(mode="after")
    def _ceilings_and_order(self) -> RiskProfile:
        for field, pct in _PCT_CEILINGS.items():
            value = getattr(self, field)
            ceiling = self.capital_inr * pct / 100.0
            if value > ceiling + 1e-9:
                raise ValueError(
                    f"{field}=Rs {value:g} exceeds hard ceiling Rs {ceiling:g} "
                    f"({pct}% of capital_inr {self.capital_inr:g})"
                )
        chain = [
            "risk_per_trade_inr",
            "max_daily_loss_inr",
            "max_weekly_loss_inr",
            "max_drawdown_halt_inr",
        ]
        for lower, higher in pairwise(chain):
            if getattr(self, lower) > getattr(self, higher):
                raise ValueError(f"{lower} must not exceed {higher}")
        if self.max_position_value_inr > self.max_total_invested_inr:
            raise ValueError("max_position_value_inr must not exceed max_total_invested_inr")
        return self


_PCT_CEILINGS: dict[str, float] = {
    "risk_per_trade_inr": C.MAX_RISK_PER_TRADE_PCT,
    "max_daily_loss_inr": C.MAX_DAILY_LOSS_PCT,
    "max_weekly_loss_inr": C.MAX_WEEKLY_LOSS_PCT,
    "max_drawdown_halt_inr": C.MAX_DRAWDOWN_HALT_PCT,
    "max_position_value_inr": C.MAX_POSITION_VALUE_PCT,
    "max_total_invested_inr": C.MAX_TOTAL_INVESTED_PCT,
}

DEFAULT_PROFILES: dict[str, RiskProfile] = {
    "paper": RiskProfile(
        kind=ProfileKind.PAPER,
        capital_inr=50_000.0,
        risk_per_trade_inr=125.0,
        max_daily_loss_inr=250.0,
        max_weekly_loss_inr=750.0,
        max_drawdown_halt_inr=2000.0,
        max_open_positions=2,
        max_position_value_inr=10_000.0,
        max_total_invested_inr=20_000.0,
        max_new_entries_per_week=3,
        max_orders_per_day=6,
        max_proposals_per_day=3,
    ),
    "live_canary": RiskProfile(
        kind=ProfileKind.LIVE,
        capital_inr=25_000.0,
        risk_per_trade_inr=60.0,
        max_daily_loss_inr=125.0,
        max_weekly_loss_inr=375.0,
        max_drawdown_halt_inr=1000.0,
        max_open_positions=1,
        max_position_value_inr=5000.0,
        max_total_invested_inr=5000.0,
        max_new_entries_per_week=2,
        max_orders_per_day=4,
        max_proposals_per_day=3,
    ),
}


class TradingRulesConfig(_Strict):
    """Rules shared by all profiles. Protective values may only be tightened."""

    entry_price_band_pct: float = Field(default=0.75, gt=0, le=C.MAX_ENTRY_PRICE_BAND_PCT)
    stop_distance_min_pct: float = Field(default=1.0, ge=C.STOP_DISTANCE_MIN_PCT_FLOOR)
    stop_distance_max_pct: float = Field(default=6.0, le=C.STOP_DISTANCE_MAX_PCT_CEILING)
    stop_min_atr_multiple: float = Field(default=0.75, ge=C.STOP_MIN_ATR_MULTIPLE_FLOOR)
    atr_period: Literal[14] = 14
    min_net_reward_to_risk: float = Field(default=1.5, ge=C.MIN_NET_REWARD_TO_RISK_FLOOR)
    reentry_cooldown_days: int = Field(default=5, ge=C.REENTRY_COOLDOWN_DAYS_FLOOR)
    losing_streak_losses: int = Field(default=3, ge=1, le=C.LOSING_STREAK_LOSSES_CEILING)
    losing_streak_pause_trading_days: int = Field(default=2, ge=C.LOSING_STREAK_PAUSE_DAYS_FLOOR)
    losing_streak_requires_review_note: Literal[True] = True
    min_confidence: float = Field(default=0.6, ge=C.MIN_CONFIDENCE_FLOOR, le=1.0)
    stale_data_seconds: int = Field(default=60, ge=1, le=600)
    max_consecutive_errors: int = Field(default=3, ge=1, le=10)
    max_claim_mismatches_per_day: int = Field(default=2, ge=1, le=5)
    auto_exit_on_loss_breach: bool = False

    @model_validator(mode="after")
    def _stop_range(self) -> TradingRulesConfig:
        if self.stop_distance_min_pct >= self.stop_distance_max_pct:
            raise ValueError("stop_distance_min_pct must be below stop_distance_max_pct")
        return self


class OrderPolicyConfig(_Strict):
    """v1 order policy. Anything other than NSE_EQ / CNC / LIMIT / long-only is invalid."""

    exchange_segment: str = "NSE_EQ"
    allowed_product_types: tuple[str, ...] = ("CNC",)
    allowed_order_types: tuple[str, ...] = ("LIMIT",)
    allow_short: Literal[False] = False
    require_protective_stop: Literal[True] = True

    @field_validator("exchange_segment")
    @classmethod
    def _segment(cls, v: str) -> str:
        if v not in C.ALLOWED_EXCHANGE_SEGMENTS:
            raise ValueError(f"exchange_segment {v!r} not allowed in v1 (only NSE_EQ)")
        return v

    @field_validator("allowed_product_types", mode="before")
    @classmethod
    def _products(cls, v: object) -> object:
        return _check_subset(v, C.ALLOWED_PRODUCT_TYPES, "product type")

    @field_validator("allowed_order_types", mode="before")
    @classmethod
    def _orders(cls, v: object) -> object:
        return _check_subset(v, C.ALLOWED_ORDER_TYPES, "order type")


def _check_subset(v: object, allowed: frozenset[str], label: str) -> tuple[str, ...]:
    if not isinstance(v, list | tuple) or not v:
        raise ValueError(f"allowed {label}s must be a non-empty list")
    items = tuple(v)
    for item in items:
        if not isinstance(item, str) or item not in allowed:
            raise ValueError(f"{label} {item!r} is not allowed in v1 (allowed: {sorted(allowed)})")
    return items


class BlackoutEntry(_Strict):
    symbol: str
    start: date
    end: date
    reason: str = Field(min_length=1, max_length=200)

    @field_validator("symbol")
    @classmethod
    def _sym(cls, v: str) -> str:
        if not SYMBOL_RE.match(v):
            raise ValueError(f"invalid NSE symbol: {v!r}")
        return v

    @model_validator(mode="after")
    def _range(self) -> BlackoutEntry:
        if self.end < self.start:
            raise ValueError("blackout end must not be before start")
        return self


class InstrumentsConfig(_Strict):
    whitelist_file: Path = Path("config/whitelist.yaml")
    blackout: tuple[BlackoutEntry, ...] = ()

    @field_validator("whitelist_file", mode="before")
    @classmethod
    def _to_path(cls, v: object) -> object:
        return Path(v) if isinstance(v, str) else v

    @field_validator("blackout", mode="before")
    @classmethod
    def _to_tuple(cls, v: object) -> object:
        return tuple(v) if isinstance(v, list) else v


class CostsConfig(_Strict):
    """Dhan delivery (CNC) charges. Re-check against Dhan's pricing page before relying on them."""

    rates_checked_on: date = date(2026, 11, 5)
    brokerage_per_order_inr: float = Field(default=0.0, ge=0)
    stt_pct: float = Field(default=0.1, ge=0)  # on buy and sell for delivery
    stt_exempt_categories: tuple[Literal["gold", "liquid", "gilt"], ...] = (
        "gold",
        "liquid",
        "gilt",
    )
    stamp_duty_buy_pct: float = Field(default=0.015, ge=0)
    exchange_txn_pct: float = Field(default=0.003, ge=0)
    sebi_fee_pct: float = Field(default=0.0001, ge=0)
    gst_pct: float = Field(default=18.0, ge=0)  # on brokerage, transaction and SEBI charges
    dp_charge_per_scrip_sell_inr: float = Field(default=12.5, ge=0)  # plus GST, per scrip/day

    @field_validator("stt_exempt_categories", mode="before")
    @classmethod
    def _to_tuple(cls, v: object) -> object:
        return tuple(v) if isinstance(v, list) else v


class ApprovalConfig(_Strict):
    """Live mode ALWAYS uses Telegram approval; there is deliberately no option to change that.

    `paper_mode` only selects how paper-mode proposals are approved.
    """

    paper_mode: Literal["auto", "telegram"] = "auto"
    expiry_minutes: int = Field(default=60, ge=1, le=C.APPROVAL_EXPIRY_MINUTES_CEILING)
    latest_approval_time: str = C.APPROVAL_LATEST_TIME

    @field_validator("latest_approval_time")
    @classmethod
    def _latest(cls, v: str) -> str:
        if parse_hhmm(v) > parse_hhmm(C.APPROVAL_LATEST_TIME):
            raise ValueError(f"latest_approval_time must be at or before {C.APPROVAL_LATEST_TIME}")
        return v


class RateLimitConfig(_Strict):
    """Our own budget. Each value must be <= the broker-documented limit."""

    orders_per_second: int = Field(default=2, ge=1, le=C.DHAN_ORDERS_PER_SECOND)
    orders_per_minute: int = Field(default=20, ge=1, le=C.DHAN_ORDERS_PER_MINUTE)
    orders_per_hour: int = Field(default=100, ge=1, le=C.DHAN_ORDERS_PER_HOUR)
    orders_per_day: int = Field(default=200, ge=1, le=C.DHAN_ORDERS_PER_DAY)
    modifications_per_order: int = Field(default=10, ge=1, le=C.DHAN_MODIFICATIONS_PER_ORDER)
    data_requests_per_second: int = Field(default=2, ge=1, le=C.DHAN_DATA_REQUESTS_PER_SECOND)
    data_requests_per_day: int = Field(default=10_000, ge=1, le=C.DHAN_DATA_REQUESTS_PER_DAY)
    quote_requests_per_second: int = Field(default=1, ge=1, le=C.DHAN_QUOTE_REQUESTS_PER_SECOND)
    feed_max_connections: int = Field(default=1, ge=1, le=C.DHAN_FEED_MAX_CONNECTIONS)
    feed_max_instruments_per_connection: int = Field(
        default=100, ge=1, le=C.DHAN_FEED_MAX_INSTRUMENTS_PER_CONNECTION
    )


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
    profile: str = "paper"
    timezone: str = C.ALLOWED_TIMEZONE
    entry_window: str = "09:30-14:30"
    profiles: dict[str, RiskProfile] = Field(default_factory=lambda: dict(DEFAULT_PROFILES))
    rules: TradingRulesConfig = TradingRulesConfig()
    orders: OrderPolicyConfig = OrderPolicyConfig()
    instruments: InstrumentsConfig = InstrumentsConfig()
    costs: CostsConfig = CostsConfig()
    approval: ApprovalConfig = ApprovalConfig()
    rate_limits: RateLimitConfig = RateLimitConfig()
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

    @field_validator("profiles")
    @classmethod
    def _profile_names(cls, v: dict[str, RiskProfile]) -> dict[str, RiskProfile]:
        if not v:
            raise ValueError("at least one profile is required")
        for name in v:
            if not _PROFILE_NAME_RE.match(name):
                raise ValueError(f"invalid profile name {name!r}")
        return v

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        if v != C.ALLOWED_TIMEZONE:
            raise ValueError(f"timezone must be {C.ALLOWED_TIMEZONE}")
        return v

    @field_validator("entry_window")
    @classmethod
    def _window(cls, v: str) -> str:
        m = _WINDOW_RE.match(v)
        if not m:
            raise ValueError("entry_window must look like 'HH:MM-HH:MM'")
        try:
            start = time(int(m[1]), int(m[2]))
            end = time(int(m[3]), int(m[4]))
        except ValueError as exc:
            raise ValueError(f"entry_window has an invalid time: {v}") from exc
        if not start < end:
            raise ValueError("entry_window start must be before end")
        if start < parse_hhmm(C.NSE_SESSION_OPEN) or end > parse_hhmm(C.NSE_SESSION_CLOSE):
            raise ValueError(
                f"entry_window must be inside the NSE session "
                f"{C.NSE_SESSION_OPEN}-{C.NSE_SESSION_CLOSE}"
            )
        return v

    @model_validator(mode="after")
    def _profile_matches_mode(self) -> AppConfig:
        if self.profile not in self.profiles:
            raise ValueError(
                f"profile {self.profile!r} is not defined (have: {sorted(self.profiles)})"
            )
        if self.mode is Mode.LIVE and self.active_profile.kind is not ProfileKind.LIVE:
            raise ValueError(f"mode 'live' requires a profile of kind 'live', not {self.profile!r}")
        return self

    @property
    def active_profile(self) -> RiskProfile:
        return self.profiles[self.profile]

    @property
    def window_times(self) -> tuple[time, time]:
        start, end = self.entry_window.split("-")
        return parse_hhmm(start), parse_hhmm(end)
