from __future__ import annotations

import pytest

from automator.config import AppConfig, Mode, parse_config_text
from automator.modes import LiveGateRefusedError, ModeError, resolve_mode

LIVE_ENV = {"DHAN_LIVE_ENABLED": "true"}
LIVE_CFG = "mode: live\nprofile: live_canary\n"


def test_default_resolves_to_paper() -> None:
    assert resolve_mode(AppConfig(), env={}) is Mode.PAPER


def test_sandbox_resolves_to_sandbox() -> None:
    assert resolve_mode(parse_config_text("mode: sandbox"), env={}) is Mode.SANDBOX


def test_live_flag_with_paper_config_is_refused() -> None:
    with pytest.raises(ModeError):
        resolve_mode(AppConfig(), live_flag=True, env=LIVE_ENV)


@pytest.mark.parametrize("env_value", ["", "TRUE", "True", "1", "yes", " true"])
def test_live_refused_when_env_not_exactly_true(env_value: str) -> None:
    with pytest.raises(LiveGateRefusedError) as exc:
        resolve_mode(
            parse_config_text(LIVE_CFG), live_flag=True, env={"DHAN_LIVE_ENABLED": env_value}
        )
    assert any("(b)" in m for m in exc.value.missing)


def test_live_refused_without_flag() -> None:
    with pytest.raises(LiveGateRefusedError) as exc:
        resolve_mode(parse_config_text(LIVE_CFG), live_flag=False, env=LIVE_ENV)
    assert any("(c)" in m for m in exc.value.missing)


def test_live_refused_even_when_a_b_c_all_present() -> None:
    with pytest.raises(LiveGateRefusedError) as exc:
        resolve_mode(parse_config_text(LIVE_CFG), live_flag=True, env=LIVE_ENV)
    assert len(exc.value.missing) == 1
    assert "Phase 6" in exc.value.missing[0]
