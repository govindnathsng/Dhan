"""Dhan instrument master (scrip master CSV): download with a daily cache, or a local file."""

from __future__ import annotations

import csv
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

SCRIP_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
CACHE_MAX_AGE_SECONDS = 20 * 3600


class InstrumentError(Exception):
    pass


@dataclass(frozen=True)
class Instrument:
    symbol: str
    security_id: int
    tick_size_raw: float  # [verify] units as published in SEM_TICK_SIZE (appears to be paise)
    lot_units: float
    exch_instrument_type: str  # e.g. ETF, ES
    series: str


def download_scrip_master(dest: Path, timeout: float = 60.0) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    with urllib.request.urlopen(SCRIP_MASTER_URL, timeout=timeout) as resp:
        tmp.write_bytes(resp.read())
    tmp.replace(dest)
    return dest


def cached_scrip_master(cache_dir: Path, refresh: bool = False) -> Path:
    path = cache_dir / "api-scrip-master.csv"
    fresh = path.is_file() and time.time() - path.stat().st_mtime < CACHE_MAX_AGE_SECONDS
    if refresh or not fresh:
        download_scrip_master(path)
    return path


def load_nse_equities(path: Path, symbols: set[str] | None = None) -> dict[str, Instrument]:
    """NSE cash-segment (exchange NSE, segment E) rows, optionally filtered to `symbols`."""
    out: dict[str, Instrument] = {}
    try:
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("SEM_EXM_EXCH_ID") != "NSE" or r.get("SEM_SEGMENT") != "E":
                    continue
                sym = r.get("SEM_TRADING_SYMBOL", "")
                if symbols is not None and sym not in symbols:
                    continue
                if sym in out:
                    raise InstrumentError(f"ambiguous: {sym} appears more than once in NSE_EQ")
                out[sym] = Instrument(
                    symbol=sym,
                    security_id=int(r["SEM_SMST_SECURITY_ID"]),
                    tick_size_raw=float(r["SEM_TICK_SIZE"]),
                    lot_units=float(r["SEM_LOT_UNITS"]),
                    exch_instrument_type=r.get("SEM_EXCH_INSTRUMENT_TYPE", ""),
                    series=r.get("SEM_SERIES", ""),
                )
    except (KeyError, ValueError) as exc:
        raise InstrumentError(f"scrip master has an unexpected format: {exc}") from exc
    return out
