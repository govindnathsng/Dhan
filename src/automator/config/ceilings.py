"""Hard ceilings and floors that no config file can cross.

These are code constants on purpose: editing YAML must never be enough to take on
more risk. Changing them requires an explicit code change requested by the account
owner (see .cursor/rules/safety.mdc and docs/DECISIONS.md D-002).

Two kinds of bound:
- CEILINGS on exposure/loss limits (config may be lower, never higher).
- FLOORS on protective settings (config may be stricter, never looser).
"""

from __future__ import annotations

from typing import Final

# Absolute cap on any profile's capital (paper or live). Live scale-up is manual, <= 2x per step.
MAX_PROFILE_CAPITAL_INR: Final[float] = 50_000.0

# Exposure/loss ceilings as % of the profile's capital_inr.
# 0.5% gives Rs 250 on the 50k paper profile and Rs 125 on the 25k canary.
MAX_RISK_PER_TRADE_PCT: Final[float] = 0.5
MAX_DAILY_LOSS_PCT: Final[float] = 1.0
MAX_WEEKLY_LOSS_PCT: Final[float] = 3.0
MAX_DRAWDOWN_HALT_PCT: Final[float] = 8.0
MAX_POSITION_VALUE_PCT: Final[float] = 40.0
MAX_TOTAL_INVESTED_PCT: Final[float] = 80.0

# Count ceilings.
MAX_OPEN_POSITIONS: Final[int] = 4
MAX_NEW_ENTRIES_PER_WEEK: Final[int] = 5
MAX_ORDERS_PER_DAY: Final[int] = 10
MAX_PROPOSALS_PER_DAY: Final[int] = 5

# Entry price band vs last traded price.
MAX_ENTRY_PRICE_BAND_PCT: Final[float] = 1.0

# Protective floors (owner's settings; config may only tighten).
STOP_DISTANCE_MIN_PCT_FLOOR: Final[float] = 1.0
STOP_DISTANCE_MAX_PCT_CEILING: Final[float] = 6.0
STOP_MIN_ATR_MULTIPLE_FLOOR: Final[float] = 0.75
MIN_NET_REWARD_TO_RISK_FLOOR: Final[float] = 1.5
REENTRY_COOLDOWN_DAYS_FLOOR: Final[int] = 5
LOSING_STREAK_LOSSES_CEILING: Final[int] = 3
LOSING_STREAK_PAUSE_DAYS_FLOOR: Final[int] = 2
MIN_CONFIDENCE_FLOOR: Final[float] = 0.5

# Approval service.
APPROVAL_EXPIRY_MINUTES_CEILING: Final[int] = 120
APPROVAL_LATEST_TIME: Final[str] = "15:00"

# Broker-documented API limits (https://dhanhq.co/docs/v2/ [verify]). Config may only lower these.
DHAN_ORDERS_PER_SECOND: Final[int] = 10
DHAN_ORDERS_PER_MINUTE: Final[int] = 250
DHAN_ORDERS_PER_HOUR: Final[int] = 1000
DHAN_ORDERS_PER_DAY: Final[int] = 7000
DHAN_MODIFICATIONS_PER_ORDER: Final[int] = 25
DHAN_DATA_REQUESTS_PER_SECOND: Final[int] = 5
DHAN_DATA_REQUESTS_PER_DAY: Final[int] = 100_000
DHAN_QUOTE_REQUESTS_PER_SECOND: Final[int] = 1
DHAN_FEED_MAX_CONNECTIONS: Final[int] = 5
DHAN_FEED_MAX_INSTRUMENTS_PER_CONNECTION: Final[int] = 5000

# NSE equity continuous session, IST. The entry window must sit inside it.
NSE_SESSION_OPEN: Final[str] = "09:15"
NSE_SESSION_CLOSE: Final[str] = "15:30"

# Only these values are ever accepted in v1.
ALLOWED_TIMEZONE: Final[str] = "Asia/Kolkata"
ALLOWED_EXCHANGE_SEGMENTS: Final[frozenset[str]] = frozenset({"NSE_EQ"})
ALLOWED_PRODUCT_TYPES: Final[frozenset[str]] = frozenset({"CNC"})
ALLOWED_ORDER_TYPES: Final[frozenset[str]] = frozenset({"LIMIT"})

# Explicitly forbidden in v1; listed so error messages can name them.
FORBIDDEN_PRODUCT_TYPES: Final[frozenset[str]] = frozenset(
    {"INTRADAY", "MARGIN", "MTF", "CO", "BO"}
)
FORBIDDEN_ORDER_TYPES: Final[frozenset[str]] = frozenset({"MARKET", "STOP_LOSS_MARKET"})
FORBIDDEN_SEGMENTS: Final[frozenset[str]] = frozenset(
    {"NSE_FNO", "BSE_FNO", "MCX_COMM", "NSE_CURRENCY", "BSE_CURRENCY", "BSE_EQ"}
)
