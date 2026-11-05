"""Credential access. Values come only from environment variables and are never logged.

Callers get pydantic SecretStr objects whose repr/str are masked.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Final

from pydantic import SecretStr

# Live host only. These must NEVER be set in a cloud environment.
LIVE_CLIENT_ID: Final = "DHAN_CLIENT_ID"
LIVE_ACCESS_TOKEN: Final = "DHAN_ACCESS_TOKEN"
LIVE_ENABLED: Final = "DHAN_LIVE_ENABLED"
# Cloud paper loop: data endpoints only.
DATA_CLIENT_ID: Final = "DHAN_DATA_CLIENT_ID"
DATA_ACCESS_TOKEN: Final = "DHAN_DATA_ACCESS_TOKEN"
# Sandbox tests only.
SANDBOX_CLIENT_ID: Final = "DHAN_SANDBOX_CLIENT_ID"
SANDBOX_ACCESS_TOKEN: Final = "DHAN_SANDBOX_ACCESS_TOKEN"
# Telegram alerts and approval.
TELEGRAM_BOT_TOKEN: Final = "TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID: Final = "TELEGRAM_CHAT_ID"
TELEGRAM_ALLOWED_USER_ID: Final = "TELEGRAM_ALLOWED_USER_ID"

SECRET_ENV_VARS: Final[tuple[str, ...]] = (
    LIVE_CLIENT_ID,
    LIVE_ACCESS_TOKEN,
    DATA_CLIENT_ID,
    DATA_ACCESS_TOKEN,
    SANDBOX_CLIENT_ID,
    SANDBOX_ACCESS_TOKEN,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_ALLOWED_USER_ID,
)

LIVE_HOST_ONLY_VARS: Final[tuple[str, ...]] = (LIVE_CLIENT_ID, LIVE_ACCESS_TOKEN, LIVE_ENABLED)


def get_secret(name: str, env: Mapping[str, str] | None = None) -> SecretStr | None:
    if name not in SECRET_ENV_VARS:
        raise KeyError(f"unknown secret name: {name}")
    value = (os.environ if env is None else env).get(name, "")
    value = value.strip()
    return SecretStr(value) if value else None


def credential_status(env: Mapping[str, str] | None = None) -> dict[str, bool]:
    """Presence only (True/False). Never returns values."""
    return {name: get_secret(name, env) is not None for name in SECRET_ENV_VARS}


def live_host_vars_present(env: Mapping[str, str] | None = None) -> list[str]:
    """Names (never values) of live-host-only variables that are set."""
    environ = os.environ if env is None else env
    return [n for n in LIVE_HOST_ONLY_VARS if environ.get(n, "").strip()]


def known_secret_values(env: Mapping[str, str] | None = None) -> list[str]:
    """Raw values currently set, for the log redaction filter only."""
    out: list[str] = []
    for name in SECRET_ENV_VARS:
        s = get_secret(name, env)
        if s is not None and len(s.get_secret_value()) >= 4:
            out.append(s.get_secret_value())
    return out
