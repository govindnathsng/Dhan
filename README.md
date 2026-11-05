# automator: a safety-first DhanHQ trading automator (personal use)

A small, deliberately boring trading automator for **one personal DhanHQ account**. Scope:
NSE cash segment, CNC (delivery), long-only, limit orders, a stop on every entry.
It runs in **paper mode by default**.

> **Honest note.** This software does not guarantee profit, and profit is not the goal of
> the early versions. The goal is a correct, well-tested system that can lose only a small,
> pre-set amount. Backtests and paper results do not predict live results. Trading involves
> real risk of loss. Every live decision is yours.

## Safety properties (enforced in code and tests)

- **Paper is the default.** Live mode is refused unless every step of the live gate passes.
  The gate arrives in Phase 5; until then live trading is impossible.
- **Invalid config means refuse to start.** This covers unknown keys, duplicate keys, wrong
  types, ambiguous `mode` values (`Live`, `true`, `1` and so on) and anything above a hard
  ceiling. The app never falls back to live.
- **Hard ceilings** in `src/automator/config/ceilings.py` cap every risk limit, whatever the
  YAML says. For example, risk per trade can never exceed 0.5% of the capital cap.
- **v1 policy:** only `NSE_EQ` and `CNC`, only `LIMIT` orders, no shorting, stop-loss required.
  Other values are config errors.
- **No secrets in the repo or logs.** Credentials come only from environment variables. Logs
  pass through a redaction filter (JWTs, bearer tokens, PIN/TOTP, client IDs, Telegram tokens,
  and the literal values of known secret variables). A pre-commit secret scan
  (`detect-secrets`) blocks accidental commits.

## Install

Requires Python 3.11+.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"          # versions pinned in pyproject.toml
# exact, fully pinned environment: pip install -r requirements.lock && pip install -e . --no-deps
pre-commit install               # ruff + secret scan on every commit
```

## Configure

```bash
cp config.example.yaml config.yaml     # config.yaml is gitignored
cp .env.example .env                   # optional; .env is gitignored. Fill values yourself.
automator check-config                 # validates config, shows limits in INR and mode
```

`automator check-config` needs no credentials. It shows only whether each credential
variable is **set** or **not set**, never its value. Config lookup order: `--config PATH`,
then `$AUTOMATOR_CONFIG`, then `./config.yaml`, then the built-in defaults (paper mode).
An explicitly named file that does not exist is an error.

Environment variables (values are never stored in the repo):

| Purpose | Variables |
|---|---|
| Live account (Phase 5 only) | `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN` |
| Dhan sandbox (Phase 3) | `DHAN_SANDBOX_CLIENT_ID`, `DHAN_SANDBOX_ACCESS_TOKEN` |
| Telegram alerts (optional) | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| Live gate step (b) | `DHAN_LIVE_ENABLED` (must be exactly `true`) |

## Run tests and checks

```bash
pytest            # unit tests; never touch the network or real order endpoints
ruff check . && ruff format --check .
mypy
pre-commit run --all-files
```

Sandbox integration tests (Phase 3) are opt-in only: `pytest -m sandbox`. Passing sandbox
tests proves only that the API plumbing works. It says nothing about the strategy.

## Running in paper mode

Phase 0 has only `automator check-config`. The paper run commands
(`automator paper run --once | --schedule`, `automator status`, `automator kill`) arrive in Phase 2.

## Phase roadmap

| Phase | Content | Status |
|---|---|---|
| 0 | Scaffold, strict config + hard ceilings, redaction, CLI skeleton, safety rules | **done, awaiting review** |
| 1 | Instrument master, historical data + offline import, v1 trend strategy, walk-forward backtester + report | not started |
| 2 | Risk engine, order manager, paper simulator, SQLite journal, kill switch, lock, restart safety | not started |
| 3 | Live data feed, order-update WS, Dhan sandbox broker + opt-in tests, Telegram alerts, daily report | not started |
| 4 | Paper-trading gates (`docs/GATES.md`), `automator gate-report`, runbook | not started |
| 5 | Live broker behind the full live gate, only on the owner's request | not started |

Docs: [architecture](docs/ARCHITECTURE.md), [decisions](docs/DECISIONS.md),
[open questions](docs/OPEN_QUESTIONS.md). Agent rules: `.cursor/rules/safety.mdc`.
