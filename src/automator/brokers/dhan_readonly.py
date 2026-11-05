"""Read-only Dhan client. It can NEVER place, modify or cancel orders.

Every request is checked against an explicit (method, endpoint) allowlist before it
reaches the SDK's HTTP layer. Anything else raises ReadOnlyViolationError.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Protocol

READ_ONLY_ENDPOINTS: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("GET", "/profile"),
        ("GET", "/fundlimit"),
        ("GET", "/holdings"),
        ("GET", "/positions"),
        ("GET", "/orders"),
        ("GET", "/ip/getIP"),
        ("GET", "/killswitch"),
        ("POST", "/marketfeed/ltp"),  # data request; POST only because of the payload shape
    }
)

OPEN_ORDER_STATUSES: Final[frozenset[str]] = frozenset({"TRANSIT", "PENDING", "PART_TRADED"})

ERROR_HINTS: Final[dict[str, str]] = {
    "DH-901": "access token invalid or expired: generate a fresh token on web.dhan.co",
    "DH-902": "API access not activated for this account [verify]",
    "DH-903": "account issue (e.g. segment not active) [verify]",
    "DH-904": "rate limit hit: wait and retry later",
    "DH-905": "bad input, or request from a non-whitelisted IP",
    "DH-906": "order error",
    "805": "too many requests or connections (data API)",
    "806": "Data API not subscribed / not active",
}


class ReadOnlyViolationError(Exception):
    pass


class _Http(Protocol):
    def get(self, endpoint: str) -> dict[str, Any]: ...
    def post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class CallResult:
    ok: bool
    data: Any
    error_code: str | None = None
    error_message: str | None = None

    @property
    def hint(self) -> str:
        return ERROR_HINTS.get(self.error_code or "", "")


class DhanReadOnlyClient:
    def __init__(self, client_id: str, access_token: str, http: _Http | None = None) -> None:
        if http is None:
            from dhanhq.dhan_http import DhanHTTP

            http = DhanHTTP(client_id, access_token)
        self._http = http

    def _call(
        self, method: str, endpoint: str, payload: dict[str, Any] | None = None
    ) -> CallResult:
        if (method, endpoint) not in READ_ONLY_ENDPOINTS:
            raise ReadOnlyViolationError(f"{method} {endpoint} is not a read-only endpoint")
        if method == "GET":
            resp = self._http.get(endpoint)
        else:
            resp = self._http.post(endpoint, dict(payload or {}))
        return _to_result(resp)

    def profile(self) -> CallResult:
        return self._call("GET", "/profile")

    def fund_limit(self) -> CallResult:
        return self._call("GET", "/fundlimit")

    def holdings(self) -> CallResult:
        return self._call("GET", "/holdings")

    def positions(self) -> CallResult:
        return self._call("GET", "/positions")

    def orders(self) -> CallResult:
        return self._call("GET", "/orders")

    def registered_ips(self) -> CallResult:
        return self._call("GET", "/ip/getIP")

    def ltp(self, security_ids: list[int]) -> CallResult:
        return self._call("POST", "/marketfeed/ltp", {"NSE_EQ": security_ids})


def _to_result(resp: dict[str, Any]) -> CallResult:
    if resp.get("status") == "success":
        return CallResult(ok=True, data=resp.get("data"))
    remarks = resp.get("remarks")
    code: str | None = None
    message: str | None = None
    if isinstance(remarks, dict):
        raw = remarks.get("error_code")
        code = str(raw) if raw is not None else None
        message = str(remarks.get("error_message") or "") or None
    elif remarks:
        message = str(remarks)[:200]
    data = resp.get("data")
    if code is None and isinstance(data, dict):
        nested = data.get("data")
        inner: dict[str, Any] = nested if isinstance(nested, dict) else data
        for key in inner:
            if str(key) in ERROR_HINTS:
                code = str(key)
                message = str(inner[key])[:200]
    return CallResult(ok=False, data=None, error_code=code, error_message=message)


def parse_ltp(data: Any, security_id: int) -> float | None:
    try:
        value = data["data"]["NSE_EQ"][str(security_id)]["last_price"]
    except (KeyError, TypeError):
        return None
    return float(value) if isinstance(value, int | float) else None
