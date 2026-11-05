"""Structured JSON logging with secret redaction.

Redaction happens twice: a Filter rewrites each record's message, and the
formatter scrubs the final rendered line (covers tracebacks and extra fields).
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Any

from automator.secrets import known_secret_values

REDACTED = "[REDACTED]"

_SENSITIVE_KEYS = (
    r"access[-_ ]?token|token|jwt|pin|totp|otp|password|passwd|secret|api[-_]?key"
    r"|authorization|client[-_ ]?id|bot[-_ ]?token|chat[-_ ]?id|user[-_ ]?id"
)

_PATTERNS: tuple[re.Pattern[str], ...] = (
    # JWT-looking strings (Dhan access tokens are JWTs).
    re.compile(r"eyJ[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]*"),
    # Authorization: Bearer <x>
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-+/=]+"),
    # Telegram bot token: <digits>:<35ish chars>
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_\-]{30,}\b"),
    # Any long opaque token-like run.
    re.compile(r"[A-Za-z0-9_\-+/=]{40,}"),
)

# key=value, key: value, "key": "value", 'key': 'value'
_KV_PATTERN = re.compile(
    r"(?i)(?P<key>[\"']?\b(?:[A-Za-z0-9]+[_\-])*(?:" + _SENSITIVE_KEYS + r")\b[\"']?\s*[:=]\s*)"
    r"(?P<q>[\"']?)(?P<val>[^\s\"',}&]+)(?P=q)"
)


def redact(text: str, extra_values: Iterable[str] = ()) -> str:
    for value in sorted(set(extra_values), key=len, reverse=True):
        if value:
            text = text.replace(value, REDACTED)
    text = _KV_PATTERN.sub(lambda m: f"{m['key']}{m['q']}{REDACTED}{m['q']}", text)
    for pat in _PATTERNS:
        if pat.groups:
            text = pat.sub(lambda m: f"{m.group(1)}{REDACTED}", text)
        else:
            text = pat.sub(REDACTED, text)
    return text


class RedactingFilter(logging.Filter):
    def __init__(self, secret_values: Callable[[], list[str]] = known_secret_values) -> None:
        super().__init__()
        self._secret_values = secret_values

    def filter(self, record: logging.LogRecord) -> bool:
        values = self._secret_values()
        try:
            message = record.getMessage()
        except Exception:  # malformed format args must not leak them raw
            message = str(record.msg)
        record.msg = redact(message, values)
        record.args = None
        if record.exc_info:
            record.exc_text = redact(logging.Formatter().formatException(record.exc_info), values)
            record.exc_info = None
        return True


_STD_ATTRS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {
    "message",
    "asctime",
}


class JsonFormatter(logging.Formatter):
    def __init__(self, secret_values: Callable[[], list[str]] = known_secret_values) -> None:
        super().__init__()
        self._secret_values = secret_values

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_text:
            payload["exc"] = record.exc_text
        elif record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key, value in vars(record).items():
            if key not in _STD_ATTRS and not key.startswith("_"):
                payload[key] = value
        return redact(json.dumps(payload, default=str), self._secret_values())


class RedactingTextFormatter(logging.Formatter):
    def __init__(self, secret_values: Callable[[], list[str]] = known_secret_values) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s: %(message)s")
        self._secret_values = secret_values

    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record), self._secret_values())


def configure_logging(level: str = "INFO", json_format: bool = True) -> None:
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler()
    handler.addFilter(RedactingFilter())
    handler.setFormatter(JsonFormatter() if json_format else RedactingTextFormatter())
    root.addHandler(handler)
    root.setLevel(level)
