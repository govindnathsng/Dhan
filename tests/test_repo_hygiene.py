"""Repo-level safety rails."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "automator"


def test_env_example_has_only_empty_placeholders() -> None:
    for line in (ROOT / ".env.example").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        assert value == "", f"{key} must be empty in .env.example"


def test_gitignore_covers_secrets() -> None:
    lines = (ROOT / ".gitignore").read_text().splitlines()
    assert ".env" in lines
    assert "config.yaml" in lines


def test_only_brokers_package_imports_dhanhq() -> None:
    pattern = re.compile(r"^\s*(from|import)\s+dhanhq\b", re.MULTILINE)
    offenders = [
        p
        for p in SRC.rglob("*.py")
        if "brokers" not in p.relative_to(SRC).parts and pattern.search(p.read_text())
    ]
    assert offenders == []


def test_example_config_is_paper() -> None:
    text = (ROOT / "config.example.yaml").read_text()
    assert re.search(r"^mode:\s*paper\b", text, re.MULTILINE)
