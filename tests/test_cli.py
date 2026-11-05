from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from automator.cli import EXIT_CONFIG_INVALID, EXIT_MODE_REFUSED, EXIT_OK, main
from automator.secrets import credential_status, get_secret
from tests.conftest import EXAMPLE_CONFIG as EXAMPLE


@pytest.fixture(autouse=True)
def _wl(workdir: Path) -> None:
    """All CLI tests run in a dir that has config/whitelist.yaml."""


def test_check_config_defaults_no_credentials(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check-config"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "effective mode        : paper" in out
    assert "54 instruments" in out
    assert "<built-in defaults>" in out
    assert "not set" in out


def test_check_config_example(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check-config", "--config", str(EXAMPLE)]) == EXIT_OK
    out = capsys.readouterr().out
    assert "Rs    125.00  (ceiling Rs 250.00)" in out


def test_check_config_invalid(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("rules:\n  min_net_reward_to_risk: 1.0\n")
    assert main(["check-config", "--config", str(p)]) == EXIT_CONFIG_INVALID
    assert "REFUSING TO START" in capsys.readouterr().err


def test_check_config_live_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    p = tmp_path / "live.yaml"
    p.write_text("mode: live\nprofile: live_canary\n")
    monkeypatch.setenv("DHAN_LIVE_ENABLED", "true")
    assert main(["check-config", "--config", str(p), "--live"]) == EXIT_MODE_REFUSED
    err = capsys.readouterr().err
    assert "Phase 6" in err
    assert "live-host-only variables are set: DHAN_LIVE_ENABLED" in err


def test_missing_whitelist_refuses(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "config" / "whitelist.yaml").unlink()
    assert main(["check-config"]) == EXIT_CONFIG_INVALID
    assert "whitelist file not found" in capsys.readouterr().err


def test_live_flag_on_paper_config_refused() -> None:
    assert main(["check-config", "--live"]) == EXIT_MODE_REFUSED


def test_credential_values_never_printed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", "fake-token-should-not-appear")
    monkeypatch.setenv("DHAN_CLIENT_ID", "9988776655")
    assert main(["check-config"]) == EXIT_OK
    captured = capsys.readouterr()
    assert "fake-token-should-not-appear" not in captured.out + captured.err
    assert "9988776655" not in captured.out + captured.err
    assert credential_status()["DHAN_ACCESS_TOKEN"] is True


def test_secretstr_masks_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", "fake-token-xyz")
    s = get_secret("DHAN_ACCESS_TOKEN")
    assert s is not None
    assert "fake-token-xyz" not in repr(s) + str(s)


def test_whitespace_only_secret_is_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", "   ")
    assert get_secret("DHAN_ACCESS_TOKEN") is None


def test_help_runs_as_console_script() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "automator.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert "check-config" in r.stdout
