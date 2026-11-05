"""Runtime mode resolution. Never falls back to live.

Phase 0-4: live mode is always refused. The full gate (section 4 of the plan:
typed confirmation phrase + pre-flight checks) is implemented in Phase 5.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from automator.config.models import AppConfig, Mode

LIVE_ENABLED_ENV_VAR = "DHAN_LIVE_ENABLED"
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
    if environ.get(LIVE_ENABLED_ENV_VAR) != "true":
        missing.append(f"(b) environment variable {LIVE_ENABLED_ENV_VAR} is not exactly 'true'")
    if not live_flag:
        missing.append("(c) CLI flag --live was not given")
    if not LIVE_GATE_IMPLEMENTED:
        missing.append(
            "(d)+(e) confirmation phrase and pre-flight checks are not implemented "
            "until Phase 5; live trading is impossible in this version"
        )
    return missing


def resolve_mode(
    config: AppConfig, live_flag: bool = False, env: Mapping[str, str] | None = None
) -> Mode:
    """Return the mode to run in, or raise. The result is never LIVE in Phase 0-4."""
    if config.mode is Mode.LIVE or live_flag:
        if config.mode is not Mode.LIVE:
            raise ModeError(
                f"--live given but config mode is {config.mode.value!r}; refusing (ambiguous)"
            )
        raise LiveGateRefusedError(live_gate_missing_steps(config, live_flag, env))
    return config.mode
