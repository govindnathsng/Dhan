from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from automator.secrets import LIVE_ENABLED, SECRET_ENV_VARS

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG = REPO_ROOT / "config.example.yaml"
WHITELIST = REPO_ROOT / "config" / "whitelist.yaml"


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Every test runs in an empty temp dir with no credentials set."""
    for name in (*SECRET_ENV_VARS, LIVE_ENABLED, "AUTOMATOR_CONFIG"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    """Temp dir containing the repo whitelist at config/whitelist.yaml."""
    (tmp_path / "config").mkdir(exist_ok=True)
    shutil.copy(WHITELIST, tmp_path / "config" / "whitelist.yaml")
    return tmp_path
