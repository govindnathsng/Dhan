from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from automator.brokers.dhan_readonly import (
    READ_ONLY_ENDPOINTS,
    DhanReadOnlyClient,
    ReadOnlyViolationError,
)
from automator.cli import EXIT_MISSING_CREDENTIALS, main
from automator.data.instruments import Instrument, InstrumentError, load_nse_equities
from automator.dhan_check import run_dhan_check

FAKE_CLIENT_ID = "1100223344"
FAKE_TOKEN = "fake-token-for-tests"
NIFTYBEES = Instrument("NIFTYBEES", 10576, 1.0, 1.0, "ETF", "EQ")


def ok(data: Any) -> dict[str, Any]:
    return {"status": "success", "remarks": "", "data": data}


def err(code: str, msg: str = "x") -> dict[str, Any]:
    return {
        "status": "failure",
        "remarks": {"error_code": code, "error_type": "t", "error_message": msg},
        "data": "",
    }


GOOD: dict[tuple[str, str], dict[str, Any]] = {
    ("GET", "/profile"): ok(
        {
            "dhanClientId": FAKE_CLIENT_ID,
            "tokenValidity": "06/11/2026 19:00",
            "activeSegment": "Equity, Derivative",
            "ddpi": "Active",
            "dataPlan": "Active",
            "dataValidity": "2026-12-05 09:37:52.0",
        }
    ),
    ("GET", "/fundlimit"): ok({"availabelBalance": 60_000.0}),
    ("GET", "/holdings"): ok([]),
    ("GET", "/positions"): ok([]),
    ("GET", "/orders"): ok([{"orderStatus": "TRADED"}]),
    ("GET", "/ip/getIP"): ok({"primaryIP": "203.0.113.7", "secondaryIP": ""}),
    ("POST", "/marketfeed/ltp"): ok(
        {"data": {"NSE_EQ": {"10576": {"last_price": 271.35}}}, "status": "success"}
    ),
}


class FakeHttp:
    def __init__(self, responses: dict[tuple[str, str], dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str]] = []

    def get(self, endpoint: str) -> dict[str, Any]:
        self.calls.append(("GET", endpoint))
        return self.responses[("GET", endpoint)]

    def post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("POST", endpoint))
        return self.responses[("POST", endpoint)]


def client(responses: dict[tuple[str, str], dict[str, Any]]) -> tuple[DhanReadOnlyClient, FakeHttp]:
    http = FakeHttp(responses)
    return DhanReadOnlyClient(FAKE_CLIENT_ID, FAKE_TOKEN, http=http), http


def by_name(checks: list[Any]) -> dict[str, Any]:
    return {c.name: c for c in checks}


def test_all_good_and_only_read_only_endpoints_called() -> None:
    c, http = client(GOOD)
    checks = by_name(run_dhan_check(c, {"NIFTYBEES": NIFTYBEES}, 25_000, "203.0.113.7"))
    assert all(ch.status in {"PASS", "INFO"} for ch in checks.values()), checks
    assert checks["LTP NIFTYBEES"].detail == "Rs 271.35"
    assert checks["account"].detail == "client ID ending 3344"
    assert checks["this machine's IP"].status == "PASS"
    assert set(http.calls) <= READ_ONLY_ENDPOINTS


def test_order_endpoints_are_unreachable() -> None:
    c, http = client(GOOD)
    for method, endpoint in [
        ("POST", "/orders"),
        ("POST", "/super/orders"),
        ("POST", "/forever/orders"),
        ("PUT", "/orders/1"),
        ("DELETE", "/orders/1"),
        ("POST", "/killswitch"),
        ("POST", "/pnlExit"),
        ("POST", "/ip/setIP"),
    ]:
        with pytest.raises(ReadOnlyViolationError):
            c._call(method, endpoint)
    assert http.calls == []


def test_no_order_methods_exposed() -> None:
    public = {n for n in dir(DhanReadOnlyClient) if not n.startswith("_")}
    assert not {n for n in public if any(w in n for w in ("place", "modify", "cancel", "exit"))}


def test_expired_token_stops_early_with_hint() -> None:
    c, http = client({**GOOD, ("GET", "/profile"): err("DH-901")})
    checks = run_dhan_check(c, {"NIFTYBEES": NIFTYBEES}, 25_000, None)
    assert len(checks) == 1
    assert checks[0].status == "FAIL"
    assert "fresh token" in checks[0].detail
    assert http.calls == [("GET", "/profile")]


def test_data_plan_inactive_and_ltp_806() -> None:
    prof = dict(GOOD[("GET", "/profile")]["data"], dataPlan="Deactive")
    c, _ = client({**GOOD, ("GET", "/profile"): ok(prof), ("POST", "/marketfeed/ltp"): err("806")})
    checks = by_name(run_dhan_check(c, {"NIFTYBEES": NIFTYBEES}, 25_000, None))
    assert checks["Data API plan"].status == "FAIL"
    assert "not subscribed" in checks["market data (LTP)"].detail


def test_ip_mismatch_and_none_registered() -> None:
    c, _ = client(GOOD)
    checks = by_name(run_dhan_check(c, {}, 25_000, "198.51.100.1"))
    assert checks["this machine's IP"].status == "FAIL"
    c, _ = client({**GOOD, ("GET", "/ip/getIP"): ok({"primaryIP": "", "secondaryIP": ""})})
    assert by_name(run_dhan_check(c, {}, 25_000, None))["static IP"].status == "FAIL"


def test_funds_shown_as_yes_no_only() -> None:
    c, _ = client({**GOOD, ("GET", "/fundlimit"): ok({"availabelBalance": 12_345.67})})
    f = by_name(run_dhan_check(c, {}, 25_000, None))["funds"]
    assert f.status == "WARN"
    assert "12,345" not in f.detail
    assert "12345" not in f.detail


def test_open_positions_and_orders_warn() -> None:
    c, _ = client(
        {
            **GOOD,
            ("GET", "/positions"): ok([{"netQty": 3}]),
            ("GET", "/orders"): ok([{"orderStatus": "PENDING"}]),
        }
    )
    checks = by_name(run_dhan_check(c, {}, 25_000, None))
    assert checks["open positions"].status == "WARN"
    assert checks["open orders"].status == "WARN"


def test_ddpi_inactive_warns() -> None:
    prof = dict(GOOD[("GET", "/profile")]["data"], ddpi="Deactive")
    c, _ = client({**GOOD, ("GET", "/profile"): ok(prof)})
    assert by_name(run_dhan_check(c, {}, 25_000, None))["DDPI"].status == "WARN"


def test_cli_missing_credentials(workdir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["dhan-check"]) == EXIT_MISSING_CREDENTIALS
    assert "read -rs DHAN_ACCESS_TOKEN" in capsys.readouterr().err


SCRIP_HEADER = (
    "SEM_EXM_EXCH_ID,SEM_SEGMENT,SEM_SMST_SECURITY_ID,SEM_INSTRUMENT_NAME,SEM_EXPIRY_CODE,"
    "SEM_TRADING_SYMBOL,SEM_LOT_UNITS,SEM_CUSTOM_SYMBOL,SEM_EXPIRY_DATE,SEM_STRIKE_PRICE,"
    "SEM_OPTION_TYPE,SEM_TICK_SIZE,SEM_EXPIRY_FLAG,SEM_EXCH_INSTRUMENT_TYPE,SEM_SERIES,"
    "SM_SYMBOL_NAME\n"
)


def test_load_nse_equities(tmp_path: Path) -> None:
    p = tmp_path / "m.csv"
    p.write_text(
        SCRIP_HEADER
        + "NSE,E,10576,EQUITY,,NIFTYBEES,1.0,x,,,,1.0000,,ETF,EQ,x\n"
        + "BSE,E,1,EQUITY,,NIFTYBEES,1.0,x,,,,1.0000,,ETF,EQ,x\n"
        + "NSE,D,2,OPTIDX,,NIFTYBEES,1.0,x,,,,1.0000,,OP,EQ,x\n"
        + "NSE,E,2031,EQUITY,,M&M,1.0,x,,,,10.0000,,ES,EQ,x\n"
    )
    got = load_nse_equities(p, {"NIFTYBEES", "M&M"})
    assert got["NIFTYBEES"].security_id == 10576
    assert got["M&M"].security_id == 2031
    p.write_text(
        SCRIP_HEADER + "NSE,E,1,EQUITY,,A,1,x,,,,1,,ES,EQ,x\nNSE,E,2,EQUITY,,A,1,x,,,,1,,ES,EQ,x\n"
    )
    with pytest.raises(InstrumentError, match="ambiguous"):
        load_nse_equities(p)
