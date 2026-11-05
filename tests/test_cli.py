from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from automator.cli import EXIT_CONFIG_INVALID, EXIT_MODE_REFUSED, EXIT_OK, main
from automator.secrets import SECRET_ENV_VARS, credential_status, get_secret

EXAMPLE = Path(__file__).resolve().parents[1] / "config.example.yaml"


@pytest.fixture(autouse=True)
def _no_creds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in (*SECRET_ENV_VARS, "DHAN_LIVE_ENABLED", "AUTOMATOR_CONFIG"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)


def test_check_config_defaults_no_credentials(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check-config"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "effective mode       : paper" in out
    assert "<built-in defaults>" in out
    assert "not set" in out


def test_check_config_example(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check-config", "--config", str(EXAMPLE)]) == EXIT_OK
    assert "INR 125.00" in capsys.readouterr().out


def test_check_config_invalid(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("risk:\n  risk_per_trade_pct: 2\n")
    assert main(["check-config", "--config", str(p)]) == EXIT_CONFIG_INVALID
    assert "REFUSING TO START" in capsys.readouterr().err


def test_check_config_live_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    p = tmp_path / "live.yaml"
    p.write_text("mode: live\n")
    monkeypatch.setenv("DHAN_LIVE_ENABLED", "true")
    assert main(["check-config", "--config", str(p), "--live"]) == EXIT_MODE_REFUSED
    assert "Phase 5" in capsys.readouterr().err


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
