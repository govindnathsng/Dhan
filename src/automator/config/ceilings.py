"""Hard ceilings that no config file can exceed.

These are code constants on purpose: editing a YAML file must never be enough to
take on more risk than these values. Changing them requires an explicit code
change requested by the account owner (see .cursor/rules/ and docs/DECISIONS.md).
"""

from __future__ import annotations

from typing import Final

# Risk limits, as percentages of the live capital cap.
MAX_RISK_PER_TRADE_PCT: Final[float] = 0.5
MAX_DAILY_LOSS_PCT: Final[float] = 1.0
MAX_WEEKLY_LOSS_PCT: Final[float] = 3.0
MAX_DRAWDOWN_PCT: Final[float] = 8.0
MAX_POSITION_VALUE_PCT: Final[float] = 40.0
MAX_PRICE_BAND_PCT: Final[float] = 1.0

# Counts.
MAX_OPEN_POSITIONS: Final[int] = 4
MAX_ORDERS_PER_DAY: Final[int] = 20

# Absolute capital cap. Scale-up is manual, at most 2x per step (Phase 5 docs).
MAX_LIVE_CAPITAL_CAP_INR: Final[float] = 100_000.0

# Broker-documented API limits (https://dhanhq.co/docs/v2/). Config may only lower these.
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

# NSE equity continuous session, IST. The configured trading window must sit inside it.
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
