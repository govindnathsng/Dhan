"""Read-only Dhan connection check: token, Data API, DDPI, funds, holdings, orders, static IP, LTP.

Never places, modifies or cancels anything. Output never contains the token, the full client
ID or balances (only "sufficient: yes/no").
"""

from __future__ import annotations

import ipaddress
import urllib.request
from dataclasses import dataclass
from typing import Any, Literal

from automator.brokers.dhan_readonly import (
    OPEN_ORDER_STATUSES,
    CallResult,
    DhanReadOnlyClient,
    parse_ltp,
)
from automator.data.instruments import Instrument

Status = Literal["PASS", "WARN", "FAIL", "INFO"]
PUBLIC_IP_URL = "https://api.ipify.org"


@dataclass(frozen=True)
class Check:
    name: str
    status: Status
    detail: str


def detect_public_ip(timeout: float = 10.0) -> str | None:
    try:
        with urllib.request.urlopen(PUBLIC_IP_URL, timeout=timeout) as resp:
            text = str(resp.read(64).decode()).strip()
        ipaddress.ip_address(text)
    except (OSError, ValueError):
        return None
    return text


def _fail(name: str, r: CallResult) -> Check:
    code = f" [{r.error_code}]" if r.error_code else ""
    hint = r.hint or (r.error_message or "unknown error")
    return Check(name, "FAIL", f"{hint}{code}")


def _rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return [x for x in data["data"] if isinstance(x, dict)]
    return []


def run_dhan_check(
    client: DhanReadOnlyClient,
    instruments: dict[str, Instrument],
    required_funds_inr: float,
    detected_ip: str | None,
) -> list[Check]:
    checks: list[Check] = []

    prof = client.profile()
    if not prof.ok or not isinstance(prof.data, dict):
        checks.append(_fail("access token", prof))
        return checks
    p = prof.data
    checks.append(Check("access token", "PASS", f"valid until {p.get('tokenValidity', '?')}"))
    cid = str(p.get("dhanClientId", ""))
    checks.append(Check("account", "INFO", f"client ID ending {cid[-4:] if cid else '????'}"))
    segments = str(p.get("activeSegment", ""))
    checks.append(
        Check("equity segment", "PASS", "active")
        if "Equity" in segments
        else Check("equity segment", "FAIL", "Equity segment not active on this account")
    )
    data_plan = str(p.get("dataPlan", ""))
    checks.append(
        Check("Data API plan", "PASS", f"active, valid until {p.get('dataValidity', '?')}")
        if data_plan == "Active"
        else Check("Data API plan", "FAIL", f"dataPlan is {data_plan or 'unknown'}")
    )
    ddpi = str(p.get("ddpi", ""))
    checks.append(
        Check("DDPI", "PASS", "active")
        if ddpi == "Active"
        else Check(
            "DDPI",
            "WARN",
            "not active: resting sell stops on holdings may need TPIN/eDIS each time [verify]",
        )
    )

    funds = client.fund_limit()
    if funds.ok and isinstance(funds.data, dict):
        bal = funds.data.get("availabelBalance", funds.data.get("availableBalance"))
        if isinstance(bal, int | float):
            enough = bal >= required_funds_inr
            checks.append(
                Check(
                    "funds",
                    "PASS" if enough else "WARN",
                    f"available balance {'>=' if enough else '<'} Rs {required_funds_inr:,.0f}",
                )
            )
        else:
            checks.append(Check("funds", "WARN", "balance field missing in response [verify]"))
    else:
        checks.append(_fail("funds", funds))

    hold = client.holdings()
    if hold.ok:
        checks.append(Check("holdings", "INFO", f"{len(_rows(hold.data))} holding(s)"))
    elif "no holding" in (hold.error_message or "").lower():  # [verify] empty-holdings reply
        checks.append(Check("holdings", "INFO", "0 holding(s)"))
    else:
        checks.append(_fail("holdings", hold))

    pos = client.positions()
    if pos.ok:
        open_pos = [r for r in _rows(pos.data) if r.get("netQty") not in (0, None)]
        checks.append(
            Check("open positions", "WARN" if open_pos else "PASS", f"{len(open_pos)} open")
        )
    else:
        checks.append(_fail("open positions", pos))

    orders = client.orders()
    if orders.ok:
        pending = [r for r in _rows(orders.data) if r.get("orderStatus") in OPEN_ORDER_STATUSES]
        checks.append(
            Check("open orders", "WARN" if pending else "PASS", f"{len(pending)} pending")
        )
    else:
        checks.append(_fail("open orders", orders))

    ips = client.registered_ips()
    if ips.ok and isinstance(ips.data, dict):
        registered = [str(ips.data[k]) for k in ("primaryIP", "secondaryIP") if ips.data.get(k)]
        if not registered:
            checks.append(Check("static IP", "FAIL", "none registered: order APIs will be refused"))
        else:
            checks.append(Check("static IP", "PASS", f"registered: {', '.join(registered)}"))
            if detected_ip is not None:
                match = detected_ip in registered
                checks.append(
                    Check(
                        "this machine's IP",
                        "PASS" if match else "FAIL",
                        f"{detected_ip} {'matches' if match else 'does NOT match'} a registered IP",
                    )
                )
    else:
        checks.append(_fail("static IP", ips))

    if instruments:
        ids = [i.security_id for i in instruments.values()]
        ltp = client.ltp(ids)
        if ltp.ok:
            for inst in instruments.values():
                price = parse_ltp(ltp.data, inst.security_id)
                checks.append(
                    Check(f"LTP {inst.symbol}", "PASS", f"Rs {price:,.2f}")
                    if price is not None
                    else Check(f"LTP {inst.symbol}", "FAIL", "no price in response")
                )
        else:
            checks.append(_fail("market data (LTP)", ltp))
    return checks
