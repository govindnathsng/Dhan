"""Instrument whitelist: a YAML file maintained by the account owner only."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from automator.config.models import SYMBOL_RE, _Strict


class WhitelistEntry(_Strict):
    symbol: str
    kind: Literal["ETF", "EQUITY"]
    # Drives STT exemption in the cost model (gold, liquid and gilt ETFs are STT-exempt).
    category: Literal["equity", "gold", "liquid", "gilt"] = "equity"
    security_id: int | None = Field(default=None, ge=1)  # resolved from the instrument master
    note: str = Field(default="", max_length=200)

    @field_validator("symbol")
    @classmethod
    def _sym(cls, v: str) -> str:
        if not SYMBOL_RE.match(v):
            raise ValueError(f"invalid NSE symbol: {v!r}")
        return v

    @model_validator(mode="after")
    def _category(self) -> WhitelistEntry:
        if self.kind == "EQUITY" and self.category != "equity":
            raise ValueError(f"{self.symbol}: EQUITY entries must have category 'equity'")
        return self


class Whitelist(_Strict):
    version: Literal[1]
    instruments: tuple[WhitelistEntry, ...] = Field(min_length=1)

    @field_validator("instruments", mode="before")
    @classmethod
    def _to_tuple(cls, v: object) -> object:
        return tuple(v) if isinstance(v, list) else v

    @model_validator(mode="after")
    def _unique(self) -> Whitelist:
        seen: set[str] = set()
        for e in self.instruments:
            if e.symbol in seen:
                raise ValueError(f"duplicate symbol in whitelist: {e.symbol}")
            seen.add(e.symbol)
        return self

    @property
    def symbols(self) -> frozenset[str]:
        return frozenset(e.symbol for e in self.instruments)

    def get(self, symbol: str) -> WhitelistEntry | None:
        for e in self.instruments:
            if e.symbol == symbol:
                return e
        return None
