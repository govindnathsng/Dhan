from __future__ import annotations

import io
import json
import logging

import pytest

from automator.logging_setup import (
    REDACTED,
    JsonFormatter,
    RedactingFilter,
    RedactingTextFormatter,
    redact,
)

# Obviously fake values built at runtime so no secret-shaped literal sits in the repo.
FAKE_JWT = ".".join(["eyJ" + "a" * 20, "b" * 30, "c" * 25])
FAKE_TG = "1234567890:" + "Z" * 35
FAKE_LONG = "x9" * 25


@pytest.mark.parametrize(
    "text",
    [
        f"token is {FAKE_JWT}",
        f"Authorization: Bearer {FAKE_JWT}",
        f"access-token: {FAKE_JWT}",
        f'{{"access_token": "{FAKE_JWT}"}}',
        f"DHAN_ACCESS_TOKEN={FAKE_JWT}",
        f"telegram {FAKE_TG}",
        f"blob {FAKE_LONG}",
    ],
)
def test_token_like_strings_redacted(text: str) -> None:
    out = redact(text)
    assert REDACTED in out
    assert FAKE_JWT not in out
    assert FAKE_TG not in out
    assert FAKE_LONG not in out


@pytest.mark.parametrize(
    ("text", "secret"),
    [
        ("pin=4321", "4321"),
        ("PIN: 4321", "4321"),
        ('{"pin": "4321"}', "4321"),
        ("totp=987654", "987654"),
        ("password: hunter2", "hunter2"),
        ("client-id: 1100223344", "1100223344"),
        ("DHAN_CLIENT_ID=1100223344", "1100223344"),
        ("TELEGRAM_CHAT_ID=-100998877", "-100998877"),
    ],
)
def test_key_value_secrets_redacted(text: str, secret: str) -> None:
    assert secret not in redact(text)


def test_known_env_values_redacted_anywhere() -> None:
    assert "abc123short" not in redact("weird abc123short value", ["abc123short"])


def test_normal_text_untouched() -> None:
    msg = "placed LIMIT BUY NIFTYBEES qty=3 price=271.35 mode=paper"
    assert redact(msg) == msg


def _logger(fmt: logging.Formatter, secrets: list[str]) -> tuple[logging.Logger, io.StringIO]:
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.addFilter(RedactingFilter(lambda: secrets))
    handler.setFormatter(fmt)
    lg = logging.getLogger(f"test.redact.{id(buf)}")
    lg.handlers = [handler]
    lg.propagate = False
    lg.setLevel(logging.DEBUG)
    return lg, buf


def test_logger_redacts_args_extras_and_tracebacks() -> None:
    marker = "envsecretvalue"
    lg, buf = _logger(JsonFormatter(lambda: [marker]), [marker])
    lg.info("token %s and %s", FAKE_JWT, marker, extra={"hdr": f"Bearer {FAKE_JWT}"})
    try:
        raise RuntimeError(f"failed with access_token={FAKE_JWT} {marker}")
    except RuntimeError:
        lg.exception("boom")
    out = buf.getvalue()
    assert FAKE_JWT not in out
    assert marker not in out
    for line in out.strip().splitlines():
        json.loads(line)


def test_text_formatter_redacts() -> None:
    lg, buf = _logger(RedactingTextFormatter(lambda: []), [])
    lg.warning("pin=1111 %s", FAKE_JWT)
    out = buf.getvalue()
    assert "1111" not in out
    assert FAKE_JWT not in out


def test_redaction_reads_real_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", "plain-env-token-value")
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.addFilter(RedactingFilter())
    handler.setFormatter(JsonFormatter())
    lg = logging.getLogger("test.redact.env")
    lg.handlers = [handler]
    lg.propagate = False
    lg.error("oops plain-env-token-value")
    assert "plain-env-token-value" not in buf.getvalue()
