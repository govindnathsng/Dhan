"""Runtime mode resolution. Never falls back to live.

Before Phase 6, live mode is always refused. The full gate (plan section 5:
typed confirmation phrase, pre-flight checks, mandatory Telegram approval) is
implemented in Phase 6.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from automator.config.models import AppConfig, Mode, ProfileKind
from automator.secrets import LIVE_ENABLED

LIVE_GATE_IMPLEMENTED = False


class LiveGateRefusedError(Exception):
    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__("live mode refused:\n" + "\n".join(f"  - {m}" for m in missing))


class ModeError(Exception):
    pass


def live_gate_missing_steps(
    config: AppConfig, live_flag: bool, env: Mapping[str, str] | None = None
) -> list[str]:
    environ = os.environ if env is None else env
    missing: list[str] = []
    if config.mode is not Mode.LIVE:
        missing.append("(a) config 'mode' is not 'live'")
    elif config.active_profile.kind is not ProfileKind.LIVE:
        missing.append(f"(a) profile {config.profile!r} is not a live profile")
    if environ.get(LIVE_ENABLED) != "true":
        missing.append(f"(b) environment variable {LIVE_ENABLED} is not exactly 'true'")
    if not live_flag:
        missing.append("(c) CLI flag --live was not given")
    if not LIVE_GATE_IMPLEMENTED:
        missing.append(
            "(d)-(f) confirmation phrase, pre-flight checks and Telegram approval are not "
            "implemented until Phase 6; live trading is impossible in this version"
        )
    return missing


def resolve_mode(
    config: AppConfig, live_flag: bool = False, env: Mapping[str, str] | None = None
) -> Mode:
    """Return the mode to run in, or raise. The result is never LIVE before Phase 6."""
    if config.mode is Mode.LIVE or live_flag:
        if config.mode is not Mode.LIVE:
            raise ModeError(
                f"--live given but config mode is {config.mode.value!r}; refusing (ambiguous)"
            )
        raise LiveGateRefusedError(live_gate_missing_steps(config, live_flag, env))
    return config.mode
