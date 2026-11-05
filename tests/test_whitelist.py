from __future__ import annotations

import pytest

from automator.config import ConfigError, parse_whitelist_text
from tests.conftest import WHITELIST


def test_repo_whitelist_is_valid() -> None:
    wl = parse_whitelist_text(WHITELIST.read_text())
    assert {"NIFTYBEES", "JUNIORBEES", "BANKBEES", "GOLDBEES", "M&M", "BAJAJ-AUTO"} <= wl.symbols
    assert sum(1 for e in wl.instruments if e.kind == "EQUITY") == 50
    gold = wl.get("GOLDBEES")
    assert gold is not None
    assert gold.category == "gold"


@pytest.mark.parametrize(
    "body",
    [
        "version: 1\ninstruments: []\n",
        "version: 2\ninstruments:\n  - {symbol: NIFTYBEES, kind: ETF}\n",
        "instruments:\n  - {symbol: NIFTYBEES, kind: ETF}\n",
        "version: 1\ninstruments:\n  - {symbol: niftybees, kind: ETF}\n",
        "version: 1\ninstruments:\n  - {symbol: NIFTYBEES, kind: FUTURE}\n",
        "version: 1\ninstruments:\n  - {symbol: INFY, kind: EQUITY, category: gold}\n",
        "version: 1\ninstruments:\n  - {symbol: INFY, kind: EQUITY, segment: NSE_FNO}\n",
        "version: 1\ninstruments:\n"
        "  - {symbol: INFY, kind: EQUITY}\n  - {symbol: INFY, kind: EQUITY}\n",
        "version: 1\ninstruments:\n  - {symbol: '<ETF or large-cap symbol 1>', kind: ETF}\n",
    ],
)
def test_invalid_whitelists_rejected(body: str) -> None:
    with pytest.raises(ConfigError):
        parse_whitelist_text(body)
