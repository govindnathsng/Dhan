# automator: a safety-first, AI-assisted DhanHQ trading automator (personal use)

A small, deliberately cautious trading automator for **one personal DhanHQ account**. Scope:
NSE cash segment ETFs and large caps, CNC delivery, long-only, limit orders, a protective stop on
every entry. It runs in **paper mode by default**.

**How it works.** An AI research agent *proposes* trades as JSON. A deterministic risk engine
*disposes*: it sizes, caps or rejects each proposal against hard rupee limits. In live mode, the
human *approves* every order with one Telegram tap. In paper mode the same loop runs automatically.
The AI never holds trading credentials and cannot change limits, the whitelist or config.

> **Honest note.**
> - This software does not guarantee profit, and profit is not the goal of the early versions. The
>   goal is a correct, well-tested system that can lose only a small, pre-set amount.
> - **The AI's trading decisions are unproven.** The AI cannot be honestly backtested, because the
>   model has already seen the historical data. It is judged only by forward paper trading. Only the
>   deterministic shadow baseline is backtested.
> - Backtests and paper results do not predict live results. Trading carries a real risk of loss.
>   Every live decision is yours.

## Safety properties (enforced in code and tests)

- **Paper is the default.** Live mode is refused unless every step of the live gate passes. The
  gate is built in Phase 6; until then live trading is impossible.
- **Invalid config means refuse to start.** This covers unknown keys, duplicate keys, wrong types,
  ambiguous `mode` values, a missing or invalid whitelist, and any value past a hard ceiling or
  floor. The app never falls back to live.
- **Rupee risk profiles** (`paper` Rs 50k, `live_canary` Rs 25k). Code ceilings scale with each
  profile's capital. For example, risk per trade can never exceed 0.5% of capital (Rs 250 / Rs 125).
  Protective settings (minimum net reward-to-risk, stop rules, cooldown, losing-streak pause) can
  only be tightened. See `src/automator/config/ceilings.py` and `docs/DECISIONS.md`.
- **v1 policy:** `NSE_EQ` + `CNC` + `LIMIT` only, no shorting, a protective stop required. Live
  approval is always Telegram; auto-approval in live is not a config option.
- **No secrets in the repo or logs.** Credentials come only from environment variables. Logs go
  through a redaction filter. A pre-commit secret scan (`detect-secrets`) blocks accidental commits.

## Install

Requires Python 3.11+.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"          # direct dependencies pinned in pyproject.toml
# fully pinned alternative: pip install -r requirements.lock && pip install -e . --no-deps
pre-commit install               # ruff + secret scan on every commit
```

## Configure

```bash
cp config.example.yaml config.yaml     # config.yaml is gitignored; it uses config/whitelist.yaml
cp .env.example .env                   # optional; .env is gitignored. Fill values yourself.
automator check-config                 # validates config + whitelist, shows rupee limits and mode
```

- `automator check-config` needs no credentials. It shows only whether each variable is **set** or
  **not set**, never its value.
- It warns if any live-host-only variable is set; those must never be set in the cloud.
- Config lookup order: `--config PATH`, then `$AUTOMATOR_CONFIG`, then `./config.yaml`, then the
  built-in defaults (paper).

| Purpose | Variables |
|---|---|
| Live host only (Phase 6; never in the cloud) | `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN`, `DHAN_LIVE_ENABLED` |
| Cloud paper loop, data endpoints only | `DHAN_DATA_CLIENT_ID`, `DHAN_DATA_ACCESS_TOKEN` |
| Dhan sandbox tests (opt-in) | `DHAN_SANDBOX_CLIENT_ID`, `DHAN_SANDBOX_ACCESS_TOKEN` |
| Telegram alerts and approvals | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_ALLOWED_USER_ID` |

You maintain the instrument whitelist (`config/whitelist.yaml`). It starts with the Nifty 50 plus
four liquid ETFs. The constituent list is marked [verify], so check it against the current index.

## Run tests and checks

```bash
pytest            # unit tests; no network, no LLM, never real order endpoints
ruff check . && ruff format --check .
mypy
pre-commit run --all-files
```

Sandbox integration tests (Phase 3) are opt-in: `pytest -m sandbox`. Passing sandbox tests proves
only that the API plumbing works. It says nothing about the strategy or the AI.

## Running in paper mode

Phase 0 has only `automator check-config`. Phase 1 adds `automator snapshot`,
`automator proposals validate <file>`, `automator paper step`, `automator status` and
`automator kill`. Phase 2 adds the scheduled evening, pre-open and weekly runs.

## Phase roadmap

| Phase | Content | Status |
|---|---|---|
| 0 | Scaffold, strict config with rupee profiles and ceilings, whitelist file, redaction, CLI skeleton, agent safety rules | **done, awaiting review** |
| 1 | Deterministic core: data, calendar, snapshot, costs, proposal schema, claim checker, risk engine, paper simulator, order manager, journal, kill switch, shadow baseline and backtester, fake-AI tests | not started |
| 2 | AI research loop in paper (agent prompts, evening/pre-open/weekly runs, Cursor Automations doc) | not started |
| 3 | Dhan sandbox plumbing and probes, Telegram approval service, live data feed | not started |
| 4 | Daily and weekly reviews, tax export, gate report, GATES.md, RUNBOOK.md | not started |
| 5 | Paper evidence period, 8-12 weeks (process only) | not started |
| 6 | Live mode behind the full gate, only when the owner writes "start Phase 6" | not started |

Docs: [architecture](docs/ARCHITECTURE.md), [decisions](docs/DECISIONS.md),
[open questions](docs/OPEN_QUESTIONS.md). Agent rules: `.cursor/rules/safety.mdc`.
